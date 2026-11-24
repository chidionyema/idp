#!/usr/bin/env python3
"""Falsifier for sovereign_reconciler.py -- run in CI (R1/R2: a gate that cannot
fail is not a gate; this proves the gate rejects known-bad and accepts known-good)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sovereign_reconciler as sr  # noqa: E402

cfg = json.loads(json.dumps(sr.DEFAULT_DESIRED_STATE))

# KNOWN-BAD 1: blind (no token, dry-run probes) -> RED_FREEZE + fail_closed, never GREEN
bad = sr.reconcile(cfg, github_token=None, dry_run=True)
assert bad["error_budget"]["status"] == "RED_FREEZE"
assert bad["error_budget"]["fail_closed"] is True
assert "TELEMETRY_BLIND" in {b["code"] for b in bad["error_budget"]["blockers"]}
print("KNOWN-BAD blind: REJECTED ok")

# KNOWN-BAD 2: GitHub API error -> fail closed, not silent GREEN
sr.inspect_github = lambda *a, **k: {
    "connected": False,
    "error": "GitHub API HTTP 401",
    "allowlisted_failures": [],
    "zombie_failures": [],
    "head_sha": "UNKNOWN",
}
bad2 = sr.reconcile(cfg, github_token="fake", dry_run=False)
assert bad2["error_budget"]["status"] == "RED_FREEZE"
assert bad2["error_budget"]["fail_closed"] is True
assert "TELEMETRY_BLIND" in {b["code"] for b in bad2["error_budget"]["blockers"]}
print("KNOWN-BAD github-error: REJECTED ok")

# KNOWN-GOOD: verified probes, green GitHub, no credential cliff -> GREEN
cfg_ok = json.loads(json.dumps(sr.DEFAULT_DESIRED_STATE))
cfg_ok["secrets_watchlist"] = [
    {
        "name": "argon-sync",
        "scope": "PAT",
        "expires_on": "2027-12-02",
        "owner": "founder",
    }
]
# The real checkout's AGENTS.md is over the 1,500-token cap (a true finding, asserted
# separately below); the GREEN fixture scopes the audit to the compact contract files.
cfg_ok["rule_files_to_audit"] = ["ops/desired_state.json"]
sr.probe_endpoint = lambda ep, dry_run=False: {
    "id": ep["id"],
    "ok": True,
    "verified": True,
    "required": True,
    "name": ep["name"],
    "url": ep["url"],
    "expected_status": 200,
    "observed_status": 200,
    "latency_ms": 12,
    "diagnostic": "OK",
}
sr.inspect_github = lambda *a, **k: {
    "connected": True,
    "error": None,
    "head_sha": "deadbeef1234",
    "allowlisted_failures": [],
    "zombie_failures": [],
    "recent_runs": [],
    "open_prs": 0,
    "stale_prs_7d": 0,
}
good = sr.reconcile(cfg_ok, github_token="fake", dry_run=False)
assert good["error_budget"]["status"] == "GREEN"
assert good["error_budget"]["feature_merges_allowed"] is True
assert good["error_budget"]["fail_closed"] is False
# TRUE FINDING asserted: this checkout's auto-injected rules exceed the cap
live_audit = sr.audit_context_tokens(sr.DEFAULT_DESIRED_STATE["rule_files_to_audit"])
if live_audit["total_tokens"] > 1500:
    print(
        f"TRUE FINDING: rule files measure {live_audit['total_tokens']} tokens vs 1,500 cap (CONTEXT_TOKEN_OVERFLOW)"
    )
print("KNOWN-GOOD green: ACCEPTED ok")
print("FALSIFIER: all assertions passed")
