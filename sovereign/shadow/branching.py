"""Client side of temporal branching (R19): builds the parent workflow's
params from config and starts it. This is the process that owns
sovereign.config; the workflow module never imports it.

`params()` is separate from `start()` so the acceptance suite can hand the
same params to a Temporal test environment worker, and `sb start
--branches N` hands them to the estate's own server.
"""
from __future__ import annotations

import uuid
from typing import Any

from temporalio.client import Client

from sovereign import config
from sovereign.shadow import config_keys as ck
from sovereign.shadow.workflow import BranchParentWorkflow


def new_parent_id() -> str:
    return "sbb-" + uuid.uuid4().hex[: int(config.get("session.id_hex_len").value)]


def params(
    task: str,
    *,
    runner: str,
    repo: str | None,
    budget: int,
    count: int | None = None,
    parent_id: str | None = None,
) -> dict[str, Any]:
    return {
        "parent_id": parent_id or new_parent_id(),
        "task": task,
        "runner": runner,
        "repo": repo,
        "budget": int(budget),
        "count": int(count if count is not None else config.get("branch.count").value),
        "budget_pct": int(config.get("branch.budget_pct").value),
        "branch_prefix": str(ck.get("branch.name_prefix")),
        "child_id_sep": str(ck.get("branch.child_id_sep")),
        "steps": int(ck.get("branch.steps")),
        "step_timeout_s": int(ck.get("branch.step_timeout_s")),
        "heartbeat_s": int(config.get("step.heartbeat_s").value),
        "merge_timeout_s": int(ck.get("branch.merge_timeout_s")),
        "retry_max_attempts": int(ck.get("branch.retry_max_attempts")),
        "halt_reason": str(ck.get("branch.halt_reason")),
        "halt_receipt_kind": str(ck.get("branch.halt_receipt_kind")),
    }


def child_ids(parent_id: str, count: int) -> list[str]:
    sep = str(ck.get("branch.child_id_sep"))
    return [f"{parent_id}{sep}{i}" for i in range(1, int(count) + 1)]


async def start(client: Client, p: dict[str, Any], task_queue: str | None = None) -> dict[str, Any]:
    handle = await client.start_workflow(
        BranchParentWorkflow.run,
        p,
        id=p["parent_id"],
        task_queue=task_queue or config.TEMPORAL_TASK_QUEUE,
    )
    return {"session_id": handle.id, "children": child_ids(p["parent_id"], p["count"]), "branches": p["count"]}


async def start_on_estate(task: str, *, runner: str, repo: str | None, budget: int, count: int | None) -> dict[str, Any]:
    client = await Client.connect(config.TEMPORAL_ADDRESS, namespace=config.TEMPORAL_NAMESPACE)
    return await start(client, params(task, runner=runner, repo=repo, budget=budget, count=count))
