"""idp#3525 CP5, ORCH-02 (property test).

Binds sovereign/engine/tier_budget.py against the spec's own ACCEPT
line, verbatim: "on flat-rate tier, budget_pct ignored, time-box
honored; on metered tier, dollar budget honored." Swept as a property
over tier x budget_pct rather than one example each, per the platform's
existing no-hypothesis-dependency convention (sovereign/presence/
test_presence.py): every value in the sweep must hold the same
invariant, not just the one value a single example would pick.
"""

from __future__ import annotations

import pytest

from sovereign.engine.tier_budget import (
    FLAT_RATE_HARDWARE_CLASSES,
    METERED_HARDWARE_CLASSES,
    TierBudgetError,
    is_flat_rate,
    resolve_candidate_volume,
)

_LADDER = {
    "version": 1,
    "rungs": [
        {"rung": 0, "name": "local_free", "hardware_class": "local"},
        {"rung": 1, "name": "router_metered", "hardware_class": "router"},
        {
            "rung": 2,
            "name": "flat_rate_apple_silicon",
            "hardware_class": "apple_silicon",
        },
        {"rung": 3, "name": "gpu_burst_vast_ai", "hardware_class": "gpu"},
    ],
}


def test_the_real_shipped_ladder_classifies_every_rung_as_flat_rate_or_metered() -> (
    None
):
    from sovereign.engine import cost_ladder

    ladder = cost_ladder.load_ladder()
    for row in ladder["rungs"]:
        assert (
            row["hardware_class"]
            in FLAT_RATE_HARDWARE_CLASSES | METERED_HARDWARE_CLASSES
        )


@pytest.mark.parametrize("tier", ["local_free", "flat_rate_apple_silicon"])
def test_flat_rate_tiers_are_flat_rate(tier: str) -> None:
    assert is_flat_rate(tier, _LADDER) is True


@pytest.mark.parametrize("tier", ["router_metered", "gpu_burst_vast_ai"])
def test_metered_tiers_are_not_flat_rate(tier: str) -> None:
    assert is_flat_rate(tier, _LADDER) is False


def test_unknown_tier_is_refused_not_guessed() -> None:
    from sovereign.engine.cost_ladder import LadderError

    with pytest.raises(LadderError):
        is_flat_rate("no-such-tier", _LADDER)


@pytest.mark.parametrize("tier", ["local_free", "flat_rate_apple_silicon"])
@pytest.mark.parametrize("budget_pct", [0, 10, 50, 100])
def test_property_flat_rate_tier_ignores_budget_pct_and_honors_the_time_box(
    tier: str, budget_pct: int
) -> None:
    decision = resolve_candidate_volume(
        tier,
        time_box_s=14400,  # 4h, the spec's own grind ceiling elsewhere
        step_s=600,
        budget_usd=1_000_000,  # deliberately huge: must still not move candidate_volume
        budget_pct=budget_pct,
        cost_per_candidate_usd=0.01,
        ladder=_LADDER,
    )
    assert decision.governed_by == "time_box"
    assert decision.budget_pct_ignored is True
    assert (
        decision.candidate_volume == 24
    )  # 14400 // 600, independent of budget_pct/budget_usd


@pytest.mark.parametrize("tier", ["router_metered", "gpu_burst_vast_ai"])
@pytest.mark.parametrize("budget_pct", [10, 25, 50])
def test_property_metered_tier_honors_the_dollar_budget_and_ignores_the_time_box(
    tier: str, budget_pct: int
) -> None:
    small = resolve_candidate_volume(
        tier,
        time_box_s=1,  # deliberately tiny: must not move candidate_volume
        step_s=600,
        budget_usd=100,
        budget_pct=budget_pct,
        cost_per_candidate_usd=1.0,
        ladder=_LADDER,
    )
    huge_time_box = resolve_candidate_volume(
        tier,
        time_box_s=999_999,
        step_s=600,
        budget_usd=100,
        budget_pct=budget_pct,
        cost_per_candidate_usd=1.0,
        ladder=_LADDER,
    )
    assert small.governed_by == "budget_pct"
    assert small.budget_pct_ignored is False
    assert (
        small.candidate_volume
        == huge_time_box.candidate_volume
        == max(1, int(100 * budget_pct / 100))
    )


def test_metered_tier_requires_a_positive_cost_per_candidate() -> None:
    with pytest.raises(TierBudgetError):
        resolve_candidate_volume(
            "router_metered",
            time_box_s=3600,
            step_s=60,
            budget_usd=100,
            budget_pct=10,
            cost_per_candidate_usd=0,
            ladder=_LADDER,
        )


def test_flat_rate_tier_requires_a_positive_step_s() -> None:
    with pytest.raises(TierBudgetError):
        resolve_candidate_volume(
            "local_free",
            time_box_s=3600,
            step_s=0,
            budget_usd=100,
            budget_pct=10,
            cost_per_candidate_usd=1,
            ladder=_LADDER,
        )
