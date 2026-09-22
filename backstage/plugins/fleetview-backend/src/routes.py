"""FleetView backend plugin: the two routes CP1's done-command names.

`GET /api/fleetview/sessions` and `GET /api/fleetview/stream` are served from the portal backend at
`backstage/packages/backend/src/`. This module is the plugin's router: it owns the paths, the
envelope and the status codes, and it delegates every decision about what a session IS to
`src/sessions.py`, so the translation lives in exactly one file.

The envelope. A read that cannot produce an answer says so rather than returning an empty board:
  {"available": true,  "sessions": [...], "unreachable": []}
  {"available": false, "error": "...", "sessions": [], "unreachable": [...]}
An empty board and a broken board are different facts and the page must be able to tell them
apart. `unreachable` names each adapter that could not answer, so a dead runtime is visible
instead of looking like a quiet fleet -- the same rule the estate's world-model graders follow
when a grader that cannot run is UNKNOWN rather than a pass.

The stream is server-sent events. A client opens it once and receives one frame per session change;
that is what replaces the old 3-second poll (the retired cockpit). The event shape comes from
`sessions.stream_event_for`.

`GET /api/fleetview/notes?session_id=...` and `POST /api/fleetview/notes` are the notes mailbox
(`src/notes.py`): leave a note for a session, any runtime, read back later. No runtime delivers a
note into a live process today -- that is a documented, honest gap, not hidden behind this route.

`POST /api/fleetview/nudge` (item #6, `src/signals.py`) steers a real, running sovereign session --
the one runtime with a live signal path -- and always records the attempt. A runtime with no such
path gets 422, never a 200 that pretended to deliver something.

`GET /api/fleetview/signals?session_id=...` (`src/signals.py`'s `signals_for`) reads back that same
audit trail -- every nudge attempt ever recorded for a session, newest first -- so a focus view can
show what was already tried, not just offer the button again.

`GET /api/fleetview/blast-radius?node_id=...` (item #7, `src/blast.py`) answers "if this dies,
what dies with it" over the same `edges` table `bin/estate-twin-runtime --blast-radius` already
walks -- a Backstage door onto an existing CLI-only answer, not a new graph.

`GET /api/fleetview/graph` (`src/graph.py`) hands over every node and edge in the estate graph
once, unfiltered, so the board can lay the estate out spatially instead of as a table -- the walk
itself (what a click asks) still goes through `/blast-radius`, the one place that logic exists.

`POST /api/fleetview/check-receipts` (item #9, `src/evals.py`) checks real production Langfuse
traces for sessions tagged a success status but recording zero observations -- a claimed win with
no evidence behind it. Deliberately mechanical, not a model grading a session (see evals.py's own
docstring for why): a 503 means Langfuse is not configured or not reachable, never a fabricated
verdict.

`GET /api/fleetview/mutations` (`src/mutations.py`) lists every pending typed multi-domain
mutation ledger (docs/tickets/2026-09-15-typed-multidomain-mutation-ledger.md, "The door"):
ledger id, domains touched, each domain's verdict. `POST /api/fleetview/mutations/approve` and
`/mutations/reject` are the founder's own merge path for one ledger -- never an agent-executed
admit; see `mutations.py`'s own docstring for why a button press here is the founder acting, not
the pipeline auto-merging.

CONFIG (LAW 46): the catalogue path and the ledger prefix are env vars read in `src/sessions.py`;
nothing about a machine's layout is typed here.
"""

from __future__ import annotations

import json
import os
from typing import Any

# The plugin's own module. Imported by path so the portal's build does not need a workspace entry
# before the routes work; the Backstage package wiring lands with the plugin's package.json.
import importlib.util
from pathlib import Path

