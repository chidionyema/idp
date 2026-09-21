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
    pre_bash_token_gate.py (PreToolUse/Bash) — REFUSES raw shell, the one mechanism
      of the eight a subscription CLI can actually run
    This Stop hook — measures compliance per turn
    context-guard-hook.py (UserPromptSubmit+PreToolUse) — marathon detection

TRANSCRIPT SHAPE (measured 2026-09-21, 467 lines of a real session transcript).
Until today this hook reported zeros on a session with 49 Bash calls, because it read
the wrong shape. A Claude Code transcript line is:

    {"type": "assistant", "uuid": "...",
     "message": {"usage": {...}, "content": [{"type": "tool_use", "name": "Bash", ...}]}}

`tool_use` and `usage` are nested under `message`; the top-level `type` is only ever
"assistant" / "user" / "attachment" / "system" / ... . The counts, measured on
4ea7b7a1's own transcript:

    top-level  type == "tool_use"   ->   0 entries     <- what the old parser looked for
    nested     message.content[]    ->  56 tool_use blocks, 49 of them Bash
    top-level  "usage"              ->   0 entries     <- old cache hit-rate was always 0.0%
    nested     message.usage        -> 104 entries

So the compliance line printed `bash_calls=0 ... -> PASS` for every session ever run.
A gate that cannot fail is not a gate (estate law, ~/AGENTS.md §3) — it was reporting a
verdict on data it had never read.

DEDUPE. This hook runs on every Stop and re-reads the last 400KB of the transcript, so
counting without a key would re-count the same blocks each turn and inflate the report.
Every content-bearing entry carries a `uuid` (measured: 169/169), so `state["seen"]` keys
off that. Entries without one carry no tool_use and no usage.
"""

import json
import os
import sys
import time

STATE_DIR = os.path.expanduser("~/.pi/agent/state/efficiency")
MAX_INPUT_TOKENS = int(os.environ.get("ESTATE_MAX_INPUT_TOKENS", "128000"))

# Where the LiteLLM pre-call hook (platform/llm/efficiency_gateway.py) records what the
# eight mechanisms actually saved, one JSON object per proxied call.
LEDGER = os.path.expanduser("~/.estate/efficiency-ledger.jsonl")

# The uuid ring kept in state, so a long session does not grow its state file without
# bound. 4,000 entries covers far more than the 400KB tail this hook ever re-reads.
SEEN_CAP = 4000


def _load_state(session_id: str) -> dict:
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, f"{session_id}.json")
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:  # noqa: S110
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
    except Exception:  # noqa: S110
        pass


def _blocks(entry: dict) -> list:
    """The content blocks of one transcript line, or [] when it carries none.

    See the TRANSCRIPT SHAPE note in the module docstring: tool_use lives here, nested
    under `message`, and never at the top level of the line.
    """
    message = entry.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    return content if isinstance(content, list) else []


def _count_entry(entry: dict, state: dict) -> None:
    """Fold one not-yet-counted transcript line into the running totals."""
    for block in _blocks(entry):
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        name = block.get("name", "")
        if name == "Bash":
            state["bash_calls"] += 1
            inp = block.get("input")
            cmd = inp.get("command", "") if isinstance(inp, dict) else ""
            if "idp-exec" in cmd:
                state["idp_exec_calls"] += 1
        elif name.startswith("mcp__"):
            state["mcp_calls"] += 1

    message = entry.get("message")
    usage = message.get("usage") if isinstance(message, dict) else None
    if isinstance(usage, dict):
        state["total_input_tokens"] += int(usage.get("input_tokens", 0) or 0)
        state["total_cache_read"] += int(usage.get("cache_read_input_tokens", 0) or 0)

    if entry.get("type") == "system":
        if entry.get("subtype") == "compact_boundary":
            state["compactions"] += 1

    # The proxy ceiling's refusal comes back as the text of a tool_result block.
    for block in _blocks(entry):
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        content = str(block.get("content", ""))
        if "estate's ceiling" in content or "Refused before it was sent" in content:
            state["proxy_refused"] += 1


def _measure_transcript(transcript_path: str, state: dict) -> dict:
    state["turns"] += 1
    seen = state.setdefault("seen", [])
    if not transcript_path or not os.path.exists(transcript_path):
        return state
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as f:
            f.seek(max(0, size - 400_000))
            tail = f.read().decode("utf-8", errors="replace")
        already = set(seen)
        for line in tail.splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except Exception:  # noqa: S112
                continue
            if not isinstance(entry, dict):
                continue
            uuid = entry.get("uuid")
            # No uuid means no tool_use and no usage (measured: 169/169 content-bearing
            # entries carry one), so there is nothing here to count twice.
            if not uuid or uuid in already:
                continue
            already.add(uuid)
            seen.append(uuid)
            _count_entry(entry, state)
        if len(seen) > SEEN_CAP:
            del seen[: len(seen) - SEEN_CAP]
    except Exception:  # noqa: S110
        pass
    return state


def _gateway_line() -> str:
    """What the LiteLLM gateway has actually recorded — measured, not asserted.

    This line used to read "all 8 mechanisms active in efficiency_gateway.py" as a
    hardcoded string, printed whether or not the gateway had ever run. It is also the
    wrong claim for a Claude Code session: the eight mechanisms are a LiteLLM pre-call
    hook and Claude Code does not route through LiteLLM, so nothing the gateway does
    applies to the session this report is about. The line now reports the ledger, and
    says plainly that this session is not in it.
    """
    try:
        with open(LEDGER) as f:
            rows = [json.loads(line) for line in f if line.strip()]
    except Exception:  # noqa: BLE001
        return "    [gateway] no ledger at ~/.estate/efficiency-ledger.jsonl — has not run"
    if not rows:
        return "    [gateway] ledger present but empty — the 8 mechanisms have not run"
    saved = sum(int(r.get("bytes_saved", 0) or 0) for r in rows if isinstance(r, dict))
    last = rows[-1].get("at", "?") if isinstance(rows[-1], dict) else "?"
    return (
        f"    [gateway] {len(rows)} proxied calls, {saved:,} bytes saved, last {last}"
        " (proxy only — this Claude Code session is not routed through it)"
    )


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
            _gateway_line(),
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
    except Exception:  # noqa: S110
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
    except Exception:  # noqa: S110
        pass
    print(report)
    sys.exit(0)


if __name__ == "__main__":
    main()
