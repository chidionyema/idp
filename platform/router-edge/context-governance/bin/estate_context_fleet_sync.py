#!/usr/bin/env python3
"""Meridian Fleet Context Compiler & Pre-Push Bloat/Bypass Gate.

Two deterministic modes:
  1. `--compile --repo-root <path>`: Generates lean, pinned, policy-compiled fleet configs
     for Cline, Codex, OpenCode, Aider, and Lane 3 agent-sandbox from
     `governance/context-policy.v1.json` (zero manual drift).
  2. `--audit --repo-root <path>`: Fail-closed gate for `bin/pre-push-wall.py` and
     GitHub Actions (`context-budget-gate.yml`). Blocks PRs that:
       - Push auto-injected instruction files over 1,500 tokens
       - Declare >10 always-on MCP tools in active agent configs
       - Reintroduce raw upstream provider URLs bypassing `llm.meridianlabs.cloud/v1`
       - Reintroduce retired Zone A (`~/.estate`, `launchctl`) paths

Exit codes: 0 = PASS, 43 = CONTEXT_GOVERNANCE_VIOLATION (fail-closed).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

AUTO_INJECTED_FILES = (
    "AGENTS.md",
    "CLINE.md",
    ".clinerules",
    ".github/copilot-instructions.md",
)

ZONE_A_FORBIDDEN = ("~/.estate", "launchctl", "LaunchAgents", "LaunchDaemons")


def est_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(math.ceil((len(text.encode("utf-8")) / 3.2) * 1.15)))


def compile_fleet_configs(policy: Dict[str, Any], out_root: Path) -> List[str]:
    written: List[str] = []
    gw = policy["gateway_base_url"]
    inv = policy["global_invariants"]
    roles = policy["roles"]

    # 1. Lean Cline core rule (< 350 tokens — prevents Turn-1 30k tax)
    cline_rule = f"""# Meridian Cline Core Rules (Compiled from context-policy.v1.json)
- Gateway: route all inference via `{gw}` (`role:ops-dispatch` default; reasoning clamped to `low`).
- Zone B Only: never edit or inspect `~/.estate` or macOS `launchctl`.
- Token Discipline: never dump raw CI logs (>25 lines) or full multi-hundred-line files unless isolating a proven 1-line fault. Run single-shot scripts emitting compact JSON.
- Rotation: on header `X-Meridian-Context-Directive: CHECKPOINT_AND_ROTATE`, stop immediately and emit a structured handoff packet (`mission_id`, `target_repo`, `target_sha`, `acceptance_receipt_contract`, `next_discriminating_step`, `pinned_failure_receipts`) before starting a fresh task.
- Epistemic Law: never cite Drive JSONs or chat summaries (`TIER_2`) as primary facts; never declare `OPERATIONAL` from `raw.githubusercontent.com`.
"""
    p_cline = out_root / ".clinerules" / "00-meridian-context-core.md"
    p_cline.parent.mkdir(parents=True, exist_ok=True)
    p_cline.write_text(cline_rule, encoding="utf-8")
    written.append(str(p_cline.relative_to(out_root)))

    # 2. Lean Codex / OpenCode / Aider core rule (< 350 tokens)
    agents_core = f"""# Meridian Fleet Context Contract (Compiled from context-policy.v1.json)
