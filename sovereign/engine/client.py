"""The only module B (otto) and C (cockpit) import from the engine. Async,
plain dicts in and out -- no Temporal types cross this boundary (contract
sovereign/CONTRACT.md, "Engine API").
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Literal

from temporalio.client import Client, WorkflowFailureError, WorkflowHandle
from temporalio.service import RPCError

from sovereign import config
from sovereign.engine import receipts as receipts_mod

_client: Client | None = None

WORKFLOW = "SessionWorkflow"


async def get_client() -> Client:
    global _client
    if _client is None:
        _client = await Client.connect(config.TEMPORAL_ADDRESS, namespace=config.TEMPORAL_NAMESPACE)
    return _client


def _new_session_id() -> str:
    return f"sb-{uuid.uuid4().hex[:config.SESSION_ID_HEX_LEN]}"


async def start(
    task: str, runner: str = "echo", repo: str | None = None, by: str = "cli", budget: int = 0
) -> dict[str, Any]:
    client = await get_client()
    session_id = _new_session_id()
    params = {
        "session_id": session_id,
        "task": task,
        "runner": runner,
        "repo": repo,
        "by": by,
        "budget": budget,
        # Engine-internal tuning, resolved here (the process that owns
        # config.py) and carried into the workflow so workflow.py stays
        # free of both vendor imports (cp6) and magic literals (cp22)
        # without importing sovereign.config into the Temporal sandbox.
        "receipt_activity_timeout_s": config.RECEIPT_ACTIVITY_TIMEOUT_S,
        "receipt_retry_max_attempts": config.RECEIPT_RETRY_MAX_ATTEMPTS,
        "notify_activity_timeout_s": config.NOTIFY_ACTIVITY_TIMEOUT_S,
        "notify_retry_max_attempts": config.NOTIFY_RETRY_MAX_ATTEMPTS,
        "step_start_to_close_min": config.STEP_START_TO_CLOSE_MIN,
        "step_heartbeat_s": config.STEP_HEARTBEAT_S,
        "step_activity_retry_max_attempts": config.STEP_ACTIVITY_RETRY_MAX_ATTEMPTS,
        "last_output_max_chars": config.SESSION_LAST_OUTPUT_MAX_CHARS,
    }
    await client.start_workflow(
        WORKFLOW,
        params,
        id=session_id,
        task_queue=config.TEMPORAL_TASK_QUEUE,
    )
    return {"session_id": session_id}


async def _state_of(handle: WorkflowHandle) -> dict[str, Any] | None:
    """A query is answered from the workflow's own in-memory attributes
    (workflow.py's `state()` never awaits), so it must never take long --
    but a client-side timeout still guards `list_sessions` against any
    server- or network-side stall, so one session can never hang the
    whole list (defect: builder C, 2026-08-25)."""
    timeout = config.CLIENT_QUERY_TIMEOUT_S
    try:
        return await asyncio.wait_for(handle.query("state"), timeout=timeout)
    except asyncio.TimeoutError:
        # A running workflow's `result()` would only block further, so
        # degrade to "unknown" rather than stacking a second wait.
        return None
    except (RPCError, Exception):
        pass
    try:
        result = await asyncio.wait_for(handle.result(), timeout=timeout)
        if isinstance(result, dict):
            return result
    except (asyncio.TimeoutError, WorkflowFailureError, RPCError, Exception):
        pass
    return None


def _to_row(state: dict[str, Any] | None, session_id: str) -> dict[str, Any]:
    if state is None:
        return {
            "session_id": session_id,
            "repo": None,
            "task": "",
            "step": 0,
            "status": "unknown",
            "runner": "",
            "asking": None,
            "started_at": None,
            "updated_at": None,
            "last_output": "",
            "line_message_id": None,
            "budget": 0,
            "budget_remaining": 0,
        }
    row = dict(state)
    row["last_output"] = (row.get("last_output") or "")[: config.SESSION_LAST_OUTPUT_MAX_CHARS]
    return row


async def list_sessions() -> list[dict[str, Any]]:
    client = await get_client()
    out: list[dict[str, Any]] = []
    async for wf in client.list_workflows(query=f"WorkflowType='{WORKFLOW}'"):
        handle = client.get_workflow_handle(wf.id)
        state = await _state_of(handle)
        row = _to_row(state, wf.id)
        out.append(
            {
                "session_id": row.get("session_id", wf.id),
                "repo": row.get("repo"),
                "task": row.get("task", ""),
                "step": row.get("step", 0),
                "status": row.get("status", "unknown"),
                "runner": row.get("runner", ""),
                "asking": row.get("asking"),
                "started_at": row.get("started_at"),
                "updated_at": row.get("updated_at"),
                "last_output": row.get("last_output", ""),
                "line_message_id": row.get("line_message_id"),
                "budget": row.get("budget", 0),
                "budget_remaining": row.get("budget_remaining", 0),
            }
        )
    return out


async def show(session_id: str) -> dict[str, Any]:
    client = await get_client()
    handle = client.get_workflow_handle(session_id)
    state = await _state_of(handle)
    return _to_row(state, session_id)


async def signal(
    session_id: str,
    kind: Literal["stop", "approve", "deny", "steer", "refill"],
    by: str,
    text: str = "",
    tokens: int = 0,
    signed: bool = False,
) -> dict[str, Any]:
    client = await get_client()
    handle = client.get_workflow_handle(session_id)
    if kind == "stop":
        await handle.signal("stop", args=[by, text])
    elif kind == "approve":
        await handle.signal("approve", args=[by])
    elif kind == "deny":
        await handle.signal("deny", args=[by])
    elif kind == "steer":
        await handle.signal("steer", args=[by, text])
    elif kind == "refill":
        await handle.signal("refill", args=[by, tokens, signed])
    else:
        return {"ok": False, "error": f"unknown signal kind: {kind}"}
    return {"ok": True}


async def set_line_message_id(session_id: str, msg_id: int) -> dict[str, Any]:
    client = await get_client()
    handle = client.get_workflow_handle(session_id)
    return await handle.execute_update("set_line_message_id", msg_id)


async def episodes(kind: str | None = None) -> list[dict[str, Any]]:
    return receipts_mod.episodes(kind)
