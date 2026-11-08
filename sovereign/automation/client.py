"""One gateway-normalized Temporal client for CLI/MCP/founder/voice."""
from __future__ import annotations

import os
from typing import Any

from sovereign import config
from sovereign.automation.contracts import compile_request
from sovereign.engine.client import get_client


async def start(request: dict[str, Any], release: dict[str, str]) -> dict[str, Any]:
    # JSON "actor" is not authentication. Must match the trusted gateway's
    # authenticated service principal before any Temporal start or side effect.
    verified_actor = os.environ.get("ESTATE_AUTOMATION_AUTHENTICATED_ACTOR", "")
    if not verified_actor or request.get("actor") != verified_actor:
        raise PermissionError("authenticated gateway actor missing or does not match")
    plan = compile_request(request, release)
    client = await get_client()
    handle = await client.start_workflow(
        "EstateAutomationWorkflowV1", plan, id=plan["workflow_id"],
        task_queue=config.TEMPORAL_TASK_QUEUE,
    )
    return {"workflow_id": plan["workflow_id"], "run_id": handle.result_run_id,
            "plan_hash": plan["plan_hash"], "status": "started"}


async def state(workflow_id: str) -> dict[str, Any]:
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        return await handle.query("state")
    except Exception as exc:
        result = await handle.result()
        if not isinstance(result, dict):
            raise TypeError("unreadable automation receipt") from exc
        return result
