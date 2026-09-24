"""The /metrics renderer, gated: a gauge must render the turnlog's real numbers, render NaN for
absent (never 0 = "fine"), and preserve the per-voice latency breakdown. Pure functions — no
HTTP, no models, no clock — so the gate is the thing itself, not a synthetic probe."""

from __future__ import annotations

import sys
from pathlib import Path

# Resolve the plugin src dir so `import metrics` works from the test without package machinery.
_SRC = (
    Path(__file__).resolve().parents[1]
    / "backstage"
    / "plugins"
    / "fleetview-backend"
    / "src"
)
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import metrics  # noqa: E402


def _summary(**over):
    base = {
        "turns": 10,
        "empty": 2,
        "errors": 1,
        "empty_rate": 0.2,
        "asr_median_s": 1.5,
        "first_clause_median_s": 0.9,
        "first_clause_p90_s": 2.1,
        "by_voice": {
            "af_heart": {"n": 5, "first_clause_median_s": 0.8},
            "kokoro": {"n": 4, "first_clause_median_s": 1.1},
        },
    }
    base.update(over)
    return base


def test_renders_all_gauges_with_real_values():
    body = metrics.render(_summary())
    assert "voice_turns_total 10.0" in body
    assert "voice_turns_empty_total 2.0" in body
    assert "voice_turns_error_total 1.0" in body
    assert "voice_empty_rate 0.2" in body
    assert "voice_asr_median_seconds 1.5" in body
    assert "voice_first_clause_median_seconds 0.9" in body
    assert "voice_first_clause_p90_seconds 2.1" in body


def test_per_voice_latency_is_a_labeled_gauge():
    body = metrics.render(_summary())
    assert 'voice_clause_latency_median_seconds{voice="af_heart"} 0.8' in body
    assert 'voice_clause_latency_median_seconds{voice="kokoro"} 1.1' in body


def test_absent_values_render_nan_not_zero():
    body = metrics.render({"turns": 0, "empty": 0, "errors": 0})
    assert "voice_turns_total 0.0" in body  # a count of zero turns IS zero
    assert (
        "voice_empty_rate NaN" in body
    )  # but a rate with no denominator is UNKNOWN, not "fine"
    assert "voice_first_clause_median_seconds NaN" in body


def test_every_gauge_has_help_and_type():
    body = metrics.render(_summary())
    for name in (
        "voice_turns_total",
        "voice_empty_rate",
        "voice_first_clause_median_seconds",
    ):
        assert f"# HELP {name}" in body
        assert f"# TYPE {name} gauge" in body


def test_non_numeric_latency_is_treated_as_unknown():
    body = metrics.render(_summary(first_clause_median_s=None))
    assert "voice_first_clause_median_seconds NaN" in body
