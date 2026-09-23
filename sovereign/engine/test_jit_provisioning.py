"""Tests for sovereign/engine/jit_provisioning.py (idp#3525 CP2, JIT-01/JIT-02).

JIT-01's ACCEPT, verbatim: "config declares activation_floor per tier;
orchestrator refuses to model Apple tiers below 24h granularity." JIT-02's
ACCEPT, verbatim: "kill instance mid-flow -> trace shows DEGRADED marker,
response continues from fallback lane."
"""

from __future__ import annotations

import copy

import pytest

from sovereign.engine import cost_ladder, jit_provisioning


def test_real_ladder_activation_floors_are_consistent() -> None:
    jit_provisioning.validate_activation_floors()


def test_apple_silicon_tier_below_24h_floor_is_refused() -> None:
    ladder = copy.deepcopy(cost_ladder.load_ladder())
    for rung in ladder["rungs"]:
        if rung["hardware_class"] == "apple_silicon":
            rung["activation_floor_minutes"] = 60  # one hour: not the licensed minimum

    with pytest.raises(jit_provisioning.ActivationFloorError, match="apple_silicon"):
        jit_provisioning.validate_activation_floors(ladder)


def test_gpu_tier_claiming_a_floor_is_refused() -> None:
    ladder = copy.deepcopy(cost_ladder.load_ladder())
    for rung in ladder["rungs"]:
        if rung["hardware_class"] == "gpu":
            rung["activation_floor_minutes"] = (
                1440  # GPU tiers bill per second, not by the day
            )

    with pytest.raises(jit_provisioning.ActivationFloorError, match="gpu"):
        jit_provisioning.validate_activation_floors(ladder)


def test_apple_and_gpu_tiers_are_not_interchangeable_on_this_axis() -> None:
    """JIT-01's own "SHALL NOT be treated as interchangeable" line: the
    two floors this module enforces are different numbers, not the same
    rule applied twice."""
    assert jit_provisioning.APPLE_SILICON_FLOOR_MINUTES == 24 * 60
    assert jit_provisioning.GPU_FLOOR_MINUTES == 0
    assert (
        jit_provisioning.APPLE_SILICON_FLOOR_MINUTES
        != jit_provisioning.GPU_FLOOR_MINUTES
    )


def test_a_fast_successful_primary_call_is_not_degraded() -> None:
    result = jit_provisioning.call_with_budget(
        tier="router_metered",
        fallback_tier="local_free",
        work=lambda: "primary-answer",
        fallback=lambda: "fallback-answer",
    )
    assert result.degraded is False
    assert result.lane == "router_metered"
    assert result.value == "primary-answer"


def test_an_instance_killed_mid_flow_degrades_to_the_fallback_lane_marked() -> None:
    def killed() -> str:
        raise RuntimeError("instance killed mid-flow")

    result = jit_provisioning.call_with_budget(
        tier="flat_rate_apple_silicon",
        fallback_tier="local_free",
        work=killed,
        fallback=lambda: "local-degraded-answer",
    )
    assert result.degraded is True
    assert result.lane == "local_free"
    assert result.value == "local-degraded-answer"


def test_a_primary_call_slower_than_its_budget_degrades_too() -> None:
    ticks = iter([0.0, 999.0])  # first call() reads 0s, second reads 999s elapsed

    result = jit_provisioning.call_with_budget(
        tier="local_free",
        fallback_tier="router_metered",
        work=lambda: "too-slow",
        fallback=lambda: "router-degraded-answer",
        clock=lambda: next(ticks),
    )
    assert result.degraded is True
    assert result.lane == "router_metered"
    assert result.value == "router-degraded-answer"


def test_unknown_tier_name_raises_a_ladder_error() -> None:
    with pytest.raises(cost_ladder.LadderError):
        jit_provisioning.call_with_budget(
            tier="does_not_exist",
            fallback_tier="local_free",
            work=lambda: "unreachable",
            fallback=lambda: "unreachable",
        )
