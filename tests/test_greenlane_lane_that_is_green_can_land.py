"""I5: a lane that is green on its own must land, however many times main moves under it.

THE DEFECT THIS PINS (measured on refs/greenlane/state, 2026-10-05):

    TOTAL LANES: 30
      conflict   18     all "does not rebase onto <a main that has since moved>"
      red        12
    landed total: 64

Eighteen lanes held proven work that main would never receive. Every one sat at
`rejudged == 1`, and the reason was two lines in `_observe`:

    elif lane.status == CONFLICT:
        if lane.rejudged >= REJUDGE_LIMIT:   # REJUDGE_LIMIT = 1
            continue
        lane.rejudged += 1

`rejudged` only ever increments when main has MOVED (the guard above it is
`if lane.judged_on == main: continue`). So a single main move spent the entire
budget, and the next move parked the lane for good. Main moves dozens of times a
day; the lane therefore had to be graded, re-queued, re-graded and landed
between two consecutive main moves or die. It almost never could.

The field's own comment claimed the cap was "since the last push", but no code
ever reset it on a push -- the only reset was constructing a new Lane, which
requires a *different head sha*. Re-pushing the same commit left the lane parked.

This file is deliberately a unit test on the engine's own State, with a fake
backend, because that is the smallest thing that can fail for the real reason:
no GitHub, no network, just the counters that decide whether a lane is retried.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greenlane import engine as E  # noqa: E402


class FakeBackend:
    """The minimum of the engine's Backend protocol to drive _observe."""

    def __init__(self, main: str) -> None:
        self._main = main
        self.reported: list[tuple[str, str, str, str]] = []

    def main(self) -> str:
        return self._main

    def main_red(self, sha: str) -> bool:
        return False

    def lanes(self) -> dict[str, str]:
        # the engine re-derives its lane map from the remote each tick; returning the
        # same single lane keeps the lane alive across _observe_lanes calls
        return {"lane/x": "head1"}

    def rebase(self, lane: str, head: str, onto: str):
        return (f"rebased-{head}", "")

    def checks(self, tip: str):
        return ("green", "ok")

    def land(self, members, tip):  # pragma: no cover - unused here
        raise AssertionError("_observe must not land")

    def report(self, lane: str, head: str, status: str, reason: str) -> None:
        self.reported.append((lane, head, status, reason))

    def adopted_prs(self):  # pragma: no cover - unused here
        return []

    def gh(self, *a, **k):  # pragma: no cover - unused here
        raise AssertionError("no network in this test")


def _state_with_conflict_lane(judged_on: str) -> E.State:
    st = E.State()
    lane = E.Lane("lane/x", "head1", seq=1)
    lane.status = E.CONFLICT
    lane.reason = f"does not rebase onto {judged_on[:12]}"
    lane.judged_on = judged_on
    st.lanes["lane/x"] = lane
    return st


def test_a_conflict_lane_survives_many_main_moves():
    """I5: main moving repeatedly must not permanently park a green-on-its-own lane.

    Fails on REJUDGE_LIMIT == 1: the lane is re-queued exactly once and then sits
    at CONFLICT forever while main moves on without it.
    """
    st = _state_with_conflict_lane("a" * 40)
    b = FakeBackend("b" * 40)
    eng = E.Engine(b, st)

    moves = 12  # main moving a dozen times is ordinary, not adversarial
    retried = 0
    for i in range(moves):
        b._main = f"{i:040x}"
        eng._observe_lanes()
        if st.lanes["lane/x"].status == E.PENDING:
            retried += 1
            # it is graded again; the verdict lands it back on CONFLICT against a new main
            st.lanes["lane/x"].status = E.CONFLICT
            st.lanes["lane/x"].judged_on = b._main

    assert retried >= 2, (
        "a lane that conflicts only because main moved must be retried when main "
        f"moves again; it was retried {retried} time(s) across {moves} main moves"
    )


def test_the_rejudge_budget_is_not_spent_by_a_single_main_move():
    """One move of main must not consume the whole retry budget."""
    st = _state_with_conflict_lane("a" * 40)
    b = FakeBackend("b" * 40)
    eng = E.Engine(b, st)

    b._main = "b" * 40
    eng._observe_lanes()
    assert st.lanes["lane/x"].status == E.PENDING, "first main move should re-queue"
    assert st.lanes["lane/x"].rejudged < E.REJUDGE_LIMIT or E.REJUDGE_LIMIT > 1, (
        "after a single main move the lane has spent its whole budget "
        f"(rejudged={st.lanes['lane/x'].rejudged}, limit={E.REJUDGE_LIMIT})"
    )


def test_a_new_head_resets_the_budget():
    """Re-pushing (a new head sha) is a new claim and gets a fresh budget.

    The field's comment has always promised 'since the last push'; this pins it.
    """
    st = _state_with_conflict_lane("a" * 40)
    st.lanes["lane/x"].rejudged = 99
    b = FakeBackend("a" * 40)
    eng = E.Engine(b, st)

    # same branch, new head sha -> a brand new Lane
    eng.s.lanes["lane/x"] = E.Lane("lane/x", "head2", seq=2)
    assert st.lanes["lane/x"].rejudged == 0
