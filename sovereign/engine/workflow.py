"""SessionWorkflow: one Temporal workflow per agent session. Durable across
worker restarts (cp1), stop is a signal applied even while the worker was
dead (cp2), an approval gate parks in "waiting" and never proceeds on
silence (cp3). Activities are referenced by name (string), never imported
here, so this module pulls in no vendor SDK and stays sandbox-clean (cp6).
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, CancelledError

STATUSES = ("running", "waiting", "stopped", "denied", "done", "failed")


@workflow.defn(name="SessionWorkflow")
class SessionWorkflow:
    def __init__(self) -> None:
        self.session_id: str = ""
        self.repo: str | None = None
        self.task: str = ""
        self.runner: str = "echo"
        self.by: str = "cli"
        self.status: str = "running"
        self.step: int = 0
        self.asking: str | None = None
        self.stopped_by: str | None = None
        self.reason: str = ""
        self.steps: list[dict[str, Any]] = []
        self.last_output: str = ""
        self.line_message_id: int | None = None
        self.started_at: str = ""
        self.updated_at: str = ""
        self.budget: int = 0
        self.budget_remaining: int = 0

        # Engine tuning, filled in from params at the top of run() -- these
        # come from client.start(), which is the process that owns
        # sovereign.config; workflow.py itself imports no config module so
        # it never re-executes config.py's file/socket/keychain reads
        # inside the Temporal sandbox.
        self._receipt_activity_timeout_s: int = 0
        self._receipt_retry_max_attempts: int = 0
        self._notify_activity_timeout_s: int = 0
        self._notify_retry_max_attempts: int = 0
        self._step_start_to_close_min: int = 0
        self._step_heartbeat_s: int = 0
        self._step_activity_retry_max_attempts: int = 0
        self._last_output_max_chars: int = 0

        self._steer_texts: list[str] = []
        self._pending_receipts: list[dict[str, Any]] = []
        self._stop_requested = False
        self._decision: str | None = None
        self._decision_by: str = ""
        self._active_activity_handle: workflow.ActivityHandle | None = None
        self._refill: dict[str, Any] | None = None

    # ---- signals ----

    @workflow.signal
    def stop(self, by: str, reason: str = "") -> None:
        self._stop_requested = True
        self.stopped_by = by
        self.reason = reason
        if self._active_activity_handle is not None:
            self._active_activity_handle.cancel()

    @workflow.signal
    def approve(self, by: str) -> None:
        if self.status == "waiting":
            self._decision = "approve"
            self._decision_by = by

    @workflow.signal
    def deny(self, by: str) -> None:
        if self.status == "waiting":
            self._decision = "deny"
            self._decision_by = by

    @workflow.signal
    def steer(self, by: str, text: str = "") -> None:
        self._steer_texts.append(text)
        self._pending_receipts.append({"kind": "steer", "by": by, "text": text})

    @workflow.signal
    def refill(self, by: str, tokens: int, signed: bool = False) -> None:
        if self.status == "halted":
            self._refill = {"by": by, "tokens": int(tokens), "signed": bool(signed)}

    # ---- update ----

    @workflow.update
    def set_line_message_id(self, msg_id: int) -> dict[str, Any]:
        self.line_message_id = msg_id
        return self._state()

    # ---- query ----

    @workflow.query
    def state(self) -> dict[str, Any]:
        return self._state()

    def _state(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "repo": self.repo,
            "task": self.task,
            "step": self.step,
            "status": self.status,
            "runner": self.runner,
            "asking": self.asking,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "last_output": self.last_output,
            "line_message_id": self.line_message_id,
            "stopped_by": self.stopped_by,
            "reason": self.reason,
            "steps": self.steps,
            "budget": self.budget,
            "budget_remaining": self.budget_remaining,
        }

    # ---- run ----

    async def _receipt(self, kind: str, by: str, text: str = "") -> None:
        self.updated_at = workflow.now().isoformat()
        record = {
            "ts": self.updated_at,
            "session_id": self.session_id,
            "kind": kind,
            "by": by,
            "text": text,
            "step": self.step,
            "status": self.status,
            "task": self.task,
            "runner": self.runner,
            "state": self._state(),
        }
        await workflow.execute_activity(
            "append_receipt",
            record,
            start_to_close_timeout=timedelta(seconds=self._receipt_activity_timeout_s),
            retry_policy=RetryPolicy(maximum_attempts=self._receipt_retry_max_attempts),
        )
        await self._notify()

    def _apply_notify_result(self, result: Any) -> None:
        """card.on_change (via the notify_change activity) never calls back
        into this workflow -- it returns {session_id: line_message_id}
        instead, so a stuck/blocked chat call can never deadlock an update
        against the same workflow whose activity is still running it."""
        if isinstance(result, dict):
            msg_id = result.get(self.session_id)
            if msg_id is not None:
                self.line_message_id = msg_id

    async def _notify(self) -> None:
        result = await workflow.execute_activity(
            "notify_change",
            self._state(),
            start_to_close_timeout=timedelta(seconds=self._notify_activity_timeout_s),
            retry_policy=RetryPolicy(maximum_attempts=self._notify_retry_max_attempts),
        )
        self._apply_notify_result(result)

    async def _drain_pending_receipts(self) -> None:
        while self._pending_receipts:
            rec = self._pending_receipts.pop(0)
            await self._receipt(rec["kind"], rec["by"], rec.get("text", ""))

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        self.session_id = params["session_id"]
        self.repo = params.get("repo")
        self.task = params["task"]
        self.runner = params.get("runner", "echo")
        self.by = params.get("by", "cli")
        self.budget = int(params["budget"])
        self.budget_remaining = self.budget
        self._receipt_activity_timeout_s = int(params["receipt_activity_timeout_s"])
        self._receipt_retry_max_attempts = int(params["receipt_retry_max_attempts"])
        self._notify_activity_timeout_s = int(params["notify_activity_timeout_s"])
        self._notify_retry_max_attempts = int(params["notify_retry_max_attempts"])
        self._step_start_to_close_min = int(params["step_start_to_close_min"])
        self._step_heartbeat_s = int(params["step_heartbeat_s"])
        self._step_activity_retry_max_attempts = int(params["step_activity_retry_max_attempts"])
        self._last_output_max_chars = int(params["last_output_max_chars"])
        self.started_at = workflow.now().isoformat()
        self.updated_at = self.started_at

        await self._receipt("start", self.by, self.task)

        while True:
            if self._stop_requested:
                self.status = "stopped"
                await self._receipt("stop", self.stopped_by or "unknown", self.reason)
                return self._state()

            await self._drain_pending_receipts()

            self.step += 1
            step_input = {
                "session_id": self.session_id,
                "task": self.task,
                "repo": self.repo,
                "runner": self.runner,
                "step": self.step,
                "steer": list(self._steer_texts),
            }
            self._steer_texts = []

            activity_handle = workflow.start_activity(
                "run_step",
                step_input,
                start_to_close_timeout=timedelta(minutes=self._step_start_to_close_min),
                heartbeat_timeout=timedelta(seconds=self._step_heartbeat_s),
                retry_policy=RetryPolicy(maximum_attempts=self._step_activity_retry_max_attempts),
            )
            self._active_activity_handle = activity_handle
            result = None
            try:
                result = await activity_handle
            except (ActivityError, CancelledError, asyncio.CancelledError):
                result = None
            finally:
                self._active_activity_handle = None

            if self._stop_requested:
                self.status = "stopped"
                await self._receipt("stop", self.stopped_by or "unknown", self.reason)
                return self._state()

            if result is None:
                self.status = "failed"
                await self._receipt("fail", "engine", "activity did not complete")
                return self._state()

            self.last_output = str(result.get("output", ""))[: self._last_output_max_chars]
            self.steps.append({"n": self.step, "output": result.get("output", ""), "ts": workflow.now().isoformat()})
            self.budget_remaining -= int(result.get("tokens", 0))

            if self.budget_remaining <= 0:
                self.budget_remaining = 0
                self.status = "halted"
                self.reason = "budget"
                await self._receipt("halt", "engine", "budget")

                await workflow.wait_condition(lambda: self._refill is not None or self._stop_requested)

                if self._stop_requested:
                    self.status = "stopped"
                    await self._receipt("stop", self.stopped_by or "unknown", self.reason)
                    return self._state()

                refill = self._refill
                self._refill = None
                self.budget += refill["tokens"]
                self.budget_remaining += refill["tokens"]
                self.status = "running"
                self.reason = ""
                await self._receipt("refill", refill["by"], str(refill["tokens"]))
                continue

            if result.get("ask"):
                self.asking = result["ask"]
                self.status = "waiting"
                self.updated_at = workflow.now().isoformat()
                await self._notify()

                while True:
                    await workflow.wait_condition(
                        lambda: self._decision is not None or self._stop_requested or bool(self._pending_receipts)
                    )
                    if self._pending_receipts:
                        await self._drain_pending_receipts()
                        continue
                    break

                if self._stop_requested:
                    self.status = "stopped"
                    await self._receipt("stop", self.stopped_by or "unknown", self.reason)
                    return self._state()

                if self._decision == "deny":
                    self.status = "denied"
                    await self._receipt("deny", self._decision_by, "")
                    return self._state()

                # approve: continue the loop for the next step
                self.status = "running"
                self.asking = None
                await self._receipt("approve", self._decision_by, "")
                self._decision = None
                self._decision_by = ""
                continue

            if result.get("done"):
                self.status = "done"
                self.asking = None
                await self._receipt("done", "engine", "")
                return self._state()

            # neither ask nor done: loop for another step
            continue
