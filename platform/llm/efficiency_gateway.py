"""Estate efficiency gateway: all 9 token-optimisation mechanisms in one LiteLLM pre-call hook.

MODEL-AGNOSTIC: runs before every vendor call through llm.${ESTATE_ZONE}.
Applies to: minimax, groq, gemini, cerebras, sambanova, openrouter, ollama.
Registered as: efficiency_gateway.proxy_handler_instance in litellm_settings.callbacks.
Mounted at: /etc/litellm/ceilings/efficiency_gateway.py (same ConfigMap as request_ceiling.py).
PYTHONPATH: /etc/litellm/ceilings (set in platform/llm/litellm.yaml env block).

The ceiling (request_ceiling.py) REFUSES oversized requests before they reach this hook.
This hook OPTIMISES requests that pass the ceiling — reducing tokens billed per call.

MECHANISMS:
  [1] CacheGuardian        — detects system-prompt drift that kills prefix caching
  [2] TokenKiller          — deduplicates repeated lines in tool_result messages
  [3] MCPAdapter           — truncates verbose tool descriptions to MAX_TOOL_DESC_CHARS
  [4] TokenBudgetOrchestrator — tracks cumulative estimated spend per session key
  [5] SoLPi                — deduplicates large identical tool-result payloads via handles
  [6] DynamicContextPruning — prunes duplicate tool_result entries from history
  [7] CompactionManager    — bounds conversation history to MAX_HISTORY_MSGS
  [8] GistingSimulator     — gists old assistant turns beyond GIST_AFTER_MSGS
  [9] ToolPairValidator    — drops orphaned tool messages (final safety net)

INVARIANT (2026-10-13): A role="tool" message is valid only when the immediately
preceding assistant message contains a tool_calls entry with a matching id. Every
mechanism that touches tool messages MUST preserve this invariant. Mechanism [9]
runs last as a safety net to catch any orphans before dispatch.

Each mechanism modifies data["messages"] or data["tools"] in place and logs a metric.
The combined return value is the optimised request body LiteLLM sends to the vendor.

ANTHROPIC MODE (2026-09-26, the laptop router's `claude-*` lane). Claude Code sends the
Anthropic Messages format and its economics are the prompt cache: a cache read costs 0.1x an
uncached input token, and ANY change to an earlier message invalidates everything after it.
Measured on a real 233-message session, the OpenAI-shaped chain above rewrote history so that
consecutive turns shared 0 of 60 prefix messages -- every turn a full cache miss -- and dropped
173 messages. So on that lane every mechanism is APPEND-STABLE: a message's transform depends
only on itself and the messages before it, never on the conversation's length, so turn n+1
re-sends byte-identical bytes for everything turn n cached. Concretely:
  [2] collapses runs of identical CONSECUTIVE lines inside tool_result text (never the
      non-adjacent dedup above, which deletes a repeated `}` or `return` and corrupts code);
  [5] replaces an exact repeat of an earlier large tool_result with a pointer to the first
      one, which is still in the request (per request -- never a cross-call memory, which
      would point the model at a result it cannot see);
  [1] proves the cache survives: it hashes system+tools and every transformed message per
      conversation and records how much of the previous call's prefix this call re-sent;
  [3][7][8] do NOT act: tool descriptions sit in the cached prefix at 0.1x and trimming them
      degrades tool use; Claude Code compacts its own history; assistant turns carry thinking
      signatures that Anthropic rejects if touched. Each records why, every call;
  [9] checks tool_use/tool_result pairing and the first role, and never drops anything.
async_log_success_event then records what Anthropic actually billed for the call (uncached,
cache read, cache write 5m/1h, output), so "saved" is measured, not estimated.
"""

import hashlib
import json
import logging
import os
import time
from typing import Any, Optional, Union

log = logging.getLogger("estate.efficiency-gateway")


# --------------------------------------------------------------------------- ledger
#
# WHY THIS EXISTS (2026-09-18). Every mechanism below already mutated the request and
# incremented an in-memory counter, and that counter died with the process. Measured on the
# founder's own machine: `efficiency-latest.txt` read `hit_rate=0.0% (0 cached / 0 fresh)`
# while ~18M tokens were served at a 99.9% cache-hit rate one process away, so the one
# file that claimed to report the mechanisms reported nothing at all. "Built and wired" is
# not evidence; a scientist wants the per-call delta.
#
# So each mechanism now records bytes in -> bytes out for EVERY call, and the row carries
# the raw before/after sizes so the saving is recomputable by a reader rather than trusted.
# Same ledger shape read_shunt already uses (`est_*` fields, one JSONL line per event), so
# the estate has one audit format and not two.
#
# The ledger may NEVER fail a request (LAW 38): every write is wrapped, and a failure to
# journal is logged and dropped, never raised into the vendor call.
_LEDGER_ENV = "ESTATE_EFFICIENCY_LEDGER"
_LEDGER_DEFAULT = "~/.estate/efficiency-ledger.jsonl"


