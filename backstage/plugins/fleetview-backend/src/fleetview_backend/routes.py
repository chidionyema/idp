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
import sqlite3
from datetime import datetime, timezone
from typing import Any

# Sibling modules in the same package. Direct imports replace the old importlib.util _load() hacks.
from fleetview_backend import (
    blast,
    claims,
    device_access,
    handoff,
    evals,
    graph,
    greenlane,
    harness,
    harv,
    ledger_tail,
    memory,
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
    "MEMORY_PATH",
    "CHECK_RECEIPTS_PATH",
    "MUTATIONS_PATH",
    "MUTATIONS_APPROVE_PATH",
    "MUTATIONS_REJECT_PATH",
    "TRACE_PATH",
    "LEDGER_PATH",
    "DEVICE_STATUS_PATH",
    "RESEARCH_PATH",
    "ESTATE_PATH",
    "device_status_envelope",
    "DEVICE_AUTHORIZE_PATH",
    "device_authorize_envelope",
    "sessions_envelope",
    "stream_frames",
    "notes_envelope",
    "add_note",
    "add_nudge",
    "signals_envelope",
    "blast_radius_envelope",
    "graph_envelope",
    "memory_envelope",
    "greenlane_envelope",
    "claims_envelope",
    "research_envelope",
    "estate_envelope",
    "harv_envelope",
    "HARNESS_PATH",
    "harness_envelope",
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
REPLIES_PATH = "/replies"
WORK_PATH = "/work"
BLAST_RADIUS_PATH = "/blast-radius"
GRAPH_PATH = "/graph"
MEMORY_PATH = "/memory"
GREENLANE_PATH = "/greenlane"
CLAIMS_PATH = "/claims"
RESEARCH_PATH = "/research"
ESTATE_PATH = "/estate"
HARV_PATH = "/harv"
HARNESS_PATH = "/harness"
CHECK_RECEIPTS_PATH = "/check-receipts"
MUTATIONS_PATH = "/mutations"
MUTATIONS_APPROVE_PATH = "/mutations/approve"
MUTATIONS_REJECT_PATH = "/mutations/reject"
TRACE_PATH = "/trace"
LEDGER_PATH = "/ledger"
DEVICE_STATUS_PATH = "/device-status"
DEVICE_AUTHORIZE_PATH = "/device-authorize"
DELIVERY_PATH = "/delivery"


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
            # The window is configuration, not a reading, so it is known even when the fleet is
            # not: the page can say what it will count over once the source answers.
            "fresh_window_minutes": sessions.fresh_running_minutes(),
            "generated_at": _now(),
        }, 503
    return {
        "available": True,
        "error": None,
        "sessions": sessions_list,
        "unreachable": unreachable,
        # The window `state` calls "running" travels with the rows, so the interface can print
        # "3 wrote in the last 40m" instead of "3 running". A caller that receives rows has
        # received the definition too, and a caller that ignores it is at least not lied to.
        "fresh_window_minutes": sessions.fresh_running_minutes(),
        "generated_at": _now(),
    }, 200


def stream_frames(records: list[dict[str, Any]]) -> list[str]:
    return [f"data: {json.dumps(sessions.stream_event_for(r))}\n\n" for r in records]


def cue_frame(cue: dict[str, Any]) -> str:
    """One SSE frame for a cinema cue; the page routes type == 'cue' to its CineCam."""
    return f"data: {json.dumps({**cue, 'type': 'cue'})}\n\n"


def story_frame(on: str, story: dict[str, Any]) -> str:
    """One SSE frame for a news story; `on` is the channel the story was published on."""
    return f"data: {json.dumps({'type': 'story', 'on': on, 'story': story})}\n\n"


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


