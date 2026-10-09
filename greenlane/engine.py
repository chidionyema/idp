"""The Greenlane engine: a serial gated trunk (the "not rocket science rule", Rust's bors 2013;
Uber's SubmitQueue, EuroSys'19) with batching and bisection, written so the same code is driven
by an in-memory chaos simulation and by GitHub.

Invariants the engine keeps, and the simulation proves under 500 concurrent lanes:

  I1  main only ever moves to a sha whose required checks all passed at that exact sha.
  I2  nothing but the engine moves main (the backend refuses everyone else).
  I3  a pull request exists only for a lane that is already proven green on top of the current
      main, and it is landed in the same act it is raised: there is never an open red PR.
  I4  no work is lost: a lane that cannot land keeps its branch and carries a reason.
  I5  a lane that is green on its own lands within a bounded number of batches, whatever the
      other lanes do (bisection isolates a red lane instead of blocking the batch forever).

The state is small and serialisable (`State`), because every GitHub tick is a fresh process.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Optional, Protocol

PENDING, TESTING, LANDED, RED, CONFLICT = (
    "pending",
    "testing",
    "landed",
    "red",
    "conflict",
)

DEFAULT_BATCH = (
    8  # lanes stacked into one candidate; a red batch is bisected, never blocked
)
DEFAULT_RETRIES = (
    2  # a lone red lane is re-tested twice before it is called red (flaky checks)
)
DEFAULT_TIMEOUT = (
    90  # minutes a candidate may sit without a verdict before it counts as red
)
REJUDGE_LIMIT = (
    8  # consecutive main moves a CONFLICT lane is re-queued across before it is parked
)


@dataclass
class Lane:
    name: str
    head: str
    status: str = PENDING
    reason: str = ""
    attempts: int = 0
    seq: int = 0  # arrival order; the queue is FIFO by this
    judged_on: str = (
        ""  # main sha a verdict is void against once main moves off it; "" = final
    )
    rejudged: int = (
        0  # CONSECUTIVE failed conflicts against successive mains; not a lifetime cap
    )


@dataclass
class Batch:
    id: str
    base: str  # main sha the candidate was built on
    tip: str  # candidate sha, the one thing under test
    members: list[
        tuple[str, str, str]
    ]  # (lane, head as pushed, head rebased onto the stack)
    started: float  # backend clock, minutes


@dataclass
class State:
    lanes: dict[str, Lane] = field(default_factory=dict)
    batch: Optional[Batch] = None
    queued: list[list[str]] = field(
        default_factory=list
    )  # bisection halves, front first
    seq: int = 0
    landed: int = 0
    candidates: int = 0

    def dumps(self) -> str:
        d = asdict(self)
        return json.dumps(d, sort_keys=True)

    @classmethod
    def loads(cls, text: str) -> "State":
        if not text.strip():
            return cls()
        d = json.loads(text)
        st = cls(
            seq=d.get("seq", 0),
            landed=d.get("landed", 0),
            candidates=d.get("candidates", 0),
        )
        st.lanes = {k: Lane(**v) for k, v in d.get("lanes", {}).items()}
        st.queued = [list(x) for x in d.get("queued", [])]
        if d.get("batch"):
            b = d["batch"]
            st.batch = Batch(
                b["id"],
                b["base"],
                b["tip"],
                [tuple(m) for m in b["members"]],
                b["started"],
            )
        return st


class Backend(Protocol):
    """Everything the engine needs from the world. Every method is a read or an idempotent write."""

    def now(self) -> float: ...  # minutes
    def main(self) -> str: ...  # sha main points to
    def lanes(self) -> dict[str, str]: ...  # lane name -> head sha
    def rebase(
        self, head: str, onto: str
    ) -> Optional[str]: ...  # new sha, or None on conflict
    def push_candidate(
        self, batch_id: str, tip: str
    ) -> None: ...  # starts the checks on `tip`
    def checks(
        self, tip: str
    ) -> tuple[str, str]: ...  # ("pending"|"green"|"red", reason)
    def land(self, members: list[tuple[str, str, str]], tip: str) -> None: ...
    def report(self, lane: str, head: str, status: str, reason: str) -> None: ...
    def main_red(
        self, sha: str
    ) -> bool: ...  # main's own required checks failed at sha
    def foreign_prs(self) -> list[dict]: ...  # open PRs the engine did not raise
    def relane(self, pr: dict) -> None: ...  # close it, keep the branch as a lane
    def unclaimed(
        self, head: str, base: str
    ) -> str: ...  # why head may not land on a claim; "" if it may or cannot be judged


class Engine:
    def __init__(
        self,
        backend: Backend,
        state: State,
        batch_size: int = DEFAULT_BATCH,
        retries: int = DEFAULT_RETRIES,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.b, self.s = backend, state
        self.batch_size, self.retries, self.timeout = batch_size, retries, timeout
        self.log: list[str] = []

    # -- one tick: observe, judge, act; safe to run again at any moment ---------------------
    def tick(self) -> State:
        for pr in self.b.foreign_prs():
            self.b.relane(pr)
            self.log.append(
                f"refused hand-raised PR #{pr.get('number')} -> lane {pr.get('lane')}"
            )
        self._observe_lanes()
        if self.s.batch is not None:
            self._judge_batch()
        if self.s.batch is None:
            self._start_batch()
        return self.s

    def _observe_lanes(self) -> None:
        heads = self.b.lanes()
        for name, head in heads.items():
            lane = self.s.lanes.get(name)
            if lane is None:
                self.s.seq += 1
                self.s.lanes[name] = Lane(name, head, seq=self.s.seq)
            elif lane.head != head:
                self.s.seq += 1
                self.s.lanes[name] = Lane(
                    name, head, seq=self.s.seq
                )  # a new head is a new claim
        for name in list(self.s.lanes):
            if name not in heads:
                del self.s.lanes[name]  # branch gone: nothing to prove
        self.s.queued = [[n for n in grp if n in self.s.lanes] for grp in self.s.queued]
        self.s.queued = [g for g in self.s.queued if g]
        main = self.b.main()
        main_green: Optional[bool] = (
            None  # asked at most once a tick, and only when needed
        )
        for lane in self.s.lanes.values():
            if not lane.judged_on or lane.judged_on == main:
                continue
            if lane.status == RED:
                # it went red while main itself was red, so the verdict says nothing about the
                # lane (2026-09-30: 9 lanes stuck this way); judge it again on a green main
                if main_green is None:
                    main_green = not self.b.main_red(main)
                if not main_green:
                    continue
            elif lane.status == CONFLICT:
                # A lane that is merely BEHIND main is not in conflict with it, and a lane whose
                # conflict is real still deserves to be retried when main moves again -- main
                # moving is the event that can dissolve a conflict, so it must not be the event
                # that ends the retries. This spent the whole budget on the FIRST move
                # (`rejudged >= 1`), because `rejudged` only ever incremented when main moved and
                # was reset nowhere: rg found `rejudged = 0` only in Lane.__init__ and one `+=`.
                # So a lane had to be graded, re-queued, re-graded and landed between two
                # consecutive main moves or be parked for good. Main moves dozens of times a day.
                # I5 says a lane that is green on its own lands within a bounded number of
                # batches; it cannot, if main moving is what parks it.
                #
                # The count is now consecutive: it is cleared the moment the lane leaves CONFLICT
                # (a fresh verdict, a re-push, or a landing), so a lane that recovers is not
                # punished for having conflicted before, and only a lane that conflicts through
                # REJUDGE_LIMIT successive mains is called stuck -- parked with its reason, as I4
                # requires. The reason is now truthful (`does not rebase onto main <sha>`), so a
                # parked lane means what it says.
                if lane.rejudged >= REJUDGE_LIMIT:
                    continue  # I4: genuine conflict; keep the branch, keep the reason
                # It is retried, not yet re-failed: the count is incremented in _start_batch when
                # the grade actually comes back CONFLICT again against main. Incrementing here
                # would charge the lane for a main move it has not even been tested against.
                pass
            else:
                continue
            lane.status, lane.reason, lane.attempts = PENDING, "main moved; retrying", 0

    def _judge_batch(self) -> None:
        b = self.s.batch
        if b is None:
            return
        live = [
            m
            for m in b.members
            if m[0] in self.s.lanes and self.s.lanes[m[0]].head == m[1]
        ]
        if self.b.main() != b.base:
            # I2 says this cannot happen; if it does, the candidate no longer sits on main and
            # nothing it proved is worth anything. Re-queue, never land.
            self.log.append(f"batch {b.id}: main moved under it; requeued")
            self._requeue([m[0] for m in live])
            self.s.batch = None
            return
        if len(live) != len(b.members):
            # a member was re-pushed or withdrawn mid-test: the candidate no longer represents
            # the lanes, so its verdict is void for all of them.
            self.log.append(f"batch {b.id}: member changed under test; requeued")
            self._requeue([m[0] for m in live])
            self.s.batch = None
            return
        verdict, reason = self.b.checks(b.tip)
        if verdict == "pending":
            if self.b.now() - b.started > self.timeout:
                verdict, reason = "red", f"no verdict after {self.timeout:g} min"
            else:
                return
        if verdict == "green":
            try:
                self.b.land(b.members, b.tip)
            except RuntimeError as e:
                # 2026-10-08, b1990..b1992: a land refused after a green candidate used to kill
                # the tick, and the next tick saw the lane head moved (land had pushed the squash
                # over it) and requeued it as new work, uncounted, squashing the squash. A
                # refused land is a red verdict on this batch: it counts against the retries.
                verdict, reason = "red", f"land refused: {e}"
        if verdict == "green":
            for name, head, _ in b.members:
                self.s.lanes[name].status = LANDED
                self.s.lanes[name].reason = f"landed in {b.id}"
                self.b.report(name, head, LANDED, f"landed in {b.id}")
                self.s.landed += 1
            self.log.append(
                f"batch {b.id}: landed {len(b.members)} lane(s) -> main {b.tip}"
            )
            self.s.batch = None
            return
        # red
        if len(b.members) == 1:
            name, head, _ = b.members[0]
            lane = self.s.lanes[name]
            lane.attempts += 1
            if lane.attempts <= self.retries:
                lane.status = PENDING
                lane.reason = f"retry after: {reason}"
                self.s.queued.insert(0, [name])
            else:
                lane.status, lane.reason = RED, reason
                # main red under it: the verdict says nothing about the lane (2026-09-30)
                if self.b.main_red(b.base):
                    lane.judged_on = b.base
                self.b.report(name, head, RED, reason)
            self.log.append(
                f"batch {b.id}: {name} red ({reason}); attempts={lane.attempts}"
            )
        else:
            half = len(b.members) // 2
            first, second = (
                [m[0] for m in b.members[:half]],
                [m[0] for m in b.members[half:]],
            )
            self.s.queued[0:0] = [first, second]
            for name in first + second:
                self.s.lanes[name].status = PENDING
            self.log.append(
                f"batch {b.id}: red, bisected into {len(first)}+{len(second)}"
            )
        self.s.batch = None

    def _requeue(self, names: list[str]) -> None:
        for n in names:
            if n in self.s.lanes and self.s.lanes[n].status == TESTING:
                self.s.lanes[n].status = PENDING
                # left the parked state (or was mid-test): its conflict count is consecutive,
                # so it starts again from zero. Only a lane that conflicts through
                # REJUDGE_LIMIT successive mains is genuinely stuck.
                self.s.lanes[n].rejudged = 0
        if names:
            self.s.queued.insert(0, names)

    def _held(self, lane: Lane, base: str) -> bool:
        """A lane that does not land on a live claim waits outside the batch (idp#5612).

        claim-gate in ci-success refuses it anyway, but only after the batch has run: PR #5606
        spent b2181 that way, and its batch-mates waited on the verdict. It stays PENDING, so
        the CLAIM comment that fixes it is enough -- the next tick admits it, no re-push. The
        reason is reported once, not every tick.
        """
        why = self.b.unclaimed(lane.head, base)
        if not why:
            return False
        if lane.reason != why:
            lane.reason = why
            self.b.report(lane.name, lane.head, RED, why)
        return True

    def _start_batch(self) -> None:
        base = self.b.main()
        if self.s.queued:
            names = self.s.queued.pop(
                0
            )  # bisection halves were admitted with their batch
        else:
            pend = sorted(
                (l for l in self.s.lanes.values() if l.status == PENDING),
                key=lambda l: l.seq,
            )
            names = []
            for l in pend:
                if len(names) == self.batch_size:
                    break
                if not self._held(l, base):
                    names.append(l.name)
        names = [
            n for n in names if n in self.s.lanes and self.s.lanes[n].status == PENDING
        ]
        if not names:
            return
        tip, members = base, []
        for n in names:
            lane = self.s.lanes[n]
            # First: does this lane apply to MAIN? That is the only question CONFLICT may answer.
            #
            # This loop used to ask `rebase(lane.head, tip)` FIRST, with tip accumulating every
            # batch-mate accepted before it, and brand the lane CONFLICT when that returned None.
            # A lane that rebases perfectly onto main but overlaps a sibling in the SAME batch
            # was therefore called "does not rebase onto {tip}" -- the batch-mate's sha, which no
            # human or engine recognises as main -- and `judged_on` was set to `base`, so
            # _observe_lanes believed it had been judged against main and would only retry when
            # main moved. Parked, permanently, at REJUDGE_LIMIT=1. Measured on
            # refs/greenlane/state 2026-10-05: 18 of 30 lanes sat exactly there, holding proven
            # work main never received; the mic fix 51eca9766 was one of them and landed only
            # after a hand rebase. The reason string read like staleness, which is why it was
            # misdiagnosed as "main moved" for so long: by the time anyone read the sha, it was
            # an ancestor of a later main.
            #
            # So the two questions are asked separately, and answered honestly:
            #   rebase(head, base) is None -> the lane does not apply to main. CONFLICT, judged
            #                                 against main, exactly as judged_on says.
            #   rebase(head, tip)  is None -> it applies to main but not alongside the batch-mate
            #                                 already ahead of it. That is a batch-order collision,
            #                                 not a conflict with main: leave it PENDING so it gets
            #                                 its own batch, and it lands on the next tick.
            if self.b.rebase(lane.head, base) is None:
                # Genuine conflict with main. Charge the retry HERE, where the grade actually
                # failed, so the count is consecutive failures against successive mains and not
                # merely the number of times main happened to move past the lane.
                lane.rejudged += 1
                lane.status, lane.reason = (
                    CONFLICT,
                    f"does not rebase onto main {base[:12]}",
                )
                lane.judged_on = base
                self.b.report(n, lane.head, CONFLICT, lane.reason)
                continue
            new = self.b.rebase(lane.head, tip)
            if new is None:
                # batch-order collision: main would take it, a batch-mate would not. Not a
                # conflict -- it stays PENDING and is tried again, on its own if need be.
                self.log.append(
                    f"batch: {n} applies to main {base[:12]} but not after {tip[:12]}; "
                    "deferring to its own batch"
                )
                continue
            members.append((n, lane.head, new))
            tip = new
        if not members:
            return
        self.s.candidates += 1
        bid = f"b{self.s.candidates}"
        self.b.push_candidate(bid, tip)
        for n, head, _ in members:
            self.s.lanes[n].status = TESTING
            self.s.lanes[n].reason = f"testing in {bid}"
            self.b.report(n, head, TESTING, f"testing in {bid} at {tip[:12]}")
        self.s.batch = Batch(bid, base, tip, members, self.b.now())
        self.log.append(
            f"batch {bid}: {len(members)} lane(s) on {base[:12]} -> candidate {tip[:12]}"
        )