def _ledger_path() -> str:
    return os.path.expanduser(os.environ.get(_LEDGER_ENV) or _LEDGER_DEFAULT)


def _ledger_write(row: dict[str, Any]) -> None:
    try:
        p = _ledger_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    except Exception as exc:  # noqa: BLE001 - the ledger may never fail the request (LAW 38)
        log.warning("[ledger] not written: %s", exc)


def _json_bytes(obj: Any) -> int:
    """The size of what the vendor would actually be sent, not a character count.

    The mechanisms below mutate nested dicts in place, so measuring the whole messages/
    tools payload before and after is the only honest way to attribute a delta to the
    mechanisms as a group. Per-mechanism numbers are recorded alongside it.
    """
    try:
        return len(json.dumps(obj, separators=(",", ":"), default=str).encode())
    except Exception:  # noqa: BLE001
        return 0


try:
    from litellm.integrations.custom_logger import CustomLogger
except ModuleNotFoundError:
    # Importable on any machine without litellm (CI, laptop).
    class CustomLogger:  # type: ignore[no-redef]
        async def async_pre_call_hook(self, *a, **k):
            raise NotImplementedError


CHARS_PER_TOKEN = 4
TOKENS_PER_MTOK = 1_000_000
MAX_TOOL_DESC_CHARS = int(os.environ.get("ESTATE_MAX_TOOL_DESC_CHARS", "400"))
MAX_HISTORY_MSGS = int(os.environ.get("ESTATE_MAX_HISTORY_MSGS", "60"))
MAX_HISTORY_BYTES = int(os.environ.get("ESTATE_MAX_HISTORY_BYTES", "200000"))
GIST_AFTER_MSGS = int(os.environ.get("ESTATE_GIST_AFTER_MSGS", "40"))
STALE_THRESHOLD = int(os.environ.get("ESTATE_STALE_THRESHOLD", "10"))
MIN_OBS_CHARS = int(os.environ.get("ESTATE_MIN_OBS_CHARS", "500"))


RUN_MIN = int(os.environ.get("ESTATE_RUN_MIN_LINES", "3"))
CONV_MEMORY = 256  # conversations whose prefix hashes are kept for the stability check
CACHE_READ_RATE = (
    0.1  # Anthropic's price of a cache read, relative to an uncached input token
)
CACHE_WRITE_5M_RATE = 1.25
CACHE_WRITE_1H_RATE = 2.0


def _is_anthropic(data: dict, call_type: Any) -> bool:
    if "anthropic_messages" in str(call_type):
        return True
    for m in data.get("messages") or []:
        c = m.get("content") if isinstance(m, dict) else None
        if isinstance(c, list) and any(
            isinstance(b, dict) and b.get("type") in ("tool_use", "tool_result")
            for b in c
        ):
            return True
    return False


def _session_id(data: dict) -> str:
    """Claude Code puts {"session_id": ...} as a JSON string in metadata.user_id."""
    meta = data.get("metadata") or {}
    uid = meta.get("user_id") if isinstance(meta, dict) else None
    if isinstance(uid, str):
        try:
            sid = json.loads(uid).get("session_id")
            if sid:
                return str(sid)
        except (ValueError, AttributeError):
            return uid[:64]
    return str(data.get("litellm_session_id") or "-")


def _strip_cache_control(obj: Any) -> Any:
    # Claude Code moves its cache_control breakpoints every turn; they are not content.
    if isinstance(obj, dict):
        return {
            k: _strip_cache_control(v) for k, v in obj.items() if k != "cache_control"
        }
    if isinstance(obj, list):
        return [_strip_cache_control(v) for v in obj]
    return obj


