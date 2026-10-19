"""Recency and frequency in retrieval ranking (the gap idp#6543 named against Muse).

MAPLE-Guard scores a fact on trust and safety: cosine + rho + tau - harm - taint - scope. It has
no notion of how old a fact is or how often it has proved useful, so a six-month-old note and
yesterday's decision with the same embedding distance tie. This adds both, under three rules:

  1. They ORDER; they never ADMIT. The MAPLE gate (> 0.35) and the cosine floor run on the
     unboosted score. A fact that would be refused is refused however recent or popular it is.
  2. They are bounded. At most RECENCY_WEIGHT + FREQUENCY_WEIGHT (0.08) is added, against a
     cosine range of 0..1, so a clearly nearer fact still beats a merely fresher one.
  3. They cannot run away. Frequency is logarithmic and capped, so a fact retrieved often does not
     crowd out the rest (the rich-get-richer loop a raw access count would create).

Decisions and incidents do not decay: "we chose X" stays true until superseded, and the brief
asks for those kinds whatever their age. Everything else halves its recency weight every
RECENCY_HALF_LIFE_DAYS.

The weights are a starting point, NOT calibrated against live retrieval (the same honesty as
RECALL_MIN_COSINE in main.py). Tune by env var; do not trust the defaults.

Pure stdlib on purpose: main.py needs fastapi and psycopg and cannot be imported by a unit test.
"""

from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from typing import Any, Optional

RECENCY_WEIGHT = float(os.environ.get("MEMORY_RECENCY_WEIGHT", "0.05"))
FREQUENCY_WEIGHT = float(os.environ.get("MEMORY_FREQUENCY_WEIGHT", "0.03"))
RECENCY_HALF_LIFE_DAYS = float(os.environ.get("MEMORY_RECENCY_HALF_LIFE_DAYS", "30"))
# access_count at which the frequency term saturates at its full weight.
FREQUENCY_SATURATION = float(os.environ.get("MEMORY_FREQUENCY_SATURATION", "50"))
# Kinds that are true until superseded, not until they are old.
NON_DECAYING_KINDS = frozenset({"decision", "incident"})


def recency_factor(
    updated_at: Optional[datetime], now: datetime, kind: str = ""
) -> float:
    """1.0 for a fact written just now, halving every half-life; 1.0 always for a decision."""
    if kind in NON_DECAYING_KINDS:
        return 1.0
    if updated_at is None:
        return 0.0
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - updated_at).total_seconds() / 86400.0)
    return 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)


def frequency_factor(access_count: Optional[int]) -> float:
    """0 for a fact never retrieved, rising logarithmically to 1.0 at FREQUENCY_SATURATION."""
    n = max(0, int(access_count or 0))
    if n == 0:
        return 0.0
    return min(1.0, math.log1p(n) / math.log1p(FREQUENCY_SATURATION))


def boost(
    updated_at: Optional[datetime],
    access_count: Optional[int],
    now: datetime,
    kind: str = "",
) -> float:
    """What is added to the MAPLE score to order admitted facts. In [0, 0.08] by default."""
    return RECENCY_WEIGHT * recency_factor(
        updated_at, now, kind
    ) + FREQUENCY_WEIGHT * frequency_factor(access_count)


def kind_of(provenance: Any) -> str:
    """The `kind` that estate_memory.py's remember writes into provenance."""
    return str(provenance.get("kind", "")) if isinstance(provenance, dict) else ""


def rank(scored: list, now: Optional[datetime] = None) -> list:
    """Order already-admitted results by maple_score + boost, best first.

    Each result carries `maple_score`, `recorded_at` (ISO), `access_count` (may be missing) and
    `provenance`. The boost is reported as `rank_boost` so a caller can see why a fact moved.
    """
    now = now or datetime.now(timezone.utc)
    for r in scored:
        try:
            updated = datetime.fromisoformat(r["recorded_at"])
        except (KeyError, TypeError, ValueError):
            updated = None
        b = boost(updated, r.get("access_count"), now, kind_of(r.get("provenance")))
        r["rank_boost"] = round(b, 4)
        r["rank_score"] = round(r["maple_score"] + b, 4)
    return sorted(scored, key=lambda r: r["rank_score"], reverse=True)
