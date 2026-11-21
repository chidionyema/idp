#!/usr/bin/env python3
"""Prototype: evidence-gated, multi-objective decision operator.

This is NOT a trained model of any person's intelligence. It is a minimal
falsifiable executable approximation to a set of observed founder corrections.
No network, models, accounts, credentials, or estate permissions are accessed.

Usage: python3 founder_method.py cases.json
"""
from __future__ import annotations
import hashlib
import json
import math
import sys
from typing import Any

REQUIRED = {"id", "mode", "authority", "budget", "custody", "capacity",
            "verifier", "recoverable", "evidence", "cost", "risk", "unlocks", "learns"}
STATUSES = {"VERIFIED", "UNKNOWN", "DENIED"}


def validate(c: dict[str, Any]) -> None:
    missing = REQUIRED - c.keys()
    if missing:
        raise ValueError(f"{c.get('id', '<missing>')}: missing {sorted(missing)}")
    if c["mode"] not in ("PROBE", "EFFECT"):
        raise ValueError(f"{c['id']}: invalid mode")
    for key in ("authority", "budget", "custody", "capacity", "verifier", "recoverable", "evidence"):
        if c[key] not in STATUSES:
            raise ValueError(f"{c['id']}: invalid {key} status")
    for key in ("cost", "risk"):
        if type(c[key]) not in (int, float) or not math.isfinite(c[key]) or c[key] < 0:
            raise ValueError(f"{c['id']}: invalid {key}")
    for key in ("unlocks", "learns"):
        if not isinstance(c[key], list) or any(not isinstance(v, str) or not v for v in c[key]):
            raise ValueError(f"{c['id']}: invalid {key}")


def assess(c: dict[str, Any]) -> list[str]:
    """Identify vetoes; existence of a feature or a file is not a live proof."""
    validate(c)
    fail = []
    if c["authority"] != "VERIFIED":
        fail.append("AUTHORITY_NOT_VERIFIED")
    if c["budget"] != "VERIFIED":
        fail.append("BUDGET_NOT_VERIFIED")
    if c["mode"] == "EFFECT":
        for key, reason in (("custody", "NO_DURABLE_CUSTODY"),
                            ("capacity", "WORKER_NOT_VERIFIED"),
                            ("verifier", "NO_INDEPENDENT_VERIFIER"),
                            ("recoverable", "EFFECT_NOT_RECOVERABLE"),
                            ("evidence", "CAUSAL_EVIDENCE_UNKNOWN")):
            if c[key] != "VERIFIED":
                fail.append(reason)
    # PROBE is a read-only diagnostic: it cannot cause external effects or consume
    # unapproved resources. Marked effects cannot be laundered as PROBEs.
    if c["mode"] == "PROBE" and c.get("external_effect", False):
        fail.append("MISCLASSIFIED_EFFECT")
    return fail


def dominates(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Pareto comparison: no invented scalar weights or unsupported tradeoffs."""
    ua, ub = set(a["unlocks"]), set(b["unlocks"])
    la, lb = set(a["learns"]), set(b["learns"])
    non_worse = (ua >= ub and la >= lb and a["cost"] <= b["cost"]
                 and a["risk"] <= b["risk"])
    better = (ua > ub or la > lb or a["cost"] < b["cost"]
              or a["risk"] < b["risk"])
    return non_worse and better


def decide(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        return {"decision": "BLIND", "reason": "NO_CANDIDATES", "selected": None}
    if len({c["id"] for c in candidates}) != len(candidates):
        raise ValueError("candidate IDs must be unique")
    rejected = {c["id"]: reasons for c in candidates if (reasons := assess(c))}
    eligible = [c for c in candidates if c["id"] not in rejected]
    if not eligible:
        return {"decision": "REFUSED", "selected": None, "rejected": rejected,
                "reason": "NO_AUTHORISABLE_ACTION"}
    frontier = [c for c in eligible if not any(dominates(b, c) for b in eligible if b is not c)]
    if len(frontier) != 1:
        return {"decision": "UNRESOLVED", "selected": None,
                "frontier": sorted(c["id"] for c in frontier), "rejected": rejected,
                "reason": "INCOMPARABLE_TRADEOFFS_REQUIRE_DISCRIMINATING_EVIDENCE"}
    chosen = frontier[0]
    return {"decision": "SELECTED_FOR_EXECUTION" if chosen["mode"] == "EFFECT" else "SELECTED_FOR_PROBE",
            "selected": chosen["id"], "rejected": rejected,
            "dominated": sorted(c["id"] for c in eligible if c is not chosen),
            "note": "Selection is not an effect receipt or operational certification"}


def run_benchmark(path: str) -> dict[str, Any]:
    from pathlib import Path
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    results = []
    for case in data["cases"]:
        actual = decide(case["options"])
        matched = actual["decision"] == case["expected_decision"] and actual.get("selected") == case.get("expected_selected")
        results.append({"id": case["id"], "matched": matched, "actual": actual,
                        "expected": case["expected_decision"]})
    return {"benchmark_sha256": hashlib.sha256(raw).hexdigest(),
            "cases": len(results), "matched": sum(r["matched"] for r in results),
            "results": results}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 founder_method.py cases.json")
    print(json.dumps(run_benchmark(sys.argv[1]), indent=2, sort_keys=True))