- All fleet agents route through `{gw}` with explicit `X-Meridian-Role`, `X-Meridian-Mission-Id`, and `X-Meridian-Session-Id`.
- Turn-1 auto-injected rule budget: <= {inv["max_auto_injected_rules_tokens"]} tokens total; always-on MCP tools: <= {inv["max_always_on_mcp_tools"]}.
- Externalize any tool output > {inv["externalize_tool_result_bytes"]} bytes to file pointers while pinning the last 15 lines of failure traces verbatim.
- Never mutate system prompt or tool schemas mid-session (protects KV-cache prefix).
- Sub-agents receive compiled briefs <= {inv["subagent_max_brief_tokens"]} tokens; never forward full parent transcripts.
- On `CHECKPOINT_AND_ROTATE`, flush an atomic handoff packet at the next tool boundary; use `X-Meridian-Critical-Section` only to complete an in-flight commit/push/rollback (max {inv["critical_section_max_turns"]} turns).
"""
    p_agents = out_root / "AGENTS.md"
    if p_agents.exists() and not p_agents.read_text(encoding="utf-8").startswith(
        "# Meridian Fleet Context Contract (Compiled from context-policy.v1.json)"
    ):
        p_agents = out_root / ".meridian" / "context-core.md"
        p_agents.parent.mkdir(parents=True, exist_ok=True)
    p_agents.write_text(agents_core, encoding="utf-8")
    written.append(str(p_agents.relative_to(out_root)))

    # 3. Unified fleet client gateway profile (Cline / Codex / OpenCode / agent-sandbox)
    fleet_profile = {
        "schema": "urn:estate:fleet:gateway-profile:v1",
        "openai_compatible_base_url": gw,
        "auth_env_var": "MERIDIAN_CLIENT_KEY",
        "direct_upstream_keys_allowed": False,
        "surfaces": {
            "cline": {
                "default_role": "role:ops-dispatch",
                "reasoning_effort": roles["role:ops-dispatch"][
                    "reasoning_effort_clamp"
                ],
            },
            "codex_cli": {
                "default_role": "role:surgical-patch",
                "reasoning_effort": roles["role:surgical-patch"][
                    "reasoning_effort_clamp"
                ],
            },
            "opencode": {
                "default_role": "role:surgical-patch",
                "reasoning_effort": roles["role:surgical-patch"][
                    "reasoning_effort_clamp"
                ],
            },
            "agent_sandbox": {
                "default_role": "role:sandbox-legion",
                "reasoning_effort": roles["role:sandbox-legion"][
                    "reasoning_effort_clamp"
                ],
            },
            "architecture_review": {
                "default_role": "role:architecture-audit",
                "reasoning_effort": roles["role:architecture-audit"][
                    "reasoning_effort_clamp"
                ],
            },
        },
    }
    p_prof = out_root / ".meridian" / "fleet-gateway-profile.json"
    p_prof.parent.mkdir(parents=True, exist_ok=True)
    p_prof.write_text(
        json.dumps(fleet_profile, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    written.append(str(p_prof.relative_to(out_root)))

    return written


def audit_repo(policy: Dict[str, Any], repo_root: Path) -> Tuple[bool, Dict[str, Any]]:
    inv = policy["global_invariants"]
    max_rule_tokens = int(inv["max_auto_injected_rules_tokens"])
    max_mcp_tools = int(inv["max_always_on_mcp_tools"])
    forbidden_hosts = tuple(inv["forbidden_direct_provider_hosts"])

    violations: List[str] = []
    rule_token_total = 0
    scanned_rules: Dict[str, int] = {}

    # 1. Measure all auto-injected rule files (including .clinerules/*.md)
    candidates: List[Path] = []
    for rel in AUTO_INJECTED_FILES:
        p = repo_root / rel
        if p.is_file():
            candidates.append(p)
        elif p.is_dir():
            candidates.extend(sorted(p.rglob("*.md")))

    for p in candidates:
        txt = p.read_text(encoding="utf-8", errors="replace")
        toks = est_tokens(txt)
        rel = p.relative_to(repo_root).as_posix()
        scanned_rules[rel] = toks
        rule_token_total += toks
        for bad in ZONE_A_FORBIDDEN:
            if bad in txt and "never edit or inspect" not in txt.lower():
                violations.append(f"FC_ZONE_A_DARWIN_REGRESSION:{rel}:{bad}")

    if rule_token_total > max_rule_tokens:
        violations.append(
            f"FC_TURN1_BLOATED_RULES:total_{rule_token_total}_exceeds_{max_rule_tokens}"
        )

    # 2. Check active MCP server config JSONs for >10 always-on tools or raw provider bypass
    for cfg_name in (
        ".mcp.json",
        "mcp.json",
        ".meridian/mcp-servers.json",
        ".meridian/fleet-gateway-profile.json",
    ):
        cfg_p = repo_root / cfg_name
        if not cfg_p.is_file():
            continue
        raw_txt = cfg_p.read_text(encoding="utf-8", errors="replace")
        for host in forbidden_hosts:
            if host in raw_txt:
                violations.append(f"FC_GATEWAY_BYPASS_RAW_PROVIDER:{cfg_name}:{host}")
        try:
            data = json.loads(raw_txt)
            tools_list = data.get("always_on_tools") or data.get("tools") or []
            if isinstance(tools_list, list) and len(tools_list) > max_mcp_tools:
                violations.append(
                    f"FC_MCP_TOOL_CEILING_EXCEEDED:{cfg_name}:got_{len(tools_list)}_max_{max_mcp_tools}"
                )
        except json.JSONDecodeError:
            violations.append(f"ERR_MALFORMED_CONFIG_JSON:{cfg_name}")

    report = {
        "passed": len(violations) == 0,
        "auto_injected_rule_tokens_total": rule_token_total,
        "auto_injected_rule_tokens_cap": max_rule_tokens,
        "scanned_rule_files": scanned_rules,
        "violations": sorted(set(violations)),
    }
    return len(violations) == 0, report


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Meridian Fleet Context Compiler & Audit Gate"
    )
    parser.add_argument(
        "--policy", required=True, help="Path to context-policy.v1.json"
    )
    parser.add_argument("--repo-root", required=True, help="Target repository root")
    parser.add_argument(
        "--compile", action="store_true", help="Compile fleet configs into repo-root"
    )
    parser.add_argument(
        "--audit", action="store_true", help="Audit repo-root against policy"
    )
    args = parser.parse_args(argv)

    policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
    root = Path(args.repo_root).resolve()

    if args.compile:
        written = compile_fleet_configs(policy, root)
        print(json.dumps({"compiled_files": written}, indent=2))

    if args.audit or not args.compile:
        ok, report = audit_repo(policy, root)
        print(json.dumps(report, indent=2))
        return 0 if ok else 43
    return 0


if __name__ == "__main__":
    sys.exit(main())
