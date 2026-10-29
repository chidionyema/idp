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
  - A second home (#7397): past the last good answer in RAM, the brief and the focus are served
    from the memory snapshot (platform/estate/memory/snapshot.py), with their age in the block.
    A dead cluster costs freshness, not memory.

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
import threading
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
# Past FOCUS_TTL_S a good answer is still served while one background read replaces it: the
# laptop door's gh search takes ~3.6 s, longer than the whole read deadline, so a caller that
# waited for it lost the focus at every expiry (measured 2026-10-20: 3 of 40 calls). Past this
# age the answer is too old to show and the caller waits again.
FOCUS_STALE_S = 600
MAX_FOCUS_ROWS = 8
TASK_CHARS = 2000
MARKER = "<estate-memory"
INTERNAL = (
    "estate-shadow-state"  # efficiency_gateway.INTERNAL: the router's own fold calls
)
CHAT_CALLS = {"completion", "acompletion", "anthropic_messages", "text_completion"}

_brief_cache: dict[str, tuple[float, dict | None]] = {}
_focus_cache: list = [0.0, None]
_focus_refresh = threading.Lock()  # held by the one read in flight
_focus_tried: list = [0.0]
_written: dict[str, float] = {}
_door_key: list = [0.0, ""]
# The last answer each leg got right, kept past its TTL: when a read stalls or fails, an old fact
# beats no fact (the router lost ~2,100 reads to "no answer inside 3.5s" on 2026-10-21/22).
STALE_MAX_S = float(os.environ.get("ACTIVE_MEMORY_STALE_MAX_S", "1800"))
_last_good: dict[str, tuple[float, dict]] = {}
# Past STALE_MAX_S, or after a restart emptied _last_good, the memory snapshot is the floor
# (platform/estate/memory/snapshot.py, #7397): on 2026-10-28 the door was down for hours and 841
# brief reads ended "nothing to serve". Found through MEMORY_LIB, else beside this file in the repo.
SNAPSHOT_LIB = os.environ.get("ESTATE_SNAPSHOT_LIB") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "estate", "memory"
)
SNAP_KEEP_S = 60  # a good brief is folded into the local snapshot at most once a minute
# The background focus refresh waits on nobody, so it is not cut at BUDGET_S (see _door_focus).
FOCUS_REFRESH_S = float(os.environ.get("ACTIVE_FOCUS_REFRESH_S", "10"))
_snap_tried: list = [0.0]
_snap_kept: list = [0.0]
_started: dict[str, float] = {}  # leg -> when its latest read began
_elapsed: dict[str, float] = {}  # leg -> how long its latest finished read took


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


def _named(data: dict, user_api_key_dict: Any = None) -> bool:
    """Whether the caller names itself (header, metadata, virtual-key alias)."""
    hdrs = _headers(data)
    meta = data.get("metadata") or {}
    return any(
        str(c or "").strip()
        for c in (
            hdrs.get("x-estate-agent"),
            meta.get("agent") if isinstance(meta, dict) else None,
            meta.get("user_api_key_alias") if isinstance(meta, dict) else None,
            getattr(user_api_key_dict, "key_alias", None),
        )
    )


def skip_reason(data: dict, call_type: Any, user_api_key_dict: Any = None) -> str:
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
    # The drain is the urllib caller that names nobody (growmos cannot set a header; the laptop
    # router has no virtual keys). The UA alone also matched fleetview-voice, keyed and named,
    # which then never got memory (docs/diagnoses/2026-10-20-stdlib-callers-skipped-as-graph-drain.yaml).
    if str(hdrs.get("user-agent", "")).startswith("Python-urllib") and not _named(
        data, user_api_key_dict
    ):
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


def _door_focus(timeout: float = 0.0) -> dict:
    _, focus = _lib()
    # A caller waits at most BUDGET_S, so its gh read is cut there: past it, an abandoned gh kept
    # running, uncached, and the next call started another. The background refresh is nobody's
    # wait and gets FOCUS_REFRESH_S. Cutting it at BUDGET_S too killed every refresh, because the
    # gh search itself takes longer (4.6 s measured 2026-10-29 against BUDGET_S 3.0), and once the
    # register aged past FOCUS_STALE_S every caller had nothing (#7397). An unreadable ledger
    # answers with the last register, aged (focus.last_register).
    rows = focus.live_focus(timeout=timeout or BUDGET_S, fallback=True)
    if rows is None:
        return {
            "available": False,
            "error": "claim ledger unreadable (gh)",
            "claims": [],
        }
    return _focus_body(rows)