_SESSIONS_MODULE = Path(__file__).resolve().parent / "sessions.py"
_NOTES_MODULE = Path(__file__).resolve().parent / "notes.py"
_SIGNALS_MODULE = Path(__file__).resolve().parent / "signals.py"
# The Observer lives in platform/intent/, NOT beside this file: it is a producer of contracts that
# the backend merely reads, and the voice service is its peer, not its parent. Resolved from the
# module's own location so it does not depend on the process's working directory.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_OBSERVER_MODULE = _REPO_ROOT / "platform" / "intent" / "observer.py"
_VOICE_MEDIA_MODULE = Path(__file__).resolve().parent / "voice_media.py"
_BLAST_MODULE = Path(__file__).resolve().parent / "blast.py"
_GRAPH_MODULE = Path(__file__).resolve().parent / "graph.py"
_EVALS_MODULE = Path(__file__).resolve().parent / "evals.py"
_MUTATIONS_MODULE = Path(__file__).resolve().parent / "mutations.py"
_EXECUTOR_LINK_MODULE = Path(__file__).resolve().parent / "executor_link.py"
_TRACE_MODULE = Path(__file__).resolve().parent / "trace.py"
_LEDGER_TAIL_MODULE = Path(__file__).resolve().parent / "ledger_tail.py"
_DEVICE_ACCESS_MODULE = Path(__file__).resolve().parent / "device_access.py"
_HANDOFF_MODULE = Path(__file__).resolve().parent / "handoff.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    # Raised, not asserted: an assert is stripped under `python -O`, and this module then would
    # fail with an AttributeError on None instead of saying the module could not be loaded.
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sessions():
    return _load(_SESSIONS_MODULE, "fleetview_sessions_impl")


def _notes():
    return _load(_NOTES_MODULE, "fleetview_notes_impl")


def newest_event_seq() -> int:
    """The highest `session_events.id`, or 0.

    THE LIVE SIGNAL ON A MACHINE WITH NO BUS. `session_events` gains a row every time a session
    writes; its AUTOINCREMENT id only ever rises, so one indexed `MAX(id)` answers "has anything
    happened since I last looked". One query per second, no dependency, no cluster -- and it is
    what makes the stream live rather than a heartbeat.
    """
    import sqlite3 as _sqlite3

    path = os.environ.get("ESTATE_DB")
    if not path:
        root = Path(__file__).resolve().parents[4]
        path = str(root / "catalog" / "estate.db")
    if not Path(path).is_file():
        return 0
    try:
        con = _sqlite3.connect(path)
        try:
            row = con.execute(
                "SELECT COALESCE(MAX(id), 0) FROM session_events"
            ).fetchone()
            return int(row[0]) if row else 0
        finally:
            con.close()
    except _sqlite3.Error:
        return 0


def _history():
    return _load(
        Path(__file__).resolve().parent / "history.py", "fleetview_history_impl"
    )


def history_envelope(
    session_id: str, since: str = "", until: str = "", limit: int = 500
) -> tuple[dict, int]:
    """One session's events over time. The raw material a trail is drawn from.

    `limit` IS PLUMBED THROUGH, and was not. The board asks for `?limit=40` on a 15-second poll;
    the route did not accept the parameter, so `history()`'s default of **500** applied and each
    open page transferred roughly nine times the rows it renders. `history.py` already clamped the
    value to 1..5000; only the two call sites in between dropped it.
    """
    body = _history().history(session_id, since or None, until or None, limit=limit)
    if body.get("error") and body.get("count", 0) == 0:
        return body, 400 if "required" in str(body.get("error")) else 503
    return body, 200


def query_envelope(directive: str) -> tuple[dict, int]:
    """The fleet over time, in four speakable verbs: stuck, slow, cost, history <id>."""
    body = _history().query(directive)
    if body.get("kind") == "blind":
        return body, 503
    return body, 200


def _voice():
    return _load(Path(__file__).resolve().parent / "voice.py", "fleetview_voice_impl")


def ask_voice(body: dict, sessions: list) -> tuple[dict, int]:
    """Ask the fleet a question in words. The sessions are passed in from the SAME list /sessions
    serves, so the answer cannot describe a fleet the reader is not looking at."""
    return _voice().ask(body.get("question", ""), sessions, body.get("history"))


def stream_voice(body: dict, sessions: list):
    """Clause-by-clause server-sent events. The browser speaks each one as it lands, so the first
    words arrive while the model is still writing the rest."""
    return _voice().stream_ask(body.get("question", ""), sessions, body.get("history"))


