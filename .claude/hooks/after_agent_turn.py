#!/usr/bin/env python3
"""Claude Code Stop hook: 8 token-efficiency mechanisms + idp-exec compliance gate.

Reads Claude Code's Stop-event stdin JSON, measures the session transcript,
runs observable efficiency metrics, and prints a compliance report.

ENFORCEMENT ARCHITECTURE (two layers, both required):
  Layer 1 — model-agnostic (proxy):  EstateRequestCeiling refuses any call
            carrying >128K estimated tokens, before a single token is billed.
            Registered in llm/config.base.yaml callbacks: ["otel","request_ceiling"].
            Fires for every estate process that routes through llm.mumchimp.com.
  Layer 2 — Claude Code sessions:    This hook (Stop) measures compliance and
            reports; context-guard-hook.py (UserPromptSubmit+PreToolUse) intercepts
            marathon sessions and blocks context-growing reads when shape is critical.

WHY BOTH:  Claude Code calls Anthropic directly, bypassing the proxy. Hook layer
           catches what the proxy cannot reach.
"""

import json
import os
import sys
import time

# Add idp root to path so platform.efficiency imports work.
# The hook file is at .claude/hooks/after_agent_turn.py; the root is two dirs up.
_IDP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _IDP not in sys.path:
    sys.path.insert(0, _IDP)

STATE_DIR = os.path.expanduser("~/.pi/agent/state/efficiency")
MAX_INPUT_TOKENS = int(os.environ.get("ESTATE_MAX_INPUT_TOKENS", "128000"))


def _load_state(session_id: str) -> dict:
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, f"{session_id}.json")
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {
            "turns": 0,
            "bash_calls": 0,
            "idp_exec_calls": 0,
            "mcp_calls": 0,
            "total_input_tokens": 0,
            "total_cache_read": 0,
            "compactions": 0,
            "proxy_refused": 0,
            "first_seen": time.time(),
        }


def _save_state(session_id: str, state: dict) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, f"{session_id}.json")
    try:
        with open(path, "w") as f:
            json.dump(state, f)
    except Exception:
        pass


def _measure_transcript(transcript_path: str, state: dict) -> dict:
    """Scan the last 400 KB of the transcript for this-turn metrics."""
    state["turns"] += 1
    if not transcript_path or not os.path.exists(transcript_path):
        return state

    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as f:
            f.seek(max(0, size - 400_000))
            tail = f.read().decode("utf-8", errors="replace")

        for line in tail.splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue

            etype = entry.get("type", "")

            # Tool calls
            if etype == "tool_use":
                name = entry.get("name", "")
                if name == "Bash":
                    state["bash_calls"] += 1
                    inp = entry.get("input") or {}
                    cmd = inp.get("command", "") if isinstance(inp, dict) else ""
                    if "idp-exec" in cmd:
                        state["idp_exec_calls"] += 1
                elif name.startswith("mcp__"):
                    state["mcp_calls"] += 1

            # Token usage (from assistant messages carrying usage blocks)
            usage = entry.get("usage") or {}
            if usage:
                state["total_input_tokens"] += int(usage.get("input_tokens", 0))
                state["total_cache_read"] += int(usage.get("cache_read_input_tokens", 0))

            # Compaction markers
            if etype == "system" and "compacted" in str(entry).lower():
                state["compactions"] += 1

            # Proxy refused calls (402/400 from the ceiling — message contains "estate's ceiling")
            if etype in ("tool_result", "error"):
                content = str(entry.get("content", "") or entry.get("error", ""))
                if "estate's ceiling" in content or "Refused before it was sent" in content:
                    state["proxy_refused"] += 1

    except Exception:
        pass

    return state


def _format_report(state: dict, session_id: str) -> str:
    bash = state["bash_calls"]
    idp_exec = state["idp_exec_calls"]
    raw_bash = bash - idp_exec

    # Compliance verdict for this session
    if raw_bash == 0:
        compliance = "PASS"
    else:
        compliance = f"FAIL — {raw_bash} raw Bash call(s) without bin/idp-exec"

    # Cache efficiency
    total_in = state["total_input_tokens"]
    total_cached = state["total_cache_read"]
    denom = total_in + total_cached
    cache_pct = round(100 * total_cached / denom, 1) if denom > 0 else 0.0

    # Proxy ceiling status
    refused = state["proxy_refused"]
    ceiling_line = (
        f"128K hard limit (model-agnostic) | {refused} call(s) refused this session"
        if refused
        else f"128K hard limit (model-agnostic) | 0 calls refused"
    )

    lines = [
        f"[token-efficiency] session={session_id[-12:]} turn={state['turns']}",
        f"  [1] Proxy ceiling:     {ceiling_line}",
        f"  [2] Cache hit rate:    {cache_pct}%  ({total_cached:,} cached / {total_in:,} fresh input tokens)",
        f"  [3] Bash compliance:   {compliance}",
        f"         bash_calls={bash}  idp_exec={idp_exec}  raw={raw_bash}",
        f"  [4] Compactions:       {state['compactions']}",
        f"  [5] MCP calls:         {state['mcp_calls']}",
        f"  [6-8] Dynamic pruning/compaction/gisting: session-shape enforcement",
        f"        via context-guard-hook.py (UserPromptSubmit+PreToolUse)",
    ]
    return "\n".join(lines)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        # Not a valid hook call — exit silently, never break the session.
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    transcript_path = data.get("transcript_path", "")

    state = _load_state(session_id)
    state = _measure_transcript(transcript_path, state)
    report = _format_report(state, session_id)
    _save_state(session_id, state)

    # Write for external tools to read
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(os.path.join(STATE_DIR, "efficiency-latest.txt"), "w") as f:
            f.write(report + "\n")
    except Exception:
        pass

    print(report)
    sys.exit(0)


if __name__ == "__main__":
    main()
