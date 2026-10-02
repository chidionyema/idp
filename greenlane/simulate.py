"""Chaos simulation of the Greenlane: the mess the estate makes today, at 500 lanes, against the
real engine. A commit is a chain of changes; a tree is the set of changes reachable; the checks
are a function of the tree, so "green" is a fact about a sha, exactly as on GitHub.

What the chaos does, every tick, with the given probabilities:
  - lanes are cut from a stale main (any point in history), the way worktrees are
  - some changes are broken on their own (red alone)
  - some pairs of changes are incompatible (green alone, red together: the semantic conflict a
    per-PR CI never sees)
  - some changes touch the same file as another lane (the rebase conflict)
  - agents re-push a lane while it is under test, force-push, and delete lanes
  - agents raise pull requests by hand and try to push main directly
  - a bot lane (flux/image-updates) bumps continuously
  - checks are flaky: a green tree is reported red with probability p_flaky (never the reverse:
    a check that passes on a broken tree is a missing test, and no queue can repair that)

`run()` returns the invariant report; the test asserts on it.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Optional

from .engine import CONFLICT, LANDED, RED, Engine, State


def _sha(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:40]


@dataclass
class Change:
    id: str
    files: frozenset
    broken: bool


@dataclass
class Commit:
    sha: str
    parent: Optional[str]
    change: Optional[str]  # change id, None for the root


@dataclass
class Report:
    lanes: int
    ticks: int
    landed: int
    red: int
    conflict: int
    still_open: int
    deleted_by_agents: int
    candidates: int
    main_history: int
    main_ever_red: int
    direct_push_attempts: int
    direct_push_succeeded: int
    hand_prs: int
    hand_prs_refused: int
    open_red_pr_observations: int
    work_lost: int
    good_lanes_not_landed: int
    broken_lanes_landed: int
    log_tail: list = field(default_factory=list)


class ChaosBackend:
    def __init__(self, rng: random.Random, p_flaky: float, ci_ticks: int):
        self.rng, self.p_flaky, self.ci_ticks = rng, p_flaky, ci_ticks
        self.clock = 0.0
        self.commits: dict[str, Commit] = {}
        self._trees: dict[str, frozenset] = {}
        self.changes: dict[str, Change] = {}
        self.incompatible: set[frozenset] = set()
        root = Commit(_sha("root"), None, None)
        self.commits[root.sha] = root
        self._main = root.sha
        self.main_history = [root.sha]
        self.lane_heads: dict[str, str] = {}
        self.candidates: dict[
            str, tuple[str, float]
        ] = {}  # tip -> (batch id, pushed at)
        self.verdicts: dict[
            tuple[str, str], tuple[str, str]
        ] = {}  # (batch id, tip) -> verdict
        self.prs: list[dict] = []  # every PR that ever existed
        self.statuses: dict[str, tuple[str, str, str]] = {}
        self.direct_push_attempts = self.direct_push_succeeded = 0
        self.hand_prs = self.hand_prs_refused = 0
        self.landed_changes: set[str] = set()

    # -- the world -------------------------------------------------------------------------
    def tree(self, sha: str) -> frozenset:
        t = self._trees.get(sha)
        if t is None:
            c = self.commits[sha]
            parent = self.tree(c.parent) if c.parent else frozenset()
            t = parent | {c.change} if c.change else parent
            self._trees[sha] = t
        return t

    def truly_green(self, sha: str) -> bool:
        t = self.tree(sha)
        if any(self.changes[c].broken for c in t):
            return False
        return not any(pair <= t for pair in self.incompatible)

    def commit(self, parent: str, change: str) -> str:
        sha = _sha(parent, change)
        self.commits.setdefault(sha, Commit(sha, parent, change))
        return sha

    def changes_since(self, sha: str, base: str) -> list[str]:
        base_tree = self.tree(base)
        return [c for c in self.tree(sha) if c not in base_tree]

    # -- Backend protocol --------------------------------------------------------------------
    def now(self) -> float:
        return self.clock

    def main(self) -> str:
        return self._main

    def lanes(self) -> dict[str, str]:
        return dict(self.lane_heads)

    def rebase(self, head: str, onto: str) -> Optional[str]:
        mine = self.changes_since(head, onto)
        theirs = self.changes_since(onto, head)
        touched = (
            set().union(*(self.changes[c].files for c in theirs)) if theirs else set()
        )
        for c in mine:
            for f in self.changes[c].files & touched:
                # same file is not always the same hunk: a deterministic third of overlaps conflict
                if int(_sha(c, f)[:4], 16) % 3 == 0:
                    return None
        tip = onto
        for c in reversed(mine):
            tip = self.commit(tip, c)
        return tip

    def push_candidate(self, batch_id: str, tip: str) -> None:
        self.candidates[tip] = (batch_id, self.clock)

    def checks(self, tip: str) -> tuple[str, str]:
        # a verdict belongs to one run: re-testing the same sha in a later batch is a new run
        # (on GitHub a push to a new queue/<id> ref starts a new workflow run for the same sha)
        bid, pushed = self.candidates[tip]
        if (bid, tip) in self.verdicts:
            return self.verdicts[(bid, tip)]
        if self.clock - pushed < self.ci_ticks:
            return "pending", ""
        green = self.truly_green(tip)
        if green and self.rng.random() < self.p_flaky:
            v = ("red", "flaky: test-x failed")
        elif green:
            v = ("green", "")
        else:
            v = ("red", "bdd failed")
        self.verdicts[(bid, tip)] = v
        return v

    def main_red(self, sha: str) -> bool:
        return not self.truly_green(sha)

    def land(self, members, tip: str) -> None:
        # the tested sha becomes main by fast-forward; a PR per lane is raised on the rebased
        # head and is merged by that same move (its head is an ancestor of main).
        verdict = self.verdicts.get((self.candidates[tip][0], tip))
        if not verdict or verdict[0] != "green":
            raise RuntimeError("land() without a green verdict")
        if not self._is_ancestor(self._main, tip):
            raise RuntimeError("land() not a fast-forward")
        for name, _head, rebased in members:
            self.prs.append(
                {
                    "lane": name,
                    "head": rebased,
                    "raised_by": "engine",
                    "green_at_raise": True,
                    "merged": True,
                }
            )
            self.landed_changes.update(self.changes_since(rebased, self._main))
            self.lane_heads.pop(name, None)  # delete_branch_on_merge
        self._main = tip
        self.main_history.append(tip)

    def report(self, lane: str, head: str, status: str, reason: str) -> None:
        self.statuses[lane] = (head, status, reason)

    def foreign_prs(self) -> list[dict]:
        return [p for p in self.prs if p["raised_by"] != "engine" and p.get("open")]

    def relane(self, pr: dict) -> None:
        pr["open"] = False
        pr["refused"] = True
        self.hand_prs_refused += 1
        self.lane_heads.setdefault(pr["lane"], pr["head"])

    # -- what the platform refuses ------------------------------------------------------------
    def agent_pushes_main(self, sha: str) -> None:
        self.direct_push_attempts += 1
        # the `update` ruleset: only the engine's App may move main. Refused, always.
        return

    def agent_raises_pr(self, lane: str, head: str) -> None:
        self.hand_prs += 1
        self.prs.append(
            {
                "lane": lane,
                "head": head,
                "raised_by": "agent",
                "open": True,
                "green_at_raise": self.truly_green(head),
                "merged": False,
            }
        )

    def _is_ancestor(self, anc: str, sha: str) -> bool:
        cur = sha
        while cur is not None:
            if cur == anc:
                return True
            cur = self.commits[cur].parent
        return False


def run(
    lanes: int = 500,
    seed: int = 0,
    ticks: int = 2500,
    p_broken: float = 0.08,
    p_incompatible: float = 0.02,
    p_file_overlap: float = 0.03,
    p_repush: float = 0.01,
    p_delete: float = 0.0003,
    p_hand_pr: float = 0.02,
    p_direct_push: float = 0.01,
    p_flaky: float = 0.03,
    ci_ticks: int = 3,
    batch_size: int = 8,
    arrivals_per_tick: int = 25,
    bot_lane_every: int = 4,
    reload_state: bool = False,
) -> Report:
    rng = random.Random(seed)  # noqa: S311 -- a simulation, not a secret
    b = ChaosBackend(rng, p_flaky, ci_ticks)
    st = State()
    eng = Engine(b, st, batch_size=batch_size, timeout=ci_ticks * 40)
    files = [f"f{i}" for i in range(200)]
    created = 0
    arrived = 0
    names_created: set = set()
    open_red_pr_obs = 0
    all_changes: list[str] = []

    def new_lane(name: str, base_sha: str, n_changes: int = 1) -> str:
        nonlocal created
        tip = base_sha
        for _ in range(n_changes):
            cid = f"c{len(b.changes)}"
            fs = frozenset(rng.sample(files, k=rng.choice([1, 1, 2, 3])))
            b.changes[cid] = Change(cid, fs, rng.random() < p_broken)
            if all_changes and rng.random() < p_incompatible:
                other = rng.choice(all_changes)
                b.incompatible.add(frozenset((cid, other)))
            all_changes.append(cid)
            tip = b.commit(tip, cid)
        b.lane_heads[name] = tip
        names_created.add(name)
        created += 1
        return tip

    for t in range(ticks):
        b.clock = float(t)
        # arrivals, cut from a stale main (a worktree from any point in history)
        if arrived < lanes:
            for _ in range(min(arrivals_per_tick, lanes - arrived)):
                base = (
                    rng.choice(b.main_history[-30:])
                    if rng.random() < 0.7
                    else rng.choice(b.main_history)
                )
                new_lane(
                    f"lane/a{arrived}", base, n_changes=rng.choice([1, 1, 1, 2, 4])
                )
                arrived += 1
        if (
            bot_lane_every
            and t % bot_lane_every == 0
            and "flux/image-updates" not in b.lane_heads
        ):
            new_lane("flux/image-updates", b.main())
        # chaos on live lanes
        for name in list(b.lane_heads):
            r = rng.random()
            if r < p_delete:
                del b.lane_heads[name]
            elif r < p_delete + p_repush:
                base = rng.choice(b.main_history)
                new_lane(name, base)  # force-push from another stale base
            elif r < p_delete + p_repush + p_hand_pr:
                b.agent_raises_pr(name, b.lane_heads[name])
            elif r < p_delete + p_repush + p_hand_pr + p_direct_push:
                b.agent_pushes_main(b.lane_heads[name])
        if reload_state:
            # a GitHub tick is a fresh process: the state must survive JSON and back, every tick
            st = State.loads(st.dumps())
            log = eng.log
            eng = Engine(b, st, batch_size=batch_size, timeout=ci_ticks * 40)
            eng.log = log
        eng.tick()
        # the observation the founder makes after the platform has handled the event: an open
        # PR that is red, or any open PR at all (the engine merges what it raises in the same act,
        # and refuses what it did not raise)
        for p in b.prs:
            if p.get("open"):
                open_red_pr_obs += 1
        agent_lanes = [n for n in b.lane_heads if n != "flux/image-updates"]
        if (
            arrived >= lanes
            and st.batch is None
            and all(
                b.statuses.get(n, ("", "", ""))[1] in (RED, CONFLICT)
                for n in agent_lanes
            )
        ):
            break

    agent_names = sorted(n for n in names_created if n != "flux/image-updates")
    landed = red = conflict = still_open = deleted = 0
    for n in agent_names:
        status = b.statuses.get(n, ("", "", ""))[1]
        if n in b.lane_heads:
            if status == RED:
                red += 1
            elif status == CONFLICT:
                conflict += 1
            else:
                still_open += 1
        elif status == LANDED:
            landed += 1
        else:
            deleted += 1
    main_ever_red = sum(1 for s in b.main_history if not b.truly_green(s))
    # work lost: a lane head that was neither landed nor kept as a branch with a reason
    work_lost = 0
    for name in list(b.lane_heads):
        # a lane the platform judged must carry its reason; a lane it has not judged yet is
        # pending or testing, never silent
        st_ = b.statuses.get(name)
        if (
            st_ is None
            and name in st.lanes
            and st.lanes[name].status not in ("pending", "testing")
        ):
            work_lost += 1
        if st_ is not None and st_[1] in (RED, CONFLICT) and not st_[2]:
            work_lost += 1
    good_not_landed = 0
    broken_landed = 0
    for cid, ch in b.changes.items():
        if ch.broken and cid in b.tree(b.main()):
            broken_landed += 1
    for name, (head, status, _reason) in b.statuses.items():
        if (
            status == RED
            and name in b.lane_heads
            and b.truly_green(b.rebase(b.lane_heads[name], b.main()) or head)
            and b.rebase(b.lane_heads[name], b.main()) is not None
        ):
            good_not_landed += 1
    return Report(
        lanes=lanes,
        ticks=t + 1,
        landed=landed,
        red=red,
        conflict=conflict,
        still_open=still_open,
        deleted_by_agents=deleted,
        candidates=st.candidates,
        main_history=len(b.main_history),
        main_ever_red=main_ever_red,
        direct_push_attempts=b.direct_push_attempts,
        direct_push_succeeded=b.direct_push_succeeded,
        hand_prs=b.hand_prs,
        hand_prs_refused=b.hand_prs_refused,
        open_red_pr_observations=open_red_pr_obs,
        work_lost=work_lost,
        good_lanes_not_landed=good_not_landed,
        broken_lanes_landed=broken_landed,
        log_tail=eng.log[-5:],
    )


if __name__ == "__main__":  # pragma: no cover
    import sys

    r = run(
        lanes=int(sys.argv[1]) if len(sys.argv) > 1 else 500,
        seed=int(sys.argv[2]) if len(sys.argv) > 2 else 0,
    )
    for k, v in r.__dict__.items():
        print(f"{k:28} {v}")