def _focus_body(rows: list) -> dict:
    """focus.py register rows in fleetview's /claims shape."""
    body = {
        "available": True,
        "claims": [
            {
                "issue": str(r.get("claim", "")).rpartition("#")[2],
                "agent": r.get("agent"),
                "paths": r.get("paths"),
                "live": r.get("live") is True,
            }
            for r in rows
            if isinstance(r, dict)
        ],
    }
    stale_s = max(
        (r.get("stale_s") or 0 for r in rows if isinstance(r, dict)), default=0
    )
    if stale_s:
        body["stale_s"] = stale_s
    return body


# --------------------------------------------------------------------------- the snapshot


def _snap():
    """platform/estate/memory/snapshot.py, or None where it is not shipped: the router runs fine
    without its second home, it only loses it."""
    import sys  # noqa: PLC0415

    for d in (MEMORY_LIB, SNAPSHOT_LIB):
        if d and os.path.isdir(d) and d not in sys.path:
            sys.path.insert(0, d)
    try:
        import snapshot  # noqa: PLC0415

        return snapshot
    except Exception:  # noqa: BLE001
        return None


def snapshot_brief(task: str, now: float | None = None) -> tuple[dict, float] | None:
    """(brief, facts age in seconds) answered from the local snapshot, or None. Local only: the
    caller is waiting, so the R2 read happens in the background (_pull_snapshot)."""
    snap_mod = _snap()
    if snap_mod is None:
        return None
    now = time.time() if now is None else now
    snap = snap_mod.read_local()
    _pull_snapshot(snap_mod, snap, now)
    if not snap or not snap.get("facts"):
        return None
    body = snap_mod.brief(snap, task, BRIEF_LIMIT, now)
    if not (body["relevant"] or body["recent"]):
        return None
    return body, float(body["snapshot"]["facts_age_s"])


def snapshot_focus(now: float | None = None) -> tuple[dict, float] | None:
    snap_mod = _snap()
    if snap_mod is None:
        return None
    now = time.time() if now is None else now
    snap = snap_mod.read_local()
    _pull_snapshot(snap_mod, snap, now)
    if not snap or not snap.get("focus_at"):
        return None
    return _focus_body(snap_mod.focus_rows(snap, now)), now - float(snap["focus_at"])


def _pull_snapshot(snap_mod: Any, local: dict | None, now: float) -> None:
    """Refresh the local copy from R2 in the background, at most once per PULL_AFTER_S."""
    if local and now - snap_mod.stamp(local) < snap_mod.PULL_AFTER_S:
        return
    if now - _snap_tried[0] < snap_mod.PULL_AFTER_S or not snap_mod.r2_config():
        return
    _snap_tried[0] = now
    threading.Thread(
        target=lambda: snap_mod.load(now=now), daemon=True, name="snapshot-pull"
    ).start()


def keep_brief(body: dict | None, now: float | None = None) -> None:
    """Fold a good brief's facts into the local snapshot, at most once per SNAP_KEEP_S, so a
    router restart or an hour-long door outage still has the facts this machine last read.
    Bounded and floor-guarded by snapshot.write_local; never raises."""
    now = time.time() if now is None else now
    if not isinstance(body, dict) or now - _snap_kept[0] < SNAP_KEEP_S:
        return
    snap_mod = _snap()
    if snap_mod is None:
        return
    _snap_kept[0] = now

    def fold() -> None:
        try:
            snap = snap_mod.read_local() or {
                "version": snap_mod.VERSION,
                "namespace": NAMESPACE,
                "facts": [],
                "focus": [],
            }
            by_key = {
                str(f.get("key")): f for f in snap["facts"] if isinstance(f, dict)
            }
            for f in (body.get("relevant") or []) + (body.get("recent") or []):
                if isinstance(f, dict) and f.get("key"):
                    by_key[str(f["key"])] = f
            snap.update(facts=list(by_key.values()), facts_at=now, source="router")
            why = snap_mod.write_local(snap)
            if why:
                log.warning("active_memory snapshot not kept: %s", why)
        except Exception as exc:  # noqa: BLE001
            log.warning("active_memory snapshot not kept: %s", exc)

    threading.Thread(target=fold, daemon=True, name="snapshot-keep").start()