def voice_media():
    """`voice_media.py` -- hearing, speaking, and the bus rows a voice turn puts on it.

    CACHED IN `sys.modules`, unlike its `_load`-by-path neighbours, for the same reason
    `_executor_link` is: this module holds process-wide state. It imports `sovereign.voice.engine`,
    whose loaded ASR model and currently-selected voice live in module globals -- a second copy
    would mean a 90-second model load per request and a voice chosen on one route that another
    route does not speak with.

    Returned as a module rather than wrapped in envelope functions like the routes above, because
    every entry point on it is `async` (transcription and synthesis run in a thread pool, and the
    bus publish awaits NATS). A sync wrapper here could only re-enter the event loop.
    """
    import sys

    name = "fleetview_voice_media_impl"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, _VOICE_MEDIA_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module at {_VOICE_MEDIA_MODULE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def voice_static_dir() -> Path:
    """Where the VAD and onnxruntime bundles live: one copy, in the package that owns them."""
    return _REPO_ROOT / "sovereign" / "voice" / "static"


def _signals():
    return _load(_SIGNALS_MODULE, "fleetview_signals_impl")


def _observer():
    """The Observer, loaded by path exactly as every other sibling module here is.

    WHY BY PATH. `routes.py` is executed by `serve.py` through `importlib.util.spec_from_file_location`
    (see `_load_routes`), so it is NOT a package and a relative import would fail at runtime. Every
    neighbour -- `_signals`, `_graph`, `_blast` -- is reached the same way, and the fixed
    `sys.modules` name is what makes two callers share one module instance instead of two.
    """
    return _load(_OBSERVER_MODULE, "idp_intent_observer")


def _blast():
    return _load(_BLAST_MODULE, "fleetview_blast_impl")


def _graph():
    return _load(_GRAPH_MODULE, "fleetview_graph_impl")


def _evals():
    return _load(_EVALS_MODULE, "fleetview_evals_impl")


def _mutations():
    return _load(_MUTATIONS_MODULE, "fleetview_mutations_impl")


def _trace():
    return _load(_TRACE_MODULE, "fleetview_trace_impl")


def _ledger_tail():
    return _load(_LEDGER_TAIL_MODULE, "fleetview_ledger_tail_impl")


def _device_access():
    """`device_access.py` -- what this device's read-only identity is, if anything.

    Path-loaded like every other module here rather than imported as a package, because these
    files are loaded by importlib path and a relative import is unavailable to them.
    """
    return _load(_DEVICE_ACCESS_MODULE, "fleetview_device_access_impl")


def _handoff():
    """`handoff.py` -- the challenge the portal mints and the check that it carries no secret."""
    return _load(_HANDOFF_MODULE, "fleetview_handoff_impl")


def _executor_link():
    """`executor_link.py` carries process-wide state (the one laptop connection, its pending
    replies) -- unlike every other `_load`-by-path helper above, this one MUST return the same
    module object every call, and the same object `serve.py`'s executor app holds, or the two
    halves of the relay would each keep their own, disconnected copy of "is a laptop connected".
    Cached in `sys.modules` under a fixed name so whichever of routes.py/serve.py loads it first
    wins and the other reuses it -- the same singleton-via-sys.modules idiom a normal `import`
    gives for free, without needing this plugin's path-loaded files to become a real package."""
    import sys

    name = "fleetview_executor_link_impl"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, _EXECUTOR_LINK_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module at {_EXECUTOR_LINK_MODULE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _relay_mode() -> bool:
    """FLEETVIEW_EXECUTOR_MODE=relay is set only by the cluster deployment's sidecar env
    (platform/backstage/overlays/oke/kustomization.yaml); every existing local-dev launch of
    serve.py leaves it unset, so mutations.py's direct laptop-local calls below are completely
    unchanged there. See executor_link.py's own docstring for why a relay exists at all."""
    return os.environ.get("FLEETVIEW_EXECUTOR_MODE") == "relay"


# The plugin's HTTP paths as the launcher registers them. The Backstage proxy prepends
# `/api/proxy/<key>` so the browser-facing URL is `/api/proxy/fleetview/<this>` and the
# launcher's pathRewrite strips that prefix, leaving these inner paths for FastAPI.
SESSIONS_PATH = "/sessions"
STREAM_PATH = "/stream"
NOTES_PATH = "/notes"
NUDGE_PATH = "/nudge"
STOP_PATH = "/stop"
APPROVE_PATH = "/approve"
DENY_PATH = "/deny"
SIGNALS_PATH = "/signals"
# THE CONTRACTS CHANNEL. The Reactor's `requestAnimationFrame` loop polls this to render a node per
# spoken request. Its own path rather than a filter on /signals, because a contract has a lifecycle
# (PENDING -> RUNNING -> COMPLETED) and a signal is a moment; merging them would make the board
# re-derive "is this still running" from a list of moments, which is the ticket-board shape the
# founder's spec replaces.
CONTRACTS_PATH = "/contracts"
REPLIES_PATH = "/replies"
WORK_PATH = "/work"
KILL_PATH = "/kill"

# The channel table the UI must not guess. `SIGNAL_RUNTIMES` in signals.py is the ONLY source of
# truth for which verb a runtime can actually receive; a front end that hard-codes a second copy
# will offer a button that the backend refuses, and the person pressing it learns that the board
# lies. Measured 2026-09-19: the radial menu offered Stop on a `pi` session, which has no stop
# channel, so the button was enabled for an action that could only ever 422.
CHANNELS_PATH = "/channels"
VOICE_PATH = "/voice"
VOICE_STREAM_PATH = "/voice/stream"

# THE VOICE MEDIA LEG, which used to be a WebSocket to 127.0.0.1:8899 and therefore could not
# exist in the cluster. These are plain HTTP, so the Backstage proxy carries them exactly as it
# carries /sessions, and the microphone reaches the estate's own models from a portal served
# anywhere. `voice_media.py`'s docstring has the full account of what moved and why.
VOICE_HEAR_PATH = "/voice/hear"
VOICE_SAY_PATH = "/voice/say"
VOICE_STEER_PATH = "/voice/steer"
VOICE_DONE_PATH = "/voice/done"
VOICE_VOICES_PATH = "/voice/voices"
VOICE_SELECT_PATH = "/voice/select"
VOICE_PREVIEW_PATH = "/voice/preview"
VOICE_LOG_PATH = "/voice/log"
VOICE_LOG_SUMMARY_PATH = "/voice/log/summary"
# The VAD and onnxruntime bundles the browser needs before it can hear anything. Served from this
# process as a fallback for a caller that is not the Backstage app; the app itself serves them at
# its own origin (the bytes live in backstage/packages/app/public/voice, and sovereign/voice/static
# is a symlink to them), because a `<script src>` and an AudioWorklet cannot carry the proxy's
# Authorization header.
VOICE_STATIC_PATH = "/voice/static"
HISTORY_PATH = "/history"
QUERY_PATH = "/query"
BLAST_RADIUS_PATH = "/blast-radius"
GRAPH_PATH = "/graph"
CHECK_RECEIPTS_PATH = "/check-receipts"
MUTATIONS_PATH = "/mutations"
MUTATIONS_APPROVE_PATH = "/mutations/approve"
MUTATIONS_REJECT_PATH = "/mutations/reject"
TRACE_PATH = "/trace"
LEDGER_PATH = "/ledger"
DEVICE_STATUS_PATH = "/device-status"
DEVICE_AUTHORIZE_PATH = "/device-authorize"


def sessions_envelope() -> tuple[dict[str, Any], int]:
    """The body and status for `GET /api/fleetview/sessions`.

    Returns the envelope described in this module's docstring. A catalogue that cannot be read is
    a 503 with `available: false` and the reason -- never a 200 carrying an empty list, which
    would render as "no sessions" on the page when the truth is "the catalogue is gone".
    """
    impl = _sessions()
    try:
        sessions, unreachable = impl.list_all_sessions()
    except Exception as exc:  # noqa: BLE001 - an unreadable source is reported, not disguised
        return {
            "available": False,
            "error": f"{exc.__class__.__name__}: {exc}",
            "sessions": [],
            "unreachable": [],
            "generated_at": _now(),
        }, 503
    return {
        "available": True,
        "error": None,
        "sessions": sessions,
        "unreachable": unreachable,
        "generated_at": _now(),
    }, 200


def stream_frames(records: list[dict[str, Any]]) -> list[str]:
    """The server-sent-event frames for a batch of changed records.

    Each frame is `data: <json>\\n\\n`, which is the SSE wire format. The page reads `session_id`
    and `state` out of it and updates one row without a reload; `record` carries the whole session
    so a client that has not seen it yet can insert it rather than needing a second request.
    """
    impl = _sessions()
    return [f"data: {json.dumps(impl.stream_event_for(r))}\n\n" for r in records]


def notes_envelope(session_id: str) -> tuple[dict[str, Any], int]:
    """The body and status for `GET /api/fleetview/notes?session_id=...`.

    Read-only; always 200 with a (possibly empty) list. A session with no notes is not an error,
    same rule as an empty board.
    """
    impl = _notes()
    return {"notes": impl.notes_for(session_id)}, 200


def add_note(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """The body and status for `POST /api/fleetview/notes`.

    `body` carries session_id, runtime, note, author. A malformed request is a 400 naming what is
    missing, not a 500 -- this is a person typing into a form, not a machine that already validated.
    """
    impl = _notes()
    try:
        record = impl.add_note(
            session_id=body.get("session_id", ""),
            runtime=body.get("runtime", ""),
            note=body.get("note", ""),
            author=body.get("author", ""),
        )
    except impl.InvalidNote as exc:
        return {"error": str(exc)}, 400
    return record, 201


def add_nudge(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """The body and status for `POST /api/fleetview/nudge`.

    `body` carries session_id, runtime, by, and an optional text. A request that never reaches a
    real session (missing field) is a 400; a runtime with no live signal path is a 422 -- distinct
    from a 502, which means the signal was actually attempted against a real session and failed.
    """
    impl = _signals()
    try:
        record = impl.nudge(
            session_id=body.get("session_id", ""),
            runtime=body.get("runtime", ""),
            by=body.get("by", ""),
            text=body.get("text", ""),
        )
    except impl.InvalidSignal as exc:
        return {"error": str(exc)}, 400
    except impl.UnsupportedRuntime as exc:
        return {"error": str(exc)}, 422
    if not record["ok"]:
        return record, 502
    return record, 200


def add_stop(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    impl = _signals()
    try:
        record = impl.stop(
            session_id=body.get("session_id", ""),
            runtime=body.get("runtime", ""),
            by=body.get("by", ""),
        )
    except impl.InvalidSignal as exc:
        return {"error": str(exc)}, 400
    except impl.UnsupportedRuntime as exc:
        return {"error": str(exc)}, 422
    return record, 502 if not record["ok"] else 200


def add_approve(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    impl = _signals()
    try:
        record = impl.approve(
            session_id=body.get("session_id", ""),
            runtime=body.get("runtime", ""),
            by=body.get("by", ""),
            text=body.get("text", ""),
        )
    except impl.InvalidSignal as exc:
        return {"error": str(exc)}, 400
    except impl.UnsupportedRuntime as exc:
        return {"error": str(exc)}, 422
    return record, 502 if not record["ok"] else 200


def add_deny(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    impl = _signals()
    try:
        record = impl.deny(
            session_id=body.get("session_id", ""),
            runtime=body.get("runtime", ""),
            by=body.get("by", ""),
            text=body.get("text", ""),
        )
    except impl.InvalidSignal as exc:
        return {"error": str(exc)}, 400
    except impl.UnsupportedRuntime as exc:
        return {"error": str(exc)}, 422
    return record, 502 if not record["ok"] else 200


def device_status_envelope() -> tuple[dict[str, Any], int]:
    """The body and status for `GET /api/fleetview/device-status`.

    A thin passthrough to `device_access.py` so every route in this file has the same shape:
    the route function owns the HTTP contract, the impl module owns the logic and holds no
    response codes of its own. `device_access.py` already answers with a `state` field in both
    the 200 and the 503 case, which is why this does not need to synthesise one.
    """
    impl = _device_access()
    return impl.device_status_envelope()


def device_authorize_envelope() -> tuple[dict[str, Any], int]:
    """The body and status for `POST /api/fleetview/device-authorize`.

    Mints a single-use challenge and returns the LOCAL handoff URL. It deliberately does not
    deliver anything: per the founder's ruling (2026-09-18), key delivery stays out of the
    portal, which holds no vault credentials and must never see a key or a token. The browser
    opens `idp-device://`, the device's own helper performs the delivery, and the only thing
    that crossed between them is the nonce.

    The payload is built by `handoff.handoff_payload`, which runs `assert_no_secret` before
    returning it -- so this route cannot emit a credential even if a future edit tries to.
    """
    handoff = _handoff()
    challenge = handoff.new_challenge()
    try:
        body = handoff.handoff_payload(challenge, state="awaiting_helper")
        body["url"] = handoff.handoff_url(challenge)
        body["scheme"] = "idp-device"
        # Re-check with the two fields added, so the URL itself is proven clean rather than
        # assumed to be because its inputs were.
        handoff.assert_no_secret(body, where="device-authorize")
    except handoff.SecretLeak as exc:
        # A leak here is a programming error, and it must fail loudly rather than return a
        # redacted payload nobody notices is redacted.
        return {"state": "error", "error": f"refusing to emit: {exc}"}, 500
    return body, 200


def channels_envelope() -> tuple[dict[str, Any], int]:
    """Which signal each runtime has a live path for, read from signals.py itself.

    Served rather than duplicated so the front end cannot drift from the gate. A runtime absent
    from a verb's list means the backend will refuse that verb for it -- and the UI should say so
    before the press, not after.
    """
    mod = _signals()
    table = getattr(mod, "SIGNAL_RUNTIMES", {})
    return (
        {
            "signals": {verb: sorted(runtimes) for verb, runtimes in table.items()},
            "note": (
                "A runtime missing from a verb's list has no channel for it; the backend refuses "
                "that verb for that runtime with 422 and the reason."
            ),
        },
        200,
    )


def signals_envelope(session_id: str) -> tuple[dict[str, Any], int]:
    """The body and status for `GET /api/fleetview/signals?session_id=...`.

    Read-only audit trail of every nudge attempt for a session (`src/signals.py`'s
    `signals_for`), newest first. Always 200 with a (possibly empty) list -- same rule
    `notes_envelope` follows: a session with no signals yet is not an error.
    """
    impl = _signals()
    return {"signals": impl.signals_for(session_id)}, 200


def reply_envelope(session_id: str, limit: int = 20) -> tuple[dict[str, Any], int]:
    """`GET /api/fleetview/replies?session_id=...` -- what the sessions said back.

    THE READ HALF OF THE REPLY CHANNEL. Empty `session_id` returns the fleet-wide feed, which is
    what a board shows when the reader is not looking at any one agent; a session id narrows it to
    that conversation. Always 200 with a possibly-empty list, like `signals_envelope`: an agent
    that has not spoken yet is not an error.
    """
    impl = _signals()
    return {"replies": impl.replies_for(session_id, limit=limit)}, 200


def post_reply(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """`POST /api/fleetview/replies` -- a session (or a person) records what was said.

    A blank session_id or text is 400 (`InvalidSignal`, the same distinction signals draw between
    'never reached a session' and 'reached it and failed'). Anything else is recorded.
    """
    impl = _signals()
    try:
        row = impl.reply(
            session_id=str(body.get("session_id") or ""),
            runtime=str(body.get("runtime") or "unknown"),
            text=str(body.get("text") or ""),
            author=str(body.get("author") or "agent"),
            in_reply_to=body.get("in_reply_to"),
        )
    except impl.InvalidSignal as exc:
        return {"error": str(exc)}, 400
    return {"reply": row}, 201


def blast_radius_envelope(node_id: str) -> tuple[dict[str, Any], int]:
    """The body and status for `GET /api/fleetview/blast-radius?node_id=...`.

    A blank node_id is a 400 (a form filled in wrong); a graph that has never been swept is a
    503 with the reason, matching `sessions_envelope`'s own rule that "could not be read" is
    never disguised as an empty answer.
    """
    impl = _blast()
    try:
        result = impl.blast_radius_for(node_id)
    except impl.InvalidQuery as exc:
        return {"error": str(exc)}, 400
    except impl.GraphUnavailable as exc:
        return {"error": str(exc)}, 503
    return result, 200


def graph_envelope() -> tuple[dict[str, Any], int]:
    """The body and status for `GET /api/fleetview/graph`.

    Whole-graph read, no query params. A graph that has never been swept is 503 with the reason,
    matching `blast_radius_envelope`'s own rule that a real gap is never disguised as an empty
    graph -- an empty estate and an unswept one must never look the same on the board.
    """
    impl = _graph()
    try:
        result = impl.graph_snapshot()
    except impl.GraphUnavailable as exc:
        return {"error": str(exc)}, 503
    return result, 200


def check_receipts_envelope(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """The body and status for `POST /api/fleetview/check-receipts`.

    `body` carries `session_ids`, a list. An empty list is a 400 (nothing named to check); no
    Langfuse configured or reachable is a 503 with the reason -- matching `blast_radius_envelope`'s
    own rule that a real gap is never disguised as a result.
    """
    impl = _evals()
    try:
        results = impl.check_receipts_batch(body.get("session_ids", []))
    except impl.InvalidQuery as exc:
        return {"error": str(exc)}, 400
    except impl.EvalsUnavailable as exc:
        return {"error": str(exc)}, 503
    return {"results": results}, 200


async def mutations_envelope() -> tuple[dict[str, Any], int]:
    """The body and status for `GET /api/fleetview/mutations`.

    A daemon that has never proposed a ledger is not an error -- an empty list, 200, same rule
    `sessions_envelope` and `notes_envelope` already follow: "nothing pending" and "could not be
    read" must never look the same, so a read failure (a proposal file this plugin cannot parse,
    a `ledger_root()` it cannot reach) still only drops that one row rather than the whole board.

    In the cluster (FLEETVIEW_EXECUTOR_MODE=relay), the ledger this plugin's own process can see
    on disk is empty by construction -- it lives on the laptop, not in this Pod (executor_link.py's
    docstring). "Nothing pending" and "no laptop connected" must not look the same either: an
    unconnected laptop is reported as such, `connected: false`, never as a quiet, wrong "0 pending".
    """
    if _relay_mode():
        link = _executor_link()
        if not link.is_connected():
            return {
                "mutations": [],
                "connected": False,
                "error": "the laptop executor is not connected",
            }, 200
        try:
            result = await link.relay("list_pending", {})
        except link.RelayTimeout as exc:
            return {"mutations": [], "connected": True, "error": str(exc)}, 503
        return {"mutations": result.get("mutations", []), "connected": True}, 200
    impl = _mutations()
    return {"mutations": impl.list_pending(), "connected": True}, 200


async def approve_mutation(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """The body and status for `POST /api/fleetview/mutations/approve`.

    `body` carries `ledger_id`. A blank id is 400; the executor daemon not answering is 503,
    matching `blast_radius_envelope`'s rule that a real gap is never disguised as a result.
    """
    ledger_id = body.get("ledger_id", "")
    if not ledger_id:
        return {"error": "approve needs a ledger_id"}, 400
    if _relay_mode():
        link = _executor_link()
        if not link.is_connected():
            return {"error": "the laptop executor is not connected"}, 503
        try:
            result = await link.relay("approve", {"ledger_id": ledger_id})
        except link.RelayTimeout as exc:
            return {"error": str(exc)}, 503
        return result, (200 if result.get("ok") else 409)
    impl = _mutations()
    try:
        result = impl.approve(ledger_id)
    except impl.InvalidQuery as exc:
        return {"error": str(exc)}, 400
    except impl.LedgerUnavailable as exc:
        return {"error": str(exc)}, 503
    return result, (200 if result.get("ok") else 409)


async def reject_mutation(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """The body and status for `POST /api/fleetview/mutations/reject`. Same shape as
    `approve_mutation`; rejecting never touches the executor socket (see `mutations.py`), so
    there is no `LedgerUnavailable` case here in local mode -- relay mode can still time out
    waiting on the laptop, which is a 503 the same way approve's can."""
    ledger_id = body.get("ledger_id", "")
    if not ledger_id:
        return {"error": "reject needs a ledger_id"}, 400
    if _relay_mode():
        link = _executor_link()
        if not link.is_connected():
            return {"error": "the laptop executor is not connected"}, 503
        try:
            result = await link.relay("reject", {"ledger_id": ledger_id})
        except link.RelayTimeout as exc:
            return {"error": str(exc)}, 503
        return result, (200 if result.get("ok") else 409)
    impl = _mutations()
    try:
        result = impl.reject(ledger_id)
    except impl.InvalidQuery as exc:
        return {"error": str(exc)}, 400
    return result, (200 if result.get("ok") else 409)


def trace_envelope(session_id: str) -> tuple[dict[str, Any], int]:
    """The body and status for `GET /api/fleetview/trace?session_id=...`.

    On success: {"available": True, "error": None, "nodes": [...], "edges": [...]}, 200.
    On TraceUnavailable (Langfuse not configured, trace missing, or unreachable):
        {"available": False, "error": str(e), "nodes": [], "edges": []}, 503 —
    the same rule blast_radius_envelope follows: a real gap is never disguised as empty data.
    """
    impl = _trace()
    try:
        result = impl.trace_graph(session_id)
    except impl.TraceUnavailable as exc:
        return {
            "available": False,
            "error": str(exc),
            "nodes": [],
            "edges": [],
        }, 503
    return {"available": True, "error": None, **result}, 200


def ledger_tail_envelope(session_id: str) -> tuple[dict[str, Any], int]:
    """The body and status for `GET /api/fleetview/ledger?session_id=...`.

    Always 200 — log-pane errors are soft: an empty list and an unreadable ledger look the same
    to the page (no rows to show), and a broken log pane must not take down the session card.
    On any error the error is included so a developer can diagnose it from the response.
    """
    impl = _ledger_tail()
    try:
        rows = impl.ledger_tail(session_id)
        return {"rows": rows}, 200
    except Exception as exc:  # noqa: BLE001 — soft failure for the log pane
        return {"rows": [], "error": str(exc)}, 200


def contracts_envelope(limit: int = 10) -> tuple[dict[str, Any], int]:
    """`GET /api/fleetview/contracts` -- the action contracts a person is currently watching.

    ALWAYS 200 WITH A POSSIBLY-EMPTY LIST, the rule `signals_envelope` and `notes_envelope` follow:
    nobody having asked for anything yet is not an error, and a board that showed an error there
    would train its reader to ignore the error.

    THE READ IS SOFT. The Observer commits contracts from its own process, so a database that is
    mid-migration, or absent because nothing has ever been asked, must not take down the HUD. On
    any failure the rows are empty AND the reason is carried in the body -- an empty list and an
    unreadable database look identical to a page, so the reason is the difference between a quiet
    fleet and a broken one. That distinction is not optional (AGENTS.md section 8).
    """
    impl = _observer()
    try:
        rows = impl.contracts_for(limit)
        return {"contracts": rows}, 200
    except Exception as exc:  # noqa: BLE001 -- soft read; see the docstring
        return {"contracts": [], "error": str(exc)}, 200


def _now() -> str:
    import datetime as dt

    return dt.datetime.now(dt.timezone.utc).isoformat()


def work_envelope() -> tuple[dict[str, Any], int]:
    """`GET /api/fleetview/work` -- what each session is working on: branch and current step.

    Keyed by session id so the board can merge it into rows it already has, rather than a list the
    reader has to join by hand. Always 200 with a possibly-empty map.
    """
    impl = _signals()
    return {"work": impl.work_for()}, 200


def post_work(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """`POST /api/fleetview/work` -- a session reports its branch and step.

    One row per session, upserted: "what is it working on" has one answer at a time, and a log of
    forty steps would make the reader choose between them.
    """
    impl = _signals()
    try:
        row = impl.record_work(
            session_id=str(body.get("session_id") or ""),
            runtime=str(body.get("runtime") or "unknown"),
            branch=str(body.get("branch") or ""),
            step=str(body.get("step") or ""),
            # The pid is its own field. Encoded as `step = "pid 1234"` it survived exactly until
            # the agent ran its first tool, which overwrote the step -- a kill that stops working
            # the moment the agent starts working.
            pid=body.get("pid") if isinstance(body.get("pid"), int) else None,
        )
    except impl.InvalidSignal as exc:
        return {"error": str(exc)}, 400
    return {"work": row}, 201


def kill_envelope(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """`POST /api/fleetview/kill` -- SIGTERM a session's process.

    Separate from `/stop`, which is a cooperative marker. This is the rogue-agent path: the process
    itself, addressed by the PID the session volunteered. A session with no reported PID is a 502
    with that reason, not a silent success -- there was nothing to signal.
    """
    impl = _signals()
    try:
        row = impl.kill(
            session_id=str(body.get("session_id") or ""),
            runtime=str(body.get("runtime") or ""),
            by=str(body.get("by") or "reactor"),
            force=bool(body.get("force")),
        )
    except impl.InvalidSignal as exc:
        return {"error": str(exc)}, 400
    return row, (200 if row.get("ok") else 502)
