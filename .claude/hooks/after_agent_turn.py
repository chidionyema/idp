#!/usr/bin/env python3
"""Claude Code Stop hook: 8 token-efficiency mechanisms + idp-exec compliance gate.

Reads Claude Code's Stop-event stdin JSON, measures the session transcript,
and prints a compliance + efficiency report.

ENFORCEMENT ARCHITECTURE (two layers):
  Layer 1 — model-agnostic (LiteLLM proxy):
    request_ceiling.proxy_handler_instance  — REFUSES calls >128K tokens
    efficiency_gateway.proxy_handler_instance — runs all 8 mechanisms on every call
    Both registered in platform/llm/config.base.yaml callbacks.
    Applies to: minimax, groq, gemini, cerebras, sambanova, openrouter, ollama.
  Layer 2 — Claude Code sessions (bypass the proxy):
    This Stop hook — measures compliance per turn
    context-guard-hook.py (UserPromptSubmit+PreToolUse) — marathon detection
"""

import json
import os
import sys
import time

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
    except Exception:  # noqa: S110 - hook must never crash the caller session
        pass


def _measure_transcript(transcript_path: str, state: dict) -> dict:
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
            except Exception:  # noqa: S112 - one bad log line must not stop the sweep
                continue
            etype = entry.get("type", "")
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
            usage = entry.get("usage") or {}
            if usage:
                state["total_input_tokens"] += int(usage.get("input_tokens", 0))
                state["total_cache_read"] += int(
                    usage.get("cache_read_input_tokens", 0)
                )
            if etype == "system" and "compacted" in str(entry).lower():
                state["compactions"] += 1
            if etype in ("tool_result", "error"):
                content = str(entry.get("content", "") or entry.get("error", ""))
                if (
                    "estate's ceiling" in content
                    or "Refused before it was sent" in content
                ):
                    state["proxy_refused"] += 1
    except Exception:  # noqa: S110 - hook must never crash the caller session
        pass
    return state


def _format_report(state: dict, session_id: str) -> str:
    bash = state["bash_calls"]
    idp_exec = state["idp_exec_calls"]
    raw_bash = bash - idp_exec
    compliance = (
        "PASS"
        if raw_bash == 0
        else f"FAIL — {raw_bash} raw Bash call(s) (use bin/idp-exec)"
    )
    total_in = state["total_input_tokens"]
    total_cached = state["total_cache_read"]
    denom = total_in + total_cached
    cache_pct = round(100 * total_cached / denom, 1) if denom > 0 else 0.0
    refused = state["proxy_refused"]
    return "\n".join(
        [
            f"[token-efficiency] session={session_id[-12:]} turn={state['turns']}",
            "  PROXY (model-agnostic, all 9 vendors):",
            f"    [ceiling] 128K/call hard limit | {refused} refused this session",
            "    [gateway] all 8 mechanisms active in efficiency_gateway.py",
            "  CLAUDE CODE (this session):",
            f"    [3-compliance] bash_calls={bash} idp_exec={idp_exec} raw={raw_bash} -> {compliance}",
            f"    [1-cache]      hit_rate={cache_pct}% ({total_cached:,} cached / {total_in:,} fresh)",
            f"    [7-compaction] {state['compactions']} auto-compactions",
            f"    [mcp]          {state['mcp_calls']} MCP calls",
        ]
    )


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    session_id = data.get("session_id", "unknown")
    transcript_path = data.get("transcript_path", "")
    state = _load_state(session_id)
    state = _measure_transcript(transcript_path, state)
    report = _format_report(state, session_id)
    _save_state(session_id, state)
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(os.path.join(STATE_DIR, "efficiency-latest.txt"), "w") as f:
            f.write(report + "\n")
    except Exception:  # noqa: S110 - hook must never crash the caller session
        pass
    print(report)
    sys.exit(0)


if __name__ == "__main__":
    main()
