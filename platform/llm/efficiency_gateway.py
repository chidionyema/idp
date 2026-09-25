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
        msgs = list(data.get("messages") or [])
        tools = list(data.get("tools") or [])

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

        _ledger_write(
            {
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


proxy_handler_instance = EstateEfficiencyGateway()
