#!/usr/bin/env python3
"""KARMA: existing estate-state/Chronos proof-of-observation, not another ledger.

Consumes the GitHub run evidence estate-state ALREADY gathered, optionally the
QUAD-backed router action JSONL. Does not call models, write a new store, alter
authority, self-verify reward, or assume a missing value is zero.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def valid_time(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        ).isoformat().replace("+00:00", "Z")
    except (ValueError, OverflowError):
        return None


def reconcile(runs, actions=None, *, sha="UNKNOWN", observed_at=None):
    """A bounded scientific projection: actor-supplied scores never settle debt."""
    if not isinstance(runs, list):
        raise ValueError("run source must be a list; a blind read cannot be green")
    status = Counter()
    by_workflow = defaultdict(Counter)
    identifiers = set()
    duplicates = missing_ids = missing_times = 0
    examples = []
    for item in runs:
        if not isinstance(item, dict):
            missing_times += 1
            continue
        ident = item.get("id")
        repo = str(item.get("repo") or "UNKNOWN")
        key = (repo, ident) if type(ident) is int and ident > 0 else None
        if key in identifiers and key is not None:
            duplicates += 1
            continue
        if key:
            identifiers.add(key)
        else:
            missing_ids += 1
        time = valid_time(item.get("created_at"))
        if not time:
            missing_times += 1
        conclusion = item.get("conclusion") or "UNKNOWN"
        if not isinstance(conclusion, str):
            conclusion = "UNKNOWN"
        status[conclusion] += 1
        workflow = repo + "/" + str(item.get("workflow") or "UNKNOWN")
        by_workflow[workflow][conclusion] += 1
        if len(examples) < 20 and conclusion in ("failure", "cancelled", "timed_out"):
            examples.append({
                "run_id": ident if key else None,
                "sha": item.get("sha") or "UNKNOWN",
                "workflow": workflow,
                "event_at": time,
                "conclusion": conclusion,
                "independent_production_yield": "UNKNOWN",
            })
    quad_source = "NOT_CONNECTED" if actions is None else "ROUTER_SOURCE_UNVERIFIED"
    groups = Counter()
    known_tokens = 0
    tokens_missing = 0
    unlinked = 0
    calls = None
    if actions is not None:
        if not isinstance(actions, list):
            raise ValueError("QUAD-router source must be list")
        calls = 0
        for row in actions:
            if not isinstance(row, dict) or not isinstance(row.get("karma"), dict):
                continue
            k = row["karma"]
            if k.get("schema") != "estate.karma.call.v1":
                continue
            calls += 1
            provider = str(k.get("provider") or "UNKNOWN")
            model = str(k.get("returned_model") or "UNKNOWN")
            groups[(provider, model, "UNKNOWN")] += 1
            if not k.get("instruction_id"):
                unlinked += 1
            n = k.get("total_tokens")
            if type(n) is int and n >= 0:
                known_tokens += n
            else:
                tokens_missing += 1
    return {
        "schema": "estate.karma.readback.v1",
        "code_name": "KARMA",
        "main_sha": sha,
        "observed_at": valid_time(observed_at) if observed_at else datetime.now(
            timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "observation_clock": "RUNNER_HOST_UNATTESTED",
        "chronos": "ESTATE_STATE_EXISTING_SCHEDULE",
        "ci": {
            "observed_runs": sum(status.values()),
            "conclusions": dict(sorted(status.items())),
            "workflow_counts": {k: dict(sorted(v.items()))
                                for k, v in sorted(by_workflow.items())},
            "duplicates": duplicates,
            "missing_run_ids": missing_ids,
            "missing_or_invalid_times": missing_times,
            "failure_examples": examples,
            "runner_minutes": None,
            "billable_cost": None,
            "cost_quality": "UNKNOWN_NOT_ZERO",
            "verified_production_yield": None,
        },
        "quad": {
            "source": quad_source,
            "model_calls_observed": calls,
            "group_by_provider_model_revision": {
                "/".join(k): v for k, v in sorted(groups.items())
            },
            "token_count_observed": known_tokens if calls is not None else None,
            "token_unknown_calls": tokens_missing if calls is not None else None,
            "missing_instruction_link": unlinked if calls is not None else None,
            "verified_obligation_settlements": None,
            "yield_quality": "NO_INDEPENDENT_SETTLEMENT_WITNESS",
        },
        "coverage_gaps": [
            "QUAD_ROUTER_SOURCE_NOT_CONNECTED" if actions is None
            else "QUAD_METADATA_NOT_SIGNATURE_ATTESTED",
            "ACCEPTED_INSTRUCTION_REGISTRY_NOT_CONNECTED",
            "CI_TO_INSTRUCTION_CAUSAL_LINK_NOT_VERIFIED",
            "PRODUCTION_YIELD_WITNESS_NOT_CONNECTED",
            "BILLING_SOURCE_NOT_CONNECTED",
            *([f"RUN_ID_MISSING:{missing_ids}"] if missing_ids else []),
            *([f"RUN_DUPLICATES:{duplicates}"] if duplicates else []),
        ],
        "investor": {
            "stage": "INTERNAL_RESEARCH",
            "safe_to_assert_live_verified_KARMA": False,
            "observed_ci_runs": sum(status.values()),
        },
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="KARMA readback on existing evidence")
    p.add_argument("--runs", required=True)
    p.add_argument("--actions", default=None, help="optional trusted-access router JSONL")
    p.add_argument("--out", required=True)
    p.add_argument("--summary", default=None)
    p.add_argument("--main-sha", default="UNKNOWN")
    a = p.parse_args(argv)
    runs = json.loads(Path(a.runs).read_text(encoding="utf8"))
    actions = None
    if a.actions:
        with open(a.actions, encoding="utf8") as stream:
            actions = [json.loads(line) for line in stream if line.strip()]
    result = reconcile(runs, actions, sha=a.main_sha)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf8")
    ci = result["ci"]
    summary = (f"KARMA: {ci['observed_runs']} CI observations, "
               f"{ci['conclusions'].get('failure', 0)} failed, "
               f"{ci['missing_run_ids']} missing run IDs; "
               f"QUAD={result['quad']['source']}; "
               "verified yield=UNKNOWN; billed cost=UNKNOWN")
    print(summary)
    if a.summary:
        with open(a.summary, "a", encoding="utf8") as sink:
            sink.write("\n### KARMA — Chronos-observed research readback\n" + summary + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
