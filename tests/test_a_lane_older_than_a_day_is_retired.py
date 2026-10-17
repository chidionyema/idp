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
is re-pushed: a re-push is the only signal an agent has to say it is still working, and a lane
held 24 hours without one is not being worked on. A re-push of a DIFFERENT head is a new claim
with a new `arrived`; the SAME head coming back -- the branch pruned as landed and pushed straight
back, or a state write that raced another tick -- is the same claim and keeps the clock it had
(`State.timed`).

Each test below fails on the pre-change engine: the first four because `_observe_lanes` never
deleted a lane for being old, the next because every `tick` left an unworked lane in state,
and the last because a re-push on a held lane did not reset the timer (there was no timer).

THE HALF THAT LANDED FIRST WAS NOT ENOUGH (measured 2026-10-16). The retirement itself was one
tick long: `tick` observed the lanes before it retired them, and `_observe_lanes` re-added any
lane whose branch was still on origin with `arrived = now`, overwriting the RED reason with
`queued`. refs/greenlane/state that day held both lanes >=24h old, each with `arrived` stamped
seconds earlier -- so the 24-hour timer restarted on every tick and the queue never shortened.
Swapping those two lines would not have fixed it either (the tick after any retirement re-adds
the lane), so `State.retired` records the retired head and `_observe_lanes` leaves it parked.
The four tests after `test_a_re_pushed_lane_resets_its_retirement_timer` are that half -- and
the measured blast radius was wider than a wasted queue slot: with the test backend's green
verdict the resurrected lane was batched and then LANDED, so a lane whose agent had walked away
could still put its candidate on main, which is the thing the 24-hour rule exists to stop.

AND THE CLOCK ITSELF WAS NOT DURABLE (measured 2026-10-16). `State.retired` made a retirement
outlive its tick, but the timer it reads did not outlive a state wipe: a lane record lost for one
tick came back with `arrived = now`. refs/greenlane/state at 10:11Z held 45 lanes, not one older
than about nine hours, and 33 of them carried heads from 2026-10-01/04, all re-created in a single
pass at 01:10Z (`seq` 1829-1845, contiguous). So `State.timed` records the instant each head was
first timed, and a re-add of a head this engine has already timed keeps that instant: only a NEW
head is a new claim.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

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


def test_a_retired_lane_is_not_resurrected_by_the_tick_after_it():
    """Retirement must outlive the tick that made it, or it is not a retirement (2026-10-16).

    The landed half deleted the lane from state; the tick after put it back -- `arrived` reset
    to now, status back to `queued` -- so the 24-hour timer restarted forever and the queue the
    fresh push waits in never shortened. refs/greenlane/state that day: both lanes >=24h old
    were present, each `arrived` stamped about five minutes earlier.
    """
    st = E.State(lanes={"lane/old": E.Lane("lane/old", "ho", seq=1, arrived=1_000.0)})
    be = Clock({"lane/old": "ho"}, minute=1_000.0 + E.RETIRE_AFTER_MIN + 1)
    eng = _engine(be, st)
    eng.tick()
    assert "lane/old" not in eng.s.lanes
    for _ in range(3):
        be.minute += 5
        eng.tick()
        assert "lane/old" not in eng.s.lanes, (
            f"a retired lane came back on a later tick: {eng.s.lanes['lane/old']}"
        )


def test_the_retired_verdict_is_not_overwritten_by_a_later_tick():
    """The agent's last word on that head is the retirement, not a `queued` line (2026-10-16).

    The retirement reason is the only place an agent learns its lane was parked rather than
    queued, and the resurrecting tick overwrote it about 80 seconds later. The status on the
    head has to keep saying it.
    """
    st = E.State(lanes={"lane/old": E.Lane("lane/old", "ho", seq=1, arrived=1_000.0)})
    be = Clock({"lane/old": "ho"}, minute=1_000.0 + E.RETIRE_AFTER_MIN + 1)
    eng = _engine(be, st)
    eng.tick()
    for _ in range(3):
        be.minute += 5
        eng.tick()
    verdicts = [r for r in be.reported if r[0] == "lane/old" and r[1] == "ho"]
    assert verdicts, "the retirement was never reported"
    lane, head, status, reason = verdicts[-1]
    assert status == E.RED and "retired" in reason, (
        f"the last word on this head is {status} {reason!r}; a retired lane must stay retired"
    )


