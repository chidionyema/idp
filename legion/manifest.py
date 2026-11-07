"""Legion manifest loading and validation — discovery as data.

Every legion repo carries a legion.yaml (or legion.json) at its root. The
manifest is the single source of truth an agent reads to learn what a legion
can do, how it runs, what it may cost, and how it proves itself.

Shape (all top-level keys required unless marked optional):

    legion: 3                     # legion number, positive int
    name: army                    # short slug
    repo: agent-foundry           # owning repo
    summary: goal -> DAG of micro-nodes
    capabilities: [dag-execution] # non-empty list of strings
    modes: [in-process, nats-worker]   # subset of VALID_MODES
    budget: {max_usd_per_day: 5}  # hard envelope, positive number
    proof:                        # how this legion proves itself
      command: "python -m pytest tests/test_army.py -q"
      max_seconds: 600            # clamped to <= 3600
    slo:                          # the bar the ranking plane enforces
      success_rate_min: 0.98      # 0..1
      p95_latency_s_max: 300      # seconds
    health:                       # optional dead-man's switch config
      max_heartbeat_age_minutes: 30

Validation is eager and total: every problem is reported, not just the first.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VALID_MODES = frozenset(
    {
        "in-process",
        "nats-worker",
        "temporal",
        "gh-runner",
        "cron",
        "kronos-isolated",
    }
)

MAX_PROOF_SECONDS = 3600  # estate-wide ceiling, shared with pi_bridge/army/cron-run


class ManifestError(ValueError):
    """The manifest could not be parsed at all (bad JSON/YAML, not a mapping)."""


def load_manifest(path: str | Path) -> dict[str, Any]:
    """Load a legion manifest. YAML if pyyaml is importable, JSON otherwise;
    .json files always parse as JSON (JSON is valid YAML anyway)."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ManifestError(
                f"{path}: pyyaml not installed; write the manifest as legion.json "
                f"(JSON is the dependency-free form)"
            ) from exc
        try:
            data = yaml.safe_load(text)
        except Exception as exc:
            raise ManifestError(f"{path}: not parseable YAML - {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError(f"{path}: manifest root must be a mapping")
    return data


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate(manifest: dict[str, Any]) -> list[str]:
    """Return every validation error found; empty list means the manifest is
    fit for indexing into estate-graph."""
    errors: list[str] = []

    legion = manifest.get("legion")
    if not isinstance(legion, int) or isinstance(legion, bool) or legion <= 0:
        errors.append("legion: must be a positive integer")

    for key in ("name", "repo", "summary"):
        if not isinstance(manifest.get(key), str) or not manifest.get(key, "").strip():
            errors.append(f"{key}: must be a non-empty string")

    caps = manifest.get("capabilities")
    if (
        not isinstance(caps, list)
        or not caps
        or not all(isinstance(c, str) and c.strip() for c in caps)
    ):
        errors.append("capabilities: must be a non-empty list of strings")

    modes = manifest.get("modes")
    if not isinstance(modes, list) or not modes:
        errors.append("modes: must be a non-empty list")
    else:
        bad = [m for m in modes if m not in VALID_MODES]
        if bad:
            errors.append(f"modes: unknown {bad}; valid: {sorted(VALID_MODES)}")

    budget = manifest.get("budget")
    if not isinstance(budget, dict) or not _is_num(budget.get("max_usd_per_day")):
        errors.append("budget.max_usd_per_day: must be a number")
    elif budget["max_usd_per_day"] <= 0:
        errors.append("budget.max_usd_per_day: must be positive")

    proof = manifest.get("proof")
    if not isinstance(proof, dict):
        errors.append("proof: must be a mapping with command and max_seconds")
    else:
        if (
            not isinstance(proof.get("command"), str)
            or not proof.get("command", "").strip()
        ):
            errors.append("proof.command: must be a non-empty string")
        ms = proof.get("max_seconds")
        if not _is_num(ms) or ms <= 0:
            errors.append("proof.max_seconds: must be a positive number")
        elif ms > MAX_PROOF_SECONDS:
            errors.append(
                f"proof.max_seconds: {ms} exceeds the estate ceiling {MAX_PROOF_SECONDS}"
            )

    slo = manifest.get("slo")
    if not isinstance(slo, dict):
        errors.append("slo: must be a mapping")
    else:
        sr = slo.get("success_rate_min")
        if not _is_num(sr) or not 0 < sr <= 1:
            errors.append("slo.success_rate_min: must be in (0, 1]")
        p95 = slo.get("p95_latency_s_max")
        if not _is_num(p95) or p95 <= 0:
            errors.append("slo.p95_latency_s_max: must be a positive number")

    health = manifest.get("health")
    if health is not None:
        if not isinstance(health, dict):
            errors.append("health: must be a mapping when present")
        else:
            age = health.get("max_heartbeat_age_minutes")
            if not _is_num(age) or age <= 0:
                errors.append("health.max_heartbeat_age_minutes: must be positive")

    return errors
