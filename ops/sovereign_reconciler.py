#!/usr/bin/env python3
"""
Sovereign Estate Reconciler (Zero-Dependency Closed-Loop Control Plane)

Implements the 5 Google SRE Inversion Invariants:
  1. Bounded Desired State (<= 1,500 context tokens, <= 3 active WIP directives)
  2. Pull-Only Blackbox Truth (live HTTP probes + GitHub API + secret expiry clock)
  3. Mechanical Error-Budget Freeze (exits non-zero under --gate when RED or BLIND)
  4. Single Materialized Founder Truth (ops/status.json + single edited Telegram msg)
  5. Deterministic Stateless Agent Boot Brief (ops/agent_brief.md, <= 1,000 tokens)

Standard library only (Python 3.9+). Zero pip installs required.

Gate law (v1.1): the gate FAILS CLOSED. Unknown = refuse.
  - Unreachable GitHub telemetry raises TELEMETRY_BLIND (P0) -> RED.
  - --dry-run raises TELEMETRY_UNVERIFIED (P0) -> RED. A gate that cannot
    observe real truth never certifies GREEN.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_CONFIG_PATH = Path("ops/desired_state.json")
DEFAULT_STATUS_PATH = Path("ops/status.json")
DEFAULT_BRIEF_PATH = Path("ops/agent_brief.md")
DEFAULT_HUD_DIR = Path("ops/hud")
DEFAULT_WORKFLOW_PATH = Path(".github/workflows/sovereign-reconciler.yml")


DEFAULT_DESIRED_STATE: Dict[str, Any] = {
    "schema_version": "1.0",
    "estate_name": "Meridian / IDP Sovereign Estate",
    "primary_repo": "chidionyema/idp",
    "default_branch": "main",
    "invariants": {
        "max_context_tokens": 1500,
        "max_wip_directives": 3,
        "max_tier0_endpoints": 5,
        "secret_warn_days": 14,
        "secret_critical_days": 7,
    },
    "rule_files_to_audit": [
        "AGENTS.md",
        "CLAUDE.md",
        ".cursorrules",
        "ops/desired_state.json",
    ],
    "tier0_endpoints": [
        {
            "id": "llm-edge",
            "name": "Cloudflare LLM Edge",
            "url": "https://llm.meridianlabs.cloud/health",
            "expected_status": 200,
            "timeout_sec": 8,
            "owner": "infra",
            "required": True,
        },
        {
            "id": "founder-surface",
            "name": "Founder Surface Pages",
            "url": "https://genesis-founder-surface.pages.dev",
            "expected_status": 200,
            "timeout_sec": 8,
            "owner": "control-plane",
            "required": True,
        },
    ],
    "allowed_workflows": [
        "sovereign-reconciler",
        "portal-app",
        "fast-gate",
    ],
    "secrets_watchlist": [
        {
            "name": "argon-sync",
            "scope": "GitHub Fine-Grained PAT (chidionyema/argon)",
            "expires_on": "2026-12-02",
            "owner": "founder",
        }
    ],
    "directives": [
        {
            "id": "P0-1",
            "title": "Restore Tier-0 Edge & Quarantine Zombie Crons",
            "owner": "cloud-agent",
            "status": "IN_PROGRESS",
            "acceptance_check": "llm.meridianlabs.cloud/health returns HTTP 200 (or explicitly retired) AND zero allowlisted workflows failing on main",
        },
        {
            "id": "P0-2",
            "title": "Rotate argon-sync PAT & Lock Thin-Client Mac",
            "owner": "founder",
            "status": "BLOCKED_MANUAL",
            "acceptance_check": "argon-sync expiry > 30 days in desired_state.json AND zero local Mac launchd/worktree loops running",
        },
        {
            "id": "P0-3",
            "title": "Compress Auto-Injected Context to <= 1,500 Tokens",
            "owner": "cloud-agent",
            "status": "IN_PROGRESS",
            "acceptance_check": "sovereign_reconciler.py reports context_tokens <= 1500 and emits ops/agent_brief.md",
        },
    ],
}


WORKFLOW_YAML = """name: sovereign-reconciler

