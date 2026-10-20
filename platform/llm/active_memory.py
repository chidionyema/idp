"""Every model call through the router carries the estate's Active Memory and Active Focus.

WHY (2026-10-20). Measured that day: of every agent in the estate only Claude Code read the
unified memory -- through its own MCP bridge and session hooks. Otto answered from a store of its
own, the face and fleet voice never recalled anything ("Nothing here needs remembering"), and the
memory server's 24-hour log held 5 recalls against 20,166 health probes. Founder: "all models,
agents and harnesses need to use it, find a way to integrate elegantly ... rather than having to
implement multiple places." Wiring each agent separately is the shape that produced the gap: one
adapter per runtime, each its own way to forget. Every one of them already sends its model calls
through this router (face and fleet over llm.<zone>, Otto's home-estate lane, the workers, Claude
Code through litellm-local), so the memory sits here, like graph_capture: nothing to opt into,
nothing to route around.

WHAT, before a call: the last human text of the conversation is the task. The memory server's
/memories/brief answers with the facts nearest it and the newest decisions and incidents (Active
Memory); fleetview's /claims answers with who holds which files right now (Active Focus -- the
same GitHub ledger bin/claim-gate refuses lanes against, never a second record). Both render
into one <estate-memory> block appended to the last user message.

  - The tail, never the system prompt: the client's prompt-cache prefix stays byte-identical,
    so a brief costs its own few hundred tokens and never a re-write of the cached history.
  - Keyed by the human text, not the call: an agent loop's tool-result continuations carry the
    same block as the turn that started them, without asking the server again.
  - Once: a request that already holds an <estate-memory> block (a nested router hop, a client
    that pasted one) is left alone.
  - Never in the way: every read has a deadline (ACTIVE_MEMORY_BUDGET_S), every failure is
    logged and the call goes on without the block. A memory outage costs memory, not answers.

WHAT, after a call: the turn (human text and the reply) is written to the agent's working memory
through /harness/memory/consolidate as one ephemeral_turn -- scratchpad, an hour, expired by the
hourly consolidation CronJob. Durable facts still go through `remember`; a router that promoted
every exchange to a fact would bury the facts. Once per human turn, not per tool call.

Two transports, one block. In the cluster the router posts to the memory server's REST routes
and reads fleetview's /claims (ESTATE_MEMORY_URL, ESTATE_FOCUS_URL). On the laptop
(ESTATE_MEMORY_DOOR=mcp, set by bin/litellm-local) there is no in-cluster address: the brief goes
through the MCP door every local runtime uses (#6156, platform/estate/memory/door.py, its key read
by name from the env or the vault) and focus through focus.live_focus -- the same two calls
bin/estate-brief makes, imported, not copied. Door mode writes no turn: the door exposes durable
`remember`, not scratchpad, and a turn is not a fact.

Not touched: embeddings and every non-chat call (the memory server embeds through this router,
so a brief on an embedding would ask for itself), the router's own internal calls
(estate_internal), the graph drain (User-Agent Python-urllib), and any caller that sends
`x-estate-memory: off`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from typing import Any

try:
    from litellm.integrations.custom_logger import CustomLogger
except ModuleNotFoundError:  # importable without litellm (tests)

    class CustomLogger:  # type: ignore[no-redef]
        pass


log = logging.getLogger("active_memory")

MEMORY_URL = os.environ.get("ESTATE_MEMORY_URL", "").rstrip("/")
MEMORY_HOST = os.environ.get("ESTATE_MEMORY_HOST", "")
MEMORY_TOKEN_FILE = os.environ.get("ESTATE_MEMORY_TOKEN_FILE", "")
NAMESPACE = os.environ.get("ESTATE_MEMORY_NAMESPACE", "estate")
FOCUS_URL = os.environ.get("ESTATE_FOCUS_URL", "")
DOOR = os.environ.get("ESTATE_MEMORY_DOOR", "")  # "mcp": laptop, see the docstring
# Where door.py and focus.py live: bin/litellm-local stages platform/estate/memory there.
MEMORY_LIB = os.environ.get("ESTATE_MEMORY_LIB", "")
KEY_TTL_S = 300  # the door key comes from a vault subprocess: once per five minutes, not per call
# One deadline for the whole read, brief and focus together: the first call of a human turn
# waits at most this long, and every later call of that turn is a cache hit.
BUDGET_S = float(os.environ.get("ACTIVE_MEMORY_BUDGET_S", "1.5"))
MAX_CHARS = int(os.environ.get("ACTIVE_MEMORY_MAX_CHARS", "2400"))
BRIEF_LIMIT = int(os.environ.get("ACTIVE_MEMORY_BRIEF_LIMIT", "5"))
BRIEF_TTL_S = 300
FOCUS_TTL_S = 30  # fleetview itself re-reads GitHub every 30 s (claims.CACHE_S)
MAX_FOCUS_ROWS = 8
TASK_CHARS = 2000
MARKER = "<estate-memory"
INTERNAL = (
    "estate-shadow-state"  # efficiency_gateway.INTERNAL: the router's own fold calls
)
CHAT_CALLS = {"completion", "acompletion", "anthropic_messages", "text_completion"}

_brief_cache: dict[str, tuple[float, dict | None]] = {}
_focus_cache: list = [0.0, None]
_written: dict[str, float] = {}
_door_key: list = [0.0, ""]


# --------------------------------------------------------------------------- request shape


def _text(content: Any) -> str:
    """The human-readable text of a message: a string, or the text blocks of a list."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(b.get("text") or "")
            for b in content
            if isinstance(b, dict) and b.get("type") in ("text", "input_text")
        )
    return ""


