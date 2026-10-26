"""A count is not a measurement: every row carries the age its `state` was derived from.

The founder's false "12 agents running" was a board counting rows whose `state` said running, and
`state` is a recency heuristic -- nothing in this estate inspects a process. The fix is not a
better guess at liveness; it is sending the measurement (how long ago the session last wrote) and
the window the guess was made over, so the interface can print both and the reader can judge.

These grade the three facts that make the label checkable:
  1. `age_seconds` is on every row and is None, not 0, when the timestamp is missing or garbage.
  2. The window travels in the envelope, so a page cannot print a bare "running".
  3. The window is read from one place (`ESTATE_FRESH_RUNNING_MINUTES`), so the sentence and the
     derivation cannot drift apart.
"""

from __future__ import annotations

import datetime as dt

from fleetview_backend import routes, sessions


def _row(updated_at):
    return {
        "session_id": "sb-1",
        "runtime": "sovereign",
        "task": "fix the board",
        "state": "running",
        "updated_at": updated_at,
    }


def test_the_window_the_backend_calls_running_is_a_named_number(monkeypatch):
    monkeypatch.delenv("ESTATE_FRESH_RUNNING_MINUTES", raising=False)
    # 15 minutes is the backend's own default (sessions.py). It is asserted here, not copied into
    # the frontend, so a change to the default is a change a test notices.
    assert sessions.fresh_running_minutes() == 15.0

    monkeypatch.setenv("ESTATE_FRESH_RUNNING_MINUTES", "45")
    assert sessions.fresh_running_minutes() == 45.0


def test_the_window_follows_the_derivation_rather_than_a_second_constant(monkeypatch):
    # One source: the public function and the private one the derivation uses agree, so a page that
    # prints the window and a row that was labelled by it cannot disagree.
    monkeypatch.setenv("ESTATE_FRESH_RUNNING_MINUTES", "7")
    assert sessions.fresh_running_minutes() == sessions._fresh_running_minutes()


def test_an_age_is_measured_from_the_timestamp_it_was_given():
    now = dt.datetime(2026, 10, 26, 12, 0, tzinfo=dt.timezone.utc)
    assert sessions._age_seconds("2026-10-26T11:00:00Z", now) == 3600
    assert sessions._age_seconds("2026-10-26T11:59:30Z", now) == 30


def test_an_unmeasured_age_is_none_never_zero():
    now = dt.datetime(2026, 10, 26, 12, 0, tzinfo=dt.timezone.utc)
    # A missing or unreadable timestamp is an absence of evidence. Zero would render as "just
    # wrote", which is the same lie as a green dot over a session nobody knows about.
    assert sessions._age_seconds(None, now) is None
    assert sessions._age_seconds("", now) is None
    assert sessions._age_seconds("not-a-date", now) is None


def test_a_clock_skewed_timestamp_is_not_a_negative_age():
    now = dt.datetime(2026, 10, 26, 12, 0, tzinfo=dt.timezone.utc)
    # Some harnesses write a local timestamp; reading it as the future must not print "-3600s ago".
    assert sessions._age_seconds("2026-10-26T13:00:00Z", now) == 0


def test_every_row_carries_the_age_its_state_was_derived_from(monkeypatch):
    stamp = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=5)).isoformat()
    monkeypatch.setattr(
        sessions,
        "_estate_db_sessions",
        lambda now=None: [_row(stamp), _row(None)],
    )
    rows, unreachable = sessions.list_all_sessions()
    assert unreachable == []
    assert len(rows) == 2
    # Measured for the row that has a timestamp; None -- never 0 -- for the row that does not.
    assert 240 <= rows[0]["age_seconds"] <= 360
    assert rows[1]["age_seconds"] is None


def test_the_envelope_carries_the_window_so_no_label_can_be_bare(monkeypatch):
    monkeypatch.setenv("ESTATE_FRESH_RUNNING_MINUTES", "25")
    # Patch the adapter, not list_all_sessions: the age stamping is the thing under test here, and
    # stubbing it out would grade the stub.
    monkeypatch.setattr(sessions, "_estate_db_sessions", lambda now=None: [_row(None)])
    envelope, status = routes.sessions_envelope()
    assert status == 200
    assert envelope["fresh_window_minutes"] == 25.0
    # The rows travel with the evidence, in the same response that names the window.
    assert envelope["sessions"][0]["age_seconds"] is None


def test_an_unreadable_fleet_still_reports_the_window_it_would_have_used(monkeypatch):
    def boom():
        raise RuntimeError("estate.db is locked")

    monkeypatch.setattr(sessions, "list_all_sessions", boom)
    envelope, status = routes.sessions_envelope()
    assert status == 503
    assert "estate.db is locked" in envelope["error"]
    # Not a liveness claim, and not silence either: the page can still say what window it would
    # have counted over once the source answers.
    assert envelope["fresh_window_minutes"] == sessions.fresh_running_minutes()