def _brief_key(task: str) -> str:
    return hashlib.sha256(f"{NAMESPACE}\0{task}".encode()).hexdigest()


def fetch_brief(task: str, now: float | None = None) -> dict | None:
    now = time.time() if now is None else now
    key = _brief_key(task)
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
    if isinstance(body, dict):
        _last_good["brief:" + key] = (now, body)
        keep_brief(body, now)
    if len(_brief_cache) > 512:  # a router lives for days; the cache must not
        for k, _ in sorted(_brief_cache.items(), key=lambda kv: kv[1][0])[:256]:
            _brief_cache.pop(k, None)
    if len(_last_good) > 512:
        for k, _ in sorted(_last_good.items(), key=lambda kv: kv[1][0])[:256]:
            _last_good.pop(k, None)
    return _brief_cache[key][1]


def fetch_focus(now: float | None = None) -> dict | None:
    now = time.time() if now is None else now
    if not (FOCUS_URL or DOOR == "mcp") or now - _focus_cache[0] < FOCUS_TTL_S:
        return _focus_cache[1]
    stamp, good = _focus_cache
    if _usable(good) and now - stamp < FOCUS_STALE_S:
        # one read in flight, and none again until FOCUS_TTL_S after the last try: a gh
        # outage must not start a search on every chat call
        if now - _focus_tried[0] >= FOCUS_TTL_S and _focus_refresh.acquire(
            blocking=False
        ):
            threading.Thread(
                target=_refresh_focus, args=(now,), daemon=True, name="focus-refresh"
            ).start()
        return good
    with _focus_refresh:
        if _focus_cache[0] != stamp:  # another caller read it while this one waited
            return _focus_cache[1]
        _read_focus(now, BUDGET_S)
    return _focus_cache[1]


def _read_focus(now: float, timeout: float = 0.0) -> None:
    _focus_tried[0] = now
    timeout = timeout or BUDGET_S
    body = _door_focus(timeout) if DOOR == "mcp" else _get_json(FOCUS_URL, timeout)
    body = body if isinstance(body, dict) else None
    # an unreadable answer never replaces a good one young enough to show
    if (
        _usable(body)
        or not _usable(_focus_cache[1])
        or (now - _focus_cache[0] >= FOCUS_STALE_S)
    ):
        _focus_cache[:] = [now, body]


def _usable(body: dict | None) -> bool:
    return isinstance(body, dict) and body.get("available", True) is not False


def _refresh_focus(now: float) -> None:
    try:
        _read_focus(now, FOCUS_REFRESH_S)
    except Exception as exc:  # the stale answer stands; the next expiry tries again
        log.warning("active_memory focus refresh failed: %s", exc)
    finally:
        _focus_refresh.release()


def _timed(leg: str, fn: Any, *args: Any) -> Any:
    """Run one read and record when it started and how long it took, so a read the router gave up
    on can still be measured (the 2026-10-22 failures logged neither a time nor a duration)."""
    t0 = time.time()
    _started[leg] = t0
    try:
        return fn(*args)
    finally:
        _elapsed[leg] = time.time() - t0


def stale(leg_key: str, now: float | None = None) -> tuple[dict, float] | None:
    """(last good answer, its age in seconds) if one is younger than STALE_MAX_S, else None."""
    hit = _last_good.get(leg_key)
    now = time.time() if now is None else now
    if hit and now - hit[0] <= STALE_MAX_S:
        return hit[1], now - hit[0]
    return None


# --------------------------------------------------------------------------- the block


def _clip(s: Any, n: int) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _live(claim: dict) -> bool:
    # fleetview judges each row (claims.claims_snapshot: `live`, and `reason` when not). Only
    # its explicit True counts: a stale or released claim shown as held is the ghost focus
    # idp#6543 removed from the brief, and a row with no verdict is not evidence of one.
    return claim.get("live") is True


def _age(seconds: Any) -> str:
    s = max(0, int(seconds or 0))
    return f"{s // 3600}h{s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60}m"


