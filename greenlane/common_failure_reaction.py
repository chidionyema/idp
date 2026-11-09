"""Single-shot event reaction for a recurrent *canonical* Greenlane failure class.

One completed trusted Greenlane workflow event = one diagnosis. Reads the
existing state ref, reuses the existing DoF incident, and adds an idempotent
receipt. No new state database, polling loop, timers, bypass, CI re-run, or
model-generated authority.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

GATE = re.compile(r"(?:^|\s--\s)dof-gate\s*>")
SHA = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")
INCIDENT = 7800


@dataclass(frozen=True)
class Finding:
    status: str  # COMMON_MODE / INSUFFICIENT / BLIND
    reason: str
    fingerprint: str = ""
    base: str = ""
    policy_sha: str = ""
    count: int = 0
    lanes: tuple[str, ...] = ()


def classify(state: object, policy_sha: str) -> Finding:
    if not isinstance(state, dict) or not isinstance(state.get("history"), list):
        return Finding("BLIND", "canonical state history is unreadable")
    if not SHA.fullmatch(policy_sha):
        return Finding("BLIND", "trusted gate blob SHA is unknown")
    history = state["history"]
    if not history:
        return Finding("INSUFFICIENT", "no candidate verdict yet")
    base = history[-1].get("base") if isinstance(history[-1], dict) else None
    if not isinstance(base, str) or not re.fullmatch(r"[0-9a-f]{12,40}", base):
        return Finding("BLIND", "missing candidate baseline")
    epoch = []
    for r in reversed(history[-200:]):
        if not isinstance(r, dict) or r.get("base") != base or r.get("outcome") == "landed":
            break
        epoch.append(r)
    hits = [r for r in epoch if r.get("outcome") in ("red", "timeout")
            and isinstance(r.get("reason"), str) and GATE.search(r["reason"])
            and isinstance(r.get("members"), list)]
    independent = tuple(sorted({n for r in hits for n in r["members"]
                                if isinstance(n, str) and n.startswith("lane/")}))
    if len(independent) < 2 or len(hits) < 2:
        return Finding("INSUFFICIENT", "no repeated baseline policy veto across independent lanes",
                       base=base, policy_sha=policy_sha)
    key = hashlib.sha256(f"greenlane\0{base}\0{policy_sha}\0dof-gate".encode()).hexdigest()
    return Finding("COMMON_MODE", "independent lanes repeatedly refused by identical trusted DoF base",
                   key, base, policy_sha, len(hits), independent)


def gh(repo: str, *args: str):
    result = subprocess.run(["gh", "api", *args], capture_output=True,
                            text=True, timeout=40, check=False)
    if result.returncode:
        raise RuntimeError("GitHub reaction API unavailable: " + result.stderr.strip()[:150])
    return json.loads(result.stdout) if result.stdout.strip() else None


def react(finding: Finding, repo: str, call=gh) -> str:
    if finding.status != "COMMON_MODE":
        return f"no action: {finding.status}: {finding.reason}"
    if not REPO.fullmatch(repo):
        raise ValueError("invalid repository identifier")
    issue = call(repo, f"repos/{repo}/issues/{INCIDENT}")
    if not isinstance(issue, dict) or issue.get("state") != "open":
        raise RuntimeError("canonical trusted-base incident is missing or closed")
    marker = f"greenlane-common-mode-fingerprint: {finding.fingerprint}"
    # Paginated finite data reads are NOT periodic polling or wait loops.
    for page in range(1, 11):
        items = call(repo, f"repos/{repo}/issues/{INCIDENT}/comments?per_page=100&page={page}")
        if not isinstance(items, list):
            raise RuntimeError("BLIND: cannot establish idempotency of incident reaction")
        if any(marker in str(x.get("body") or "") for x in items if isinstance(x, dict)):
            return f"deduplicated: {marker}"
        if len(items) < 100:
            break
    else:
        raise RuntimeError("BLIND: incident comment history exceeds bounded read")
    body = (
        "## Operations Reaction — repeated Greenlane common-mode failure\n\n"
        f"{marker}\n\n"
        f"Verified trusted base (12–40-char index): `{finding.base}`; "
        f"policy blob: `{finding.policy_sha}`. "
        f"{finding.count} failed verdicts across {len(finding.lanes)} independent lanes.\n"
        "Affected branches: " + ", ".join(finding.lanes[:25]) + "\n\n"
        "Existing #7800 owner: resolve the exact trusted-base policy rejection via "
        "its independently authorized route, then read back main and a real "
        "previously blocked lane landing. DO NOT repeat unchanged costly CI, "
        "invent authorisation, or close on source-only proof. "
        "This event cannot grant any merge or change any required check."
    )
    call(repo, "-X", "POST", f"repos/{repo}/issues/{INCIDENT}/comments", "-f", f"body={body}")
    return f"reaction recorded: {marker}"


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--policy-sha", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    try:
        with open(args.state, encoding="utf-8") as f:
            state = json.load(f)
        finding = classify(state, args.policy_sha)
        print(json.dumps(asdict(finding), sort_keys=True))
        if finding.status == "BLIND":
            return 2
        if args.apply:
            print(react(finding, args.repo))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print("BLIND: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
