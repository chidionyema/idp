"""Temporal activities. All side effects (subprocess, http, disk) live here,
never in workflow.py, so workflow replay stays deterministic.

Every activity below is `async def` (Temporal dispatches it on the worker's
event loop), so any *synchronous* I/O inside it -- a blocking httpx.post, a
file open()+fcntl.flock(), a `security` Keychain subprocess call made via
subprocess.run -- must run on `asyncio.to_thread`, never inline. Inline sync
I/O here stalls the whole event loop: every other workflow task on this
worker stops being polled, a workflow task then exceeds its 5s limit
(TMPRL1104), and an update sent to a workflow whose task the worker can't
service in time is reported as failed. Observed 2026-08-25: notify_change
called sovereign.otto.card.on_change synchronously (blocking httpx.post
plus a blocking asyncio.run() of a client update back into this same
workflow) and receipts.append() did its file/flock/Keychain I/O inline;
workflow_task_duration=151152ms and "Workflow Task in failed state" on
set_line_message_id were both this one root cause.
"""
from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from temporalio import activity

from sovereign import config
from sovereign.engine import receipts as receipts_mod
from sovereign.engine import runners
from sovereign.engine import tracing


@activity.defn
async def run_step(inp: dict[str, Any]) -> dict[str, Any]:
    return await runners.run(
        inp["runner"], inp["task"], inp.get("repo"), inp["step"], inp.get("steer") or []
    )


@activity.defn
async def append_receipt(record: dict[str, Any]) -> dict[str, Any]:
    """`record` may carry a "state" sub-dict (the session's full state at
    receipt time); this activity turns it into a state_hash field before
    handing the line to the signed chain (cp18/cp19). receipts_mod.append()
    is synchronous (open/fcntl.flock/Keychain subprocess) -- off the event
    loop via asyncio.to_thread, same reasoning as notify_change below."""
    record = dict(record)
    state = record.pop("state", None)
    if state is not None:
        record["state_hash"] = hashlib.sha256(config.canonical_json(state)).hexdigest()
    return await asyncio.to_thread(receipts_mod.append, record)


@activity.defn
async def notify_change(state: dict[str, Any]) -> dict[str, int]:
    """Best-effort fan-out to Otto's card and Langfuse. Never raises: a
    down notification channel must never affect session status. Given a
    short start_to_close timeout and no retry (sovereign/config.py
    notify.activity_timeout_s / notify.retry_max_attempts) so a stuck
    notification channel can never hold up the step loop -- a failure here
    is logged, not retried, because the next state change will notify
    again anyway.

    Returns {session_id: line_message_id} when card.on_change sent or
    edited a line message, else {}. card.on_change makes no call back into
    this workflow (see sovereign/otto/card.py's on_change docstring) --
    workflow.py reads this return value and sets its own line_message_id,
    so no activity ever issues a Temporal update against the workflow that
    is still waiting on that same activity to finish."""
    tracing.trace_session(
        state.get("session_id", ""),
        state.get("task", ""),
        state.get("runner", ""),
        state.get("status", ""),
        {"step": state.get("step", 0), "asking": state.get("asking")},
    )
    try:
        from sovereign.otto import card  # type: ignore

        result = await asyncio.to_thread(card.on_change, state)
        return result if isinstance(result, dict) else {}
    except ImportError:
        return {}
    except Exception as exc:  # pragma: no cover - defensive, never fatal
        activity.logger.warning(f"notify_change: otto.card.on_change failed: {exc}")
        return {}
