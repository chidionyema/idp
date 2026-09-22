#!/usr/bin/env python3
"""Stop hook: enforce Jev usage for bounded decisions.

WHY THIS EXISTS (founding thesis, ADR 0030, 2026-09-21):
  Bounded decisions (tool selection, risk assessment, pass/fail judgments) should go through
  Jev (~230ms, $0.00002) rather than the LLM (5-20s, thousands of tokens). The JevLayer MCP
  plugin (`mcp/plugins/jev.py`) exposes `jev_choice`, `jev_score`, `jev_noul` — the estate's
  unified confidence-and-decision service.

WHAT IT ENFORCES. When a turn makes an expensive decision without first calling a Jev tool,
this hook blocks with exit 2. "Expensive decision" means:
  - Shell/Bash calls invoking consensus, verifier, guard, or judge logic
  - Direct MCP calls to mcp__estate__propose_*, mcp__estate__consensus_*, mcp__estate__verify_*

JEV TOOLS (must appear before the expensive call):
  - jev_choice, jev_score, jev_noul
  - mcp__estate__jev_choice, mcp__estate__jev_score, mcp__estate__jev_noul

EXEMPT (turns that do not trigger the gate):
  - Only read files, search, or ask questions
  - No shell or expensive MCP calls in the turn
  - A Jev tool was called in the turn before the expensive call

THE CLASSIFICATION IS TOTAL. Every turn lands in exactly one of PASS / BLOCK / EXEMPT.
The unknown case is PASS (fail-open), because this is a new enforcement and over-blocking
would drive bypass behavior. The gate logs every refusal to stderr for auditability.

LAW 38 — a fence a correct machine cannot satisfy is an outage. Release valve:
    IDP_JEV_GATE=0 <command>     one genuine emergency, typed deliberately
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

# Tools that count as a Jev pre-check (must appear BEFORE expensive calls)
JEV_TOOLS = frozenset({
    "jev_choice",
    "jev_score",
    "jev_noul",
    "mcp__estate__jev_choice",
    "mcp__estate__jev_score",
    "mcp__estate__jev_noul",
    # Also accept direct MCP tool names with the jev namespace
    "mcp__jev__choice",
    "mcp__jev__score",
    "mcp__jev__noul",
})

# Shell commands that indicate an expensive decision being made
# (tool selection, risk assessment, pass/fail judgments)
EXPENSIVE_SHELL_PATTERNS = frozenset({
    "consensus",
    "verifier",
    "verify",
    "judge",
    "verdict",
    "z3",
    "solver",
    "evaluate",
    "assess",
    "grade",
    "score",
    "classify",
})

# MCP tools that represent expensive operations that should be Jev-gated
EXPENSIVE_MCP_PATTERNS = frozenset({
    "mcp__estate__propose_",
    "mcp__estate__consensus_",
    "mcp__estate__verify_",
    "mcp__verdict__",
    "mcp__judge__",
})

# Tools that only read (exempt from this gate)
READ_ONLY_TOOLS = frozenset({
    "Read",
    "Glob",
    "Grep",
    "WebSearch",
    "WebFetch",
    "Search",
    "LS",
    "ListDirectory",
    "mcp__estate__get_estate_state",
    "mcp__estate__get_workload_state",
    "mcp__estate__get_workload_logs",
    "mcp__estate__recall",
    "mcp__estate__ask_holmes",
    "mcp__estate__get_catalog_drift",
})


def _blocks(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """The content blocks of one transcript line, or [] when it carries none."""
    message = entry.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    return content if isinstance(content, list) else []


def _is_expensive_shell_command(cmd: str) -> bool:
    """Check if a shell command represents an expensive decision."""
    cmd_lower = cmd.lower()
    return any(pattern in cmd_lower for pattern in EXPENSIVE_SHELL_PATTERNS)


def _is_expensive_mcp_tool(name: str) -> bool:
    """Check if an MCP tool name represents an expensive operation."""
    return any(name.startswith(prefix) for prefix in EXPENSIVE_MCP_PATTERNS)


def _is_read_only_tool(name: str) -> bool:
    """Check if a tool is read-only (exempt from this gate)."""
    if name in READ_ONLY_TOOLS:
        return True
    # Also exempt any mcp__*__get_* or mcp__*__list_* patterns
    if name.startswith("mcp__") and ("__get_" in name or "__list_" in name):
        return True
    return False


def _is_jev_tool(name: str) -> bool:
    """Check if a tool is a Jev decision tool."""
    return name in JEV_TOOLS


def _extract_tool_sequence(transcript_path: str) -> list[tuple[str, str]]:
    """Extract the sequence of tool calls from the most recent turn.

    Returns list of (tool_name, tool_input_summary) tuples.
    Only looks at the most recent assistant turn.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return []

    tools: list[tuple[str, str]] = []
    try:
        # Read the last 200KB to get the most recent turn
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as f:
            f.seek(max(0, size - 200_000))
            tail = f.read().decode("utf-8", errors="replace")

        # Find the most recent assistant entries
        lines = tail.strip().split("\n")
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except Exception:  # noqa: BLE001
                continue

            if not isinstance(entry, dict):
                continue

            entry_type = entry.get("type")
            if entry_type == "user":
                # Hit a user message, stop — we only want the current turn
                break

            if entry_type != "assistant":
                continue

            # Extract tool_use blocks
            for block in _blocks(entry):
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = block.get("name", "")
                inp = block.get("input", {})
                if isinstance(inp, dict):
                    # For Bash, extract the command
                    summary = inp.get("command", "") if name == "Bash" else str(inp)[:200]
                else:
                    summary = str(inp)[:200]
                tools.append((name, summary))
    except Exception:  # noqa: BLE001
        return []

    # Reverse to get chronological order (we read backwards)
    return list(reversed(tools))