def _strip_block(text: str) -> str:
    i = text.find(MARKER)
    return text[:i] if i >= 0 else text


def last_human(messages: Any) -> str:
    """The newest user message that carries text -- a tool_result continuation is skipped,
    so every call of one agent loop resolves to the turn that started it. A block this
    module appended is not part of the task."""
    for m in reversed(messages or []):
        if isinstance(m, dict) and m.get("role") == "user":
            t = _strip_block(_text(m.get("content"))).strip()
            if t:
                return t
    return ""


def _headers(data: dict) -> dict:
    req = data.get("proxy_server_request") or {}
    hdrs = req.get("headers") if isinstance(req, dict) else None
    return {str(k).lower(): v for k, v in (hdrs or {}).items()}


def agent(data: dict, user_api_key_dict: Any = None) -> str:
    """Who is calling, by the explicit identity rule graph_capture and bin/claim-open use: the
    x-estate-agent header, request metadata, the virtual-key alias; then the harness
    User-Agent; "unknown" is the floor. A name is never invented."""
    hdrs = _headers(data)
    meta = data.get("metadata") or {}
    alias = getattr(user_api_key_dict, "key_alias", None)
    for c in (
        hdrs.get("x-estate-agent"),
        meta.get("agent"),
        meta.get("user_api_key_alias"),
        alias,
    ):
        c = str(c or "").strip()
        if c:
            return re.sub(r"[^A-Za-z0-9_.-]", "_", c)[:40]
    ua = str(hdrs.get("user-agent", ""))
    harness = re.split(r"[/\s]", ua, maxsplit=1)[0].strip().lower() if ua else ""
    return harness or "unknown"


def skip_reason(data: dict, call_type: Any) -> str:
    """Why this call gets no memory, or "" when it does."""
    ct = str(getattr(call_type, "value", call_type) or "")
    if ct and ct not in CHAT_CALLS:
        return f"call_type={ct}"
    if not isinstance(data.get("messages"), list) or not data["messages"]:
        return "no messages"
    meta = data.get("metadata") or {}
    hdrs = _headers(data)
    if (isinstance(meta, dict) and meta.get("estate_internal") == INTERNAL) or hdrs.get(
        "x-estate-internal"
    ) == INTERNAL:
        return "internal"
    if str(hdrs.get("user-agent", "")).startswith("Python-urllib"):
        return "graph drain"
    if str(hdrs.get("x-estate-memory", "")).lower() == "off":
        return "caller opted out"
    if not MEMORY_URL and DOOR != "mcp":
        return "ESTATE_MEMORY_URL unset"
    return ""


def carries_block(messages: list) -> bool:
    return any(
        MARKER in _text(m.get("content")) for m in messages if isinstance(m, dict)
    )


# --------------------------------------------------------------------------- the two reads


