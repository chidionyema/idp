"""Preserve production Cloudflare ingress on candidate-only recovery (#7387).

Pure standard-library JSON planner; no credentials, cloud writes, new service or paid runtime.
"""
from __future__ import annotations

import copy
import json
import sys

CANDIDATE = "llm-recovery.mumchimp.com"
SERVICE = "http://127.0.0.1:4000"


def plan_candidate(current: object) -> dict:
    if not isinstance(current, dict) or current.get("success") is not True:
        raise ValueError("BLIND: Cloudflare GET was not attested")
    result = current.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("config"), dict):
        raise ValueError("BLIND: missing tunnel config")
    config = copy.deepcopy(result["config"])
    rules = config.get("ingress")
    if not isinstance(rules, list) or not rules:
        raise ValueError("BLIND: missing ingress; production cannot be preserved")
    if any(not isinstance(r, dict) or not isinstance(r.get("service"), str) for r in rules):
        raise ValueError("BLIND: malformed ingress rule")
    fallback = [r for r in rules if not r.get("hostname")]
    if len(fallback) != 1 or rules[-1] is not fallback[0]:
        raise ValueError("BLIND: exactly one final fallback required")
    if not fallback[0]["service"].startswith("http_status:"):
        raise ValueError("BLIND: unknown catch-all service")
    named = [r for r in rules if r.get("hostname")]
    hosts = [r.get("hostname") for r in named]
    if any(not isinstance(h, str) or not h for h in hosts) or len(hosts) != len(set(hosts)):
        raise ValueError("BLIND: invalid or duplicate hostnames")
    config["ingress"] = (
        [{"hostname": CANDIDATE, "service": SERVICE}]
        + [r for r in named if r["hostname"] != CANDIDATE]
        + fallback
    )
    return {"config": config}


def main() -> int:
    try:
        print(json.dumps(plan_candidate(json.load(sys.stdin)), separators=(",", ":"), sort_keys=True))
        return 0
    except (ValueError, TypeError, OSError) as exc:
        print(f"REFUSED router ingress: {exc}", file=sys.stderr)
        return 70


if __name__ == "__main__":
    sys.exit(main())
