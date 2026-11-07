"""Legion scorecard — ranking is computed, never asserted.

Reads a directory of per-legion metric files (<name>.json), each:

    {"legion": "army", "success_rate": 0.99, "cost_efficiency": 0.8,
     "latency_score": 0.9, "audit_integrity": 1.0, "uptime": 0.99,
     "proof_age_hours": 3}

All components are 0..1. Composite = weighted sum (default weights below,
founder-tunable via --weights). A proof older than PROOF_STALE_HOURS halves
the composite — a legion running on stale evidence is half-trusted by
construction. Below SHADOW_THRESHOLD the legion is demoted to "shadow":
routing avoids it until it proves back in.

Output: a scoreboard JSON, sorted by composite, rank-annotated — the exact
document estate-execute and any agent query before dispatching.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_WEIGHTS = {
    "success_rate": 0.30,
    "cost_efficiency": 0.20,
    "latency_score": 0.20,
    "audit_integrity": 0.15,
    "uptime": 0.15,
}
PROOF_STALE_HOURS = 24.0
SHADOW_THRESHOLD = 0.60
STALE_PROOF_MULTIPLIER = 0.5


class ScorecardError(ValueError):
    pass


def _component(metrics: dict[str, Any], name: str) -> float:
    v = metrics.get(name)
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v <= 1:
        raise ScorecardError(
            f"{metrics.get('legion', '?')}: component {name!r} must be in [0, 1], got {v!r}"
        )
    return float(v)


def score_legion(
    metrics: dict[str, Any], weights: dict[str, float] | None = None
) -> dict[str, Any]:
    """Score one legion's metrics dict. Pure function — the same input always
    yields the same rank, so routing decisions are reproducible."""
    weights = weights or DEFAULT_WEIGHTS
    if abs(sum(weights.values()) - 1.0) > 1e-6:
        raise ScorecardError(f"weights must sum to 1.0, got {sum(weights.values())}")
    if set(weights) != set(DEFAULT_WEIGHTS):
        raise ScorecardError(f"weights must name exactly {sorted(DEFAULT_WEIGHTS)}")

    name = metrics.get("legion")
    if not isinstance(name, str) or not name.strip():
        raise ScorecardError("metrics: 'legion' must be a non-empty string")

    composite = sum(_component(metrics, k) * w for k, w in weights.items())

    proof_age = metrics.get("proof_age_hours")
    stale = False
    if proof_age is not None:
        if not isinstance(proof_age, (int, float)) or proof_age < 0:
            raise ScorecardError(f"{name}: proof_age_hours must be >= 0")
        stale = float(proof_age) > PROOF_STALE_HOURS
    else:
        stale = True  # no proof age reported == no fresh proof == stale
    if stale:
        composite *= STALE_PROOF_MULTIPLIER

    return {
        "legion": name,
        "composite": round(composite, 4),
        "proof_stale": stale,
        "status": "shadow" if composite < SHADOW_THRESHOLD else "active",
        "components": {k: _component(metrics, k) for k in DEFAULT_WEIGHTS},
    }


def build_scoreboard(
    metrics_dir: str | Path, weights: dict[str, float] | None = None
) -> dict[str, Any]:
    """Score every <name>.json in the directory and rank them."""
    d = Path(metrics_dir)
    if not d.is_dir():
        raise ScorecardError(f"{d}: not a directory")
    scored = []
    for f in sorted(d.glob("*.json")):
        scored.append(score_legion(json.loads(f.read_text(encoding="utf-8")), weights))
    scored.sort(key=lambda s: s["composite"], reverse=True)
    for i, s in enumerate(scored, 1):
        s["rank"] = i
    return {
        "weights": weights or DEFAULT_WEIGHTS,
        "shadow_threshold": SHADOW_THRESHOLD,
        "proof_stale_hours": PROOF_STALE_HOURS,
        "legions": scored,
    }
