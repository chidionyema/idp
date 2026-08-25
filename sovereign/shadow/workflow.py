"""Temporal branching (R19, spec 3.2): one parent workflow forks N child
workflows, each on its own git branch, each in Ghost mode, and merges the
winner with exactly one receipt.

Temporal is the mature tool here (LAW 43): a child workflow gives each
branch its own durable history, its own cancellation, and a parent close
policy that cancels the children if the parent dies -- none of which a
hand-rolled asyncio.gather survives a worker restart with. The parent is
BranchParentWorkflow; the children are BranchChildWorkflow, started with
workflow.start_child_workflow so a stop on the parent can cancel each one
by handle.

This module imports nothing from sovereign.config, for the same reason
sovereign/engine/workflow.py does not: it runs inside Temporal's
deterministic sandbox, and config.py reads files and sockets at import.
Every tunable arrives in `params` from the client side.

Ghost mode is structural, not a flag: there is no notify activity in
either workflow. Nothing here can reach Telegram, the card or Langfuse,
so "zero messages during their run" is true by construction.

crew#213 (founder, 2026-08-25): a child's budget is capped at
branch.budget_pct of the parent's budget, allocated as its own row in
sovereign/engine/budget.py under the child's session id and spent through
the same compare-and-swap. When a spend clamps to zero the child writes a
halt receipt and stops; the other branches keep racing.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, CancelledError
from temporalio.workflow import ParentClosePolicy

CHILD_STATUSES = ("running", "done", "halted", "stopped", "failed")


@workflow.defn(name="BranchChildWorkflow")
class BranchChildWorkflow:
    """One silent micro-session on one git branch."""

    def __init__(self) -> None:
        self.child_id: str = ""
        self.parent_id: str = ""
        self.branch: str = ""
        self.status: str = "running"
        self.step: int = 0
        self.tokens: int = 0
        self.budget: int = 0
        self.budget_remaining: int = 0
        self.commit: str | None = None
        self.output: str = ""
        self.reason: str = ""
        self._stop_requested = False
        self._handle: workflow.ActivityHandle | None = None

    @workflow.signal
    def stop(self, by: str, reason: str = "") -> None:
        self._stop_requested = True
        self.reason = reason or by
        if self._handle is not None:
            self._handle.cancel()

    @workflow.query
    def state(self) -> dict[str, Any]:
        return self._state()

    def _state(self) -> dict[str, Any]:
        return {
            "session_id": self.child_id,
            "parent_id": self.parent_id,
            "branch": self.branch,
            "status": self.status,
            "step": self.step,
            "tokens": self.tokens,
            "budget": self.budget,
            "budget_remaining": self.budget_remaining,
            "commit": self.commit,
            "output": self.output,
            "reason": self.reason,
        }

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        self.child_id = params["child_id"]
        self.parent_id = params["parent_id"]
        self.branch = params["branch"]
        self.budget = int(params["budget"])
        steps = int(params["steps"])
        step_timeout = timedelta(seconds=int(params["step_timeout_s"]))
        heartbeat = timedelta(seconds=int(params["heartbeat_s"]))
        short_timeout = timedelta(seconds=int(params["merge_timeout_s"]))
        retry = RetryPolicy(maximum_attempts=int(params["retry_max_attempts"]))

        try:
            allocated = await workflow.execute_activity(
                "branch_budget",
                {"op": "allocate", "session_id": self.child_id, "tokens": self.budget},
                start_to_close_timeout=short_timeout,
                retry_policy=retry,
            )
            self.budget_remaining = int(allocated.get("remaining", self.budget))

            for _ in range(steps):
                if self._stop_requested:
                    break
                self.step += 1
                self._handle = workflow.start_activity(
                    "branch_step",
                    {
                        "child_id": self.child_id,
                        "parent_id": self.parent_id,
                        "branch": self.branch,
                        "repo": params.get("repo"),
                        "task": params["task"],
                        "runner": params["runner"],
                        "step": self.step,
                    },
                    start_to_close_timeout=step_timeout,
                    heartbeat_timeout=heartbeat,
                    retry_policy=retry,
                )
                try:
                    result = await self._handle
                except asyncio.CancelledError:
                    if self._stop_requested:  # our own stop signal cancelled the step
                        result = None
                    else:
                        raise  # the parent cancelled us: handled below as a stop
                except (ActivityError, CancelledError) as err:
                    # Temporal delivers a workflow cancel to a running
                    # activity as an ActivityError whose cause is CancelledError.
                    if isinstance(err, CancelledError) or isinstance(err.cause, CancelledError):
                        self._stop_requested = True
                    result = None
                finally:
                    self._handle = None
                if self._stop_requested:
                    break
                if result is None:
                    self.status = "failed"
                    self.reason = "activity did not complete"
                    return self._state()
                self.output = str(result.get("output", ""))
                self.commit = result.get("commit") or self.commit
                step_tokens = int(result.get("tokens", 0))
                self.tokens += step_tokens
                spent = await workflow.execute_activity(
                    "branch_budget",
                    {"op": "spend", "session_id": self.child_id, "tokens": step_tokens},
                    start_to_close_timeout=short_timeout,
                    retry_policy=retry,
                )
                self.budget_remaining = int(spent.get("remaining", 0))
                if spent.get("halted"):
                    self.status = "halted"
                    self.reason = str(params["halt_reason"])
                    await workflow.execute_activity(
                        "branch_receipt",
                        {
                            "session_id": self.child_id,
                            "parent_id": self.parent_id,
                            "kind": str(params["halt_receipt_kind"]),
                            "by": "engine",
                            "text": self.reason,
                            "step": self.step,
                            "status": self.status,
                            "branch": self.branch,
                            "budget": self.budget,
                            "budget_remaining": self.budget_remaining,
                            "tokens": self.tokens,
                        },
                        start_to_close_timeout=short_timeout,
                        retry_policy=retry,
                    )
                    return self._state()
        except asyncio.CancelledError:
            # The parent cancelled us (founder stop). Freeze: record the
            # state and return it, so the parent can read every child's
            # final state and the query still answers "stopped".
            self._stop_requested = True

        if self._stop_requested:
            self.status = "stopped"
            return self._state()
        self.status = "done"
        return self._state()


@workflow.defn(name="BranchParentWorkflow")
class BranchParentWorkflow:
    def __init__(self) -> None:
        self.parent_id: str = ""
        self.status: str = "running"
        self.fork_hash: str = ""
        self.fork_commit: str = ""
        self.children: list[dict[str, Any]] = []
        self.winner: str | None = None
        self.merge: dict[str, Any] | None = None
        self.stopped_by: str | None = None
        self.reason: str = ""
        self._stop_requested = False
        self._handles: list[Any] = []

    @workflow.signal
    def stop(self, by: str, reason: str = "") -> None:
        self._stop_requested = True
        self.stopped_by = by
        self.reason = reason
        for handle in self._handles:
            handle.cancel()

    @workflow.query
    def state(self) -> dict[str, Any]:
        return self._state()

    def _state(self) -> dict[str, Any]:
        return {
            "session_id": self.parent_id,
            "status": self.status,
            "fork_hash": self.fork_hash,
            "fork_commit": self.fork_commit,
            "children": self.children,
            "winner": self.winner,
            "merge": self.merge,
            "stopped_by": self.stopped_by,
            "reason": self.reason,
        }

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        self.parent_id = params["parent_id"]
        count = int(params["count"])
        prefix = str(params["branch_prefix"])
        sep = str(params["child_id_sep"])
        short_timeout = timedelta(seconds=int(params["merge_timeout_s"]))
        retry = RetryPolicy(maximum_attempts=int(params["retry_max_attempts"]))
        budget_pct = int(params["budget_pct"])
        child_budget = int(params["budget"]) * budget_pct // 100
        branches = [f"{prefix}-{i}" for i in range(1, count + 1)]

        fork = await workflow.execute_activity(
            "branch_fork",
            {"parent_id": self.parent_id, "repo": params.get("repo"), "branches": branches,
             "budget": int(params["budget"]), "timestamp": int(workflow.now().timestamp())},
            start_to_close_timeout=short_timeout,
            retry_policy=retry,
        )
        self.fork_hash = str(fork.get("fork_hash", ""))
        self.fork_commit = str(fork.get("fork_commit", ""))

        if self._stop_requested:
            return await self._stopped(params, short_timeout, retry)

        for i, branch in enumerate(branches, start=1):
            child_id = f"{self.parent_id}{sep}{i}"
            child_params = {
                **{k: params[k] for k in ("task", "runner", "steps", "step_timeout_s", "heartbeat_s",
                                           "merge_timeout_s", "retry_max_attempts", "halt_reason",
                                           "halt_receipt_kind")},
                "repo": params.get("repo"),
                "child_id": child_id,
                "parent_id": self.parent_id,
                "branch": branch,
                "budget": child_budget,
            }
            handle = await workflow.start_child_workflow(
                BranchChildWorkflow.run,
                child_params,
                id=child_id,
                parent_close_policy=ParentClosePolicy.REQUEST_CANCEL,
            )
            self._handles.append(handle)

        results = await asyncio.gather(*self._handles, return_exceptions=True)
        self.children = [
            r if isinstance(r, dict) else {"session_id": f"{self.parent_id}{sep}{i}", "branch": b,
                                           "status": "failed", "reason": str(r), "tokens": 0}
            for i, (b, r) in enumerate(zip(branches, results), start=1)
        ]

        if self._stop_requested:
            return await self._stopped(params, short_timeout, retry)

        merged = await workflow.execute_activity(
            "branch_merge",
            {
                "parent_id": self.parent_id,
                "repo": params.get("repo"),
                "fork_hash": self.fork_hash,
                "fork_commit": self.fork_commit,
                "children": self.children,
                "timestamp": int(workflow.now().timestamp()),
            },
            start_to_close_timeout=short_timeout,
            retry_policy=retry,
        )
        self.merge = merged
        self.winner = merged.get("winner")
        self.status = "done" if merged.get("ok") else "failed"
        self.reason = str(merged.get("reason", ""))
        return self._state()

    async def _stopped(self, params: dict[str, Any], timeout: timedelta, retry: RetryPolicy) -> dict[str, Any]:
        self.status = "stopped"
        await workflow.execute_activity(
            "branch_receipt",
            {
                "session_id": self.parent_id,
                "kind": "stop",
                "by": self.stopped_by or "unknown",
                "text": self.reason,
                "step": 0,
                "status": self.status,
                "parent_hash": self.fork_hash,
                "fork_commit": self.fork_commit,
                "children": [{"session_id": c.get("session_id"), "status": c.get("status")} for c in self.children],
            },
            start_to_close_timeout=timeout,
            retry_policy=retry,
        )
        return self._state()
