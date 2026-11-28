"""Age alone never retires a lane; only a final verdict does, and it keeps its reason (idp#5618).

Measured 2026-11-28 on origin: 129 of 153 `lane/*` refs carried `refused: retired, this lane head
is N days old`. None had landed, 72 added at least one file main does not have (53,006 lines), and
the status no longer said why any of them could not land. The session that pushed a lane is gone
long before 24 hours pass, so a rule that waits for a re-push parks the work with no owner.

`Engine.final` already names the lanes that can never move (RED with no `judged_on`, CONFLICT
past REJUDGE_LIMIT), and only PENDING lanes are selected for a batch, so a final lane leaving the
queue is the whole of what idp#5953 needed. These tests fail on the engine that retired by age.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from greenlane import engine as E  # noqa: E402
from test_a_lane_older_than_a_day_is_retired import Clock, _engine  # noqa: E402

THIRTY_DAYS = 30 * 24 * 60


def test_a_thirty_day_old_pending_lane_is_still_in_the_queue():
    """Known-bad for the old rule: age was the verdict, and the lane left state unjudged."""
    st = E.State(lanes={"lane/old": E.Lane("lane/old", "ho", seq=1, arrived=1_000.0)})
    be = Clock({"lane/old": "ho"}, minute=1_000.0 + THIRTY_DAYS)
    eng = _engine(be, st)
    eng.tick()
    assert "lane/old" not in eng.s.retired, f"retired by age alone: {eng.s.retired}"
    retirements = [r for r in be.reported if "retired" in r[3]]
    assert not retirements, f"a pending lane was reported retired: {retirements}"


def test_a_retired_final_lane_keeps_the_reason_it_could_not_land():
    """The status is the only thing a later agent reads: it must still name the cause."""
    why = "red: fast-gate / fast-gate failure"
    lane = E.Lane("lane/red", "hr", seq=1, status=E.RED, reason=why, arrived=1_000.0)
    be = Clock({"lane/red": "hr"}, minute=1_000.0 + E.RETIRE_AFTER_MIN + 1)
    eng = _engine(be, E.State(lanes={"lane/red": lane}))
    eng.tick()
    retirements = [r for r in be.reported if r[0] == "lane/red" and "retired" in r[3]]
    assert len(retirements) == 1, f"expected one retirement report: {be.reported}"
    assert why in retirements[0][3], f"the cause was overwritten: {retirements[0][3]!r}"


def test_a_final_lane_past_the_bound_still_leaves_the_queue():
    """Known-good: the half of idp#5953 that was right is kept."""
    lane = E.Lane(
        "lane/red", "hr", seq=1, status=E.RED, reason="red: x", arrived=1_000.0
    )
    be = Clock({"lane/red": "hr"}, minute=1_000.0 + E.RETIRE_AFTER_MIN + 1)
    eng = _engine(be, E.State(lanes={"lane/red": lane}))
    eng.tick()
    assert "lane/red" not in eng.s.lanes
    assert eng.s.retired.get("lane/red") == "hr"
