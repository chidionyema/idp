"""A red lane's retry takes its place in the queue instead of buying a batch of its own.

2026-10-11: `_judge_batch` re-queued a lone red lane with `self.s.queued.insert(0, [name])`, and
`_start_batch` serves `self.s.queued` before the pending list. A lane that had already spent a
full check suite was therefore tested again -- alone -- ahead of every lane that had never been
tested. refs/greenlane/state carried 12 red lanes against 11 pending, and the lane pushed at
14:29:58 waited 46 min for its first batch while successful ticks ran every ~80s and main kept
moving. The lane is set PENDING either way and its `seq` is unchanged, so `seq` order already
retries it near the front; the priority group only gave it a one-lane suite and a place ahead of
newer work.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greenlane import engine as E  # noqa: E402

BASE = "m" * 40


class Red:
    """Every candidate is red, so every lone lane takes the retry path."""

    def __init__(self, heads: dict[str, str]):
        self.heads = dict(heads)
        self.candidates: list[tuple[str, str]] = []
        self.reported: list[tuple[str, str, str, str]] = []

    def now(self) -> float:
        return 0.0

    def main(self) -> str:
        return BASE

    def main_red(self, sha: str) -> bool:
        return False

    def rebase(self, head: str, onto: str, lane: str = ""):
        return f"{head}@{onto}"

    def push_candidate(self, batch_id: str, tip: str) -> None:
        self.candidates.append((batch_id, tip))

    def checks(self, tip: str):
        return ("red", "bdd failure")

    def report(self, lane, head, status, reason) -> None:
        self.reported.append((lane, head, status, reason))

    def unclaimed(self, head: str, base: str) -> str:
        return ""


def _state() -> E.State:
    """`lane/a` is red under test; `lane/b` and `lane/c` have never been tested."""
    st = E.State()
    a = E.Lane("lane/a", "ha", seq=1)
    a.status = E.TESTING
    b = E.Lane("lane/b", "hb", seq=2)
    b.status = E.PENDING
    c = E.Lane("lane/c", "hc", seq=3)
    c.status = E.PENDING
    st.lanes.update({"lane/a": a, "lane/b": b, "lane/c": c})
    st.batch = E.Batch("b1", BASE, "tip", [("lane/a", "ha", "ra")], 0.0)
    return st


def _red_under_test() -> tuple[Red, E.State, E.Engine]:
    be = Red({"lane/a": "ha", "lane/b": "hb", "lane/c": "hc"})
    st = _state()
    return be, st, E.Engine(be, st, batch_size=2)


def test_a_retry_is_a_pending_lane_not_a_priority_group():
    _be, st, eng = _red_under_test()
    eng._judge_batch()
    assert st.lanes["lane/a"].status == E.PENDING
    assert st.lanes["lane/a"].reason == "retry after: bdd failure"
    assert st.queued == [], "a retry must not claim a place ahead of the pending list"


def test_a_retried_lane_shares_the_batch_behind_it_instead_of_running_alone():
    be, st, eng = _red_under_test()
    eng._judge_batch()
    eng._start_batch()
    assert [n for n, _, _ in st.batch.members] == ["lane/a", "lane/b"], (
        "the retry takes its seq place and shares the suite; a one-lane batch for a lane that "
        "already failed is what starved the never-tested lanes behind it"
    )
    assert be.candidates, "the shared batch must still be pushed"


def test_the_retry_budget_is_unchanged():
    """Two re-tests, then RED -- the same budget as before, just not in front of the queue."""
    _be, st, eng = _red_under_test()
    lane = st.lanes["lane/a"]
    for attempt, verdict in ((1, E.PENDING), (2, E.PENDING), (3, E.RED)):
        eng._judge_batch()
        assert (lane.attempts, lane.status) == (attempt, verdict)
        lane.status = E.TESTING
        st.batch = E.Batch(
            f"b{attempt + 1}", BASE, "tip", [("lane/a", "ha", "ra")], 0.0
        )
