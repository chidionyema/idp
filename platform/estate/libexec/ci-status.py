#!/usr/bin/env python3
"""ci-status — structured CI status for a PR or SHA."""

import base64
import hashlib
import json
import subprocess
import sys
from urllib.parse import quote

POLICY_PATH = "platform/github/ruleset.idp.required-checks.json"
GREEN = {"success", "skipped", "neutral"}


def gh_json(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        print(json.dumps({"error": r.stderr.strip()}))
        sys.exit(1)
    return json.loads(r.stdout)


repo = "chidionyema/idp"
sha = ""
pr_num = 0
pr_mergeable = None

for arg in sys.argv[1:]:
    if arg.startswith("pr="):
        pr_num = int(arg.split("=", 1)[1])
    elif arg.startswith("sha="):
        sha = arg.split("=", 1)[1]
    elif arg.startswith("repo="):
        repo = arg.split("=", 1)[1]

if pr_num and not sha:
    d = gh_json(f"repos/{repo}/pulls/{pr_num}")
    sha = d["head"]["sha"]
    branch = d["head"]["ref"]
    title = d["title"]
    pr_mergeable = d.get("mergeable")
    is_draft = d.get(
        "draft", False
    )  # REST says "draft"; "isDraft" is the GraphQL/gh name
elif not sha:
    # "check ci status" out loud names no PR: the question is main's head (2026-10-13).
    d = gh_json(f"repos/{repo}/commits/main")
    sha = d["sha"]
    branch = "main"
    title = d["commit"]["message"].splitlines()[0]
    is_draft = False
else:
    branch = "?"
    title = "?"
    is_draft = False

# The first page is diagnostic only. This SHA may have >500 non-required
# Greenlane/land/tick runs; page 1 cannot establish merge-readiness.
raw = gh_json(f"repos/{repo}/commits/{sha}/check-runs?per_page=100")
runs = raw.get("check_runs", [])

def policy():
    """Read the real main policy through the estate's existing GitHub authority.

    ci-status.py is deployed as ~/.estate/libexec/ci-status.py, NOT beneath
    the source checkout. Guessing __file__.parents[3] silently points outside
    the repo on Pi/Mac. A trusted remote content read works from every agent
    surface and fails BLIND if GitHub/its permission is missing.
    """
    if repo != "chidionyema/idp":
        return [], "", "no verified IDP policy for requested repository"
    url = f"repos/{repo}/contents/{POLICY_PATH}?ref=main"
    try:
        proc = subprocess.run(["gh", "api", url], capture_output=True,
                              text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as ex:
        return [], "", "cannot read canonical GitHub ruleset: " + str(ex)[:120]
    if proc.returncode != 0:
        return [], "", "cannot read canonical GitHub ruleset: " + proc.stderr.strip()[:120]
    try:
        payload = json.loads(proc.stdout)
        if payload.get("encoding") != "base64":
            raise ValueError("GitHub policy content not base64")
        raw_policy = base64.b64decode(payload["content"])
        data = json.loads(raw_policy)
        checks = next(rule["parameters"]["required_status_checks"]
                      for rule in data["rules"]
                      if rule.get("type") == "required_status_checks")
        names = [x["context"] for x in checks]
        if not names or len(set(names)) != len(names):
            raise ValueError("required checks empty or duplicated")
        return checks, hashlib.sha256(raw_policy).hexdigest(), ""
    except (ValueError, KeyError, TypeError, StopIteration) as ex:
        return [], "", f"policy unreadable: {ex}"


def required_result(name, app_id):
    url = (f"repos/{repo}/commits/{sha}/check-runs?"
           f"check_name={quote(name, safe='')}&per_page=100")
    try:
        proc = subprocess.run(["gh", "api", url], capture_output=True,
                              text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as ex:
        return {"state": "unreadable", "reason": str(ex)[:160]}
    if proc.returncode != 0:
        return {"state": "unreadable", "reason": proc.stderr.strip()[:160]}
    try:
        obj = json.loads(proc.stdout)
        if not isinstance(obj, dict) or not isinstance(obj.get("check_runs"), list):
            raise ValueError("malformed check response")
        match = [c for c in obj["check_runs"] if c.get("name") == name
                 and (app_id is None or (c.get("app") or {}).get("id") == app_id)]
        if not match:
            return {"state": "absent"}
        chosen = max(match, key=lambda c: (c.get("id") or 0,
                     c.get("completed_at") or c.get("started_at") or ""))
        state = chosen.get("conclusion") if chosen.get("status") == "completed" else "pending"
        return {"state": state or "pending", "url": chosen.get("html_url", ""),
                "check_run_id": chosen.get("id")}
    except (ValueError, KeyError, TypeError, AttributeError) as ex:
        return {"state": "unreadable", "reason": str(ex)[:160]}

required, policy_digest, policy_error = policy()
per_required = {c["context"]: required_result(c["context"], c.get("integration_id"))
                for c in required}
missing = [k for k, v in per_required.items() if v["state"] == "absent"]
unreadable = [k for k, v in per_required.items() if v["state"] == "unreadable"]
pending_required = [k for k, v in per_required.items() if v["state"] == "pending"]
failed_required = [k for k, v in per_required.items()
                   if v["state"] not in GREEN | {"absent", "unreadable", "pending"}]
passing = [k for k, v in per_required.items() if v["state"] in GREEN]
ready = bool(required) and len(passing) == len(required)
if not required:
    required_verdict = "BLIND_REQUIRED_POLICY"
elif unreadable:
    required_verdict = "BLIND_REQUIRED_CHECKS"
elif failed_required:
    required_verdict = "FAILED_REQUIRED_CHECKS"
elif missing:
    required_verdict = "ABSENT_REQUIRED_CHECKS"
elif pending_required:
    required_verdict = "PENDING_REQUIRED_CHECKS"
else:
    required_verdict = "REQUIRED_CHECKS_GREEN"
if missing:
    next_action = {"code": "RECONCILE_REQUIRED_CHECK_PRODUCERS",
                   "owner": "estate-greenlane", "sha": sha, "contexts": missing,
                   "boundary": "run genuine checks; never synthesize green"}
elif failed_required:
    next_action = {"code": "REMEDIATE_FAILED_CHECK_CLASS",
                   "owner": "estate-greenlane", "sha": sha, "contexts": failed_required}
elif unreadable or policy_error:
    next_action = {"code": "REPAIR_CHECK_VISIBILITY",
                   "owner": "estate-greenlane", "sha": sha}
elif pending_required:
    next_action = {"code": "OBSERVE_REQUIRED_CHECKS",
                   "owner": "estate-greenlane", "sha": sha}
else:
    next_action = None

pending = [r for r in runs if r.get("conclusion") is None]
failed = [r for r in runs if r.get("conclusion") == "failure"]
skipped = [r for r in runs if r.get("conclusion") == "skipped"]
passed = [r for r in runs if r.get("conclusion") == "success"]

where = f"PR {pr_num}" if pr_num else ("main" if branch == "main" else sha[:8])
if failed:
    verdict = f"{len(failed)} failed: " + ", ".join(r["name"] for r in failed[:3])
elif pending:
    verdict = f"no failures, {len(pending)} still running"
else:
    verdict = "no failures in first diagnostic page"
# Existing check pagination is NOT proof of required-context coverage.
verdict += f"; required {len(passing)}/{len(required)} green ({required_verdict})"
# One sentence a voice can say; the rest of this JSON is for agents (voice_intents._spoken_result).
summary = f"CI on {where}: {len(passed)} passed, {verdict}."

result = {
    "summary": summary,
    "sha": sha[:8],
    "full_sha": sha,
    "branch": branch,
    "title": title,
    "draft": is_draft,
    "repo": repo,
    "total": len(runs),
    "passed": len(passed),
    "failed": len(failed),
    "skipped": len(skipped),
    "running": len(pending),
    "failures": [{"name": r["name"], "url": r.get("html_url", "")} for r in failed],
    "running_names": [r["name"] for r in pending],
    "required_policy": POLICY_PATH if required else None,
    "required_policy_sha256": policy_digest,
    "required_policy_error": policy_error,
    "required_checks": per_required,
    "required_verdict": required_verdict,
    "required_missing": missing,
    "required_failed": failed_required,
    "required_unreadable": unreadable,
    "required_pending": pending_required,
    "required_green": passing,
    "next_estate_action": next_action,
    "required_checks_green": ready,
    "merge_ready": bool(pr_num and ready and not is_draft and pr_mergeable is True),
    "merge_readiness_scope": "PR only; source SHA checks alone never establish branch mergeability",
}
print(json.dumps(result, indent=2))
