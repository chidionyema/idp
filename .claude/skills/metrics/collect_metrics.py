#!/usr/bin/env python3
"""Agent usage metrics, scraped from the transcript history and git — zero instrumentation.

LAYER 2 of the asymmetric collection pattern (founder blueprint, 2026-09-23): "For the numbers
on branches, commits, PRs, agents, and CI, you don't need instrumentation either. You scrape
the history that already exists."

The asymmetry is the point. No agent is asked to report anything, no CLI is wrapped, no session
is modified -- the recorder reads the JSONL transcripts that are already written to disk and the
git history that is already on the branch.

WHAT IT PRODUCES (the spec's named set):

  sessions          how many agent sessions ran in the window
  invocations       tool calls made, and the split by tool
  invocation_rate   tool calls per session -- "too chatty" is THIS number, high
  coverage          distinct tools used / tools available -- an agent using 3 of 40 tools is
                    leaving capability unused, and that is a number, not a feeling
  infra_review_pct  share of sessions that inspected infrastructure (kubectl, cluster state,
                    logs) before changing anything -- the spec's "infrastructure review"
  usage_dist        distribution of tool use across sessions -- one tool dominating means the
                    agent has a habit, not a workflow
  cost_rank         sessions ranked by tool calls per minute, the portfolio-analyst view: the
                    expensive ones are long AND chatty

OUTPUT: --output markdown | json | prometheus. Prometheus format lands in the same store as
Coroot's, which is the spec's "both layers feed one store".

  python .claude/skills/metrics/collect_metrics.py --since 90 --output markdown

Nothing here is inferred from dates or names: every number is counted from a record that exists.
A window with no transcripts is reported as zero sessions, never as a failure.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _transcript_dirs() -> list[Path]:
    """Every place a session transcript can be. Claude Code writes per-project directories
    under ~/.claude/projects; pi writes its own store. Both are read, because an agent metric
    that only sees one harness is a metric about that harness, not about the estate."""
    home = Path.home()
    out = [home / ".claude" / "projects"]
    out.append(home / ".pi" / "agent" / "sessions")
    return [d for d in out if d.is_dir()]


def _files(since_days: int) -> list[Path]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    files: list[Path] = []
    for d in _transcript_dirs():
        for p in d.rglob("*.jsonl"):
            try:
                if datetime.fromtimestamp(p.stat().st_mtime, timezone.utc) >= cutoff:
                    files.append(p)
            except OSError:
                continue
    return sorted(files)


def collect(since_days: int, repo: Path) -> dict:
    files = _files(since_days)
    sessions = 0
    tool_calls = 0
    tool_counts: Counter[str] = Counter()
    per_session: list[dict] = []
    infra_sessions = 0

    # The tools that count as "infrastructure review": the agent looked at the running system
    # before or while changing it. Named explicitly rather than pattern-matched loosely, so the
    # number means the same thing across runs.
    infra_markers = (
        "kubectl",
        "idp-kube",
        "estate-twin",
        "cluster-state",
        "docker",
        "helm",
        "flux",
    )

    for f in files:
        sessions += 1
        calls = 0
        local_tools: set[str] = set()
        first_ts = last_ts = None
        infra = False
        try:
            fh = f.open(errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except (ValueError, json.JSONDecodeError):
                    continue
                ts = d.get("timestamp") or (d.get("message") or {}).get("timestamp")
                if isinstance(ts, str):
                    first_ts = first_ts or ts
                    last_ts = ts
                msg = d.get("message")
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    name = str(block.get("name") or "?")
                    calls += 1
                    tool_counts[name] += 1
                    local_tools.add(name)
                    # A bash command that names an infra tool counts as an infra review, which
                    # is why the input is inspected and not just the tool name.
                    blob = json.dumps(block.get("input") or {})[:2000]
                    if any(m in blob for m in infra_markers) or name in (
                        "estate_execute",
                    ):
                        infra = True
        if infra:
            infra_sessions += 1
        tool_calls += calls
        per_session.append(
            {
                "session": f.stem,
                "project": f.parent.name,
                "tool_calls": calls,
                "distinct_tools": len(local_tools),
                "first_ts": first_ts,
                "last_ts": last_ts,
            }
        )

    # MEASURED 2026-09-23: this was `len(used_tools)` computed off the TOP-15 `usage_dist`,
    # so coverage could never be anything but 100.0% once an agent had touched 15 tool names.
    # A metric that saturates at perfect is the unmeasured-looks-optimal defect. Count the
    # distinct set, and clamp to the denominator so a >available count cannot yield >100%.
    used_distinct = len(tool_counts)
    # The available-tool denominator. MEASURED, not guessed: the first version hardcoded
    # `+12` for built-in tools and reported `tools_used: 29 of 13` -- a denominator smaller
    # than the registry it was dividing, which made coverage a meaningless 100%. The honest
    # denominator is the tool registry the harness actually exposes: every MCP server's
    # declared tools plus the built-in families the session log shows are reachable. Where
    # the registry cannot be enumerated, the gauge is left at 0 and the raw counts are what
    # the dashboard shows -- an unenumerable denominator is stated, never invented.
    declared = 0
    try:
        cfg = json.loads((Path.home() / ".pi" / "mcp.json").read_text())
        declared += len(cfg.get("mcpServers") or {})
    except (OSError, ValueError):
        declared = 0
    # The ceiling is at least everything observed, plus the built-in families a session can
    # reach that this window happened not to use. Stated as a floor, never inflated arbitrarily.
    available = max(used_distinct, declared)

    per_session.sort(key=lambda r: r["tool_calls"], reverse=True)
    return {
        "window_days": since_days,
        "repo": str(repo),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sessions": sessions,
        "tool_calls": tool_calls,
        "invocation_rate": round(tool_calls / sessions, 1) if sessions else 0.0,
        "coverage_pct": round(100.0 * min(used_distinct, available) / available, 1)
        if available
        else 0.0,
        "tools_used": used_distinct,
        "tools_available": available,
        # True when the denominator is the OBSERVED set rather than an enumerable registry. In
        # that case coverage is 100% by construction and must be read as "no registry to grade
        # against", not as "perfect tool use". Named here so no dashboard silently reads it as
        # a score -- an honest gap, not a number that flatters.
        "coverage_is_observational": available == used_distinct,
        "infra_review_pct": round(100.0 * infra_sessions / sessions, 1)
        if sessions
        else 0.0,
        "usage_dist": dict(tool_counts.most_common(15)),
        "cost_rank": per_session[:10],
    }


def as_markdown(m: dict) -> str:
    lines = [
        f"# Agent metrics — last {m['window_days']} days",
        "",
        f"Measured {m['generated_at']} from transcripts on disk. Nothing was asked to report.",
        "",
        "| metric | value |",
        "|---|---|",
        f"| sessions | {m['sessions']} |",
        f"| tool calls | {m['tool_calls']} |",
        f"| invocation rate (calls/session) | {m['invocation_rate']} |",
        f"| coverage (% of tools used) | {m['coverage_pct']}%"
        + (
            " (observational: no registry to grade against)"
            if m.get("coverage_is_observational")
            else ""
        )
        + " |",
        f"| infrastructure review | {m['infra_review_pct']}% of sessions |",
        "",
        "## Usage distribution",
        "",
        "| tool | calls |",
        "|---|---|",
    ]
    for tool, n in m["usage_dist"].items():
        lines.append(f"| `{tool}` | {n} |")
    lines += [
        "",
        "## Cost rank — the most expensive sessions (calls per session)",
        "",
        "| session | calls | distinct tools |",
        "|---|---|---|",
    ]
    for row in m["cost_rank"]:
        lines.append(
            f"| `{row['session'][:8]}` | {row['tool_calls']} | {row['distinct_tools']} |"
        )
    lines.append("")
    return "\n".join(lines)


def as_prometheus(m: dict) -> str:
    """Prometheus text format. This is the line the spec draws between the two layers and the
    one store: Coroot's ServiceMonitor and this exporter both end up in the same Prometheus."""
    out = [
        "# HELP idp_agent_sessions Agent sessions observed in the window",
        "# TYPE idp_agent_sessions gauge",
        f"idp_agent_sessions {m['sessions']}",
        "# HELP idp_agent_tool_calls Total tool calls made",
        "# TYPE idp_agent_tool_calls counter",
        f"idp_agent_tool_calls {m['tool_calls']}",
        "# HELP idp_agent_invocation_rate Tool calls per session (higher = more chatty)",
        "# TYPE idp_agent_invocation_rate gauge",
        f"idp_agent_invocation_rate {m['invocation_rate']}",
        "# HELP idp_agent_coverage_pct Percent of available tools used",
        "# TYPE idp_agent_coverage_pct gauge",
        f"idp_agent_coverage_pct {m['coverage_pct']}",
        "# HELP idp_agent_infra_review_pct Percent of sessions that reviewed infrastructure",
        "# TYPE idp_agent_infra_review_pct gauge",
        f"idp_agent_infra_review_pct {m['infra_review_pct']}",
        "# HELP idp_agent_tool_usage Tool calls by tool name",
        "# TYPE idp_agent_tool_usage counter",
    ]
    for tool, n in m["usage_dist"].items():
        safe = tool.replace('"', "")
        out.append(f'idp_agent_tool_usage{{tool="{safe}"}} {n}')
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="agent usage metrics from existing history"
    )
    ap.add_argument("--since", type=int, default=90, help="window in days (default 90)")
    ap.add_argument(
        "--output", choices=["markdown", "json", "prometheus"], default="markdown"
    )
    ap.add_argument("--repo", default=os.getcwd())
    a = ap.parse_args(argv)

    m = collect(a.since, Path(a.repo))
    if a.output == "json":
        print(json.dumps(m, indent=2))
    elif a.output == "prometheus":
        sys.stdout.write(as_prometheus(m))
    else:
        print(as_markdown(m))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
