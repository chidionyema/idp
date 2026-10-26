"""The voice answers "how much work is left?" with the same estimate the strip shows.

Founder, 2026-10-23: "why not in fleet? is this in face? can we estimate based on goals and
subgoals how much time or work left?" The strip is the visual half and this is the spoken half;
both read claims.claims_glance, and both must say "unknown" WITH the reason when a claim has no
measurable pace, because a spoken number the estate cannot stand behind is the failure this
whole line of work exists to stop.
"""

from __future__ import annotations

import pytest

from fleetview_backend import claims as claims_reader
from fleetview_backend import greenlane, research_feed, spend, voice


@pytest.fixture
def quiet_sources(monkeypatch):
    """Everything else in the block silent, so these assertions are about the claims line."""
    monkeypatch.setattr(greenlane, "cached_snapshot", lambda: None)
    monkeypatch.setattr(spend, "spend_total", lambda: {"measured": False})
    monkeypatch.setattr(research_feed, "research_claims", lambda: {"available": False})
    return monkeypatch


def _snapshot(next_claim):
    return {
        "available": True,
        "read_at": "2026-10-23T21:00:00Z",
        "claims": [
            {
                "agent": "pi",
                "issue": 6999,
                "title": "status: one block",
                "live": True,
                "reason": "live",
                "url": "https://github.com/o/r/issues/6999",
                "subgoals_done": 6,
                "subgoals_total": 8,
                "time_left_s": next_claim,
            }
        ],
    }


def test_the_voice_speaks_the_live_count_and_the_time_left(quiet_sources):
    quiet_sources.setattr(
        claims_reader,
        "claims_snapshot",
        lambda now=None: _snapshot(
            "9m-27m left (6 of 8 closed in 2.0h (this claim's own pace), +/-50%)"
        ),
    )
    block = voice.estate_block()
    assert "CLAIMS: 1 live." in block
    assert "Next: pi on issue 6999" in block
    assert "sub-goals 6/8" in block
    assert "9m-27m left" in block


def test_the_voice_quotes_unknown_rather_than_inventing_hours(quiet_sources):
    quiet_sources.setattr(
        claims_reader,
        "claims_snapshot",
        lambda now=None: _snapshot("unknown -- no pace yet: 0 of 3 closed in 7.2h"),
    )
    block = voice.estate_block()
    assert "unknown -- no pace yet: 0 of 3 closed in 7.2h" in block


def test_no_live_claims_is_a_count_and_the_stale_ones_are_named(quiet_sources):
    quiet_sources.setattr(
        claims_reader,
        "claims_snapshot",
        lambda now=None: {
            "available": True,
            "claims": [],
            "read_at": "2026-10-23T21:00:00Z",
        },
    )
    block = voice.estate_block()
    assert "CLAIMS: 0 live, 0 with a stale heartbeat." in block


def test_an_unreadable_claims_reader_says_nothing_rather_than_zero(quiet_sources):
    quiet_sources.setattr(
        claims_reader,
        "claims_snapshot",
        lambda now=None: {"available": False, "error": "TimeoutError: gh stalled"},
    )
    assert "CLAIMS" not in voice.estate_block()
