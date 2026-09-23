"""The scheduler's load gate, with no Dagster import so the rule is testable anywhere.

crew#85, 2026-08-27: a flat max_load 6.0 on a 12-core Mac skipped 3836 ticks in 24h
and ran nothing for 16 hours. The ceiling is max_load_per_core x cores, because
os.getloadavg() counts runnable threads and the same 10.0 is a bored 12-core box
and a drowning 2-core one. An explicit max_load is a deliberate per-job choice and
is honoured as written.
"""

from __future__ import annotations

import os

CORES = os.cpu_count() or 1
LOAD_PER_CORE = float(os.environ.get("ESTATE_MAX_LOAD_PER_CORE", "2.0"))


def load_ceiling(spec: dict, cores: int = CORES) -> float:
    if "max_load" in spec:
        return float(spec["max_load"])
    return float(spec.get("max_load_per_core", LOAD_PER_CORE)) * cores


def load_verdict(label: str, spec: dict, current: float, cores: int = CORES) -> str | None:
    """The skip reason, or None when the job may run."""
    ceiling = load_ceiling(spec, cores)
    if current > ceiling:
        return (f"{label}: load {current:.1f} > {ceiling:.1f} "
                f"({current / cores:.2f} per core, ceiling {ceiling / cores:.2f})")
    return None