def test_a_new_head_on_a_parked_lane_is_a_new_claim():
    """A new head is the one thing that revives a parked lane -- and it gets a full timer."""
    st = E.State(lanes={"lane/x": E.Lane("lane/x", "h1", seq=1, arrived=1_000.0)})
    be = Clock({"lane/x": "h1"}, minute=1_000.0 + E.RETIRE_AFTER_MIN + 1)
    eng = _engine(be, st)
    eng.tick()
    assert "lane/x" not in eng.s.lanes, (
        "the lane was not retired, so nothing is being proved"
    )
    # The agent re-pushed its branch with a new commit.
    be.heads["lane/x"] = "h2"
    be.minute += 60
    eng.tick()
    assert "lane/x" in eng.s.lanes, (
        "a new head on a parked lane was not taken as a new claim"
    )
    assert eng.s.lanes["lane/x"].head == "h2"
    assert eng.s.lanes["lane/x"].arrived == be.minute, (
        f"a revived lane did not get a fresh timer: {eng.s.lanes['lane/x']}"
    )
    assert eng.s.retired.get("lane/x") != "h2", "the parked head was not cleared"


def test_the_retirement_outlives_the_state_file():
    """Every tick is a fresh process reading refs/greenlane/state, so the record must serialise.

    A retirement held only in memory would come straight back on the next tick, which reads the
    state file -- the same defect, one layer down.
    """
    st = E.State(lanes={"lane/old": E.Lane("lane/old", "ho", seq=1, arrived=1_000.0)})
    be = Clock({"lane/old": "ho"}, minute=1_000.0 + E.RETIRE_AFTER_MIN + 1)
    eng = _engine(be, st)
    eng.tick()
    reloaded = E.State.loads(eng.s.dumps())
    assert reloaded.retired.get("lane/old") == "ho", (
        f"the retired head did not survive the state file: {reloaded.retired}"
    )
    be.minute += 5
    eng2 = _engine(be, reloaded)
    eng2.tick()
    assert "lane/old" not in eng2.s.lanes, (
        f"the next process re-added the retired lane: {eng2.s.lanes}"
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


def test_a_lane_that_loses_its_record_and_returns_keeps_its_clock():
    """The 24 hours belong to the head, not to the state file (measured 2026-10-16).

    refs/greenlane/state at 10:11Z held 45 lanes and not one of them older than about nine hours,
    while 33 carried heads from 2026-10-01/04: every one of the 33 was re-created in a single pass
    at 01:10Z, so the clock restarted on all of them at once. A lane record is lost for a tick
    whenever `lanes()` prunes the branch of work already on main and `adopted_prs()` pushes it
    back, or two ticks race the state ref -- and the re-add handed the head a brand-new timer,
    which is why `retired` was still empty with a 15-day-old lane in the queue. The state file
    cannot be the clock, or the queue the fresh push waits in is never shortened.
    """
    st = E.State(lanes={"lane/old": E.Lane("lane/old", "ho", seq=1, arrived=1_000.0)})
    be = Clock({"lane/old": "ho"}, minute=1_000.0 + E.RETIRE_AFTER_MIN - 30)
    eng = _engine(be, st)
    eng.tick()
    assert "lane/old" in eng.s.lanes, f"the lane was retired early: {eng.s.lanes}"
    # The record is lost for one tick -- exactly what the wholesale re-add on 2026-10-16 did --
    # and the branch is back on the next tick with the same head.
    be.heads.clear()
    be.minute += 5
    eng.tick()
    assert "lane/old" not in eng.s.lanes, (
        f"a lane whose branch is absent stayed in state: {eng.s.lanes}"
    )
    assert eng.s.timed["lane/old"]["ho"] == 1_000.0, (
        f"the instant that head was first timed was not kept: {eng.s.timed}"
    )
    be.heads["lane/old"] = "ho"
    be.minute += 10
    eng.tick()
    assert "lane/old" in eng.s.lanes, f"the re-added lane was retired: {eng.s.lanes}"
    assert eng.s.lanes["lane/old"].arrived == 1_000.0, (
        f"the clock restarted when the same head came back: {eng.s.lanes['lane/old']}"
    )
    be.minute += E.RETIRE_AFTER_MIN  # the head has now been held well past 24 hours
    eng.tick()
    assert "lane/old" not in eng.s.lanes, (
        f"a head held past RETIRE_AFTER_MIN was never retired: {eng.s.lanes}"
    )


def test_the_clock_survives_the_state_file():
    """Every tick is a fresh process, so the clock has to be in the file (idp#5953)."""
    st = E.State()
    st.timed["lane/x"] = {"h1": 123.0}
    again = E.State.loads(st.dumps())
    assert again.timed == {"lane/x": {"h1": 123.0}}, (
        f"timed did not round-trip through the state file: {again.timed}"
    )
