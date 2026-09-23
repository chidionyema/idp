"""Tests for sovereign/engine/cost_ladder.py (idp#3525 CP1, COST-03).

COST-03's ACCEPT, verbatim: "with simulated traces below band -> no
activation proposal; above -> proposal with computed numbers." Both
halves below, plus the property that the real cost-ladder.yaml shipped
in this repo reproduces the spec's own documented "~58M-233M tok/mo"
figure (docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md,
COST-03) -- so a future edit to either the ladder's prices or the router's
own prices in config.yaml that silently drifts the band out of that
documented range fails this test, not a human re-reading two files.
"""

from __future__ import annotations

from sovereign.engine import cost_ladder


def test_breakeven_band_matches_the_spec_documented_range() -> None:
    low, high = cost_ladder.breakeven_band_tokens(
        flat_rate_usd_per_month=69.0,
        input_cost_per_token=0.0000003,
        output_cost_per_token=0.0000012,
    )
    assert 55_000_000 <= low <= 60_000_000, low
    assert 225_000_000 <= high <= 235_000_000, high


def test_real_ladder_file_loads_and_evaluates() -> None:
    ladder = cost_ladder.load_ladder()
    assert ladder["version"] == 1
    evaluation = cost_ladder.evaluate(tokens_per_month=1_000_000, ladder=ladder)
    assert evaluation.band_low < evaluation.band_high


def test_volume_below_the_band_produces_no_activation_proposal() -> None:
    evaluation = cost_ladder.evaluate(tokens_per_month=1_000_000)
    assert evaluation.activation_proposed is False


def test_volume_above_the_band_produces_a_proposal_with_computed_numbers() -> None:
    evaluation = cost_ladder.evaluate(tokens_per_month=500_000_000)
    assert evaluation.activation_proposed is True
    assert evaluation.band_low > 0
    assert evaluation.band_high > evaluation.band_low
    assert evaluation.flat_rate_usd_per_month == 69.0


def test_volume_inside_the_band_is_still_no_proposal() -> None:
    """The ambiguous middle -- where a real workload's actual input/output
    mix decides whether the lease has actually paid for itself yet -- is
    deliberately "no pre-commitment", not a coin flip."""
    evaluation = cost_ladder.evaluate(tokens_per_month=100_000_000)
    assert evaluation.band_low < 100_000_000 < evaluation.band_high
    assert evaluation.activation_proposed is False


def test_a_non_positive_flat_rate_is_refused() -> None:
    import pytest

    with pytest.raises(cost_ladder.LadderError):
        cost_ladder.breakeven_band_tokens(0.0, 0.0000003, 0.0000012)
