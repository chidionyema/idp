"""A lane held longer than a day without moving is retired (idp#5953, defect 5, 6, 11).

The engine held 30 lanes on 2026-10-12: 12 RED, 7 CONFLICT, 10 PENDING, 1 TESTING. Five of the
PENDING lanes were 13-14 days old, and 19 RED/CONFLICT lanes were final and would never move.
None of them could land, and every one of them was in the queue a fresh push waited behind
(measured: a lane pushed 14:29:58 waited 46 minutes for its first batch while successful ticks
ran every ~80s). The reason was honest in the verdict but the queue did not move because the
queue itself was the parking lot.

The fix: a lane held past RETIRE_AFTER_MIN (24 hours) without moving is retired. The branch is
kept (I4: the work is not the engine's to delete), but the lane is removed from state and from
the queue, and the reason is reported once. The next tick sees no such lane until the branch
is re-pushed, which is a new claim with a new `arrived`. A re-push is the only signal an agent
has to say it is still working: a lane held 24 hours without one is not being worked on.

Each test below fails on the pre-change engine: the first four because `_observe_lanes` never
deleted a lane for being old, the next because every `tick` left an unworked lane in state,
and the last because a re-push on a held lane did not reset the timer (there was no timer).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greenlane import engine as E  # noqa: E402

BASE = "m" * 40


class Clock:
    """A backend whose clock the test moves by hand, in minutes."""

    def __init__(self, heads: dict[str, str], minute: float = 1_000.0):
        self.heads = dict(heads)
        self.minute = minute
        self.reported: list[tuple[str, str, str, str]] = []
        self.heartbeats: list[tuple[str, str]] = []
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

    def rebase(self, head: str, onto: str):
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

    def land(self, members, tip) -> None:
        pass


def _engine(be: Clock, st: E.State | None = None) -> E.Engine:
    return E.Engine(be, st if st is not None else E.State(), batch_size=2)


def test_a_lane_held_longer_than_retire_after_min_is_dropped_from_state():
    """The defect: a 13-day-old PENDING lane held the queue a fresh push waited in."""
    st = E.State(lanes={"lane/old": E.Lane("lane/old", "ho", seq=1, arrived=1_000.0)})
    be = Clock({"lane/old": "ho"}, minute=1_000.0 + E.RETIRE_AFTER_MIN + 1)
    eng = _engine(be, st)
    eng.tick()
    assert "lane/old" not in eng.s.lanes, (
        f"a lane held {E.RETIRE_AFTER_MIN + 1} minutes was not retired: {eng.s.lanes}"
    )


def test_a_lane_held_longer_than_retire_after_min_is_reported_once():
    """The reason, once: the agent learns its lane was retired, not a tick-by-tick nag."""
    st = E.State(lanes={"lane/old": E.Lane("lane/old", "ho", seq=1, arrived=1_000.0)})
    # 13 days, matching the 13-14-day-old lanes in refs/greenlane/state on 2026-10-12.
    be = Clock({"lane/old": "ho"}, minute=1_000.0 + 13 * 24 * 60)
    eng = _engine(be, st)
    eng.tick()
    eng.tick()
    eng.tick()
    retirements = [r for r in be.reported if r[0] == "lane/old" and "retired" in r[3]]
    assert len(retirements) == 1, (
        f"a retired lane was reported {len(retirements)} times, expected 1: {retirements}"
    )
    assert retirements[0][2] == E.RED, (
        f"retirement used status {retirements[0][2]!r}, expected RED: {retirements[0]}"
    )
    assert "13 days" in retirements[0][3], (
        f"the reason did not name the age: {retirements[0]!r}"
    )


def test_a_lane_younger_than_retire_after_min_is_not_retired():
    """The bound: a lane held less than RETIRE_AFTER_MIN is still in the queue."""
    st = E.State(
        lanes={"lane/young": E.Lane("lane/young", "hy", seq=1, arrived=1_000.0)}
    )
    be = Clock({"lane/young": "hy"}, minute=1_000.0 + E.RETIRE_AFTER_MIN - 1)
    eng = _engine(be, st)
    eng.tick()
    assert "lane/young" in eng.s.lanes, (
        f"a lane held {E.RETIRE_AFTER_MIN - 1} minutes was retired: {eng.s.lanes}"
    )
    retirements = [r for r in be.reported if r[0] == "lane/young" and "retired" in r[3]]
    assert not retirements, f"a young lane was reported retired: {retirements}"


def test_a_final_red_lane_is_also_retired_so_the_queue_is_shorter():
    """The 19 RED/CONFLICT lanes on 2026-10-12 were final and parked: the queue must drop them too.

    I4 keeps the branch, but the queue a fresh push waits in is the engine's, not the branch's.
    A lane that is RED with a `judged_on` is not retried by retirement (a new head is a new claim
    and gets its own `arrived`); a lane that is RED with no `judged_on` (truly final) has not moved
    and is retired like any other held lane.
    """
    st = E.State(
        lanes={
            "lane/final-red": E.Lane(
                "lane/final-red", "hfr", seq=1, status=E.RED, arrived=1_000.0
            )
        }
    )
    be = Clock({"lane/final-red": "hfr"}, minute=1_000.0 + E.RETIRE_AFTER_MIN + 1)
    eng = _engine(be, st)
    eng.tick()
    assert "lane/final-red" not in eng.s.lanes, (
        f"a final red lane held longer than RETIRE_AFTER_MIN was not retired: {eng.s.lanes}"
    )


def test_a_lane_with_no_arrived_field_migrates_to_the_current_tick():
    """A lane from a state file written before this field existed gets a fresh timer.

    Skipping the migration would let the very lanes the issue is about (the 30 on
    refs/greenlane/state) sit forever: their `arrived` is the dataclass default of 0.0.
    With the migration, they get the same 24-hour grace period a brand-new lane gets,
    and a re-push is the only thing that skips retirement.
    """
    st = E.State(lanes={"lane/legacy": E.Lane("lane/legacy", "hl", seq=1)})
    assert st.lanes["lane/legacy"].arrived == 0.0, (
        "the dataclass default should be 0.0 so a deserialised lane is recognised as legacy"
    )
    be = Clock({"lane/legacy": "hl"}, minute=2_000.0)
    eng = _engine(be, st)
    eng.tick()
    assert "lane/legacy" in eng.s.lanes, (
        f"a legacy lane was retired on its first tick after the fix: {eng.s.lanes}"
    )
    assert eng.s.lanes["lane/legacy"].arrived == 2_000.0, (
        f"the migration did not set arrived to the current tick: {eng.s.lanes['lane/legacy']}"
    )


def test_a_re_pushed_lane_resets_its_retirement_timer():
    """A new head is a new claim: the timer starts over, and the lane is back in the queue.

    Without this, a lane that was legitimately parked while its agent debugged the checks
    would be retired the moment it returned, regardless of how recent the new head was.
    """
    st = E.State(lanes={"lane/x": E.Lane("lane/x", "h1", seq=1, arrived=1_000.0)})
    be = Clock({"lane/x": "h1"}, minute=1_000.0 + E.RETIRE_AFTER_MIN - 10)
    eng = _engine(be, st)
    eng.tick()
    assert "lane/x" in eng.s.lanes, (
        f"a lane held {E.RETIRE_AFTER_MIN - 10} minutes was retired: {eng.s.lanes}"
    )
    # Re-push with a new head, 20 minutes further on.
    be.heads["lane/x"] = "h2"
    be.minute = 1_000.0 + E.RETIRE_AFTER_MIN + 10
    eng.tick()
    assert "lane/x" in eng.s.lanes, f"a re-pushed lane was retired: {eng.s.lanes}"
    assert eng.s.lanes["lane/x"].arrived == be.minute, (
        f"a re-pushed lane did not reset its arrived field: "
        f"arrived={eng.s.lanes['lane/x'].arrived!r}, expected {be.minute!r}"
    )


def test_a_retired_lane_does_not_block_a_fresh_push_from_running():
    """The whole point: the queue a fresh push waits in is shorter.

    Before the fix, the 13-day-old PENDING lane in the state file was the first lane the
    `_start_batch` FIFO list served, so a fresh push sat behind it while every minute that
    passed aged it closer to a checked batch that could never pass. After the fix, the stale
    lane is gone before the first batch is even considered.
    """
    st = E.State(
        lanes={
            "lane/old": E.Lane("lane/old", "ho", seq=1, arrived=1_000.0),
            "lane/new": E.Lane(
                "lane/new", "hn", seq=2, arrived=1_000.0 + E.RETIRE_AFTER_MIN + 100
            ),
        }
    )
    be = Clock(
        {"lane/old": "ho", "lane/new": "hn"},
        minute=1_000.0 + E.RETIRE_AFTER_MIN + 200,
    )
    eng = _engine(be, st)
    eng.tick()
    assert "lane/old" not in eng.s.lanes
    assert "lane/new" in eng.s.lanes
    # The fresh lane was the one pushed; the stale lane was the one removed.
    # The batch that ran is the one on the fresh lane, not on the stale one.
    assert be.candidates, "no batch was pushed: the fresh lane should have run alone"
    assert eng.s.batch is not None, "the batch was not recorded"
    batch_lanes = [m[0] for m in eng.s.batch.members]
    assert "lane/new" in batch_lanes, (
        f"the fresh lane was not in the batch: members={batch_lanes}"
    )
    assert "lane/old" not in batch_lanes, (
        f"the stale lane was in the batch: members={batch_lanes}"
    )
