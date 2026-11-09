"""Event-driven detector for a repeated Greenlane global DoF veto.

This is a read-only adapter over refs/greenlane/state and the existing #7800
incident, NOT a new queue, permissive gate, or an agent polling supervisor.
One GitHub workflow event produces at most one durable incident receipt per
(trusted main, policy blob, gate) epoch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable

DOF_FAILURE = re.compile(r"(?:^|\s--\s)dof-gate\s*>")
SHA = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
INCIDENT = 7800


@dataclass(frozen=True)
class Diagnosis:
    state: str
    reason: str
    base: str = ""
    policy_sha: str = ""
    fingerprint: str = ""
    batch_ids: tuple[str, ...] = ()
    affected_lanes: tuple[str, ...] = ()
    elapsed_batch_minutes: float = 0.0
    latest_verdict_minute: float | None = None

    def json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def classify(state: Any, policy_sha: str, minimum_lanes: int = 2) -> Diagnosis:
    """Only independent lanes failing the same gate at one baseline qualify."""
    if not isinstance(state, dict) or not isinstance(state.get("history"), list):
        return Diagnosis("BLIND", "unreadable canonical Greenlane history")
    if not SHA.fullmatch(policy_sha):
        return Diagnosis("BLIND", "unknown trusted policy blob SHA")
    history = state["history"][-200:]
    if not history:
        return Diagnosis("INSUFFICIENT", "no completed candidates")
    base = history[-1].get("base") if isinstance(history[-1], dict) else None
    if not isinstance(base, str) or not re.fullmatch(r"[0-9a-f]{12,40}", base):
        return Diagnosis("BLIND", "candidate baseline unavailable")
    epoch = []
    for row in reversed(history):
        if not isinstance(row, dict) or row.get("base") != base or row.get("outcome") == "landed":
            break
        epoch.append(row)
    failures = [
        row for row in epoch
        if row.get("outcome") in {"red", "timeout"}
        and isinstance(row.get("reason"), str)
        and DOF_FAILURE.search(row["reason"])
        and isinstance(row.get("members"), list)
        and isinstance(row.get("id"), str)
    ]
    lanes = tuple(sorted({
        member for row in failures for member in row["members"]
        if isinstance(member, str) and member.startswith("lane/")
    }))
    if len(lanes) < minimum_lanes or len(failures) < minimum_lanes:
        return Diagnosis(
            "INSUFFICIENT", "fewer than two independent lanes failed the DoF gate",
            base=base, policy_sha=policy_sha,
        )
    fingerprint = hashlib.sha256(
        ("greenlane\0" + base + "\0" + policy_sha + "\0dof-gate").encode()
    ).hexdigest()
    durations = [
        (r["verdict_at"] - r["started"])
        for r in failures
        if isinstance(r.get("started"), (int, float))
        and isinstance(r.get("verdict_at"), (int, float))
        and r["verdict_at"] >= r["started"]
    ]
    times = [r["verdict_at"] for r in failures if isinstance(r.get("verdict_at"), (int, float))]
    return Diagnosis(
        "COMMON_MODE", "identical trusted-base DoF veto across independent lanes",
        base, policy_sha, fingerprint, tuple(reversed([r["id"] for r in failures])),
        lanes, round(sum(durations), 2), max(times) if times else None,
    )


def github(repo: str, *args: str) -> Any:
    p = subprocess.run(["gh", "api", *args], capture_output=True, text=True,
                       check=False, timeout=40)
    if p.returncode != 0:
        raise RuntimeError("GitHub read/write rejected: " + p.stderr.strip()[:240])
    return json.loads(p.stdout) if p.stdout.strip() else None


def react(d: Diagnosis, repo: str, gh: Callable[..., Any] = github,
          incident: int = INCIDENT) -> str:
    """One incident comment per epoch; never create a duplicate ticket."""
    if d.state != "COMMON_MODE":
        return "no incident action: " + d.state
    if not REPO.fullmatch(repo):
        raise ValueError("untrusted repository name")
    issue = gh(repo, f"repos/{repo}/issues/{incident}")
    if not isinstance(issue, dict) or issue.get("state") != "open":
        raise RuntimeError("BLIND: canonical incident owner unavailable or closed")
    marker = "greenlane-common-mode-fingerprint: " + d.fingerprint
    for page in range(1, 11):
        comments = gh(repo, f"repos/{repo}/issues/{incident}/comments?per_page=100&page={page}")
        if not isinstance(comments, list):
            raise RuntimeError("BLIND: cannot read incident deduplication receipts")
        if any(marker in str(c.get("body") or "") for c in comments):
            return "duplicate event: no write"
        if len(comments) < 100:
            break
    else:
        raise RuntimeError("BLIND: bounded incident history exhausted")
    observed = (
        datetime.fromtimestamp(d.latest_verdict_minute * 60, tz=timezone.utc).isoformat()
        if d.latest_verdict_minute is not None else "UNKNOWN"
    )
    note = (
        "## Greenlane event-driven Operations Reaction\n\n"
        + marker + "\n\n"
        + f"Trusted baseline: {d.base}; trusted policy blob: {d.policy_sha}; gate: dof-gate.\n"
        + f"Distinct rejected lanes: {len(d.affected_lanes)}; rejected batches: {len(d.batch_ids)}.\n"
        + f"Last observed verdict: {observed}; {d.elapsed_batch_minutes:.2f}"
          " elapsed batch-minutes (NOT billed compute).\n"
        + "Recent batches: " + ", ".join(d.batch_ids[-8:]) + "\n\n"
        + "Existing owner #7800: independently authorised policy repair and a formerly "
          "blocked lane must be verified on real main. This is an incident receipt, "
          "not a release or a security exception. Repeating identical candidate CI "
          "without a changed failure hypothesis wastes capacity.\n"
    )
    gh(repo, "-X", "POST", f"repos/{repo}/issues/{incident}/comments",
       "-f", "body=" + note)
    return "reaction recorded: " + marker


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--state", required=True)
    p.add_argument("--policy-sha", required=True)
    p.add_argument("--repo", default="chidionyema/idp")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args(argv)
    try:
        with open(args.state, encoding="utf-8") as fd:
            report = classify(json.load(fd), args.policy_sha)
        print(report.json(), flush=True)
        if report.state == "BLIND":
            return 2
        if args.apply:
            print(react(report, args.repo), flush=True)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print("BLIND: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