def _token() -> str:
    # Read on every call, never cached: a rotation lands without a router restart.
    try:
        with open(MEMORY_TOKEN_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _memory_post(route: str, body: Any, timeout: float) -> Any:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_token()}",
    }
    if MEMORY_HOST:
        headers["Host"] = MEMORY_HOST
    req = urllib.request.Request(  # noqa: S310 - fixed in-cluster URL from the env
        MEMORY_URL + route,
        data=json.dumps(body).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        return json.loads(r.read() or b"null")


def _get_json(url: str, timeout: float) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 - in-cluster URL
        return json.loads(r.read() or b"null")


def _lib():
    """(door, focus) from platform/estate/memory -- imported, so the laptop brief cannot drift
    from bin/estate-brief's."""
    import sys  # noqa: PLC0415

    if MEMORY_LIB and MEMORY_LIB not in sys.path:
        sys.path.insert(0, MEMORY_LIB)
    import door  # noqa: PLC0415
    import focus  # noqa: PLC0415

    return door, focus


def _door_brief(task: str) -> dict | None:
    door, focus = _lib()
    now = time.time()
    if now - _door_key[0] >= KEY_TTL_S or not _door_key[1]:
        _door_key[:] = [now, door.key().strip()]
    if not _door_key[1]:
        raise RuntimeError(f"no {door.MANIFEST['door']['key_env']} and no vault entry")
    brief = door.call(
        "brief", {"task": task, "limit": BRIEF_LIMIT}, _door_key[1], BUDGET_S
    )
    if isinstance(brief, dict):
        # A hand-written focus fact whose claim is closed is a ghost (idp#6543): same rule
        # as bin/estate-brief.
        for k in ("recent", "relevant"):
            brief[k], _ = focus.drop_stale(brief.get(k) or [])
    return brief


def _door_focus() -> dict:
    _, focus = _lib()
    rows = focus.live_focus()
    if rows is None:
        return {
            "available": False,
            "error": "claim ledger unreadable (gh)",
            "claims": [],
        }
    return {
        "available": True,
        "claims": [
            {
                "issue": str(r.get("claim", "")).rpartition("#")[2],
                "agent": r.get("agent"),
                "paths": r.get("paths"),
                "live": r.get("live") is True,
            }
            for r in rows
        ],
    }


def fetch_brief(task: str, now: float | None = None) -> dict | None:
    now = time.time() if now is None else now
    key = hashlib.sha256(f"{NAMESPACE}\0{task}".encode()).hexdigest()
    hit = _brief_cache.get(key)
    if hit and now - hit[0] < BRIEF_TTL_S:
        return hit[1]
    if DOOR == "mcp":
        body = _door_brief(task[:TASK_CHARS])
    else:
        body = _memory_post(
            "/memories/brief",
            {"task": task[:TASK_CHARS], "namespace": NAMESPACE, "limit": BRIEF_LIMIT},
            BUDGET_S,
        )
    _brief_cache[key] = (now, body if isinstance(body, dict) else None)
    if len(_brief_cache) > 512:  # a router lives for days; the cache must not
        for k, _ in sorted(_brief_cache.items(), key=lambda kv: kv[1][0])[:256]:
            _brief_cache.pop(k, None)
    return _brief_cache[key][1]


def fetch_focus(now: float | None = None) -> dict | None:
    now = time.time() if now is None else now
    if (FOCUS_URL or DOOR == "mcp") and now - _focus_cache[0] >= FOCUS_TTL_S:
        body = _door_focus() if DOOR == "mcp" else _get_json(FOCUS_URL, BUDGET_S)
        _focus_cache[:] = [now, body if isinstance(body, dict) else None]
    return _focus_cache[1]


# --------------------------------------------------------------------------- the block


def _clip(s: Any, n: int) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _live(claim: dict) -> bool:
    # fleetview judges each row (claims.claims_snapshot: `live`, and `reason` when not). Only
    # its explicit True counts: a stale or released claim shown as held is the ghost focus
    # idp#6543 removed from the brief, and a row with no verdict is not evidence of one.
    return claim.get("live") is True


def render(brief: dict | None, focus: dict | None, who: str) -> str:
    """The block the model reads. Empty when neither read said anything."""
    lines: list[str] = []
    facts = [
        *((brief or {}).get("relevant") or []),
        *((brief or {}).get("recent") or []),
    ]
    facts = [f for f in facts if isinstance(f, dict)]
    if facts:
        lines.append("Active Memory -- what the estate already knows about this task:")
        for f in facts:
            kind = (f.get("provenance") or {}).get("kind") or "fact"
            lines.append(f"- [{kind}] {_clip(f.get('content'), 280)} ({f.get('key')})")
    if focus is not None:
        if focus.get("available") is False:
            lines.append(
                f"Active Focus: unreadable right now ({_clip(focus.get('error'), 120)})."
            )
        else:
            live = [
                c for c in focus.get("claims") or [] if isinstance(c, dict) and _live(c)
            ]
            if live:
                lines.append(
                    "Active Focus -- live claims; do not edit a path another agent holds:"
                )
                for c in live[:MAX_FOCUS_ROWS]:
                    paths = c.get("paths") or []
                    if isinstance(paths, str):
                        paths = [p for p in paths.split(",") if p]
                    more = f" +{len(paths) - 3} more" if len(paths) > 3 else ""
                    lines.append(
                        f"- #{c.get('issue')} {c.get('agent')}: {','.join(paths[:3])}{more}"
                    )
                if len(live) > MAX_FOCUS_ROWS:
                    lines.append(f"- +{len(live) - MAX_FOCUS_ROWS} more live claims")
            else:
                lines.append("Active Focus: no live claims.")
    if not lines:
        return ""
    lines.append(
        "Record what you learn with the estate memory `remember` tool; "
        "open a claim before editing files."
    )
    body = "\n".join(lines)
    if len(body) > MAX_CHARS:
        body = body[: MAX_CHARS - 1] + "…"
    return f'<estate-memory agent="{who}">\n{body}\n</estate-memory>'


def inject(messages: list, block: str) -> bool:
    """Append the block to the last user message, in that message's own content shape."""
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                m["content"] = f"{c}\n\n{block}"
            elif isinstance(c, list):
                m["content"] = [*c, {"type": "text", "text": block}]
            else:
                return False
            return True
    return False


# --------------------------------------------------------------------------- the callback


def _reply_text(response_obj: Any) -> str:
    try:
        d = (
            response_obj.model_dump()
            if hasattr(response_obj, "model_dump")
            else dict(response_obj)
        )
    except Exception:  # noqa: BLE001 - a reply we cannot read is a turn we do not record
        return ""
    for ch in d.get("choices") or []:
        t = ((ch or {}).get("message") or {}).get("content")
        if t:
            return str(t)
    return _text(d.get("content"))


def turn_record(kwargs: dict, response_obj: Any) -> tuple[str, list] | None:
    """(route, body) that writes this turn to working memory, or None when it is not written."""
    lp = kwargs.get("litellm_params") or {}
    data = {
        "messages": kwargs.get("messages") or [],
        "metadata": lp.get("metadata") or {},
        "proxy_server_request": lp.get("proxy_server_request") or {},
    }
    if DOOR == "mcp" or skip_reason(data, kwargs.get("call_type")):
        return None
    task = last_human(data["messages"])
    if not task:
        return None
    who = agent(data)
    turn = hashlib.sha256(f"{who}\0{task}".encode()).hexdigest()[:16]
    if turn in _written:  # once per human turn, not once per tool call
        return None
    _written[turn] = time.time()
    if len(_written) > 2048:
        for k in sorted(_written, key=_written.get)[:1024]:
            _written.pop(k, None)
    # untrusted_external: the router relays text it cannot vouch for -- whoever typed it, a
    # model wrote the answer -- and harness.py Rule B keeps that provenance from ever writing a
    # global preference. The router records turns; it never decides what the estate believes.
    route = (
        "/harness/memory/consolidate?run_id="
        + urllib.parse.quote(f"router:{who}:{turn}")
        + "&provenance=untrusted_external"
    )
    answered = _clip(_reply_text(response_obj), 1200)
    candidate = {
        "scope": "ephemeral_turn",
        "subject": who,
        "predicate": "turn",
        "object": json.dumps({"asked": _clip(task, 1200), "answered": answered}),
    }
    return route, [candidate]


class ActiveMemory(CustomLogger):
    async def async_pre_call_hook(
        self, user_api_key_dict: Any, cache: Any, data: dict, call_type: Any
    ):
        try:
            why = skip_reason(data, call_type)
            if why or carries_block(data["messages"]):
                log.debug("active_memory skip: %s", why or "already carries a brief")
                return data
            task = last_human(data["messages"])
            if not task:
                return data
            who = agent(data, user_api_key_dict)
            # A deadline each, not one over both: a slow brief must not cost the focus that
            # already answered (measured 2026-10-20: a 20 s brief dropped a 2 s focus read).
            reads = [
                asyncio.ensure_future(asyncio.to_thread(fetch_brief, task)),
                asyncio.ensure_future(asyncio.to_thread(fetch_focus)),
            ]
            await asyncio.wait(reads, timeout=BUDGET_S + 0.5)
            for (
                r
            ) in reads:  # a read left running still fills its cache for the next call
                r.add_done_callback(lambda f: f.cancelled() or f.exception())
            brief, focus = (
                (r.exception() or r.result())
                if r.done()
                else TimeoutError(f"no answer inside {BUDGET_S + 0.5:.1f}s")
                for r in reads
            )
            for name, r in (("brief", brief), ("focus", focus)):
                if isinstance(r, BaseException):
                    log.warning("active_memory %s unreadable for %s: %s", name, who, r)
            block = render(
                None if isinstance(brief, BaseException) else brief,
                None if isinstance(focus, BaseException) else focus,
                who,
            )
            if block and inject(data["messages"], block):
                meta = data.setdefault("metadata", {})
                if isinstance(meta, dict):
                    meta["active_memory"] = {"agent": who, "chars": len(block)}
                log.warning("active_memory injected agent=%s chars=%d", who, len(block))
        except Exception as exc:  # noqa: BLE001 - never fail the request (LAW 38)
            log.warning("active_memory skipped: %s", exc)
        return data

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            rec = turn_record(kwargs, response_obj)
            if rec:
                await asyncio.to_thread(_memory_post, rec[0], rec[1], BUDGET_S * 2)
        except Exception as exc:  # noqa: BLE001 - a lost turn is logged, never raised
            log.warning("active_memory turn not recorded: %s", exc)


proxy_handler_instance = ActiveMemory()
