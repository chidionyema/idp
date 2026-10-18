"""A tick killed while it works still leaves the handover visible on its head (idp#5819).

The tick that observes a lane push shares the single `greenlane` concurrency slot with every
completion on main, so it is cancelled more often than it survives -- measured 2026-10-12 over
the last 100 greenlane runs: 82 cancelled, 8 of them `push` runs (the only trigger a lane push
gets). The backstop meant to cover a lost one is not a five-minute backstop either: the `*/5`
tick fired every 3h16m to 9h41m across its last six runs (#5918).

`_observe_lanes` heartbeat every lane -- one API call each -- before anything had published the
lane, so a run killed inside that loop left the head with no status at all. `gh api
repos/.../commits/<sha>/status` answered nothing, and the agent that pushed could not tell a lane
the engine holds from one it never saw: it waited, or dispatched a tick by hand, or re-pushed.

The lane is now published in the moment the tick sees it, before the per-lane work, and the batch
that picks it up overwrites the line with `testing in <batch> at <tip>` -- so the head carries the
truth as soon as there is a truth to carry, and a cancellation leaves the last known one behind
rather than nothing.

Each test below fails on the pre-change engine: the first two because nothing was written before
the heartbeat, the last two because a line that is rewritten every tick is noise, not a status.
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


class Killed:
    """One lane on origin whose heartbeat never returns -- what a cancelled tick looks like."""

    def __init__(self, heads: dict[str, str], kill_on: str | None = None):
        self.heads = dict(heads)
        self.kill_on = kill_on
        self.events: list[tuple[str, str]] = []
        self.reported: list[tuple[str, str, str, str]] = []
        self.candidates: list[tuple[str, str]] = []

    # -- Backend protocol ----------------------------------------------------------------
    def now(self) -> float:
        return 0.0

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
        self.candidates.append((batch_id, tip))

    def checks(self, tip: str):
        return ("green", "all green")

    def report(self, lane: str, head: str, status: str, reason: str) -> None:
        self.events.append(("report", lane))
        self.reported.append((lane, head, status, reason))

    def heartbeat(self, lane: str, head: str) -> None:
        self.events.append(("heartbeat", lane))
        if lane == self.kill_on:
            raise Cancelled(f"SIGTERM during {lane}'s heartbeat")


def _fresh(kill: bool, head: str = "hx") -> tuple[Killed, E.Engine]:
    be = Killed({"lane/x": head}, kill_on="lane/x" if kill else None)
    return be, E.Engine(be, E.State(), batch_size=2)


def test_a_tick_killed_inside_its_first_loop_still_published_the_lane():
    be, eng = _fresh(kill=True)
    with pytest.raises(Cancelled):
        eng.tick()
    assert be.reported, (
        "the tick died before it said anything, so the head carries no status and the agent "
        "that pushed cannot tell a live lane from a lost one"
    )
    lane, head, status, reason = be.reported[0]
    assert (lane, head, status) == ("lane/x", "hx", E.TESTING)
    assert "queued" in reason and "judged" in reason, (
        f"the line must say what is actually true of the lane right now, not know: {reason!r}"
    )


def test_the_lane_is_published_before_the_per_lane_work():
    """The ordering is the fix: the heartbeat is where the cancellation lands, and it is last.

    idp#5951 moved that loop to the end of the tick -- stamping a claim is maintenance, judging a
    batch and pushing a candidate are the work -- so a tick killed in it has already advanced a
    lane. This test asserts both halves: something was published before the stamp, and the batch
    went out before it too, which is why `events` now ends with the heartbeat rather than being
    exactly report-then-heartbeat.
    """
    be, eng = _fresh(kill=True)
    with pytest.raises(Cancelled):
        eng.tick()
    assert be.events[-1] == ("heartbeat", "lane/x"), be.events
    assert [e for e in be.events if e[0] == "report"], (
        "the tick was killed in the heartbeat with nothing published"
    )
    assert be.candidates, (
        "the stamping loop runs after the batch work now, so a cancellation there leaves the "
        "candidate pushed instead of losing the whole tick to claim stamps"
    )


def test_a_lane_already_known_is_not_republished_every_tick():
    """A status rewritten on every tick is noise; it is written once, on first sight."""
    be, eng = _fresh(kill=False)
    eng._observe_lanes()
    eng._observe_lanes()
    assert [e for e in be.events if e[0] == "report"] == [("report", "lane/x")]


def test_a_lane_repushed_on_a_new_head_is_published_again():
    """A new head is a new claim, and it carries nothing until the engine says so."""
    be, eng = _fresh(kill=False)
    eng._observe_lanes()
    be.heads["lane/x"] = "hy"
    eng._observe_lanes()
    assert [h for _l, h, _s, _r in be.reported] == ["hx", "hy"]


def test_the_batch_that_picks_the_lane_up_replaces_the_line():
    """No stale `queued` line survives the lane being tested: the head ends on the truth."""
    be, eng = _fresh(kill=False)
    eng.tick()
    assert be.candidates, "the lane should have been batched and pushed"
    last = be.reported[-1]
    assert last[:1] == ("lane/x",) and last[2] == E.TESTING
    assert last[3].startswith("testing in "), last
