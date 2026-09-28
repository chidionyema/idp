"""FleetView backend plugin: the HTTP routes CP1's done-command names.

`GET /api/fleetview/sessions` and `GET /api/fleetview/stream` are served from the portal backend at
`backstage/packages/backend/src/`. This module is the plugin's router: it owns the paths, the
envelope and the status codes, and it delegates every decision about what a session IS to
`sessions.py`, so the translation lives in exactly one file.

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

`GET /api/fleetview/notes?session_id=...` and `POST /api/fleetview/notes` are the notes mailbox.

`POST /api/fleetview/nudge` calls the runtime signal path for the named session; the runtime
signals back through its own SSE, which the page already subscribes to, so a nudge shows up as
a session change without any additional polling.

`GET /api/fleetview/signals?session_id=...` is an audit trail of every nudge attempt for a session.

`GET /api/fleetview/trace?session_id=...` and `GET /api/fleetview/ledger?session_id=...` read Langfuse
traces and the ledger tail respectively -- neither poll is wired into the board yet (item #6).

`GET /api/fleetview/blast-radius?node_id=...` and `GET /api/fleetview/graph` read the estate graph.
`POST /api/fleetview/check-receipts` checks whether Langfuse has a trace for each named session.

`GET /api/fleetview/mutations`, `POST .../approve`, `POST .../reject` are the mutation board:
get pending proposals, approve one, or reject one. In cluster mode (FLEETVIEW_EXECUTOR_MODE=relay)
the daemon on the laptop is the one with the proposal ledger, so this plugin relays the three
verbs to it and the daemon does the actual apply/reject. See executor_link.py's own docstring.

Build: `backstage/plugins/fleetview-backend/`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

# Sibling modules in the same package. Direct imports replace the old importlib.util _load() hacks.
from fleetview_backend import (
    blast,
    evals,
    graph,
    ledger_tail,
    notes,
    sessions,
    signals,
    trace,
)

__all__ = [
    "SESSIONS_PATH",
    "STREAM_PATH",
    "NOTES_PATH",
    "NUDGE_PATH",
    "SIGNALS_PATH",
    "BLAST_RADIUS_PATH",
    "GRAPH_PATH",
    "CHECK_RECEIPTS_PATH",
    "MUTATIONS_PATH",
    "MUTATIONS_APPROVE_PATH",
    "MUTATIONS_REJECT_PATH",
    "TRACE_PATH",
    "LEDGER_PATH",
    "sessions_envelope",
    "stream_frames",
    "notes_envelope",
    "add_note",
    "add_nudge",
    "signals_envelope",
    "blast_radius_envelope",
    "graph_envelope",
    "check_receipts_envelope",
    "mutations_envelope",
    "approve_mutation",
    "reject_mutation",
    "trace_envelope",
    "ledger_tail_envelope",
]


# The plugin's HTTP paths as the launcher registers them. The Backstage proxy prepends
# `/api/proxy/<key>` so the browser-facing URL is `/api/proxy/fleetview/<this>` and the
# launcher's pathRewrite strips that prefix, leaving these inner paths for FastAPI.
SESSIONS_PATH = "/sessions"
STREAM_PATH = "/stream"
NOTES_PATH = "/notes"
NUDGE_PATH = "/nudge"
SIGNALS_PATH = "/signals"
BLAST_RADIUS_PATH = "/blast-radius"
GRAPH_PATH = "/graph"
CHECK_RECEIPTS_PATH = "/check-receipts"
MUTATIONS_PATH = "/mutations"
MUTATIONS_APPROVE_PATH = "/mutations/approve"
MUTATIONS_REJECT_PATH = "/mutations/reject"
TRACE_PATH = "/trace"
LEDGER_PATH = "/ledger"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _relay_mode() -> bool:
    """FLEETVIEW_EXECUTOR_MODE=relay is set only by the cluster deployment's sidecar env
    (platform/backstage/overlays/oke/kustomization.yaml); every existing local-dev launch of
    serve.py leaves it unset, so mutations.py's direct laptop-local calls below are completely
    unchanged there. See executor_link.py's own docstring for why a relay exists at all."""
    return os.environ.get("FLEETVIEW_EXECUTOR_MODE") == "relay"


def _executor_link():
    """Lazy import of executor_link (process-wide state, cached in sys.modules)."""
    import sys

    name = "fleetview_executor_link_impl"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    from fleetview_backend import executor_link

    sys.modules[name] = executor_link
    return executor_link


def _mutations():
    """Lazy import of mutations (may trigger model loading on first use)."""
    from fleetview_backend import mutations

    return mutations


def sessions_envelope() -> tuple[dict[str, Any], int]:
    try:
        sessions_list, unreachable = sessions.list_all_sessions()
    except Exception as exc:
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
        "sessions": sessions_list,
        "unreachable": unreachable,
        "generated_at": _now(),
    }, 200


def stream_frames(records: list[dict[str, Any]]) -> list[str]:
    return [f"data: {json.dumps(sessions.stream_event_for(r))}\n\n" for r in records]


def notes_envelope(session_id: str) -> tuple[dict[str, Any], int]:
    return {"notes": notes.notes_for(session_id)}, 200


def add_note(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        record = notes.add_note(
            session_id=body.get("session_id", ""),
            runtime=body.get("runtime", ""),
            note=body.get("note", ""),
            author=body.get("author", ""),
        )
    except notes.InvalidNote as exc:
        return {"error": str(exc)}, 400
    return record, 201


def add_nudge(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        record = signals.nudge(
            session_id=body.get("session_id", ""),
            runtime=body.get("runtime", ""),
            by=body.get("by", ""),
            text=body.get("text", ""),
        )
    except signals.InvalidSignal as exc:
        return {"error": str(exc)}, 400
    except signals.UnsupportedRuntime as exc:
        return {"error": str(exc)}, 422
    if not record["ok"]:
        return record, 502
    return record, 200


def signals_envelope(session_id: str) -> tuple[dict[str, Any], int]:
    return {"signals": signals.signals_for(session_id)}, 200


def blast_radius_envelope(node_id: str) -> tuple[dict[str, Any], int]:
    try:
        result = blast.blast_radius_for(node_id)
    except blast.InvalidQuery as exc:
        return {"error": str(exc)}, 400
    except blast.GraphUnavailable as exc:
        return {"error": str(exc)}, 503
    return result, 200


def graph_envelope() -> tuple[dict[str, Any], int]:
    try:
        result = graph.graph_snapshot()
    except graph.GraphUnavailable as exc:
        return {"error": str(exc)}, 503
    return result, 200


def check_receipts_envelope(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        results = evals.check_receipts_batch(body.get("session_ids", []))
    except evals.InvalidQuery as exc:
        return {"error": str(exc)}, 400
    except evals.EvalsUnavailable as exc:
        return {"error": str(exc)}, 503
    return {"results": results}, 200


async def mutations_envelope() -> tuple[dict[str, Any], int]:
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
    try:
        result = trace.trace_graph(session_id)
    except trace.TraceUnavailable as exc:
        return {
            "available": False,
            "error": str(exc),
            "nodes": [],
            "edges": [],
        }, 503
    return {"available": True, "error": None, **result}, 200


def ledger_tail_envelope(session_id: str) -> tuple[dict[str, Any], int]:
    try:
        result = ledger_tail.ledger_tail(session_id)
    except ledger_tail.LedgerUnavailable as exc:
        return {
            "available": False,
            "error": str(exc),
            "records": [],
        }, 503
    return {"available": True, "error": None, **result}, 200
