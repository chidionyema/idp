"""No hand-back, at the router: every model call carries the directive to drive the work to done.

The founder, 2026-10-22: "i need proactive workkers not narrators and shrikers ... once given a
feature every model should drive it thru to fully operational and proven before contacting founder
or pausing". The Stop hook (bin/estate-memory-enforce) refuses a hand-back on harnesses that have
one; this is the other half, for every model behind this router whatever harness calls it: the
instruction rides in the system prompt of every chat call, so a model that never sees a hook is
still told.

Self-contained on purpose: the router mounts flat modules from a ConfigMap, so this file cannot
import platform/estate/memory/handback.py. tests/test_no_handback.py holds DIRECTIVE equal to
handback.DIRECTIVE so the two cannot drift.

Appended at the END of the system prompt, once (MARKER makes it idempotent): the client's own
prompt-cache prefix stays byte-identical, and the added tail is a constant. Fails open on every
error (LAW 38). ESTATE_NO_HANDBACK=0 turns it off.
"""

from __future__ import annotations

import logging
import os
from typing import Any

try:
    from litellm.integrations.custom_logger import CustomLogger
except ModuleNotFoundError:  # importable without litellm (tests)

    class CustomLogger:  # type: ignore[no-redef]
        pass


log = logging.getLogger("no_handback")

MARKER = "[estate:no-handback]"
DIRECTIVE = (
    "Drive every task through to operational and proven before you stop. Never end a turn by "
    "handing work back: no 'still open' or 'remaining' lists, no 'want me to...?', 'shall I...?' "
    "or 'let me know if...', no steps left for the founder. If something is undone, do it now; if "
    "a step failed, diagnose and retry a different way. Stop only when the work is done and "
    "proven on its real path, or irrevocably blocked after you have tried to unblock yourself. "
    "A blocker is reported with its evidence: the intent you ran (estate-execute <intent>), its "
    "exit status, and the line it printed."
)
BLOCK = f"{MARKER} {DIRECTIVE}"

SYSTEM_ROLES = {"system", "developer"}
# Only prompts a model answers: an embedding call has `input` too, and an `instructions` field
# there is a parameter the provider rejects.
PROMPT_CALLS = {
    "completion",
    "acompletion",
    "anthropic_messages",
    "text_completion",
    "atext_completion",
    "responses",
    "aresponses",
}
INTERNAL = (
    "estate-shadow-state"  # efficiency_gateway.INTERNAL: the router's own fold calls
)


def enabled() -> bool:
    return os.environ.get("ESTATE_NO_HANDBACK") != "0"


def skip(data: dict, call_type: Any) -> bool:
    ct = str(getattr(call_type, "value", call_type) or "")
    if ct and ct not in PROMPT_CALLS:
        return True
    meta = data.get("metadata") or {}
    req = data.get("proxy_server_request") or {}
    hdrs = req.get("headers") if isinstance(req, dict) else None
    hdrs = {str(k).lower(): v for k, v in (hdrs or {}).items()}
    return (
        isinstance(meta, dict) and meta.get("estate_internal") == INTERNAL
    ) or hdrs.get("x-estate-internal") == INTERNAL


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and isinstance(b.get("text"), str)
        )
    return ""


def _append(content: Any) -> Any:
    """`content` with the directive appended in its own shape, or None when the shape is unknown."""
    if content is None or content == "":
        return BLOCK
    if isinstance(content, str):
        return f"{content}\n\n{BLOCK}"
    if isinstance(content, list):
        return [*content, {"type": "text", "text": BLOCK}]
    return None


def carries(data: dict) -> bool:
    if MARKER in _text(data.get("system")) or MARKER in _text(data.get("instructions")):
        return True
    return any(
        isinstance(m, dict) and MARKER in _text(m.get("content"))
        for m in data.get("messages") or []
    )


def inject(data: dict) -> str | None:
    """Put the directive in the system prompt of `data` in place. The field used, or None."""
    if carries(data):
        return None
    if "system" in data:  # Anthropic /v1/messages: system is a field, not a message
        merged = _append(data["system"])
        if merged is not None:
            data["system"] = merged
            return "system"
        return None
    messages = data.get("messages")
    if isinstance(messages, list) and messages:
        for m in reversed(messages):
            if isinstance(m, dict) and m.get("role") in SYSTEM_ROLES:
                merged = _append(m.get("content"))
                if merged is None:
                    return None
                m["content"] = merged
                return "messages"
        messages.insert(0, {"role": "system", "content": BLOCK})
        return "messages"
    if "input" in data:  # Responses API
        merged = _append(data.get("instructions"))
        if merged is not None:
            data["instructions"] = merged
            return "instructions"
    return None


class NoHandback(CustomLogger):
    async def async_pre_call_hook(
        self, user_api_key_dict: Any, cache: Any, data: dict, call_type: Any
    ):
        try:
            if enabled() and isinstance(data, dict) and not skip(data, call_type):
                field = inject(data)
                if field:
                    meta = data.setdefault("metadata", {})
                    if isinstance(meta, dict):
                        meta["no_handback"] = field
                    log.debug("no_handback injected into %s", field)
        except Exception as exc:  # noqa: BLE001 - never fail the request (LAW 38)
            log.warning("no_handback skipped: %s", exc)
        return data


proxy_handler_instance = NoHandback()
