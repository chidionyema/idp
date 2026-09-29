"""Every exchange through the laptop router lands in the estate graph's spool. Agents are not asked.

Registered (laptop only, by bin/litellm-local) as graph_capture.proxy_handler_instance.

WHY. 2026-09-28: growmos only learned when an agent chose to run remember/link/next, so it was an
agent duty, and a CI gate (growmos-writeback) policed the duty after the fact by checking that a
.jsonl file was touched. Founder: agents should have no choice; gravity does not ask. Every model
call from every harness already passes this router, so capture sits here: nothing to opt into,
nothing to route around.

WHAT. On each successful call: the last user text and the assistant's text (tool payloads and the
repeated history are dropped -- they are resent every turn) are appended to
~/.estate/graph-spool/<session>.md. No model call, no network, never raises: the request path
pays one small file append. bin/estate-graph-drain turns idle spool files into graph entities.

Not captured: the drain's own extraction calls (growmos's stdlib client, User-Agent
Python-urllib), or the graph would feed on itself.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

try:
    from litellm.integrations.custom_logger import CustomLogger
except ModuleNotFoundError:  # importable without litellm (tests)

    class CustomLogger:  # type: ignore[no-redef]
        pass


log = logging.getLogger("graph_capture")
MAX_CHARS = int(os.environ.get("ESTATE_GRAPH_CAPTURE_MAX_CHARS", "4000"))


def spool_dir() -> str:
    return os.path.expanduser(
        os.environ.get("ESTATE_GRAPH_SPOOL") or "~/.estate/graph-spool"
    )


def _text(content: Any) -> str:
    """Plain text of an OpenAI or Anthropic content value; tool blocks are not text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _reply(resp: Any) -> str:
    if hasattr(resp, "model_dump"):
        resp = resp.model_dump()
    if not isinstance(resp, dict):
        return ""
    if resp.get("choices"):
        return _text(((resp["choices"][0] or {}).get("message") or {}).get("content"))
    return _text(resp.get("content"))


def _last_user(messages: Any) -> str:
    for m in reversed(messages or []):
        if isinstance(m, dict) and m.get("role") == "user":
            t = _text(m.get("content")).strip()
            if t:
                return t
    return ""


def _session(kwargs: dict) -> str:
    meta = (kwargs.get("litellm_params") or {}).get("metadata") or {}
    uid = meta.get("user_api_key_end_user_id") or ""
    body = ((kwargs.get("litellm_params") or {}).get("proxy_server_request") or {}).get(
        "body"
    ) or {}
    raw = (
        (body.get("metadata") or {}).get("user_id") if isinstance(body, dict) else None
    )
    if isinstance(raw, str):
        try:
            uid = json.loads(raw).get("session_id") or uid
        except (ValueError, AttributeError):
            uid = raw
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(uid or "no-session"))[:80]


def _is_drain(kwargs: dict) -> bool:
    req = (kwargs.get("litellm_params") or {}).get("proxy_server_request") or {}
    ua = str((req.get("headers") or {}).get("user-agent", ""))
    return ua.startswith("Python-urllib")


def capture(kwargs: dict, response_obj: Any) -> str | None:
    """Append this exchange to its session's spool file; return the path, or None if skipped."""
    if _is_drain(kwargs):
        return None
    user = _last_user(kwargs.get("messages"))[:MAX_CHARS]
    # A streamed call's response_obj is the last chunk; the assembled reply is kept beside it.
    slo = kwargs.get("standard_logging_object") or {}
    reply = ""
    for r in (
        kwargs.get("complete_streaming_response"),
        slo.get("response"),
        response_obj,
    ):
        reply = _reply(r)
        if reply:
            break
    reply = reply[:MAX_CHARS]
    if not user and not reply:
        return None
    d = spool_dir()
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, _session(kwargs) + ".md")
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n## {stamp} {kwargs.get('model', '')}\n")
        if user:
            f.write(f"\n**asked:** {user}\n")
        if reply:
            f.write(f"\n**answered:** {reply}\n")
    return path


class GraphCapture(CustomLogger):
    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            capture(kwargs, response_obj)
        except Exception as exc:  # noqa: BLE001 - capture may never fail the request
            log.warning("[graph_capture] not spooled: %s", exc)


proxy_handler_instance = GraphCapture()