on:
  schedule:
    - cron: "*/10 * * * *"
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: write
  actions: read
  checks: read
  pull-requests: read

concurrency:
  group: sovereign-reconciler-${{ github.ref }}
  cancel-in-progress: true

jobs:
  reconcile:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Run Blackbox Reconciliation
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          TELEGRAM_MESSAGE_ID: ${{ secrets.TELEGRAM_MESSAGE_ID }}
        run: |
          python3 ops/sovereign_reconciler.py \\
            --reconcile \\
            --emit-agent-brief \\
            --notify-telegram

      - name: Publish Status Artifact to HUD (main only)
        if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'
        run: |
          git config user.name "sovereign-reconciler[bot]"
          git config user.email "sovereign-reconciler@users.noreply.github.com"
          git add ops/status.json ops/hud/status.json ops/agent_brief.md
          if ! git diff --cached --quiet; then
            git commit -m "ops(reconciler): update materialized truth [skip ci]"
            git push
          fi

      - name: Enforce Error-Budget Gate on Feature PRs
        if: github.event_name == 'pull_request' && !startsWith(github.head_ref, 'p0/') && !startsWith(github.head_ref, 'ops/')
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python3 ops/sovereign_reconciler.py --reconcile --gate
"""


def utc_now_iso() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def estimate_tokens(text: str) -> int:
    # Conservative token estimate (~4 chars/token)
    return max(0, (len(text) + 3) // 4)


def audit_context_tokens(rule_files: List[str]) -> Dict[str, Any]:
    breakdown: List[Dict[str, Any]] = []
    total_tokens = 0
    for rel in rule_files:
        p = Path(rel)
        if p.is_file():
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                tok = estimate_tokens(content)
                total_tokens += tok
                breakdown.append(
                    {
                        "file": rel,
                        "exists": True,
                        "tokens": tok,
                        "bytes": len(content.encode("utf-8")),
                    }
                )
            except OSError as exc:
                breakdown.append(
                    {"file": rel, "exists": True, "tokens": 0, "error": str(exc)}
                )
        else:
            breakdown.append({"file": rel, "exists": False, "tokens": 0})
    return {"total_tokens": total_tokens, "files": breakdown}


def diagnose_http_failure(code: Optional[int], err_msg: str) -> str:
    if code == 525:
        return "Cloudflare 525: SSL handshake failed between Cloudflare edge and origin server (check origin cert / port 443)."
    if code == 526:
        return (
            "Cloudflare 526: Invalid origin SSL certificate under Full (Strict) mode."
        )
    if code == 522:
        return "Cloudflare 522: Origin connection timed out (host down or firewall blocking Cloudflare IPs)."
    if code == 502 or code == 503:
        return f"HTTP {code}: Upstream service unavailable or crash-looping."
    if "CERTIFICATE_VERIFY_FAILED" in err_msg:
        return "TLS verification failed: certificate expired or hostname mismatch."
    if "timed out" in err_msg.lower():
        return "Connection timed out before receiving response."
    return err_msg or "Probe failed."


def probe_endpoint(ep: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    url = ep["url"]
    expected = int(ep.get("expected_status", 200))
    timeout = float(ep.get("timeout_sec", 8))

    if dry_run:
        return {
            "id": ep["id"],
            "name": ep["name"],
            "url": url,
            "owner": ep.get("owner", "unassigned"),
            "required": bool(ep.get("required", True)),
            "expected_status": expected,
            "observed_status": None,
            "ok": False,
            "verified": False,
            "latency_ms": 0,
            "diagnostic": "DRY_RUN: live probe skipped",
        }

    start = time.monotonic()
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "SovereignReconciler/1.0 (+blackbox-probe)"},
    )
    ctx = ssl.create_default_context()
    observed_status: Optional[int] = None
    ok = False
    diagnostic = "OK"

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            observed_status = int(resp.status)
            ok = observed_status == expected
            if not ok:
                diagnostic = f"Expected HTTP {expected}, got HTTP {observed_status}"
    except urllib.error.HTTPError as exc:
        observed_status = int(exc.code)
        ok = observed_status == expected
        diagnostic = "OK" if ok else diagnose_http_failure(observed_status, str(exc))
    except Exception as exc:
        observed_status = None
        ok = False
        diagnostic = diagnose_http_failure(None, str(exc))

    latency_ms = int((time.monotonic() - start) * 1000)
    return {
        "id": ep["id"],
        "name": ep["name"],
        "url": url,
        "owner": ep.get("owner", "unassigned"),
        "required": bool(ep.get("required", True)),
        "expected_status": expected,
        "observed_status": observed_status,
        "ok": ok,
        "verified": True,
        "latency_ms": latency_ms,
        "diagnostic": diagnostic,
    }


def github_api_get(path: str, token: str) -> Tuple[Optional[Any], Optional[str]]:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "SovereignReconciler/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as exc:
        return None, f"GitHub API HTTP {exc.code} on {path}"
    except Exception as exc:
        return None, f"GitHub API error on {path}: {exc}"


def inspect_github(
    repo: str,
    branch: str,
    allowed_workflows: List[str],
    token: Optional[str],
    dry_run: bool = False,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "repo": repo,
        "branch": branch,
        "connected": False,
        "head_sha": "UNKNOWN",
        "open_prs": None,
        "stale_prs_7d": None,
        "allowlisted_failures": [],
        "zombie_failures": [],
        "recent_runs": [],
        "error": None,
    }

    if dry_run:
        result["error"] = "DRY_RUN: live GitHub telemetry skipped."
        return result
    if not token:
        result["error"] = "GITHUB_TOKEN not set (live GitHub telemetry unavailable)."
        return result

    # 1. Head commit SHA
    branch_data, err = github_api_get(
        f"/repos/{repo}/branches/{urllib.parse.quote(branch)}", token
    )
    if err or not isinstance(branch_data, dict):
        result["error"] = err or "Failed to fetch branch info"
        return result

    result["connected"] = True
    result["head_sha"] = str(branch_data.get("commit", {}).get("sha", "UNKNOWN"))[:12]

    # 2. Recent workflow runs on default branch (deduplicated by workflow name -> latest state)
    runs_data, runs_err = github_api_get(
        f"/repos/{repo}/actions/runs?branch={urllib.parse.quote(branch)}&per_page=40",
        token,
    )
    if not runs_err and isinstance(runs_data, dict):
        seen_workflows: Dict[str, Dict[str, Any]] = {}
        allowed_lower = {w.lower() for w in allowed_workflows}
        for run in runs_data.get("workflow_runs", []):
            wf_name = str(run.get("name", "unknown"))
            if wf_name in seen_workflows:
                continue
            conclusion = run.get("conclusion") or run.get("status") or "unknown"
            entry = {
                "name": wf_name,
                "status": run.get("status"),
                "conclusion": conclusion,
                "event": run.get("event"),
                "updated_at": run.get("updated_at"),
                "html_url": run.get("html_url"),
                "allowlisted": wf_name.lower() in allowed_lower,
            }
            seen_workflows[wf_name] = entry
            if conclusion in {
                "failure",
                "timed_out",
                "startup_failure",
                "action_required",
            }:
                if entry["allowlisted"]:
                    result["allowlisted_failures"].append(entry)
                else:
                    result["zombie_failures"].append(entry)
        result["recent_runs"] = list(seen_workflows.values())

    # 3. Open & stale PR count
    prs_data, prs_err = github_api_get(
        f"/repos/{repo}/pulls?state=open&per_page=100", token
    )
    if not prs_err and isinstance(prs_data, list):
        now = dt.datetime.now(dt.timezone.utc)
        stale = 0
        for pr in prs_data:
            updated = pr.get("updated_at")
            if updated:
                try:
                    ts = dt.datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    if (now - ts).days >= 7:
                        stale += 1
                except ValueError:
                    pass
        result["open_prs"] = len(prs_data)
        result["stale_prs_7d"] = stale

    return result


def evaluate_secrets(
    watchlist: List[Dict[str, Any]], warn_days: int, critical_days: int
) -> List[Dict[str, Any]]:
    today = dt.datetime.now(dt.timezone.utc).date()
    evaluated: List[Dict[str, Any]] = []
    for item in watchlist:
        expires_str = str(item.get("expires_on", ""))
        days_left: Optional[int] = None
        severity = "UNKNOWN"
        try:
            exp_date = dt.date.fromisoformat(expires_str)
            days_left = (exp_date - today).days
            if days_left <= critical_days:
                severity = "CRITICAL"
            elif days_left <= warn_days:
                severity = "WARN"
            else:
                severity = "OK"
        except ValueError:
            severity = "INVALID_DATE"

        evaluated.append(
            {
                "name": item.get("name", "unnamed"),
                "scope": item.get("scope", ""),
                "owner": item.get("owner", "founder"),
                "expires_on": expires_str,
                "days_remaining": days_left,
                "severity": severity,
            }
        )
    return evaluated


def reconcile(
    config: Dict[str, Any],
    github_token: Optional[str],
    dry_run: bool = False,
) -> Dict[str, Any]:
    inv = config.get("invariants", {})
    max_tokens = int(inv.get("max_context_tokens", 1500))
    max_wip = int(inv.get("max_wip_directives", 3))
    max_ep = int(inv.get("max_tier0_endpoints", 5))
    warn_days = int(inv.get("secret_warn_days", 14))
    crit_days = int(inv.get("secret_critical_days", 7))

    # 1. Context Token Audit
    context_audit = audit_context_tokens(config.get("rule_files_to_audit", []))
    context_ok = context_audit["total_tokens"] <= max_tokens

    # 2. WIP & Surface Cardinality Audit
    directives = config.get("directives", [])
    active_directives = [
        d for d in directives if str(d.get("status", "")).upper() != "DONE"
    ]
    wip_ok = len(active_directives) <= max_wip

    endpoints_cfg = config.get("tier0_endpoints", [])
    endpoints_cardinality_ok = len(endpoints_cfg) <= max_ep

    # 3. Concurrent Blackbox HTTP Probes
    probes: List[Dict[str, Any]] = []
    if endpoints_cfg:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(8, len(endpoints_cfg))
        ) as pool:
            probes = list(
                pool.map(lambda ep: probe_endpoint(ep, dry_run=dry_run), endpoints_cfg)
            )

    # 4. GitHub Trunk & Workflow Audit
    gh_state = inspect_github(
        repo=str(config.get("primary_repo", "")),
        branch=str(config.get("default_branch", "main")),
        allowed_workflows=list(config.get("allowed_workflows", [])),
        token=github_token,
        dry_run=dry_run,
    )

    # 5. Credential Cliff Evaluation
    secrets_eval = evaluate_secrets(
        config.get("secrets_watchlist", []),
        warn_days=warn_days,
        critical_days=crit_days,
    )

    # 6. Compute Deterministic Error Budget (FAIL CLOSED: unknown = refuse)
    blockers: List[Dict[str, str]] = []

    # v1.1 FAIL-CLOSED: if live truth is unavailable, the budget can never be GREEN.
    unverified_probe = any(p.get("verified") is False for p in probes)
    telemetry_blind = bool(gh_state.get("error")) or unverified_probe
    if telemetry_blind:
        reason = gh_state.get("error") or "one or more Tier-0 probes were not executed"
        blockers.append(
            {
                "code": "TELEMETRY_BLIND",
                "severity": "P0",
                "target": "error_budget",
                "detail": f"Live truth unavailable ({reason}). A blind reconciler cannot certify GREEN.",
                "action": "Restore telemetry (GITHUB_TOKEN set, network up, no --dry-run) and re-run --reconcile.",
            }
        )

    for p in probes:
        if p["required"] and not p["ok"]:
            blockers.append(
                {
                    "code": "TIER0_ENDPOINT_DOWN",
                    "severity": "P0",
                    "target": p["url"],
                    "detail": f"{p['name']} returned {p['observed_status']} (expected {p['expected_status']}): {p['diagnostic']}",
                    "action": f"Fix {p['id']} immediately OR mark retired in ops/desired_state.json.",
                }
            )

    for s in secrets_eval:
        if s["severity"] in {"CRITICAL", "INVALID_DATE"}:
            blockers.append(
                {
                    "code": "SECRET_EXPIRY_CLIFF",
                    "severity": "P0",
                    "target": s["name"],
                    "detail": f"Credential '{s['name']}' expires in {s['days_remaining']} days ({s['expires_on']}).",
                    "action": f"Rotate {s['name']} now and update expires_on in ops/desired_state.json.",
                }
            )

    for wf in gh_state.get("allowlisted_failures", []):
        blockers.append(
            {
                "code": "TRUNK_CI_RED",
                "severity": "P0",
                "target": wf["name"],
                "detail": f"Allowlisted workflow '{wf['name']}' failed on {gh_state['branch']}.",
                "action": f"Fix failing trunk workflow '{wf['name']}' before merging any feature PR.",
            }
        )

    if not context_ok:
        blockers.append(
            {
                "code": "CONTEXT_TOKEN_OVERFLOW",
                "severity": "P0",
                "target": "rule_files_to_audit",
                "detail": f"Auto-injected rules total {context_audit['total_tokens']} tokens (cap: {max_tokens}).",
                "action": "Archive legacy prose rules and compress root agent instructions below 1,500 tokens.",
            }
        )

    if not wip_ok:
        blockers.append(
            {
                "code": "WIP_LIMIT_EXCEEDED",
                "severity": "P1",
                "target": "directives",
                "detail": f"{len(active_directives)} active directives exceed Little's Law WIP cap of {max_wip}.",
                "action": "Pause or close excess directives in ops/desired_state.json.",
            }
        )

    if not endpoints_cardinality_ok:
        blockers.append(
            {
                "code": "SURFACE_SPRAWL",
                "severity": "P1",
                "target": "tier0_endpoints",
                "detail": f"{len(endpoints_cfg)} Tier-0 endpoints exceed cap of {max_ep}.",
                "action": "Prune non-critical endpoints from Tier-0.",
            }
        )

    is_green = len(blockers) == 0
    error_budget = {
        "status": "GREEN" if is_green else "RED_FREEZE",
        "feature_merges_allowed": is_green,
        "fail_closed": telemetry_blind,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "zombie_workflow_count": len(gh_state.get("zombie_failures", [])),
    }

    return {
        "schema_version": "1.1",
        "reconciled_at_utc": utc_now_iso(),
        "estate_name": config.get("estate_name", "Sovereign Estate"),
        "primary_repo": config.get("primary_repo", ""),
        "error_budget": error_budget,
        "invariants": {
            "max_context_tokens": max_tokens,
            "observed_context_tokens": context_audit["total_tokens"],
            "context_ok": context_ok,
            "max_wip_directives": max_wip,
            "active_wip_directives": len(active_directives),
            "wip_ok": wip_ok,
            "max_tier0_endpoints": max_ep,
            "active_tier0_endpoints": len(endpoints_cfg),
            "endpoints_cardinality_ok": endpoints_cardinality_ok,
        },
        "context_audit": context_audit,
        "tier0_probes": probes,
        "github": gh_state,
        "secrets": secrets_eval,
        "directives": directives,
    }


def compile_agent_brief(status: Dict[str, Any]) -> str:
    """Compile a deterministic, <= 1,000-token boot brief for every stateless agent."""
    eb = status["error_budget"]
    inv = status["invariants"]
    lines: List[str] = [
        f"# SOVEREIGN AGENT BOOT BRIEF ({status['reconciled_at_utc']})",
        f"- **Estate:** {status['estate_name']} (`{status['primary_repo']}` @ `{status['github'].get('head_sha', 'UNKNOWN')}`)",
        f"- **Error Budget:** `{eb['status']}` | Feature Merges Allowed: `{eb['feature_merges_allowed']}` | Fail-Closed: `{eb['fail_closed']}`",
        f"- **Governance Caps:** Context `{inv['observed_context_tokens']}/{inv['max_context_tokens']}` tokens | WIP `{inv['active_wip_directives']}/{inv['max_wip_directives']}`",
        "",
        "## MANDATORY EXECUTION RULES",
        "1. You are stateless. Do NOT read legacy Drive zips, local Mac memory, or chat history.",
        "2. If Error Budget is `RED_FREEZE`, ONLY work on the P0 blockers listed below. Refuse feature requests.",
        "3. Never self-certify success; prove closure via `python3 ops/sovereign_reconciler.py --reconcile`.",
        "",
        "## ACTIVE BLOCKERS (FIX IN ORDER)",
    ]

    if not eb["blockers"]:
        lines.append("- None. Estate is GREEN; execute next active directive below.")
    else:
        for i, b in enumerate(eb["blockers"], 1):
            lines.append(
                f"{i}. **[{b['severity']} {b['code']}]** `{b['target']}` -> {b['detail']} | **Action:** {b['action']}"
            )

    zombies = status["github"].get("zombie_failures", [])
    if zombies:
        names = ", ".join(z["name"] for z in zombies[:8])
        lines.append(f"- **Zombie Crons to Quarantine (Non-Tier-0 noise):** `{names}`")

    lines.append("")
    lines.append("## CANONICAL DIRECTIVES (SINGLE SOURCE OF TRUTH)")
    for d in status["directives"]:
        lines.append(
            f"- **{d['id']} [{d['status']}] ({d['owner']}):** {d['title']} — *Done when:* {d['acceptance_check']}"
        )

    return "\n".join(lines) + "\n"


def send_or_edit_telegram(status: Dict[str, Any]) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    msg_id = os.environ.get("TELEGRAM_MESSAGE_ID", "").strip()
    if not bot_token or not chat_id:
        return

    eb = status["error_budget"]
    icon = "GREEN" if eb["status"] == "GREEN" else "RED FREEZE"
    top_blockers = (
        "\n".join(
            f"- [{b['code']}] {b['target']}: {b['action']}" for b in eb["blockers"][:4]
        )
        or "- All Tier-0 systems nominal."
    )

    text = (
        f"[{icon}] {status['estate_name']}\n"
        f"UTC: {status['reconciled_at_utc']} | SHA: {status['github'].get('head_sha', 'UNKNOWN')}\n"
        f"Blockers: {eb['blocker_count']} | Zombie Crons: {eb['zombie_workflow_count']}\n"
        f"Tokens: {status['invariants']['observed_context_tokens']}/{status['invariants']['max_context_tokens']}\n\n"
        f"Top Actions:\n{top_blockers}"
    )

    method = "editMessageText" if msg_id else "sendMessage"
    payload: Dict[str, Any] = {"chat_id": chat_id, "text": text}
    if msg_id:
        payload["message_id"] = int(msg_id)

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            resp.read()
    except Exception as exc:
        print(f"[warn] Telegram update failed ({method}): {exc}", file=sys.stderr)


def scaffold_repo(
    config_path: Path, workflow_path: Path, hud_dir: Path, force: bool = False
) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    hud_dir.mkdir(parents=True, exist_ok=True)

    if not config_path.exists() or force:
        config_path.write_text(
            json.dumps(DEFAULT_DESIRED_STATE, indent=2) + "\n", encoding="utf-8"
        )
        print(f"[init] Wrote {config_path}")
    else:
        print(f"[init] Skipped existing {config_path} (use --force to overwrite)")

    if not workflow_path.exists() or force:
        workflow_path.write_text(WORKFLOW_YAML, encoding="utf-8")
        print(f"[init] Wrote {workflow_path}")
    else:
        print(f"[init] Skipped existing {workflow_path} (use --force to overwrite)")


def print_terminal_summary(status: Dict[str, Any]) -> None:
    eb = status["error_budget"]
    inv = status["invariants"]
    print("=" * 72)
    print(f" SOVEREIGN RECONCILER :: {status['estate_name']}")
    print(
        f" UTC: {status['reconciled_at_utc']} | STATUS: {eb['status']} | SHA: {status['github'].get('head_sha')}"
    )
    print(
        f" Fail-Closed    : {eb['fail_closed']} (blind telemetry can never certify GREEN)"
    )
    print("=" * 72)
    print(
        f" Context Tokens : {inv['observed_context_tokens']} / {inv['max_context_tokens']} "
        f"({'OK' if inv['context_ok'] else 'OVERFLOW'})"
    )
    print(
        f" Active WIP     : {inv['active_wip_directives']} / {inv['max_wip_directives']} "
        f"({'OK' if inv['wip_ok'] else 'EXCEEDED'})"
    )
    probes = status["tier0_probes"]
    print(
        f" Tier-0 Probes  : {sum(1 for p in probes if p['ok'])}/{len(probes)} UP "
        f"({sum(1 for p in probes if p.get('verified'))} verified live)"
    )
    print(
        f" Zombie Crons   : {eb['zombie_workflow_count']} non-allowlisted failing workflows"
    )
    if eb["blockers"]:
        print("-" * 72)
        print(" P0/P1 BLOCKERS (ERROR BUDGET EXHAUSTED — STOP THE LINE):")
        for idx, b in enumerate(eb["blockers"], 1):
            print(f"  {idx}. [{b['severity']}] {b['code']} ({b['target']})")
            print(f"     Detail : {b['detail']}")
            print(f"     Action : {b['action']}")
    else:
        print("-" * 72)
        print(" ALL INVARIANTS GREEN — FEATURE EXECUTION UNLOCKED.")
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sovereign Closed-Loop Estate Reconciler"
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Scaffold desired_state.json and GitHub Actions workflow",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing scaffolded files with --init",
    )
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="Run blackbox reconciliation and emit status.json",
    )
    parser.add_argument(
        "--emit-agent-brief",
        action="store_true",
        help="Compile deterministic <=1000-token agent_brief.md",
    )
    parser.add_argument(
        "--notify-telegram",
        action="store_true",
        help="Edit single pinned Telegram status message",
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help="Exit 2 if Error Budget is RED_FREEZE or telemetry is blind (CI merge blocker)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip external HTTP/GitHub calls (gate always fails closed)",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--out", type=Path, default=DEFAULT_STATUS_PATH)
    parser.add_argument("--brief-out", type=Path, default=DEFAULT_BRIEF_PATH)
    parser.add_argument("--hud-dir", type=Path, default=DEFAULT_HUD_DIR)
    args = parser.parse_args()

    if not any([args.init, args.reconcile, args.emit_agent_brief]):
        parser.print_help()
        return 1

    if args.init:
        scaffold_repo(
            args.config, DEFAULT_WORKFLOW_PATH, args.hud_dir, force=args.force
        )

    if args.reconcile or args.emit_agent_brief:
        if not args.config.exists():
            print(
                f"[error] Missing {args.config}. Run with --init first.",
                file=sys.stderr,
            )
            return 1

        config = json.loads(args.config.read_text(encoding="utf-8"))
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        status = reconcile(config, github_token=token, dry_run=args.dry_run)

        args.out.parent.mkdir(parents=True, exist_ok=True)
        status_json = json.dumps(status, indent=2) + "\n"
        args.out.write_text(status_json, encoding="utf-8")

        args.hud_dir.mkdir(parents=True, exist_ok=True)
        (args.hud_dir / "status.json").write_text(status_json, encoding="utf-8")

        print_terminal_summary(status)

        if args.emit_agent_brief:
            brief = compile_agent_brief(status)
            args.brief_out.parent.mkdir(parents=True, exist_ok=True)
            args.brief_out.write_text(brief, encoding="utf-8")
            print(f"[brief] Wrote {args.brief_out} (~{estimate_tokens(brief)} tokens)")

        if args.notify_telegram:
            send_or_edit_telegram(status)

        if args.gate and status["error_budget"]["status"] != "GREEN":
            fail_closed = status["error_budget"]["fail_closed"]
            tag = "FAIL_CLOSED (telemetry blind)" if fail_closed else "RED_FREEZE"
            print(
                f"[gate] BLOCKED: Error budget is {tag}. Feature merges halted.",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