def reply_envelope(session_id: str, limit: int = 20) -> tuple[dict[str, Any], int]:
    """`GET /replies?session_id=...` -- what the sessions said back.

    THE READ HALF OF THE REPLY CHANNEL. Empty `session_id` returns the fleet-wide feed, which is
    what a board shows when the reader is not looking at any one agent; a session id narrows it to
    that conversation. Always 200 with a possibly-empty list, like `signals_envelope`: an agent
    that has not spoken yet is not an error.

    THE READ IS SOFT. The board polls this every two seconds; a database that cannot answer (a
    volume gone read-only -- which is exactly how the first deployment of this route failed) must
    not turn the HUD into a 500. Empty rows AND the reason in the body: a quiet fleet and a
    broken one look the same to a status code, so the reason is what tells them apart.
    """
    try:
        return {"replies": signals.replies_for(session_id, limit=limit)}, 200
    except sqlite3.Error as exc:
        return {"replies": [], "error": str(exc)}, 200


def post_reply(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """`POST /replies` -- a session (or a person) records what was said.

    A blank session_id or text is 400 (`InvalidSignal`, the same distinction signals draw between
    'never reached a session' and 'reached it and failed'). Anything else is recorded.
    """
    try:
        row = signals.reply(
            session_id=str(body.get("session_id") or ""),
            runtime=str(body.get("runtime") or "unknown"),
            text=str(body.get("text") or ""),
            author=str(body.get("author") or "agent"),
            in_reply_to=body.get("in_reply_to"),
        )
    except signals.InvalidSignal as exc:
        return {"error": str(exc)}, 400
    return {"reply": row}, 201


def work_envelope() -> tuple[dict[str, Any], int]:
    """`GET /work` -- what each session is working on: branch and current step.

    Keyed by session id so the board can merge it into rows it already has, rather than a list the
    reader has to join by hand. Always 200 with a possibly-empty map; SOFT for the same reason
    `reply_envelope` is -- a read that cannot be served is a reason, not a 500.
    """
    try:
        return {"work": signals.work_for()}, 200
    except sqlite3.Error as exc:
        return {"work": {}, "error": str(exc)}, 200


def post_work(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """`POST /work` -- a session reports its branch and step.

    One row per session, upserted: "what is it working on" has one answer at a time, and a log of
    forty steps would make the reader choose between them.
    """
    try:
        row = signals.record_work(
            session_id=str(body.get("session_id") or ""),
            runtime=str(body.get("runtime") or "unknown"),
            branch=str(body.get("branch") or ""),
            step=str(body.get("step") or ""),
            # The pid is its own field. Encoded as `step = "pid 1234"` it survived exactly until
            # the agent ran its first tool, which overwrote the step.
            pid=body.get("pid") if isinstance(body.get("pid"), int) else None,
        )
    except signals.InvalidSignal as exc:
        return {"error": str(exc)}, 400
    return {"work": row}, 201


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


def memory_envelope() -> tuple[dict[str, Any], int]:
    # Each part carries its own available/error; one unreadable part never hides the others.
    return memory.memory_status(), 200


def greenlane_envelope() -> tuple[dict[str, Any], int]:
    # The lane's invariants as measured now; unreadable is unavailable with a reason, never green.
    return greenlane.greenlane_status(), 200


def claims_envelope() -> tuple[dict[str, Any], int]:
    # The live agent claims as measured now -- who, what, which paths, and heartbeat age
    # (AGENTS.md section 5). Unreadable is `available: false` with its reason; an empty list
    # would say "nobody holds anything" at the moment the estate cannot tell.
    return claims.claims_snapshot(), 200


def research_envelope() -> tuple[dict[str, Any], int]:
    # The research department's claims through the portal's ONE reader (research_feed):
    # a loopback GET to the research-output plugin, never a second Postgres client here.
    from fleetview_backend import research_feed

    return research_feed.research_claims(), 200


def estate_envelope() -> tuple[dict[str, Any], int]:
    # The estate in one glance: green lane, router burn, newest verified research. Three
    # readers already proven on their own, joined per-part so one dead part reads
    # available: False with its reason while the others still answer. The /estate strip and
    # the voice's brief both draw from this -- one source, so the founder and the voice
    # cannot describe two different estates. Each part is wrapped: the readers are
    # contractually soft, but a raise from any of them must degrade ITS segment only,
    # never 500 the whole envelope.
    def _soft(fn):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 -- a dead segment says so; the envelope lives
            return {"available": False, "error": f"{type(exc).__name__}: {exc}"[:300]}

    from fleetview_backend import research_feed
    from fleetview_backend import spend

    body: dict[str, Any] = {
        "generated_at": _now(),
        "green": _soft(greenlane.greenlane_status_nowait),
        "burn": _soft(spend.spend_total),
        "research": _soft(research_feed.research_claims),
        # Who holds what, and how much is left -- the founder's question of 2026-10-23 answered
        # on the strip rather than by asking an agent. One reader (claims.claims_snapshot), the
        # same one /claims serves, so the strip and the claims panel cannot disagree.
        "claims": _soft(lambda: claims.claims_glance(claims.claims_snapshot())),
    }
    return body, 200


def harv_envelope() -> tuple[dict[str, Any], int]:
    # The harvester's funnel as measured now; unreadable is unavailable with a reason, never empty.
    return harv.harv_status(), 200


def harness_envelope() -> tuple[dict[str, Any], int]:
    # The Active Runtime Harness telemetry snapshot and harness table row counts.
    # An unreachable memory server is available: false with its reason, never a silent empty board.
    return harness.harness_stats(), 200


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
    # ledger_tail is contractually soft: it returns [] on any error and never raises, so the
    # envelope is always 200 — the log pane renders an empty fold, not an error, for a session
    # with no ledger. Rows under "rows", the key the Fleet Log fold reads.
    return {
        "available": True,
        "error": None,
        "rows": ledger_tail.ledger_tail(session_id),
    }, 200


# ── agent jobs (agent_jobs.py): give an agent a task from Fleet, watch it become a merged PR ──
AGENT_JOBS_PATH = "/agent-jobs"


def agent_jobs_envelope() -> tuple[dict[str, Any], int]:
    from fleetview_backend import agent_jobs

    return agent_jobs.list_jobs()


def submit_agent_job(body: Any) -> tuple[dict[str, Any], int]:
    from fleetview_backend import agent_jobs

    return agent_jobs.handle_post(body)


# ── concierge tasks (concierge_tasks.py): a browser task for the founder, watched as it happens ──
CONCIERGE_TASKS_PATH = "/concierge-tasks"


def concierge_tasks_envelope() -> tuple[dict[str, Any], int]:
    from fleetview_backend import concierge_tasks

    return concierge_tasks.list_tasks()


def submit_concierge_task(body: Any) -> tuple[dict[str, Any], int]:
    from fleetview_backend import concierge_tasks

    return concierge_tasks.handle_post(body)


# ── key sync (key_sync.py): is every key the estate expects arriving from Bitwarden ──
KEY_SYNC_PATH = "/key-sync"


def key_sync_envelope() -> tuple[dict[str, Any], int]:
    # Names and states only, never a value; unreadable is unavailable with a reason, never empty.
    from fleetview_backend import key_sync

    return key_sync.key_sync_status(), 200


def device_status_envelope() -> tuple[dict[str, Any], int]:
    """`GET /device-status`: this device's read-only identity, for the Fleet device tile."""
    return device_access.device_status_envelope()


def device_authorize_envelope() -> tuple[dict[str, Any], int]:
    """`POST /device-authorize`: mint a single-use challenge and return the LOCAL handoff URL.

    Key delivery stays out of the portal (founder, 2026-09-18): the browser opens
    `idp-device://`, the device's own helper delivers, and only the nonce crosses between them.
    """
    challenge = handoff.new_challenge()
    try:
        body = handoff.handoff_payload(challenge, state="awaiting_helper")
        body["url"] = handoff.handoff_url(challenge)
        body["scheme"] = "idp-device"
        # Re-checked with the two fields added, so the URL itself is proven clean.
        handoff.assert_no_secret(body, where="device-authorize")
    except handoff.SecretLeak as exc:
        return {"state": "error", "error": f"refusing to emit: {exc}"}, 500
    return body, 200
