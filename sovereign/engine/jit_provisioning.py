"""Just-in-time compute provisioning (idp#3525 CP2, JIT-01/JIT-02).

JIT-01: "All compute tiers SHALL be point-of-use ... Apple Silicon tiers
SHALL honor the documented 24h minimum per activation (Apple licensing
term, not vendor policy); GPU tiers SHALL be per-second with no floor.
The two SHALL NOT be treated as interchangeable on this axis." ACCEPT:
config declares activation_floor per tier; orchestrator refuses to model
Apple tiers below 24h granularity.

The floors themselves live in platform/llm/cost-ladder.yaml, alongside
the rungs COST-03 already versions -- one file, not a second ladder.
validate_activation_floors() is the refusal: it never repairs a bad
floor, it raises, because a silently-corrected 20h floor is a silent
violation of a term this estate did not set and cannot waive.

JIT-02: "Cold start to first-token SHALL meet a declared latency budget
per tier, or the request SHALL degrade to the next declared lane with
the degradation marked in-trace. Silent stall is a defect." ACCEPT: kill
instance mid-flow -> trace shows DEGRADED marker, response continues
from fallback lane.

call_with_budget() is that boundary: it never lets a slow or failed
primary lane produce a response with no marker. Every return value says
which lane actually answered.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from sovereign.engine import cost_ladder

APPLE_SILICON_FLOOR_MINUTES = (
    1440  # Apple's 24h licensing minimum (S3 §1), not a vendor choice
)
GPU_FLOOR_MINUTES = (
    0  # billed per second; a floor here would misrepresent the vendor's own terms
)


class ActivationFloorError(ValueError):
    """A rung's hardware_class and activation_floor_minutes disagree with
    the term that class is actually bound by."""


def validate_activation_floors(ladder: dict[str, Any] | None = None) -> None:
    """JIT-01's refusal half. Raises on the first rung whose declared
    floor contradicts its hardware_class; does nothing (no return value)
    when every rung is consistent."""
    ladder = ladder or cost_ladder.load_ladder()
    for rung in ladder["rungs"]:
        hardware_class = rung.get("hardware_class")
        floor = rung.get("activation_floor_minutes")
        label = f"rung {rung.get('rung')} ({rung.get('name')})"
        if hardware_class == "apple_silicon":
            if floor is None or floor < APPLE_SILICON_FLOOR_MINUTES:
                raise ActivationFloorError(
                    f"{label}: apple_silicon tier declares "
                    f"activation_floor_minutes={floor!r}, must be >= "
                    f"{APPLE_SILICON_FLOOR_MINUTES} (Apple's 24h licensing minimum)"
                )
        elif hardware_class == "gpu":
            if floor not in (None, GPU_FLOOR_MINUTES):
                raise ActivationFloorError(
                    f"{label}: gpu tier declares activation_floor_minutes={floor!r}, "
                    "gpu tiers are per-second with no floor"
                )


def _rung_by_name(ladder: dict[str, Any], name: str) -> dict[str, Any]:
    for row in ladder["rungs"]:
        if row.get("name") == name:
            return row
    raise cost_ladder.LadderError(f"ladder has no rung named {name!r}")


@dataclass(frozen=True)
class DegradedResult:
    degraded: bool
    lane: str
    value: Any


def call_with_budget(
    tier: str,
    fallback_tier: str,
    work: Callable[[], Any],
    fallback: Callable[[], Any],
    ladder: dict[str, Any] | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> DegradedResult:
    """Attempt `work` on `tier`; degrade to `fallback` on `fallback_tier`
    when `work` raises (an instance killed mid-flow, per JIT-02's own
    fault-injection ACCEPT test) or when it answers slower than that
    tier's declared cold_start_budget_ms. Either way the caller gets an
    explicit DEGRADED marker on the result, never a bare answer that
    hides which lane actually served it -- "silent stall is a defect."
    """
    ladder = ladder or cost_ladder.load_ladder()
    budget_ms = _rung_by_name(ladder, tier)["cold_start_budget_ms"]

    start = clock()
    try:
        value = work()
    except Exception:
        return DegradedResult(degraded=True, lane=fallback_tier, value=fallback())

    elapsed_ms = (clock() - start) * 1000
    if elapsed_ms > budget_ms:
        return DegradedResult(degraded=True, lane=fallback_tier, value=fallback())
    return DegradedResult(degraded=False, lane=tier, value=value)