def _check_jev_compliance(tool_sequence: list[tuple[str, str]]) -> tuple[str, str]:
    """Check if the tool sequence complies with Jev-first policy.

    Returns (verdict, message) where verdict is "PASS", "BLOCK", or "EXEMPT".
    """
    if not tool_sequence:
        return ("EXEMPT", "no tools called")

    saw_jev = False
    saw_expensive = False
    first_expensive_tool = ""
    first_expensive_detail = ""
    all_read_only = True

    for name, summary in tool_sequence:
        # Track if we see any non-read-only tools
        if not _is_read_only_tool(name):
            all_read_only = False

        # Track Jev calls
        if _is_jev_tool(name):
            saw_jev = True
            continue

        # Check for expensive Bash commands
        if name == "Bash" and _is_expensive_shell_command(summary):
            if not saw_jev:
                # Expensive call without prior Jev — violation
                saw_expensive = True
                first_expensive_tool = f"Bash ({summary[:50]}...)" if len(summary) > 50 else f"Bash ({summary})"
                first_expensive_detail = summary

        # Check for expensive MCP calls
        if _is_expensive_mcp_tool(name):
            if not saw_jev:
                saw_expensive = True
                first_expensive_tool = name
                first_expensive_detail = summary

    # Verdict logic
    if all_read_only:
        return ("EXEMPT", "read-only tools only")

    if saw_expensive:
        return (
            "BLOCK",
            f"expensive decision '{first_expensive_tool}' made without calling a Jev tool first"
        )

    return ("PASS", "no expensive decisions or Jev-gated properly")


def _refusal_message(expensive_tool: str, expensive_detail: str) -> str:
    """Format the refusal message for a Jev gate violation."""
    lines = [
        "[jev-gate] BLOCKED: expensive decision made without calling a Jev tool first.",
        "",
        f"  The turn made an expensive call: {expensive_tool}",
        "",
        "  ADR 0030 (JevLayer) requires bounded decisions to go through Jev first:",
        "    - jev_choice  (~230ms, $0.00002) for choosing from options",
        "    - jev_score   (~230ms, $0.00002) for rating on a scale",
        "    - jev_noul    (~230ms, $0.00002) for true/false with confidence",
        "",
        "  Instead of:",
        f"    <expensive call>  # 5-20s, thousands of tokens",
        "",
        "  Do:",
        "    jev_choice/jev_score/jev_noul  # 230ms gate",
        "    <expensive call>               # only if Jev says to proceed",
        "",
        "  Reference: docs/decisions/0030-jevlayer-unified-confidence-and-decision-service.md",
        "  Gate:      .claude/hooks/jev_decision_gate.py",
        "",
        "  Emergency release (typed deliberately, never scripted):",
        "    IDP_JEV_GATE=0",
    ]
    return "\n".join(lines)


def run(payload: dict[str, Any]) -> int:
    """Run the Jev decision gate on a Stop event."""
    # Emergency release
    if os.environ.get("IDP_JEV_GATE") == "0":
        sys.stderr.write("[jev-gate] RELEASED by IDP_JEV_GATE=0\n")
        return 0

    session_id = payload.get("session_id", "unknown")
    transcript_path = payload.get("transcript_path", "")

    # Extract the tool sequence from the most recent turn
    tool_sequence = _extract_tool_sequence(transcript_path)

    # Check compliance
    verdict, message = _check_jev_compliance(tool_sequence)

    if verdict == "EXEMPT":
        # Silent pass for read-only turns
        return 0

    if verdict == "PASS":
        # Compliant turn
        return 0

    if verdict == "BLOCK":
        # Violation — extract the expensive tool for the message
        for name, summary in tool_sequence:
            if name == "Bash" and _is_expensive_shell_command(summary):
                sys.stderr.write(_refusal_message(name, summary) + "\n")
                return 2
            if _is_expensive_mcp_tool(name):
                sys.stderr.write(_refusal_message(name, summary) + "\n")
                return 2

    # Default: pass (fail-open for unknown cases, with logging)
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - a malformed event may never brick the session
        return 0
    if not isinstance(payload, dict):
        return 0
    return run(payload)


if __name__ == "__main__":
    sys.exit(main())
