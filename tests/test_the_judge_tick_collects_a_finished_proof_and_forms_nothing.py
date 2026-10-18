"""The judge tick collects a finished proof and forms nothing.

idp#6520, measured 2026-10-18: candidates b3129/b3120/b2967 sat green on their shas for
3h40m, 4h45m and ~20h while the single `greenlane` concurrency slot churned ~90-second
ticks -- the judge kept losing the slot it shares with batch formation. The fix gives the
judge its own group and its own trigger (check_run completed on a queue/* tip), and the
judge tick is `Engine.tick(judge_only=True)`: it lands, bisects or requeues the candidate
the state names, and it must never observe, form, retire, heartbeat or relane -- because
it runs in its own group and is safe to fire on every check completion only as long as it
forms nothing (the 2026-10-17 per-event split failure was two ticks racing batch
formation, b3010..b3012; a judge tick forms nothing, so it cannot reproduce it).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greenlane import engine as E  # noqa: E402

BASE = "m" * 40
TIP = "t" * 40


class World:
    """A green candidate under test; the world a judge tick may and may not touch.

    Every method a judge tick is forbidden to need is counted, so a test fails with a
    number instead of a shrug.
    """

    def __init__(self, verdict: tuple[str, str] = ("green", "")):
        self.verdict = verdict
        self.heads: dict[str, str] = {}  # lane branches the mutator would observe
        self.check_calls = 0
        self.landed: list[str] = []
        self.candidates: list[str] = []
        self.reported: list[tuple[str, str, str, str]] = []
        self.heartbeats: list[str] = []
        self.foreign_calls = 0
        self.pushed_heads: list[tuple[str, str]] = []

    # -- reads the judge is allowed -----------------------------------------------------
    def now(self) -> float:
        return 0.0

    def main(self) -> str:
        return BASE

    def checks(self, tip: str) -> tuple[str, str]:
        self.check_calls += 1
        return self.verdict

    def main_red(self, sha: str) -> bool:
        return False

    def rebase(self, head: str, onto: str):
        return f"{head}@{onto}"

    # -- writes only a collecting tick may make ------------------------------------------
    def land(self, members, tip: str) -> None:
        self.landed.append(tip)

    def report(self, lane, head, status, reason) -> None:
        self.reported.append((lane, head, status, reason))

    # -- writes only a FORMING tick may make; the judge must leave these at zero ----------
    def lanes(self) -> dict[str, str]:
        return dict(self.heads)

    def push_head(self, lane: str, sha: str) -> None:
        self.pushed_heads.append((lane, sha))

    def push_candidate(self, batch_id: str, tip: str) -> None:
        self.candidates.append(tip)

    def foreign_prs(self) -> list[dict]:
        self.foreign_calls += 1
        return []

    def relane(self, pr: dict) -> None:
        raise AssertionError("judge tick must never relane")

    def heartbeat(self, lane: str, head: str) -> None:
        self.heartbeats.append(lane)

    def unclaimed(self, head: str, base: str) -> str:
        return ""


def _state_with_green_batch() -> E.State:
    st = E.State()
    a = E.Lane("lane/a", "ha", seq=1)
    a.status = E.TESTING
    st.lanes["lane/a"] = a
    st.batch = E.Batch("b1", BASE, TIP, [("lane/a", "ha", "ra")], 0.0)
    return st


def test_a_judge_tick_lands_a_green_batch():
    be, st = World(), _state_with_green_batch()
    E.Engine(be, st).tick(judge_only=True)
    assert be.landed == [TIP]
    assert st.lanes["lane/a"].status == E.LANDED
    assert st.lanes["lane/a"].reason == "landed in b1"
    assert st.batch is None
    assert be.check_calls == 1  # exactly one verdict read: the candidate's


def test_a_judge_tick_forms_nothing_when_idle():
    be, st = World(), E.State()  # no batch: nothing to collect
    E.Engine(be, st).tick(judge_only=True)
    assert be.check_calls == 0, "an idle judge must not poll the checks API at all"
    assert be.candidates == [] and be.landed == []


def test_a_judge_tick_never_observes_or_heartbeats():
    be, st = World(), _state_with_green_batch()
    be.heads = {"lane/new": "hn"}  # a fresh lane the mutator would pick up
    E.Engine(be, st).tick(judge_only=True)
    assert "lane/new" not in st.lanes, "judge must not observe lanes into the state"
    assert be.heartbeats == [], "stamping claims is the mutator's maintenance"
    assert be.foreign_calls == 0, "relaning hand-raised PRs is the mutator's job"
    assert be.candidates == [], "a judge tick must never form the next batch"


def test_a_pending_verdict_leaves_the_batch_for_a_later_completion():
    be, st = World(verdict=("pending", "")), _state_with_green_batch()
    E.Engine(be, st).tick(judge_only=True)
    assert st.batch is not None and be.landed == []
    assert st.lanes["lane/a"].status == E.TESTING


def test_a_judge_tick_requeues_when_main_moved_under_the_candidate():
    class Moved(World):
        def main(self) -> str:
            return "n" * 40  # main is no longer the base the candidate was built on

    be, st = Moved(), _state_with_green_batch()
    E.Engine(be, st).tick(judge_only=True)
    assert be.landed == [], "a candidate off its base proves nothing; never land it"
    assert st.batch is None
    assert st.lanes["lane/a"].status == E.PENDING
