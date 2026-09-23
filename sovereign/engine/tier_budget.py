"""Tier-aware candidate volume (idp#3525 CP5, ORCH-02).

"On flat-rate tiers, candidate volume SHALL be governed by a time budget
(generate as many as fit the time box), not a dollar-percentage.
branch.budget_pct is the wrong shape on those tiers." ACCEPT: on a
flat-rate tier, budget_pct is ignored and the time-box is honored; on a
metered tier, the dollar budget is honored. METHOD: property test.

Reuses cost_ladder's hardware_class vocabulary (idp#3525 CP1, COST-03)
instead of inventing a second tier taxonomy: local and apple_silicon
carry zero marginal cost once on, so a dollar-percentage of a budget
that costs nothing per token is not a real constraint there, and volume
is bounded by wall-clock instead; router and gpu carry a real per-token
or per-second marginal cost, so the existing dollar-budget shape still
applies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sovereign.engine import cost_ladder

FLAT_RATE_HARDWARE_CLASSES = frozenset({"local", "apple_silicon"})
METERED_HARDWARE_CLASSES = frozenset({"router", "gpu"})


class TierBudgetError(ValueError):
    """A named tier, or a hardware_class on it, this module does not
    know how to classify -- refused rather than guessed."""


def is_flat_rate(tier: str, ladder: dict[str, Any] | None = None) -> bool:
    """True for a rung whose hardware_class has zero marginal cost once
    activated; False for a metered one. Raises for a rung not on the
    ladder, or a hardware_class neither list has ever named."""
    ladder = ladder or cost_ladder.load_ladder()
    for row in ladder["rungs"]:
        if row.get("name") == tier:
            hardware_class = row.get("hardware_class")
            if hardware_class in FLAT_RATE_HARDWARE_CLASSES:
                return True
            if hardware_class in METERED_HARDWARE_CLASSES:
                return False
            raise TierBudgetError(
                f"tier {tier!r}: unclassified hardware_class {hardware_class!r}"
            )
    raise cost_ladder.LadderError(f"ladder has no rung named {tier!r}")


@dataclass(frozen=True)
class VolumeDecision:
    governed_by: str  # "time_box" (flat-rate) or "budget_pct" (metered)
    candidate_volume: int
    budget_pct_ignored: bool


def resolve_candidate_volume(
    tier: str,
    *,
    time_box_s: int,
    step_s: float,
    budget_usd: float,
    budget_pct: int,
    cost_per_candidate_usd: float,
    ladder: dict[str, Any] | None = None,
) -> VolumeDecision:
    """ORCH-02's ACCEPT, both halves, as one function: which shape governs
    candidate volume depends only on the tier's hardware_class, never on
    which arguments happen to be nonzero."""
    if is_flat_rate(tier, ladder):
        if step_s <= 0:
            raise TierBudgetError(
                "step_s must be positive to fit candidates into a time box"
            )
        n = max(1, int(time_box_s // step_s))
        return VolumeDecision(
            governed_by="time_box", candidate_volume=n, budget_pct_ignored=True
        )
    if cost_per_candidate_usd <= 0:
        raise TierBudgetError(
            "cost_per_candidate_usd must be positive on a metered tier"
        )
    dollars = budget_usd * budget_pct / 100
    n = max(1, int(dollars // cost_per_candidate_usd))
    return VolumeDecision(
        governed_by="budget_pct", candidate_volume=n, budget_pct_ignored=False
    )
