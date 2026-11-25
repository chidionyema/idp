#!/usr/bin/env python3
"""One-Shot Router & Credential Delivery Blocker Discriminator (idp#8416).

Ultra-low-token deterministic discriminator for Cline / Codex:
Runs static workflow wiring audit + live GitHub secret/env/run inspection + live edge probe
in ONE invocation (~5s) and writes a compact JSON verdict (`oneshot_verdict.json`) mapping
directly to one of 5 mutually exclusive branches (BRANCH_0..BRANCH_4).

Zero external dependencies (Python 3.10+ stdlib + optional `gh` CLI).
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TARGET_SECRETS = (
    "SEED_CLOUDFLARE_WORKERS_TOKEN",
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_ROOT_TOKEN",
    "CLOUDFLARE_ACCOUNT_ID",
    "SEED_MERIDIAN_CLIENT_KEY",
    "SEED_MERIDIAN_ADMIN_KEY",
)

HEALTH_URL = "https://llm.meridianlabs.cloud/health"
EXPECTED_BODY_TOKEN = "zone-b-cloudflare-edge"
EXPECTED_ACCOUNT_ID = "4912457480997df81450b3ea614ccf3c"


def run_cmd(cmd: List[str], timeout: int = 20) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s: {' '.join(cmd)}"


def probe_edge_health(url: str = HEALTH_URL, timeout: int = 10) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "meridian-oneshot-probe/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(2048).decode("utf-8", errors="replace")
            return {
                "url": url,
                "http_status": r.status,
                "cf_ray": r.headers.get("cf-ray"),
                "has_expected_marker": EXPECTED_BODY_TOKEN in body,
                "body_preview": body[:300],
            }
    except urllib.error.HTTPError as e:
        body = e.read(1024).decode("utf-8", errors="replace")
        return {
            "url": url,
            "http_status": e.code,
            "cf_ray": e.headers.get("cf-ray"),
            "has_expected_marker": False,
            "body_preview": body[:300],
        }
    except Exception as exc:
        return {
            "url": url,
            "http_status": None,
            "cf_ray": None,
            "has_expected_marker": False,
            "error": str(exc)[:300],
        }


def audit_workflows(repo_root: Path) -> Dict[str, Any]:
    wf_dir = repo_root / ".github" / "workflows"
    findings: List[Dict[str, Any]] = []
    if not wf_dir.is_dir():
        return {"workflow_dir_found": False, "matches": []}

    secret_re = re.compile(r"secrets\.([A-Z0-9_]+)")
    env_re = re.compile(r"^\s*environment\s*:\s*(.+)$", re.MULTILINE)
    trigger_re = re.compile(r"(router-edge|idp-bootstrap-cloudflare|cloudflare|deploy-zone-b|meridian-router)", re.IGNORECASE)

    for p in sorted(wf_dir.glob("*.y*ml")):
        text = p.read_text(encoding="utf-8", errors="replace")
        secrets_used = sorted(set(secret_re.findall(text)))
        relevant_secrets = [
            s for s in secrets_used
            if any(k in s for k in ("CLOUDFLARE", "MERIDIAN", "VAULT", "OCI", "SEED_", "BITWARDEN"))
        ]
        if not trigger_re.search(text) and not relevant_secrets:
            continue

        envs = [m.strip().strip("'\"") for m in env_re.findall(text)]
        uses_bootstrap = "idp-bootstrap-cloudflare" in text
        uses_wrangler = "wrangler" in text.lower()
        wiring_suspects: List[str] = []
        if uses_wrangler and "CLOUDFLARE_API_TOKEN" not in text:
            wiring_suspects.append("wrangler_invoked_without_CLOUDFLARE_API_TOKEN_env")
        if uses_wrangler and not any(
            s in secrets_used
            for s in ("SEED_CLOUDFLARE_WORKERS_TOKEN", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ROOT_TOKEN")
        ):
            wiring_suspects.append("wrangler_workflow_references_zero_cloudflare_secrets")

        findings.append({
            "file": str(p.relative_to(repo_root)),
            "environments": envs,
            "relevant_secrets": relevant_secrets,
            "uses_bootstrap_script": uses_bootstrap,
            "uses_wrangler": uses_wrangler,
            "wiring_suspects": wiring_suspects,
        })

    return {"workflow_dir_found": True, "matches": findings}


def audit_github_secrets_and_runs(repo: str, console_repo: str) -> Dict[str, Any]:
    if not shutil.which("gh"):
        return {"gh_available": False, "error": "gh CLI not installed"}

    out: Dict[str, Any] = {"gh_available": True, "repo": repo}

    # 1. Repo-level secret names (never values)
    rc, stdout, stderr = run_cmd(["gh", "secret", "list", "-R", repo, "--json", "name,updatedAt"])
    if rc == 0 and stdout:
        try:
            items = json.loads(stdout)
            out["repo_secrets"] = {
                i["name"]: i.get("updatedAt")
                for i in items
                if i["name"] in TARGET_SECRETS
                or any(k in i["name"] for k in ("CLOUDFLARE", "OCI", "MERIDIAN"))
            }
        except json.JSONDecodeError:
            out["repo_secrets_raw"] = stdout[:400]
    else:
        out["repo_secrets_error"] = (stderr or stdout)[:300]

    # 2. GitHub Environments + environment-scoped secrets
    rc_env, env_out, env_err = run_cmd(
        ["gh", "api", f"repos/{repo}/environments", "--jq", ".environments[].name"]
    )
    env_secrets: Dict[str, Any] = {}
    if rc_env == 0 and env_out:
        for env_name in [e.strip() for e in env_out.splitlines() if e.strip()]:
            rc_es, es_out, es_err = run_cmd(
                ["gh", "secret", "list", "-R", repo, "--env", env_name, "--json", "name,updatedAt"]
            )
            if rc_es == 0 and es_out:
                try:
                    env_secrets[env_name] = [i["name"] for i in json.loads(es_out)]
                except json.JSONDecodeError:
                    env_secrets[env_name] = es_out[:200]
            else:
                env_secrets[env_name] = f"error:{(es_err or es_out)[:120]}"
    elif env_err:
        out["environments_error"] = env_err[:200]
    out["environment_secrets"] = env_secrets

    # 3. Last 6 runs touching cloudflare/router/release/bootstrap
    rc_runs, runs_out, _ = run_cmd([
        "gh", "run", "list", "-R", repo, "--limit", "30",
        "--json", "databaseId,workflowName,conclusion,headSha,createdAt,status",
    ])
    relevant_runs: List[Dict[str, Any]] = []
    if rc_runs == 0 and runs_out:
        try:
            for r in json.loads(runs_out):
                wf = (r.get("workflowName") or "").lower()
                if any(k in wf for k in ("cloudflare", "router", "zone-b", "deploy", "release", "bootstrap")):
                    relevant_runs.append(r)
        except json.JSONDecodeError:
            pass
    out["recent_router_runs"] = relevant_runs[:6]

    # 4. ONLY last 20 non-empty lines of the latest failed router/cloudflare run
    latest_failed = next((r for r in relevant_runs if r.get("conclusion") == "failure"), None)
    if latest_failed:
        rid = str(latest_failed["databaseId"])
        _, log_out, log_err = run_cmd(["gh", "run", "view", rid, "-R", repo, "--log-failed"], timeout=25)
        lines = [ln for ln in (log_out or log_err).splitlines() if ln.strip()]
        out["latest_failed_run"] = {
            "run_id": rid,
            "workflow": latest_failed.get("workflowName"),
            "head_sha": latest_failed.get("headSha"),
            "tail_20_lines": lines[-20:],
        }

    # 5. ONLY last 15 lines of latest Bitwarden secret sync failure in console_repo
    rc_bw, bw_out, _ = run_cmd([
        "gh", "run", "list", "-R", console_repo, "--limit", "5",
        "--json", "databaseId,workflowName,conclusion,createdAt",
    ])
    if rc_bw == 0 and bw_out:
        try:
            bw_runs = json.loads(bw_out)
            bw_fail = next(
                (
                    r for r in bw_runs
                    if "bitwarden" in (r.get("workflowName") or "").lower()
                    and r.get("conclusion") == "failure"
                ),
                None,
            )
            if bw_fail:
                bid = str(bw_fail["databaseId"])
                _, bl_out, bl_err = run_cmd(
                    ["gh", "run", "view", bid, "-R", console_repo, "--log-failed"], timeout=20
                )
                bl_lines = [ln for ln in (bl_out or bl_err).splitlines() if ln.strip()]
                out["bitwarden_sync_failure"] = {
                    "run_id": bid,
                    "created_at": bw_fail.get("createdAt"),
                    "tail_15_lines": bl_lines[-15:],
                }
        except json.JSONDecodeError:
            pass

    return out


def classify_branch(
    edge: Dict[str, Any],
    workflows: Dict[str, Any],
    gh_state: Dict[str, Any],
) -> Dict[str, Any]:
    if edge.get("http_status") == 200 and edge.get("has_expected_marker"):
        return {
            "branch": "BRANCH_0_ALREADY_OPERATIONAL",
            "reason": "Live edge health returned HTTP 200 with zone-b-cloudflare-edge marker.",
            "next_action": "Run authenticated /v1/chat/completions probe; verify failover past DeepSeek 402.",
        }

    repo_secrets = gh_state.get("repo_secrets") or {}
    env_secrets = gh_state.get("environment_secrets") or {}
    tail_text = "\n".join((gh_state.get("latest_failed_run") or {}).get("tail_20_lines") or []).lower()

    token_in_repo = (
        "SEED_CLOUDFLARE_WORKERS_TOKEN" in repo_secrets
        or "CLOUDFLARE_API_TOKEN" in repo_secrets
    )
    envs_with_token = [
        env_name
        for env_name, names in env_secrets.items()
        if isinstance(names, list)
        and ("SEED_CLOUDFLARE_WORKERS_TOKEN" in names or "CLOUDFLARE_API_TOKEN" in names)
    ]

    wiring_issues = [m["file"] for m in workflows.get("matches", []) if m.get("wiring_suspects")]
    if envs_with_token:
        unmatched = [
            m["file"]
            for m in workflows.get("matches", [])
            if m.get("uses_wrangler")
            and not any(e in envs_with_token for e in m.get("environments", []))
        ]
        if unmatched:
            return {
                "branch": "BRANCH_1_WORKFLOW_WIRING_BUG",
                "reason": f"Cloudflare token exists in GitHub environment(s) {envs_with_token}, NOT bound by deploy workflow(s): {unmatched}.",
                "next_action": f"Bind `environment: {envs_with_token[0]}` (or fix secret env mapping) in {unmatched[0]} and push via Greenlane -- DO NOT mint new tokens.",
            }

    if token_in_repo and wiring_issues:
        return {
            "branch": "BRANCH_1_WORKFLOW_WIRING_BUG",
            "reason": f"Cloudflare token exists at repo secret level, but workflow wiring suspect(s) found: {wiring_issues}.",
            "next_action": f"Patch env/secret binding in {wiring_issues[0]} so wrangler receives CLOUDFLARE_API_TOKEN, then dispatch deploy.",
        }

    if any(k in tail_text for k in ("403", "forbidden", "zone not found", "meridianlabs.cloud", "authentication error", "10000")):
        return {
            "branch": "BRANCH_3_CLOUDFLARE_ZONE_OR_SCOPE_BLOCK",
            "reason": "Cloudflare API rejected existing token with 403 / zone-visibility / auth error.",
            "next_action": f"Stop agent retries immediately. Escalate tail lines to Founder to verify Cloudflare token scope for account {EXPECTED_ACCOUNT_ID} and zone meridianlabs.cloud.",
        }

    if token_in_repo or envs_with_token:
        return {
            "branch": "BRANCH_4_DEPLOY_AND_VERIFY",
            "reason": "Cloudflare token is present in GitHub secrets and no wiring mismatch detected, while live edge is still non-200.",
            "next_action": "Dispatch router-edge Zone B deploy workflow on main, wait for completion, re-run this script to verify HTTP 200 + zone-b-cloudflare-edge.",
        }

    return {
        "branch": "BRANCH_2_BOOTSTRAP_DISPATCH_NEEDED",
        "reason": "Neither SEED_CLOUDFLARE_WORKERS_TOKEN nor CLOUDFLARE_API_TOKEN appears in repo or environment secrets; PR #8474 bootstrap preflight is already merged on main.",
        "next_action": "Dispatch the Cloudflare bootstrap workflow on main (or inspect bitwarden_sync_failure tail to restore secret delivery) before minting any new credential.",
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="One-Shot Router #8416 Blocker Discriminator")
    parser.add_argument("--repo-root", default=".", help="Path to local idp checkout")
    parser.add_argument("--repo", default="chidionyema/idp")
    parser.add_argument("--console-repo", default="chidionyema/ais-c7941f7d-olat-estate-console")
    parser.add_argument("--skip-live-edge", action="store_true")
    parser.add_argument("--skip-gh", action="store_true")
    parser.add_argument("--out", default="oneshot_verdict.json")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    edge = {"skipped": True} if args.skip_live_edge else probe_edge_health()
    workflows = audit_workflows(repo_root)
    gh_state = {"skipped": True} if args.skip_gh else audit_github_secrets_and_runs(args.repo, args.console_repo)
    decision = classify_branch(edge, workflows, gh_state)

    report = {
        "observed_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decision": decision,
        "live_edge": edge,
        "workflows": workflows,
        "github_state": gh_state,
    }
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(decision, indent=2))
    print(f"WRITTEN: {args.out}")
    return 0 if decision["branch"] == "BRANCH_0_ALREADY_OPERATIONAL" else 10


if __name__ == "__main__":
    sys.exit(main())