def _fact_line(f: dict) -> str:
    # The brief sends {text, metadata: {kind, subject, ...}} (as focus.drop_stale reads it). This
    # read {content, provenance.kind, key}, a shape the server never sends, so from the day it
    # shipped every fact reached every model as "- [fact]  (None)" (seen live 2026-10-21, #6789).
    # The old names stay as a fallback; a fact with no text is dropped, not shown empty.
    meta = f.get("metadata") or f.get("provenance") or {}
    meta = meta if isinstance(meta, dict) else {}
    kind = meta.get("kind") or "fact"
    text = _clip(f.get("text") or f.get("content"), 280)
    ref = meta.get("subject") or f.get("key")
    return f"- [{kind}] {text}" + (f" ({ref})" if ref else "")


def render(brief: dict | None, focus: dict | None, who: str) -> str:
    """The block the model reads. Empty when neither read said anything."""
    lines: list[str] = []
    facts = [
        *((brief or {}).get("relevant") or []),
        *((brief or {}).get("recent") or []),
    ]
    facts = [
        f for f in facts if isinstance(f, dict) and (f.get("text") or f.get("content"))
    ]
    if facts:
        snap = (brief or {}).get("snapshot")
        if isinstance(snap, dict):
            # an old fact is still worth reading, never worth reading as new
            lines.append(
                "Active Memory (memory server unreachable; from the snapshot, facts "
                f"{_age(snap.get('facts_age_s'))} old) -- what the estate knew about this task:"
            )
        else:
            lines.append(
                "Active Memory -- what the estate already knows about this task:"
            )
        for f in facts:
            lines.append(_fact_line(f))
    if focus is not None:
        if focus.get("available") is False:
            lines.append(
                f"Active Focus: unreadable right now ({_clip(focus.get('error'), 120)})."
            )
        else:
            live = [
                c for c in focus.get("claims") or [] if isinstance(c, dict) and _live(c)
            ]
            asof = (
                f" (claim ledger unreadable; as read {_age(focus['stale_s'])} ago)"
                if focus.get("stale_s")
                else ""
            )
            if live:
                lines.append(
                    f"Active Focus{asof} -- live claims; do not edit a path another agent holds:"
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
                lines.append(f"Active Focus{asof}: no live claims.")
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
            why = skip_reason(data, call_type, user_api_key_dict)
            if why or carries_block(data["messages"]):
                log.debug("active_memory skip: %s", why or "already carries a brief")
                return data
            task = last_human(data["messages"])
            if not task:
                return data
            who = agent(data, user_api_key_dict)
            # A deadline each, not one over both: a slow brief must not cost the focus that
            # already answered (measured 2026-10-20: a 20 s brief dropped a 2 s focus read).
            began = time.time()
            reads = [
                asyncio.ensure_future(
                    asyncio.to_thread(_timed, "brief", fetch_brief, task)
                ),
                asyncio.ensure_future(asyncio.to_thread(_timed, "focus", fetch_focus)),
            ]
            await asyncio.wait(reads, timeout=BUDGET_S + 0.5)
            waited = time.time() - began
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
            # fetch_focus keeps its own last good register (FOCUS_STALE_S); past it, and for the
            # brief past STALE_MAX_S or after a restart, the snapshot is the floor.
            fallback = {
                "brief": lambda: stale("brief:" + _brief_key(task)),
                "focus": lambda: None,
            }
            floor = {"brief": lambda: snapshot_brief(task), "focus": snapshot_focus}
            for name, r in (("brief", brief), ("focus", focus)):
                # A focus read that "answered" that the ledger is unreadable is a failure too.
                failed = isinstance(r, BaseException) or (
                    name == "focus"
                    and isinstance(r, dict)
                    and r.get("available") is False
                )
                if not failed:
                    continue
                old, served = fallback[name](), "serving stale"
                if not old:
                    old, served = floor[name](), "serving snapshot"
                log.warning(
                    "active_memory %s unreadable for %s: %s at=%s waited=%.2fs "
                    "leg_elapsed=%s load1=%.1f %s",
                    name,
                    who,
                    r if isinstance(r, BaseException) else r.get("error"),
                    time.strftime("%H:%M:%SZ", time.gmtime(began)),
                    waited,
                    f"{_elapsed[name]:.2f}s" if name in _elapsed else "running",
                    os.getloadavg()[0],
                    f"{served} age={old[1]:.0f}s" if old else "nothing to serve",
                )
                if old:
                    if name == "brief":
                        brief = old[0]
                    else:
                        focus = old[0]
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
