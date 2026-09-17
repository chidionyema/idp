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
_BLAST_MODULE = Path(__file__).resolve().parent / "blast.py"
_GRAPH_MODULE = Path(__file__).resolve().parent / "graph.py"
_EVALS_MODULE = Path(__file__).resolve().parent / "evals.py"
_MUTATIONS_MODULE = Path(__file__).resolve().parent / "mutations.py"
_EXECUTOR_LINK_MODULE = Path(__file__).resolve().parent / "executor_link.py"
_TRACE_MODULE = Path(__file__).resolve().parent / "trace.py"
_LEDGER_TAIL_MODULE = Path(__file__).resolve().parent / "ledger_tail.py"


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


def _signals():
    return _load(_SIGNALS_MODULE, "fleetview_signals_impl")


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
BLAST_RADIUS_PATH = "/blast-radius"
GRAPH_PATH = "/graph"
CHECK_RECEIPTS_PATH = "/check-receipts"
MUTATIONS_PATH = "/mutations"
MUTATIONS_APPROVE_PATH = "/mutations/approve"
MUTATIONS_REJECT_PATH = "/mutations/reject"
TRACE_PATH = "/trace"
LEDGER_PATH = "/ledger"


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


def signals_envelope(session_id: str) -> tuple[dict[str, Any], int]:
    """The body and status for `GET /api/fleetview/signals?session_id=...`.

    Read-only audit trail of every nudge attempt for a session (`src/signals.py`'s
    `signals_for`), newest first. Always 200 with a (possibly empty) list -- same rule
    `notes_envelope` follows: a session with no signals yet is not an error.
    """
    impl = _signals()
    return {"signals": impl.signals_for(session_id)}, 200


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


def _now() -> str:
    import datetime as dt

    return dt.datetime.now(dt.timezone.utc).isoformat()
