"""A claim is stamped once an hour, not once a tick (idp#5953, idp#5951).

`_observe_lanes` heartbeated every lane it held -- one API call each -- at the top of every tick.
`heartbeat` is not a cheap call: measured 2026-10-12 against a real held lane, 1.88s, because it
runs two local `git` invocations to find the lane's claim trailer and then reads that issue's
comments. At the `lanes=29` a surviving tick reported, that is ~55s of an ~85s tick -- and the tick
shares the single `greenlane` concurrency slot with every completion on main, so it is cancelled
more often than it survives (measured: 82 of the last 100 runs). The freshness the call protects is
hourly by the claim gate's own rule (MAX_AGE is two hours), and the backend already refuses to
write a stamp younger than STAMP_AFTER (greenlane/github.py:768) -- but it refuses only AFTER it
has paid for the two git calls and the read that reveal the stamp's age.

So the engine answers that question from its own state: `Lane.stamped`, in minutes on the backend
clock, persisted with the rest of the lane. The lookup is skipped instead of repeated, and only
lanes that can still move are stamped at all -- a red lane and a parked conflict lane are final, so
nothing is waiting on their claims.

Each test below fails on the pre-change engine: the first four because every lane was stamped on
every tick regardless, and the last because the stamping loop ran before the batch was pushed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greenlane import engine as E  # noqa: E402

BASE = "m" * 40


class Cancelled(Exception):
    """The runner's SIGTERM, as the tick experiences it: no further lines, no cleanup."""


class Clock:
    """A backend whose clock the test moves by hand, in minutes."""

    def __init__(
        self, heads: dict[str, str], minute: float = 1_000.0, kill_on: str | None = None
    ):
        self.heads = dict(heads)
        self.minute = minute
        self.kill_on = kill_on
        self.heartbeats: list[tuple[str, str]] = []
        self.reported: list[tuple[str, str, str, str]] = []
        self.candidates: list[str] = []

    # -- Backend protocol ----------------------------------------------------------------
    def now(self) -> float:
        return self.minute

    def main(self) -> str:
        return BASE

    def main_red(self, sha: str) -> bool:
        return False

    def foreign_prs(self):
        return []

    def lanes(self) -> dict[str, str]:
        return dict(self.heads)

    def rebase(self, head: str, onto: str, lane: str = ""):
        return f"{head}@{onto}"

    def unclaimed(self, head: str, base: str) -> str:
        return ""

    def push_candidate(self, batch_id: str, tip: str) -> None:
        self.candidates.append(tip)

    def checks(self, tip: str):
        return ("green", "all green")

    def report(self, lane: str, head: str, status: str, reason: str) -> None:
        self.reported.append((lane, head, status, reason))

    def heartbeat(self, lane: str, head: str) -> None:
        self.heartbeats.append((lane, head))
        if lane == self.kill_on:
            raise Cancelled(f"SIGTERM during {lane}'s heartbeat")

    def land(self, members, tip) -> None:
        pass


def _engine(be: Clock, st: E.State | None = None) -> E.Engine:
    return E.Engine(be, st if st is not None else E.State(), batch_size=2)


def test_the_second_tick_does_not_look_up_a_claim_the_first_one_stamped():
    """The whole cost: the lookup is skipped, not repeated."""
    be = Clock({"lane/x": "hx"})
    eng = _engine(be)
    eng.tick()
    assert be.heartbeats == [("lane/x", "hx")], "the first sight of a lane stamps it"

    be.minute += 10
    eng.tick()
    eng.tick()
    assert be.heartbeats == [("lane/x", "hx")], (
        "a lane stamped ten minutes ago was looked up again: 1.88s per lane per tick"
    )


def test_the_stamp_is_renewed_once_the_hour_is_up():
    """Bound in the other direction: skipping must not mean never stamping again."""
    be = Clock({"lane/x": "hx"})
    eng = _engine(be)
    eng.tick()
    be.minute += E.HEARTBEAT_EVERY_MIN + 1
    eng.tick()
    assert be.heartbeats == [("lane/x", "hx"), ("lane/x", "hx")], be.heartbeats


def test_a_red_lane_is_never_stamped_again():
    """Final: it failed its checks, so its owner re-lanes with a new head and a new claim."""
    st = E.State(
        lanes={"lane/r": E.Lane("lane/r", "hr", status=E.RED, reason="checks failed")}
    )
    be = Clock({"lane/r": "hr"})
    _engine(be, st)._heartbeat_lanes()
    assert be.heartbeats == [], (
        "a red lane's claim was kept alive: its work is not in the queue any more, and nothing "
        "will ever re-test it"
    )


def test_a_parked_conflict_lane_is_never_stamped_again():
    """Final by REJUDGE_LIMIT: it has conflicted through successive mains and is parked (I4)."""
    st = E.State(
        lanes={
            "lane/c": E.Lane(
                "lane/c",
                "hc",
                status=E.CONFLICT,
                reason="does not rebase onto main",
                judged_on=BASE,
                rejudged=E.REJUDGE_LIMIT,
            )
        }
    )
    be = Clock({"lane/c": "hc"})
    _engine(be, st)._heartbeat_lanes()
    assert be.heartbeats == []


def test_a_red_verdict_main_was_responsible_for_is_still_stamped():
    """The exception that must not be caught: that lane is re-judged on a green main (#5618)."""
    st = E.State(
        lanes={
            "lane/r": E.Lane(
                "lane/r", "hr", status=E.RED, reason="main was red", judged_on=BASE
            )
        }
    )
    be = Clock({"lane/r": "hr"})
    _engine(be, st)._heartbeat_lanes()
    assert be.heartbeats == [("lane/r", "hr")]


def test_the_stamp_survives_the_state_round_trip():
    """It only works across ticks because the state is serialised between them."""
    be = Clock({"lane/x": "hx"})
    eng = _engine(be)
    eng.tick()
    assert eng.s.lanes["lane/x"].stamped == be.now()

    again = E.State.loads(eng.s.dumps())
    assert again.lanes["lane/x"].stamped == be.now()
    be.minute += 5
    _engine(be, again)._heartbeat_lanes()
    assert be.heartbeats == [("lane/x", "hx")], (
        "the stamp did not survive the state file"
    )


def test_the_stamp_happens_after_the_batch_has_been_pushed():
    """A tick killed while stamping has already advanced a lane: 55s of an 85s tick is why."""
    be = Clock({"lane/x": "hx"}, kill_on="lane/x")
    eng = _engine(be)
    with pytest.raises(Cancelled):
        eng.tick()
    assert be.candidates, (
        "the tick died in its stamping loop with nothing pushed: the heartbeat used to run "
        "before any batch existed, so a cancellation spent the whole tick on claim stamps"
    )
    assert [r[2] for r in be.reported] == [E.TESTING, E.TESTING], be.reported
    assert be.reported[0][3].startswith("queued"), be.reported[0]
    assert be.reported[-1][3].startswith("testing in b1"), be.reported[-1]