def _h(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(_strip_cache_control(obj), sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


def _collapse_runs(text: str) -> tuple[str, int]:
    """Collapse runs of >= RUN_MIN identical consecutive non-blank lines. Returns (text, bytes saved).

    Only adjacent repeats: the first line stays verbatim and the rest become one count marker,
    so no information is lost and nothing non-adjacent (a `}` or `return` in code) is touched.
    """
    lines = text.split("\n")
    out: list = []
    i = 0
    changed = False
    while i < len(lines):
        j = i
        while j + 1 < len(lines) and lines[j + 1] == lines[i]:
            j += 1
        n = j - i + 1
        marker = f"[router: previous line repeated {n - 1} more times]"
        if (
            lines[i].strip()
            and n >= RUN_MIN
            and len(marker) < len("\n".join(lines[i + 1 : j + 1]))
        ):
            out += [lines[i], marker]
            changed = True
        else:
            out += lines[i : j + 1]
        i = j + 1
    if not changed:
        return text, 0
    new = "\n".join(out)
    return new, len(text.encode()) - len(new.encode())


def _tool_result_text(block: dict) -> Optional[str]:
    """The text of a tool_result whose content is text only; None if it carries anything else."""
    c = block.get("content")
    if isinstance(c, str):
        return c
    if (
        isinstance(c, list)
        and c
        and all(isinstance(b, dict) and b.get("type") == "text" for b in c)
    ):
        return "\n".join(str(b.get("text") or "") for b in c)
    return None


class _AnthropicSteps:
    """The append-stable chain for the Anthropic Messages format. See the module docstring."""

    def __init__(self) -> None:
        # conversation key -> (system+tools hash, [per-message hash, ...]) from its last call
        self._convs: "dict[str, tuple[str, list]]" = {}

    def run(self, data: dict, session: str) -> dict:
        msgs = data.get("messages") or []
        steps: dict = {}

        # [2] TokenKiller -- adjacent runs only, inside tool_result text
        runs = saved2 = 0
        for m in msgs:
            if (
                not isinstance(m, dict)
                or m.get("role") != "user"
                or not isinstance(m.get("content"), list)
            ):
                continue
            for b in m["content"]:
                if not isinstance(b, dict) or b.get("type") != "tool_result":
                    continue
                c = b.get("content")
                if isinstance(c, str):
                    new, sv = _collapse_runs(c)
                    if sv > 0:
                        b["content"], runs, saved2 = new, runs + 1, saved2 + sv
                elif isinstance(c, list):
                    for tb in c:
                        if (
                            isinstance(tb, dict)
                            and tb.get("type") == "text"
                            and isinstance(tb.get("text"), str)
                        ):
                            new, sv = _collapse_runs(tb["text"])
                            if sv > 0:
                                tb["text"], runs, saved2 = new, runs + 1, saved2 + sv
        steps["m2"] = {
            "action": "collapsed" if runs else "none",
            "blocks": runs,
            "bytes": saved2,
            "why": "adjacent identical lines in tool results -> one line + count",
        }

        # [5] SoLPi -- exact repeats of an earlier large tool_result, within THIS request
        first: dict = {}
        hits = saved5 = 0
        for m in msgs:
            if (
                not isinstance(m, dict)
                or m.get("role") != "user"
                or not isinstance(m.get("content"), list)
            ):
                continue
            for b in m["content"]:
                if not isinstance(b, dict) or b.get("type") != "tool_result":
                    continue
                text = _tool_result_text(b)
                if text is None or len(text) < MIN_OBS_CHARS:
                    continue
                h = hashlib.sha256(text.encode()).hexdigest()[:16]
                if h not in first:
                    first[h] = b.get("tool_use_id")
                    continue
                ref = (
                    f"[router: identical to the tool result of {first[h]} earlier in this "
                    f"conversation ({len(text)} chars, sha256 {h[:8]}); not repeated]"
                )
                before = _json_bytes(b.get("content"))
                b["content"] = ref
                hits += 1
                saved5 += before - _json_bytes(ref)
        steps["m5"] = {
            "action": "deduplicated" if hits else "none",
            "results": hits,
            "bytes": saved5,
            "why": f"exact repeat (>= {MIN_OBS_CHARS} chars) of an earlier tool result in the same request",
        }
        steps["m6"] = {
            "action": "merged-into-m5",
            "bytes": 0,
            "why": "one dedup pass; a second would only re-hash the same blocks",
        }

        # [3] [7] [8] -- deliberately inert on this lane, and saying so every call
        tools = data.get("tools") or []
        steps["m3"] = {
            "action": "skipped",
            "bytes": 0,
            "tools": len(tools),
            "tools_bytes": _json_bytes(tools),
            "why": "tool schemas sit in the cached prefix (0.1x); trimming them costs tool-use quality",
        }
        est_tokens = (
            _json_bytes(msgs) + _json_bytes(data.get("system")) + _json_bytes(tools)
        ) // CHARS_PER_TOKEN
        steps["m7"] = {
            "action": "skipped",
            "bytes": 0,
            "est_tokens": est_tokens,
            "why": "Claude Code compacts its own history; dropping turns breaks the cache and loses context",
        }
        steps["m8"] = {
            "action": "skipped",
            "bytes": 0,
            "why": "assistant turns carry thinking signatures; Anthropic rejects edited ones",
        }

        # [9] pairing -- every tool_result answers a tool_use in the assistant turn before it
        orphans = 0
        open_ids: set = set()
        for m in msgs:
            if not isinstance(m, dict):
                continue
            c = m.get("content") if isinstance(m.get("content"), list) else []
            if m.get("role") == "assistant":
                open_ids = {
                    b.get("id")
                    for b in c
                    if isinstance(b, dict) and b.get("type") == "tool_use"
                }
            else:
                for b in c:
                    if (
                        isinstance(b, dict)
                        and b.get("type") == "tool_result"
                        and b.get("tool_use_id") not in open_ids
                    ):
                        orphans += 1
        first_role = msgs[0].get("role") if msgs and isinstance(msgs[0], dict) else None
        steps["m9"] = {
            "action": "checked",
            "orphans": orphans,
            "first_role": first_role,
            "why": "reports, never drops: the router removes no message on this lane",
        }

        # [1] CacheGuardian -- measured last, on exactly the bytes that will be sent
        head = _h([data.get("system"), tools])
        hashes = [_h(m) for m in msgs]
        conv = f"{session}:{data.get('model')}:{hashes[0] if hashes else '-'}"
        prev = self._convs.pop(conv, None)
        common = 0
        if prev:
            for a, b in zip(prev[1], hashes):  # noqa: B905 -- runtime falls back to py3.9, no strict= kwarg
                if a != b:
                    break
                common += 1
        self._convs[conv] = (head, hashes)
        while len(self._convs) > CONV_MEMORY:
            self._convs.pop(next(iter(self._convs)))
        steps["m1"] = {
            "action": "first-call" if prev is None else "checked",
            "system_tools_changed": bool(prev and prev[0] != head),
            "prefix_prev_msgs": len(prev[1]) if prev else 0,
            "prefix_kept_msgs": common,
            "prefix_broken": bool(prev and (common < len(prev[1]) or prev[0] != head)),
            "why": "this call must re-send the previous call's messages byte-identical or the cache misses",
        }
        return steps


def _usage_numbers(response_obj: Any, kwargs: dict) -> Optional[dict]:
    """What Anthropic billed for the call, from the response usage LiteLLM hands the callback."""
    u = None
    try:
        u = (
            response_obj.get("usage")
            if isinstance(response_obj, dict)
            else getattr(response_obj, "usage", None)
        )
    except Exception:  # noqa: BLE001
        u = None
    if u is None:
        slo = kwargs.get("standard_logging_object") or {}
        u = (slo.get("metadata") or {}).get("usage_object")
    if u is None:
        return None

    def g(o: Any, k: str) -> Any:
        return o.get(k) if isinstance(o, dict) else getattr(o, k, None)

    prompt = int(g(u, "prompt_tokens") or 0)
    read = int(g(u, "cache_read_input_tokens") or 0)
    write = int(g(u, "cache_creation_input_tokens") or 0)
    details = (
        g(g(u, "prompt_tokens_details") or {}, "cache_creation_token_details") or {}
    )
    w1h = int(g(details, "ephemeral_1h_input_tokens") or 0)
    w5m = max(0, write - w1h)
    uncached = max(0, prompt - read - write)
    out = int(g(u, "completion_tokens") or 0)
    # Input-token-equivalents at Anthropic's relative prices: what the call cost, and what the
    # same prompt would have cost with no cache at all. Exact given the usage, no estimation.
    billed = (
        uncached
        + w5m * CACHE_WRITE_5M_RATE
        + w1h * CACHE_WRITE_1H_RATE
        + read * CACHE_READ_RATE
    )
    return {
        "prompt_tokens": prompt,
        "uncached_input": uncached,
        "cache_read": read,
        "cache_write_5m": w5m,
        "cache_write_1h": w1h,
        "output_tokens": out,
        "input_equiv_billed": round(billed, 1),
        "input_equiv_no_cache": prompt,
        "cache_saved_input_equiv": round(prompt - billed, 1),
        "cache_hit_pct": round(read / prompt * 100, 2) if prompt else 0.0,
    }


class EstateEfficiencyGateway(CustomLogger):
    """Runs all 8 token-efficiency mechanisms on every pre-call hook invocation."""

    def __init__(self) -> None:
        # [1] CacheGuardian
        self._golden_hash: Optional[str] = None
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_prompt_bytes = 0  # the stable prefix size a hit preserves
        # [2] TokenKiller
        self._tool_line_compressions = 0
        self._tool_chars_saved = 0
        self._tool_bytes_saved = 0
        # [3] MCPAdapter
        self._schemas_compressed = 0
        self._schema_chars_saved = 0
        self._schema_bytes_saved = 0
        # [4] TokenBudgetOrchestrator
        self._calls = 0
        self._cumulative_tokens = 0
        self._cumulative_bytes = 0
        # [5] SoLPi
        self._obs_handles: dict = {}
        self._obs_hits = 0
        self._obs_bytes_saved = 0
        # [6] DynamicContextPruning
        self._pruned_duplicates = 0
        self._pruned_bytes = 0
        # [7] CompactionManager
        self._compactions = 0
        self._dropped_messages = 0
        self._compaction_bytes_saved = 0
        # [8] GistingSimulator
        self._gisted = 0
        self._gist_bytes_saved = 0
        # [9] ToolPairValidator
        self._orphaned_tool_messages_dropped = 0
        self._orphaned_bytes_saved = 0
        # Anthropic lane: prefix memory per conversation, and the pre-call summary per call id
        # so the outcome row carries what the router did next to what Anthropic billed.
        self._anthropic = _AnthropicSteps()
        self._pending: dict = {}

    # ---------------------------------------------------------------------- [1]

    def _cache_guardian(self, messages: list) -> list:
        """Detect system-prompt drift. A stable first message keeps the prefix cache alive."""
        if not messages:
            return messages
        first = messages[0]
        if isinstance(first, dict) and first.get("role") == "system":
            content = str(first.get("content") or "")
            h = hashlib.sha256(content.encode()).hexdigest()
            if self._golden_hash is None:
                self._golden_hash = h
                self._cache_hits += 1
                log.info("[1-CacheGuardian] Golden system prompt captured (%s)", h[:8])
            if h == self._golden_hash:
                self._cache_hits += 1
                self._cache_prompt_bytes += len(content.encode())
            else:
                self._cache_misses += 1
                log.warning(
                    "[1-CacheGuardian] System prompt drifted — prefix cache MISS (was %s, now %s)",
                    self._golden_hash[:8],
                    h[:8],
                )
        return messages

    # ---------------------------------------------------------------------- [2]

    def _token_killer(self, messages: list) -> list:
        """Strip repeated identical lines from tool_result content."""
        for msg in messages:
            if not isinstance(msg, dict) or msg.get("role") != "tool":
                continue
            content = msg.get("content")
            if not isinstance(content, str):
                continue
            seen: set = set()
            out_lines = []
            for line in content.split("\n"):
                key = line.strip()
                if key and key in seen:
                    self._tool_chars_saved += len(line) + 1
                    self._tool_bytes_saved += len(line.encode()) + 1
                    self._tool_line_compressions += 1
                    continue
                seen.add(key)
                out_lines.append(line)
            msg["content"] = "\n".join(out_lines)
        return messages

    # ---------------------------------------------------------------------- [3]

    def _mcp_adapter(self, tools: list) -> list:
        """Truncate verbose tool/function descriptions to MAX_TOOL_DESC_CHARS."""
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            fn = tool.get("function", tool)
            desc = fn.get("description") or ""
            if len(desc) > MAX_TOOL_DESC_CHARS:
                saved = len(desc) - MAX_TOOL_DESC_CHARS
                self._schema_chars_saved += saved
                self._schema_bytes_saved += len(desc.encode()) - len(
                    (desc[:MAX_TOOL_DESC_CHARS] + "…").encode()
                )
                self._schemas_compressed += 1
                fn["description"] = desc[:MAX_TOOL_DESC_CHARS] + "…"
                log.debug("[3-MCPAdapter] Truncated description by %d chars", saved)
        return tools

    # ---------------------------------------------------------------------- [4]

    def _budget_orchestrator(self, data: dict) -> dict:
        """Track cumulative estimated token spend per gateway instance (session lifetime)."""
        self._calls += 1
        chars = sum(
            len(str(m.get("content") or ""))
            for m in data.get("messages") or []
            if isinstance(m, dict)
        )
        est = chars // CHARS_PER_TOKEN
        self._cumulative_tokens += est
        log.debug(
            "[4-BudgetOrchestrator] call=%d est=%d cumulative=%d",
            self._calls,
            est,
            self._cumulative_tokens,
        )
        return data

    # ---------------------------------------------------------------------- [5]

    def _sol_pi(self, messages: list) -> list:
        """Replace repeated large tool-result payloads with a stable handle reference."""
        for msg in messages:
            if not isinstance(msg, dict) or msg.get("role") != "tool":
                continue
            content = msg.get("content")
            if not isinstance(content, str) or len(content) < MIN_OBS_CHARS:
                continue
            h = hashlib.sha256(content.encode()).hexdigest()[:16]
            handle = f"#OBS_{h}"
            if h in self._obs_handles:
                replacement = f"[duplicate observation — see earlier result: {handle}]"
                self._obs_bytes_saved += len(content.encode()) - len(
                    replacement.encode()
                )
                msg["content"] = replacement
                self._obs_hits += 1
                log.info(
                    "[5-SoLPi] Replaced %d-char observation with handle %s",
                    len(content),
                    handle,
                )
            else:
                self._obs_handles[h] = True
        return messages

    # ---------------------------------------------------------------------- [6]

    def _dynamic_pruning(self, messages: list) -> list:
        """Remove duplicate tool_result entries (same tool_call_id + content).

        INVARIANT: We can only prune a tool message if we also remove the
        corresponding tool_calls entry from its assistant message. Since that
        would break the assistant's other tool calls, we DON'T prune duplicates
        — we just replace their content with a short reference (same as SoLPi).

        This preserves the pairing while still saving tokens.
        """
        if len(messages) <= STALE_THRESHOLD:
            return messages

        # Track content hashes we've seen
        seen_content: dict = {}
        result = []

        for msg in messages:
            if not isinstance(msg, dict):
                result.append(msg)
                continue

            if msg.get("role") == "tool":
                content = str(msg.get("content", ""))
                content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                key = content_hash

                if key in seen_content and len(content) >= MIN_OBS_CHARS:
                    # Duplicate content — replace with reference, DON'T drop the message
                    original_bytes = _json_bytes(msg)
                    msg["content"] = f"[duplicate of earlier tool result: #{key[:8]}]"
                    new_bytes = _json_bytes(msg)
                    self._pruned_duplicates += 1
                    self._pruned_bytes += original_bytes - new_bytes
                    log.debug(
                        "[6-DynamicPruning] Replaced duplicate tool_result content (saved %d bytes)",
                        original_bytes - new_bytes,
                    )
                # Always record the hash so we can detect future duplicates
                if key not in seen_content:
                    seen_content[key] = True

            result.append(msg)
        return result

    # ---------------------------------------------------------------------- [7]

    def _compaction_manager(self, messages: list) -> list:
        """Bound conversation history: drop oldest non-system messages beyond MAX_HISTORY_MSGS.

        INVARIANT: Never drop an assistant message with tool_calls without also
        dropping the corresponding tool messages, and vice versa. We find a safe
        cut point that doesn't orphan any tool messages.
        """
        if (
            len(messages) <= MAX_HISTORY_MSGS
            and _json_bytes(messages) <= MAX_HISTORY_BYTES
        ):
            return messages
        system = [
            m for m in messages if isinstance(m, dict) and m.get("role") == "system"
        ]
        rest = [
            m
            for m in messages
            if not (isinstance(m, dict) and m.get("role") == "system")
        ]
        keep = MAX_HISTORY_MSGS - len(system)
        if len(rest) <= keep:
            return system + rest

        # Find a safe cut point that doesn't orphan tool messages.
        # We can only cut BEFORE an assistant message (not in the middle of a
        # tool_calls/tool sequence). Walk forward to find the first safe index.
        target_drop = len(rest) - keep
        cut_idx = 0
        i = 0
        while i < len(rest) and cut_idx < target_drop:
            msg = rest[i]
            if not isinstance(msg, dict):
                cut_idx = i + 1
                i += 1
                continue

            role = msg.get("role")
            if role == "assistant":
                tool_calls = msg.get("tool_calls") or []
                if tool_calls:
                    # This assistant has tool_calls — we must skip past all
                    # corresponding tool messages to find the next safe cut point.
                    expected_ids = {
                        tc.get("id") for tc in tool_calls if isinstance(tc, dict)
                    }
                    i += 1
                    while i < len(rest) and expected_ids:
                        next_msg = rest[i]
                        if (
                            isinstance(next_msg, dict)
                            and next_msg.get("role") == "tool"
                        ):
                            expected_ids.discard(next_msg.get("tool_call_id"))
                        i += 1
                    # Now i is past the tool sequence — safe to cut here
                    if cut_idx + (i - cut_idx) <= target_drop:
                        cut_idx = i
                else:
                    # Assistant without tool_calls — safe to cut after it
                    cut_idx = i + 1
                    i += 1
            elif role == "user":
                # User messages are always safe cut points
                cut_idx = i + 1
                i += 1
            else:
                # Tool message without preceding assistant — already orphaned,
                # include in cut
                cut_idx = i + 1
                i += 1

        if cut_idx > 0:
            self._compaction_bytes_saved += _json_bytes(rest[:cut_idx])
            rest = rest[cut_idx:]
            self._compactions += 1
            self._dropped_messages += cut_idx
            log.info(
                "[7-CompactionManager] Dropped %d messages (safe cut), kept %d (+ %d system)",
                cut_idx,
                len(rest),
                len(system),
            )
        return system + rest

    # ---------------------------------------------------------------------- [8]

    def _gisting(self, messages: list) -> list:
        """Condense old assistant messages: replace body with first 120 chars + length marker."""
        if len(messages) <= GIST_AFTER_MSGS:
            return messages
        boundary = len(messages) - GIST_AFTER_MSGS
        for msg in messages[:boundary]:
            if not isinstance(msg, dict) or msg.get("role") != "assistant":
                continue
            content = msg.get("content")
            if not isinstance(content, str) or len(content) <= 200:
                continue
            if content.startswith("[GISTED:"):
                continue
            gisted = f"[GISTED:{len(content)}ch] {content[:120]}…"
            self._gist_bytes_saved += len(content.encode()) - len(gisted.encode())
            msg["content"] = gisted
            self._gisted += 1
            log.debug(
                "[8-GistingSimulator] Gisted assistant message (%d chars)", len(content)
            )
        return messages

    # ---------------------------------------------------------------------- [9]

    def _tool_pair_validator(self, messages: list) -> list:
        """Drop orphaned tool messages whose assistant tool_calls entry is missing.

        INVARIANT: A role="tool" message is valid only when the most recent
        assistant message contains a tool_calls entry with a matching id.

        This runs LAST as a safety net. If it drops anything, that is a bug in
        an earlier mechanism — log loudly so we can fix the root cause.
        """
        cleaned: list = []
        open_calls: set = set()

        for msg in messages:
            if not isinstance(msg, dict):
                cleaned.append(msg)
                continue

            role = msg.get("role")
            if role == "assistant":
                # Each assistant message resets the set of valid tool_call_ids
                tool_calls = msg.get("tool_calls") or []
                open_calls = {tc.get("id") for tc in tool_calls if isinstance(tc, dict)}
                cleaned.append(msg)
            elif role == "tool":
                tool_call_id = msg.get("tool_call_id")
                if tool_call_id not in open_calls:
                    # Orphan — drop it, but log loudly so we fix the root cause
                    self._orphaned_tool_messages_dropped += 1
                    self._orphaned_bytes_saved += _json_bytes(msg)
                    log.warning(
                        "[9-ToolPairValidator] DROPPING orphaned tool message — "
                        "tool_call_id=%s has no matching assistant tool_calls entry. "
                        "This is a bug in an earlier mechanism.",
                        tool_call_id,
                    )
                    continue
                open_calls.discard(tool_call_id)
                cleaned.append(msg)
            else:
                cleaned.append(msg)

        return cleaned

    # ---------------------------------------------------------------------- hook

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: Union[Any, str],
    ) -> Optional[dict]:
        """Run all 8 mechanisms in sequence, then record what they actually saved.

        The before/after byte counts are taken around the WHOLE chain and written to the
        ledger alongside each mechanism's own per-mechanism byte delta. A reader can then
        check two independent things: that the mechanisms changed the payload at all, and
        which one changed it. `bytes_saved` is the chain total; the per-mechanism numbers
        are measured inside each step, so they are independent rather than a decomposition
        of a number that was computed after the fact.
        """
        started = time.time()
        if _is_anthropic(data, call_type):
            try:
                return self._anthropic_call(data, call_type, started)
            except Exception as exc:  # noqa: BLE001 - never fail the request (LAW 38)
                log.warning("[EfficiencyGateway] anthropic chain skipped: %s", exc)
                return data
        msgs = list(data.get("messages") or [])
        tools = list(data.get("tools") or [])
        # Per-call deltas: the m* fields below are cumulative for the process's lifetime, so a
        # reader summing them across rows over-counts. `steps` is THIS call only.
        counters_before = self._counters()

        # Snapshot the payload as the vendor would have received it, before any mechanism
        # runs. This is the only honest baseline for "what did we save on this call".
        before_bytes = _json_bytes(msgs) + _json_bytes(tools)
        before_messages = len(msgs)

        msgs = self._cache_guardian(msgs)  # [1]
        msgs = self._sol_pi(msgs)  # [5] dedup before other pruning
        msgs = self._dynamic_pruning(msgs)  # [6]
        msgs = self._compaction_manager(msgs)  # [7]
        msgs = self._gisting(msgs)  # [8]
        msgs = self._token_killer(msgs)  # [2]
        msgs = self._tool_pair_validator(
            msgs
        )  # [9] MUST be last — safety net for orphans
        tools = self._mcp_adapter(tools)  # [3]
        data = self._budget_orchestrator(data)  # [4] — always after messages are final

        data["messages"] = msgs
        if tools:
            data["tools"] = tools

        after_bytes = _json_bytes(msgs) + _json_bytes(tools)
        counters_after = self._counters()
        steps = {
            k: counters_after[k] - counters_before[k]
            for k in counters_after
            if counters_after[k] != counters_before[k]
        }

        _ledger_write(
            {
                "v": 2,
                "kind": "pre",
                "mode": "openai",
                "call_id": data.get("litellm_call_id"),
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
                "call_type": str(call_type),
                "model": (data.get("model") or ""),
                "ms": round((time.time() - started) * 1000, 2),
                # chain total, measured around the whole hook
                "bytes_before": before_bytes,
                "bytes_after": after_bytes,
                "bytes_saved": max(0, before_bytes - after_bytes),
                "messages_before": before_messages,
                "messages_after": len(msgs),
                "steps": steps,
                # per mechanism, measured inside each step (independent numbers)
                "m1_cache_hits": self._cache_hits,
                "m1_cache_misses": self._cache_misses,
                "m1_prefix_bytes_preserved": self._cache_prompt_bytes,
                "m2_lines_compressed": self._tool_line_compressions,
                "m2_bytes_saved": self._tool_bytes_saved,
                "m3_schemas_compressed": self._schemas_compressed,
                "m3_bytes_saved": self._schema_bytes_saved,
                "m4_cumulative_tokens": self._cumulative_tokens,
                "m5_obs_hits": self._obs_hits,
                "m5_bytes_saved": self._obs_bytes_saved,
                "m6_pruned": self._pruned_duplicates,
                "m6_bytes_saved": self._pruned_bytes,
                "m7_compactions": self._compactions,
                "m7_dropped_messages": self._dropped_messages,
                "m7_bytes_saved": self._compaction_bytes_saved,
                "m8_gisted": self._gisted,
                "m8_bytes_saved": self._gist_bytes_saved,
                "m9_orphans_dropped": self._orphaned_tool_messages_dropped,
                "m9_bytes_saved": self._orphaned_bytes_saved,
            }
        )

        log.info(
            "[EfficiencyGateway] [1]cache=%d/%d [2]tool_lines_saved=%d [3]schema_chars=%d "
            "[4]cumulative_tokens=%d [5]obs_hits=%d [6]pruned=%d [7]compactions=%d [8]gisted=%d [9]orphans=%d",
            self._cache_hits,
            self._cache_hits + self._cache_misses,
            self._tool_line_compressions,
            self._schema_chars_saved,
            self._cumulative_tokens,
            self._obs_hits,
            self._pruned_duplicates,
            self._compactions,
            self._gisted,
            self._orphaned_tool_messages_dropped,
        )
        return data

    def _counters(self) -> dict:
        return {
            "m1_cache_hits": self._cache_hits,
            "m1_cache_misses": self._cache_misses,
            "m2_lines_compressed": self._tool_line_compressions,
            "m2_bytes_saved": self._tool_bytes_saved,
            "m3_schemas_compressed": self._schemas_compressed,
            "m3_bytes_saved": self._schema_bytes_saved,
            "m5_obs_hits": self._obs_hits,
            "m5_bytes_saved": self._obs_bytes_saved,
            "m6_pruned": self._pruned_duplicates,
            "m6_bytes_saved": self._pruned_bytes,
            "m7_compactions": self._compactions,
            "m7_dropped_messages": self._dropped_messages,
            "m7_bytes_saved": self._compaction_bytes_saved,
            "m8_gisted": self._gisted,
            "m8_bytes_saved": self._gist_bytes_saved,
            "m9_orphans_dropped": self._orphaned_tool_messages_dropped,
            "m9_bytes_saved": self._orphaned_bytes_saved,
        }

    # ------------------------------------------------------------ anthropic lane

    def _anthropic_call(self, data: dict, call_type: Any, started: float) -> dict:
        session = _session_id(data)
        msgs = data.get("messages") or []
        before = _json_bytes(msgs)
        steps = self._anthropic.run(data, session)
        after = _json_bytes(data.get("messages") or [])
        self._calls += 1
        self._cumulative_tokens += steps["m7"]["est_tokens"]
        row = {
            "v": 2,
            "kind": "pre",
            "mode": "anthropic",
            "call_id": data.get("litellm_call_id"),
            "session": session,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
            "call_type": str(call_type),
            "model": data.get("model") or "",
            "ms": round((time.time() - started) * 1000, 2),
            "messages": len(msgs),
            "bytes_before": before,
            "bytes_after": after,
            "bytes_saved": max(0, before - after),
            "est_tokens_cut": max(0, before - after) // CHARS_PER_TOKEN,
            "steps": steps,
        }
        _ledger_write(row)
        if row["call_id"]:
            self._pending[row["call_id"]] = row
            while len(self._pending) > 512:
                self._pending.pop(next(iter(self._pending)))
        m1 = steps["m1"]
        log.info(
            "[EfficiencyGateway] anthropic %s msgs=%d saved=%dB (m2 %dB, m5 %dB) prefix %d/%d%s",
            row["model"],
            len(msgs),
            row["bytes_saved"],
            steps["m2"]["bytes"],
            steps["m5"]["bytes"],
            m1["prefix_kept_msgs"],
            m1["prefix_prev_msgs"],
            " BROKEN" if m1["prefix_broken"] else "",
        )
        return data

    def _outcome(
        self,
        kwargs: dict,
        response_obj: Any,
        start_time: Any,
        end_time: Any,
        error: Any = None,
    ) -> None:
        try:
            call_id = kwargs.get("litellm_call_id")
            pre = self._pending.pop(call_id, None) if call_id else None
            if pre is None:
                return  # not a call this gateway shaped (e.g. OpenAI lane): nothing to pair
            try:
                ms = round((end_time - start_time).total_seconds() * 1000)
            except Exception:  # noqa: BLE001
                ms = None
            row = {
                "v": 2,
                "kind": "outcome",
                "mode": pre["mode"],
                "call_id": call_id,
                "session": pre.get("session"),
                "model": pre.get("model"),
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "latency_ms": ms,
                "ok": error is None,
                "est_tokens_cut": pre.get("est_tokens_cut", 0),
                "prefix_broken": pre["steps"]["m1"]["prefix_broken"],
            }
            if error is not None:
                row["error"] = str(error)[:300]
            else:
                row["usage"] = _usage_numbers(response_obj, kwargs)
            _ledger_write(row)
        except Exception as exc:  # noqa: BLE001 - the ledger may never fail the request
            log.warning("[ledger] outcome not written: %s", exc)

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._outcome(kwargs, response_obj, start_time, end_time)

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        self._outcome(
            kwargs,
            response_obj,
            start_time,
            end_time,
            error=kwargs.get("exception") or "failed",
        )


proxy_handler_instance = EstateEfficiencyGateway()
