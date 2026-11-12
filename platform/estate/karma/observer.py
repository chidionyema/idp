"""KARMA read-only observation kernel: live GitHub runs, never fake debt or yield.

Consumes only existing estate action/CI evidence. Produces deterministic
observations with explicit absence of FLOW/QUAD identity, independent verifier,
model version, cost and actual production yield. No independent ledger.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from collections import Counter

HEX = re.compile(r"^[0-9a-f]{40}$", re.I)
UTC = dt.timezone.utc


def parse_time(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else None


def observe_runs(repo, runs, observed_at):
    """Project run events. Missing evidence is never cast into a false PASS."""
    if not isinstance(runs, list):
        raise ValueError("workflow_runs must be a list")
    now = parse_time(observed_at)
    if now is None:
        raise ValueError("observed_at requires timezone-aware ISO timestamp")
    data = []
    missing = Counter()
    seen = set()
    for run in runs:
        if not isinstance(run, dict):
            missing["INVALID_RUN"] += 1
            continue
        rid = run.get("id")
        if not isinstance(rid, int) or rid <= 0 or rid in seen:
            missing["DUPLICATE_OR_INVALID_RUN_ID"] += 1
            continue
        seen.add(rid)
        created = parse_time(run.get("created_at"))
        started = parse_time(run.get("run_started_at"))
        updated = parse_time(run.get("updated_at"))
        sha = run.get("head_sha")
        state = run.get("status")
        conclusion = run.get("conclusion")
        complete = state == "completed" and conclusion is not None
        if conclusion == "success" and complete:
            verdict = "EXECUTION_REPORTED_SUCCESS_NOT_YIELD"
        elif conclusion in ("failure", "timed_out", "action_required"):
            verdict = "EXECUTION_FAILED"
        elif conclusion in ("cancelled", "skipped", "neutral", "stale"):
            verdict = "NO_EXECUTION_YIELD"
        elif complete:
            verdict = "UNCLASSIFIED_CONCLUSION"
        else:
            verdict = "PENDING_NOT_YIELD"
        gaps = ["UNLINKED_TO_INSTRUCTION", "QUAD_IDENTITY_UNOBSERVED",
                "MODEL_VERSION_UNKNOWN", "BILLED_COST_UNKNOWN",
                "INDEPENDENT_YIELD_UNVERIFIED"]
        if created is None or started is None or updated is None:
            gaps.append("EVENT_TIME_MISSING")
        elif created > now or updated > now:
            gaps.append("CLOCK_ORDER_UNTRUSTED")
        if not isinstance(sha, str) or not HEX.fullmatch(sha):
            gaps.append("SOURCE_SHA_UNKNOWN")
        for gap in gaps:
            missing[gap] += 1
        data.append({
            "run_id": rid,
            "workflow": run.get("name") or "UNKNOWN",
            "repo": repo,
            "actor": ((run.get("actor") or {}).get("login")
                      if isinstance(run.get("actor"), dict) else None) or "UNKNOWN",
            "source_sha": sha if isinstance(sha, str) and HEX.fullmatch(sha) else "UNKNOWN",
            "trigger": run.get("event") or "UNKNOWN",
            "attempt": run.get("run_attempt") if isinstance(run.get("run_attempt"), int) else None,
            "status": state or "UNKNOWN",
            "conclusion": conclusion,
            "verdict": verdict,
            "obligation_id": None,
            "model_provider": "UNKNOWN",
            "model_revision": "UNKNOWN",
            "resource_cost": None,
            "verified_yield": None,
            "timeline": {
                "source_claimed_at": run.get("created_at") if created else None,
                "started_at": run.get("run_started_at") if started else None,
                "source_updated_at": run.get("updated_at") if updated else None,
                "observer_recorded_at": observed_at,
            },
            "evidence_url": run.get("html_url") if str(run.get("html_url") or "").startswith(
                "https://github.com/") else None,
            "gaps": gaps,
        })
    grouped = Counter(item["verdict"] for item in data)
    retries = sum(1 for x in data if (x["attempt"] or 1) > 1)
    return {
        "schema": "karma.observation.v1",
        "kind": "CHRONOS_KARMA_READ_ONLY",
        "recorded_at": observed_at,
        "repo": repo,
        "coverage": {
            "runs_received": len(runs),
            "runs_accepted": len(data),
            "invalid_or_duplicate": len(runs) - len(data),
            "unlinked_to_obligation": missing["UNLINKED_TO_INSTRUCTION"],
            "verified_yield": 0,
            "yield_coverage": "UNKNOWN_NO_INDEPENDENT_OBLIGATION_JOINS",
        },
        "counts_by_execution_outcome": dict(sorted(grouped.items())),
        "rerun_attempts_observed": retries,
        "missing_observations": dict(sorted(missing.items())),
        "runs": data,
        "policy": "NO_SETTLEMENT_OR_REWARD_FROM_GITHUB_CI_ALONE",
        "note": ("A source CI success is neither live production yield nor proof of "
                 "which model caused it. Run cost unknown is NOT free."),
    }
