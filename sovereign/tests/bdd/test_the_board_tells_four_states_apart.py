"""The board must tell FOUR states apart, not draw one amber dot twenty-two times.

A council of three independent frontier models, asked to design this interface, converged without
coordination on the same finding: an agent that has not emitted for ten minutes is not one state
but four, and the interface's whole value is discriminating them. One of them put it as the
worst mistake in every agent dashboard it had seen -- "uniform running state", because "collapsing
thinking/waiting/stuck/finished into one green dot means the CEO cannot triage".

MEASURED on the running board before this existed: 22 of 23 agents rendered as one identical
amber dot, and a session stuck in a retry loop was labelled `running`.

WHY A DERIVATION AND NOT A CSS PASS. `state` is running/paused/stopped from elapsed time alone,
and elapsed time is IDENTICAL for an agent thinking hard and an agent wedged. So the four states
are derived from evidence the estate records -- recency plus the body of work behind the row --
and this suite pins every boundary, because a state that flips on the wrong side of a threshold is
a node that lies about what it is doing.

THE HONEST LIMIT, stated here so it is not mistaken for a gap: an outside reader cannot see a long
inference mid-flight. A session that wrote inside the running window is reported as `thinking` and
nothing finer is claimed. The alternative -- inventing a "reasoning" signal nobody measures -- is
the same offence as the green dot.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SESSIONS = REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "sessions.py"


@pytest.fixture()
def sessions(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate.db"))
    spec = importlib.util.spec_from_file_location("sessions_under_test", SESSIONS)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sessions_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _ts(mod, minutes_ago: float) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    return (now - dt.timedelta(minutes=minutes_ago)).isoformat()


def _act(mod, minutes_ago, events):
    now = dt.datetime.now(dt.timezone.utc)
    return mod._activity_from_evidence(
        _ts(mod, minutes_ago), events, None, "paused", now
    )


def test_recent_writing_is_thinking(sessions):
    assert _act(sessions, 0, 183) == "thinking"
    assert _act(sessions, 14, 183) == "thinking", "inside the 15m running window"


def test_silence_with_a_body_of_work_behind_it_is_stuck(sessions):
    """The state the old board did not have, and the one that matters most.

    183 events then silence is a session that HAD been producing and stopped. Calling that
    `running` is the mistake all three models named.
    """
    assert _act(sessions, 16, 183) == "stuck"
    assert _act(sessions, 1380, 50) == "stuck"  # 23h, still inside the live window


def test_silence_with_almost_nothing_behind_it_is_waiting(sessions):
    """A session that never got going is blocked, not stuck.

    Accusing a healthy session of being stuck is worse than being slow to say so, which is why the
    threshold sits low -- but it is real, and this pins both sides of it.
    """
    assert _act(sessions, 16, 1) == "waiting"
    assert _act(sessions, 16, 9) == "waiting"
    assert _act(sessions, 16, 10) == "stuck", (
        "the threshold is exact and this is its edge"
    )


def test_past_the_live_window_is_finished(sessions):
    assert _act(sessions, 25 * 60, 183) == "finished"


def test_no_timestamp_is_unknown_never_thinking(sessions):
    """A node that breathes when nobody knows whether it is alive is the same lie as a green dot."""
    now = dt.datetime.now(dt.timezone.utc)
    assert sessions._activity_from_evidence(None, 5, None, "unknown", now) == "unknown"
    assert sessions._activity_from_evidence("", 5, None, "unknown", now) == "unknown"
    assert (
        sessions._activity_from_evidence("not-a-date", 5, None, "unknown", now)
        == "unknown"
    )


def test_a_clock_skewed_row_is_not_in_the_future(sessions):
    """A timestamp ahead of now clamps to 0 seconds, never a negative age."""
    now = dt.datetime.now(dt.timezone.utc)
    ahead = (now + dt.timedelta(minutes=5)).isoformat()
    assert (
        sessions._activity_from_evidence(ahead, 10, None, "running", now) == "thinking"
    )


def test_every_state_is_one_of_the_four_or_unknown(sessions):
    """No fifth value can appear: the UI draws one motion per state and has no branch for more."""
    allowed = {"thinking", "waiting", "stuck", "finished", "unknown"}
    now = dt.datetime.now(dt.timezone.utc)
    for mins in (0, 5, 15, 16, 60, 1439, 1441, 10000):
        for n in (0, 1, 9, 10, 100, 10000):
            got = sessions._activity_from_evidence(
                _ts(sessions, mins), n, None, "paused", now
            )
            assert got in allowed, f"{mins}m/{n} events gave {got!r}"


def test_the_stuck_threshold_is_configurable(monkeypatch, tmp_path):
    """LAW 46: a threshold is config, not a literal in behaviour."""
    monkeypatch.setenv("ESTATE_STUCK_MIN_EVENTS", "2")
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "e.db"))
    spec = importlib.util.spec_from_file_location("s2", SESSIONS)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["s2"] = mod
    spec.loader.exec_module(mod)
    assert mod._STUCK_MIN_EVENTS == 2
    assert _act(mod, 16, 2) == "stuck", "with the threshold at 2, two events is enough"
