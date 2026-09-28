#!/usr/bin/env python3
"""Claude Code Stop hook: 8 token-efficiency mechanisms + idp-exec compliance gate.

Reads Claude Code's Stop-event stdin JSON, measures the session transcript,
runs observable efficiency metrics, and prints a compliance report.

The transcript shape is the REAL one Claude Code writes: tool_use blocks are nested
inside `message.content[]` under a line whose top-level type is "assistant", and usage
lives at `message.usage`, not the top level. Reading `entry["type"] == "tool_use"` at
the top level measured 0 tool_use entries against 56 real nested ones (2026-09-21),
so the compliance line printed PASS for every session. The parser below reads the
nested shape and counts what is actually there.

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

# The proxy-bytes-saved ledger the gateway line reads. Default lives next to the state dir;
# tests monkeypatch this attribute to point at a fixture.
LEDGER = os.path.join(STATE_DIR, "proxy-bytes-saved.jsonl")


def _load_state(session_id: str) -> dict:
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, f"{session_id}.json")
    try:
        with open(path) as f:
            state = json.load(f)
            state.setdefault("seen", [])
            return state
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
            "seen": [],
            "first_seen": time.time(),
        }


def _save_state(session_id: str, state: dict) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, f"{session_id}.json")
    try:
        with open(path, "w") as f:
            json.dump(state, f)
    except Exception:  # noqa: S110 — deliberate: a hook must never break the turn
        pass


def _count_entry(entry: dict, state: dict) -> None:
    """Count one transcript line against the REAL nested shape.

    tool_use blocks live under entry["message"]["content"][]; usage lives under
    entry["message"]["usage"]. A top-level entry with type "tool_use" or a top-level
    "usage" key is the shape Claude Code does NOT emit and is ignored, not counted.
    """
    state.setdefault("seen", [])
    uuid = entry.get("uuid")
    if uuid:
        if uuid in state["seen"]:
            return
        state["seen"].append(uuid)

    message = entry.get("message") or {}
    if not isinstance(message, dict):
        return

    for block in message.get("content") or []:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        name = block.get("name", "")
        if name == "Bash":
            state["bash_calls"] += 1
            inp = block.get("input") or {}
            cmd = inp.get("command", "") if isinstance(inp, dict) else ""
            if "idp-exec" in cmd:
                state["idp_exec_calls"] += 1
        elif name.startswith("mcp__"):
            state["mcp_calls"] += 1

    usage = message.get("usage") or {}
    if usage:
        state["total_input_tokens"] += int(usage.get("input_tokens", 0))
        state["total_cache_read"] += int(usage.get("cache_read_input_tokens", 0))

    if entry.get("type") == "system" and entry.get("subtype") == "compact_boundary":
        state["compactions"] += 1

    if entry.get("type") == "user":
        for block in message.get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            content = str(block.get("content", ""))
            if "Refused before it was sent" in content:
                state["proxy_refused"] += 1


def _measure_transcript(transcript_path: str, state: dict) -> dict:
    """Scan the last 400 KB of the transcript for this-turn metrics.

    The dedupe key is the transcript line's uuid, kept in state["seen"], so a line
    re-read on a later Stop is never counted twice.
    """
    state["turns"] = state.get("turns", 0) + 1
    state.setdefault("seen", [])
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
            except Exception:  # noqa: S110, S112 — a malformed ledger line is skipped, not fatal
                continue
            if isinstance(entry, dict):
                _count_entry(entry, state)
    except Exception:  # noqa: S110 — deliberate: a hook must never break the turn
        pass

    return state


def _format_report(state: dict, session_id: str) -> str:
    bash = state.get("bash_calls", 0)
    idp_exec = state.get("idp_exec_calls", 0)
    raw_bash = bash - idp_exec

    # Compliance verdict for this session
    if raw_bash == 0:
        compliance = "PASS"
    else:
        compliance = f"FAIL — {raw_bash} raw Bash call(s) without bin/idp-exec"

    # Cache efficiency
    total_in = state.get("total_input_tokens", 0)
    total_cached = state.get("total_cache_read", 0)
    denom = total_in + total_cached
    cache_pct = round(100 * total_cached / denom, 1) if denom > 0 else 0.0

    # Proxy ceiling status
    refused = state.get("proxy_refused", 0)
    ceiling_line = (
        f"128K hard limit (model-agnostic) | {refused} call(s) refused this session"
        if refused
        else "128K hard limit (model-agnostic) | 0 calls refused"
    )

    lines = [
        f"[token-efficiency] session={session_id[-12:]} turn={state.get('turns', 0)}",
        f"  [1] Proxy ceiling:     {ceiling_line}",
        f"  [2] Cache hit rate:    {cache_pct}%  hit_rate={cache_pct}%  ({total_cached:,} cached / {total_in:,} fresh input tokens)",
        f"  [3] Bash compliance:   -> {compliance}",
        f"         bash_calls={bash} idp_exec={idp_exec} raw={raw_bash}",
        f"  [4] Compactions:       {state.get('compactions', 0)}",
        f"  [5] MCP calls:         {state.get('mcp_calls', 0)}",
        f"  [8] Gateway:           {_gateway_line()}",
        "",
    ]
    return "\n".join(lines)


def _gateway_line() -> str:
    """One measured sentence about the proxy-bytes ledger, never a bare assertion.

    Reads the LEDGER jsonl (one {"at", "bytes_saved"} per proxied call). When absent it
    says so instead of the old unconditional "all 8 mechanisms active" claim.
    """
    try:
        with open(LEDGER) as f:
            rows = [json.loads(line) for line in f if line.strip()]
    except Exception:
        return "proxy ledger has not run (no bytes_saved on record)"

    if not rows:
        return "proxy ledger has not run (no bytes_saved on record)"

    bytes_saved = sum(int(r.get("bytes_saved", 0)) for r in rows)
    latest = rows[-1].get("at", "")
    return f"{len(rows)} proxied calls, {bytes_saved:,} bytes saved" + (
        f", latest {latest}" if latest else ""
    )


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
    except Exception:  # noqa: S110 — deliberate: a hook must never break the turn
        pass

    print(report)
    sys.exit(0)


if __name__ == "__main__":
    main()
