"""SessionWorkflow: one Temporal workflow per agent session. Durable across
worker restarts (cp1), stop is a signal applied even while the worker was
dead (cp2), an approval gate parks in "waiting" and never proceeds on
silence (cp3). Activities are referenced by name (string), never imported
here, so this module pulls in no vendor SDK and stays sandbox-clean (cp6).

R28/R30 (spec 4.3) add the governance FSM alongside the lifecycle status:
`init -> planning -> tool_use -> synthesis -> terminal`, with the
`synthesis -> planning` back edge counted, and a pause before cycle
number fsm.max_cycles + 1. The two axes answer different questions --
`status` is what the founder sees on the card (running, waiting,
halted), `fsm_state` is where in the reasoning loop the session is -- so
neither replaces the other and both are in `state()`.

The ordered transition list is carried in `params` rather than imported
from sovereign.engine.fsm, for the same reason nothing here imports
sovereign.config: fsm.py reads the KEYS table at import time, and this
module runs inside the Temporal sandbox. fsm.py remains the canonical
machine; sovereign/engine/test_fsm.py drives both over the same sequence
and asserts they agree state for state, so the two cannot drift.

R29: the budget is no longer a number this workflow subtracts from. It
is a versioned row (sovereign/engine/budget.py) reached through the
`budget_op` activity, because the race the spec names is between
concurrent activities and a workflow attribute cannot see it.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, CancelledError

# MERIDIAN-CTRL-001 section 11.1: the independent verifier gets a deadline, not forever.
# Each expired round re-dispatches the verification request; after the last round the
# obligation fails closed. An uncertain external mutation is never replayed on timeout.
VERIFICATION_DEADLINE_S_DEFAULT = 3600
VERIFICATION_MAX_ROUNDS_DEFAULT = 3
# The one runner that cannot change anything outside the workflow (section 11.2).
NON_CONSEQUENTIAL_RUNNERS = frozenset({"echo"})

STATUSES = (
    "running",
    "waiting",
    "halted",
    "paused",
    "stopped",
    "denied",
    "done",
    "failed",
)

# Mirrors sovereign.engine.fsm.STATES. Never imported from there (see the
# module docstring); the exact list arrives in params and this tuple is
# only the fallback for a workflow started before the param existed.
FSM_STATES = ("init", "planning", "tool_use", "synthesis", "terminal")


@workflow.defn(name="SessionWorkflow")
class SessionWorkflow:
    def __init__(self) -> None:
        self.session_id: str = ""
        self.instruction_id: str | None = None
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
        self.fsm_state: str = FSM_STATES[0]
        self.fsm_cycles: int = 0
        self.fsm_paused: bool = False
        self.last_commit: str | None = None
        self.last_tokens: int = 0

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
        self._fsm_order: list[str] = list(FSM_STATES)
        self._fsm_max_cycles: int = 0
        self._budget_activity_timeout_s: int = 0
        self._budget_retry_max_attempts: int = 0
        self._approval_timeout_min: int = 0

        self._steer_texts: list[str] = []
        self._pending_receipts: list[dict[str, Any]] = []
        self._stop_requested = False
        self._decision: str | None = None
        self._decision_by: str = ""
        self._decision_attestation: str = ""
        self._active_activity_handle: workflow.ActivityHandle | None = None
        self._refill: dict[str, Any] | None = None
        self._yield_proposal: dict[str, Any] | None = None
        self._yield_waiting = False
        self._guarded_instruction = False
        self._bounded_verification = False
        self._verification_deadline_s = VERIFICATION_DEADLINE_S_DEFAULT
        self._verification_max_rounds = VERIFICATION_MAX_ROUNDS_DEFAULT

    # ---- signals ----

    @workflow.signal
    def stop(self, by: str, reason: str = "") -> None:
        self._stop_requested = True
        self.stopped_by = by
        self.reason = reason
        if self._active_activity_handle is not None:
            self._active_activity_handle.cancel()

    @workflow.signal
    def approve(self, by: str, attestation: str = "") -> None:
        """`attestation` names the root of trust that verified the
        signature -- "hardware" or "fallback" (R11/R22, R24). Verification
        happens client-side in sovereign/trust/approval.py, because the
        private key is on this Mac and the workflow runs inside Temporal's
        deterministic sandbox where no subprocess, socket or Keychain call
        is allowed. What the workflow records is which root of trust said
        yes, and it records it on the approve receipt."""
        if self.status == "waiting":
            self._decision = "approve"
            self._decision_by = by
            self._decision_attestation = attestation

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

    @workflow.signal
    def submit_independent_yield(self, envelope: dict[str, Any]) -> None:
        """An untrusted transport, not an authorization or completion signal."""
        if (
            self._yield_waiting
            and self._yield_proposal is None
            and isinstance(envelope, dict)
            and set(envelope) == {"receipt", "signature"}
            and isinstance(envelope["receipt"], dict)
            and isinstance(envelope["signature"], str)
            and len(envelope["signature"]) == 128
        ):
            self._yield_proposal = envelope

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
            "instruction_id": self.instruction_id,
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
            "critical": self.critical,
            "fsm_state": self.fsm_state,
            "fsm_cycles": self.fsm_cycles,
            "fsm_paused": self.fsm_paused,
            "commit": self.last_commit,
        }

    # ---- run ----

    async def _receipt(self, kind: str, by: str, text: str = "") -> None:
        self.updated_at = workflow.now().isoformat()
        record = {
            "ts": self.updated_at,
            "session_id": self.session_id,
            "instruction_id": self.instruction_id,
            "kind": kind,
            "by": by,
            "text": text,
            "step": self.step,
            "status": self.status,
            "task": self.task,
            "runner": self.runner,
            # cp24/R7: the git commit the step produced, so `sb undo` has
            # a hash to revert to, and the token delta, so the receipt
            # carries the budget movement the spec (2.2) requires.
            "repo": self.repo,
            "commit": self.last_commit,
            "tokens": self.last_tokens,
            "budget_remaining": self.budget_remaining,
            "fsm_state": self.fsm_state,
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

    async def _request_verification(
        self, expected: dict[str, Any], round_no: int
    ) -> None:
        """Durable verifier work item: a receipt in the chain, with the deadline in it.

        The independent verifier reads the chain and answers with a signed envelope. The
        request carries only identifiers and hashes the verifier must match, never a
        worker claim, and it costs no model inference to wait for the answer.
        """
        await self._receipt(
            "verification_requested",
            "engine",
            f"round={round_no}/{self._verification_max_rounds} "
            f"deadline_s={self._verification_deadline_s} "
            f"run_id={expected['run_id']} epoch={expected['epoch']}",
        )

    async def _retain_instruction(self, reason: str) -> str:
        """Hold the obligation in Temporal, not the worker's conversation.

        A separate verifier must certify the effect or safe reconciliation.
        Never replay an uncertain external mutation merely because a worker
        exited. Waiting consumes no model inference or runner lease.
        """
        self.status = "halted"
        self.reason = reason
        self.asking = None
        self._yield_waiting = True
        self._yield_proposal = None
        expected = {
            "instruction_id": self.instruction_id,
            "run_id": workflow.info().run_id,
            "epoch": self.step,
            "goal_sha256": hashlib.sha256(self.task.encode()).hexdigest(),
            "commit_sha": self.last_commit,
        }
        await self._receipt("recovery_required", "engine", reason)
        rounds = 0
        if self._bounded_verification:
            await self._request_verification(expected, 1)
        try:
            while not self._stop_requested:
                if self._bounded_verification:
                    try:
                        await workflow.wait_condition(
                            lambda: (
                                self._yield_proposal is not None or self._stop_requested
                            ),
                            timeout=timedelta(seconds=self._verification_deadline_s),
                        )
                    except asyncio.TimeoutError:
                        rounds += 1
                        await self._receipt(
                            "verification_timeout",
                            "engine",
                            f"round {rounds}/{self._verification_max_rounds}",
                        )
                        if rounds >= self._verification_max_rounds:
                            self.status = "failed"
                            self.reason = "verification-deadline-exceeded"
                            self._fsm_terminate()
                            await self._receipt("fail", "engine", self.reason)
                            return "terminal"
                        await self._request_verification(expected, rounds + 1)
                        continue
                else:
                    await workflow.wait_condition(
                        lambda: self._yield_proposal is not None or self._stop_requested
                    )
                if self._stop_requested:
                    break
                proposal = self._yield_proposal
                self._yield_proposal = None
                try:
                    verdict = await workflow.execute_activity(
                        "verify_instruction_yield",
                        {"expected": expected, "envelope": proposal},
                        start_to_close_timeout=timedelta(
                            seconds=self._receipt_activity_timeout_s
                        ),
                        retry_policy=RetryPolicy(maximum_attempts=1),
                    )
                except ActivityError:
                    continue
                if self._stop_requested:
                    break
                if verdict == "settle":
                    self.status = "done"
                    self.reason = ""
                    self._fsm_terminate()
                    await self._receipt("done", "independent-verifier", "")
                    return "terminal"
                if verdict == "retry" and self.budget_remaining > 0:
                    self.status = "running"
                    self.reason = ""
                    await self._receipt("recover", "independent-verifier", "")
                    return "retry"
            self.status = "stopped"
            self._fsm_terminate()
            await self._receipt("stop", self.stopped_by or "unknown", self.reason)
            return "terminal"
        finally:
            self._yield_waiting = False
            self._yield_proposal = None

    # ---- FSM (R28/R30) ----

    def _fsm_cycle_head(self) -> str:
        """The state a completed cycle returns to -- `planning`, the first
        state after init."""
        return self._fsm_order[1] if len(self._fsm_order) > 1 else self._fsm_order[0]

    def _fsm_next(self) -> str:
        """The one forward edge from the current state. The last state
        before terminal wraps to the head of the cycle, which is the
        `synthesis -> planning` back edge the spec counts."""
        loop = self._fsm_order[:-1]
        if self.fsm_state not in loop:
            return self._fsm_order[-1]
        idx = loop.index(self.fsm_state)
        return loop[idx + 1] if idx + 1 < len(loop) else self._fsm_cycle_head()

    def _fsm_would_pause(self) -> bool:
        """True when the next move begins one cycle too many. Checked
        BEFORE the move, so the session pauses before the sixth cycle at
        the default of five rather than after it."""
        return (
            self._fsm_max_cycles > 0
            and self._fsm_next() == self._fsm_cycle_head()
            and self.fsm_state != self._fsm_order[0]
            and self.fsm_cycles >= self._fsm_max_cycles
        )

    def _fsm_advance(self) -> str:
        nxt = self._fsm_next()
        if nxt == self._fsm_cycle_head() and self.fsm_state != self._fsm_order[0]:
            self.fsm_cycles += 1
        self.fsm_state = nxt
        return nxt

    def _fsm_terminate(self) -> None:
        self.fsm_state = self._fsm_order[-1]

    # ---- budget (R29) ----

    async def _budget(self, op: str, tokens: int = 0) -> dict[str, Any]:
        """One activity for every budget movement. The row is the
        authority; this workflow only mirrors what it returns, so two
        activities spending concurrently cannot overdraw it."""
        return await workflow.execute_activity(
            "budget_op",
            {"op": op, "session_id": self.session_id, "tokens": int(tokens)},
            start_to_close_timeout=timedelta(seconds=self._budget_activity_timeout_s),
            retry_policy=RetryPolicy(maximum_attempts=self._budget_retry_max_attempts),
        )

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        self.session_id = params["session_id"]
        self.instruction_id = params.get("instruction_id")
        self._guarded_instruction = bool(self.instruction_id) and workflow.patched(
            "independent-instruction-yield-v1"
        )
        self.repo = params.get("repo")
        self.task = params["task"]
        self.runner = params.get("runner", "echo")
        self.by = params.get("by", "cli")
        self.budget = int(params["budget"])
        self.budget_remaining = self.budget
        self.critical = bool(params.get("critical", False))
        self._receipt_activity_timeout_s = int(params["receipt_activity_timeout_s"])
        self._receipt_retry_max_attempts = int(params["receipt_retry_max_attempts"])
        self._notify_activity_timeout_s = int(params["notify_activity_timeout_s"])
        self._notify_retry_max_attempts = int(params["notify_retry_max_attempts"])
        self._step_start_to_close_min = int(params["step_start_to_close_min"])
        self._step_heartbeat_s = int(params["step_heartbeat_s"])
        self._step_activity_retry_max_attempts = int(
            params["step_activity_retry_max_attempts"]
        )
        self._last_output_max_chars = int(params["last_output_max_chars"])
        self._fsm_order = list(params.get("fsm_states") or FSM_STATES)
        self._fsm_max_cycles = int(params.get("fsm_max_cycles") or 0)
        self._budget_activity_timeout_s = int(
            params.get("budget_activity_timeout_s")
            or params["receipt_activity_timeout_s"]
        )
        self._budget_retry_max_attempts = int(
            params.get("budget_retry_max_attempts")
            or params["receipt_retry_max_attempts"]
        )
        self.fsm_state = self._fsm_order[0]
        self._approval_timeout_min = int(params.get("approval_timeout_min", 0))
        self.started_at = workflow.now().isoformat()
        self.updated_at = self.started_at
        self._bounded_verification = self._guarded_instruction and workflow.patched(
            "bounded-verification-deadline-v1"
        )
        self._verification_deadline_s = int(
            params.get("verification_deadline_s") or VERIFICATION_DEADLINE_S_DEFAULT
        )
        self._verification_max_rounds = int(
            params.get("verification_max_rounds") or VERIFICATION_MAX_ROUNDS_DEFAULT
        )

        await self._budget("allocate", self.budget)
        await self._receipt("start", self.by, self.task)

        # Section 11.2: complete mediation inside the workflow, so a caller that starts it
        # directly cannot skip the client's check. Consequential work needs an instruction_id.
        if (
            not self.instruction_id
            and self.runner not in NON_CONSEQUENTIAL_RUNNERS
            and workflow.patched("custody-required-v1")
        ):
            self.status = "failed"
            self.reason = (
                "custody-required: consequential runner without instruction_id"
            )
            self._fsm_terminate()
            await self._receipt("fail", "engine", self.reason)
            return self._state()

        while True:
            if self._stop_requested:
                self.status = "stopped"
                await self._receipt("stop", self.stopped_by or "unknown", self.reason)
                return self._state()

            await self._drain_pending_receipts()

            # R30: entering planning is where a cycle is counted, so it is
            # also where the limit is checked. Pausing here means the 6th
            # cycle never starts, which is what "pause before the 6th"
            # says; halting after it would be a different (and useless)
            # guarantee.
            if self._fsm_would_pause():
                self.status = "paused"
                self.fsm_paused = True
                self.reason = "cycle"
                await self._receipt("pause", "engine", "cycle")
                await workflow.wait_condition(
                    lambda: self._decision is not None or self._stop_requested
                )
                if self._stop_requested:
                    self.status = "stopped"
                    self._fsm_terminate()
                    await self._receipt(
                        "stop", self.stopped_by or "unknown", self.reason
                    )
                    return self._state()
                if self._decision == "deny":
                    self.status = "denied"
                    self._fsm_terminate()
                    await self._receipt("deny", self._decision_by, "cycle")
                    return self._state()
                # An explicit approval is the founder saying the loop is
                # legitimate; the counter restarts rather than the limit
                # being ignored from here on.
                self.fsm_cycles = 0
                self.fsm_paused = False
                self.status = "running"
                self.reason = ""
                self._decision = None
                await self._receipt("approve", self._decision_by, "cycle")

            self._fsm_advance()  # -> planning
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
                retry_policy=RetryPolicy(
                    maximum_attempts=self._step_activity_retry_max_attempts
                ),
            )
            self._active_activity_handle = activity_handle
            self._fsm_advance()  # -> tool_use
            result = None
            try:
                result = await activity_handle
            except (ActivityError, CancelledError, asyncio.CancelledError):
                result = None
            finally:
                self._active_activity_handle = None

            if self._stop_requested:
                self.status = "stopped"
                self._fsm_terminate()
                await self._receipt("stop", self.stopped_by or "unknown", self.reason)
                return self._state()

            if result is None:
                if self._guarded_instruction:
                    self._fsm_advance()  # tool_use -> synthesis
                    if (
                        await self._retain_instruction("worker-exit-unverified")
                        == "retry"
                    ):
                        continue
                    return self._state()
                self.status = "failed"
                self._fsm_terminate()
                await self._receipt("fail", "engine", "activity did not complete")
                return self._state()

            self._fsm_advance()  # -> synthesis
            self.last_output = str(result.get("output", ""))[
                : self._last_output_max_chars
            ]
            self.steps.append(
                {
                    "n": self.step,
                    "output": result.get("output", ""),
                    "ts": workflow.now().isoformat(),
                }
            )
            self.last_commit = result.get("commit") or self.last_commit
            self.last_tokens = int(result.get("tokens", 0))
            spent = await self._budget("spend", self.last_tokens)
            self.budget_remaining = int(spent.get("remaining", 0))

            if self._guarded_instruction and (result.get("done") or result.get("ask")):
                if await self._retain_instruction("worker-claim-unverified") == "retry":
                    continue
                return self._state()

            if self.budget_remaining <= 0:
                self.status = "halted"
                self.reason = "budget"
                await self._receipt("halt", "engine", "budget")

                await workflow.wait_condition(
                    lambda: self._refill is not None or self._stop_requested
                )

                if self._stop_requested:
                    self.status = "stopped"
                    self._fsm_terminate()
                    await self._receipt(
                        "stop", self.stopped_by or "unknown", self.reason
                    )
                    return self._state()

                refill = self._refill
                self._refill = None
                self.budget += refill["tokens"]
                refilled = await self._budget("refill", refill["tokens"])
                self.budget_remaining = int(refilled.get("remaining", 0))
                self.status = "running"
                self.reason = ""
                await self._receipt("refill", refill["by"], str(refill["tokens"]))
                continue

            if result.get("ask"):
                self.asking = result["ask"]
                self.status = "waiting"
                self.updated_at = workflow.now().isoformat()
                await self._notify()

                # R12 default-deny. cp3 already refused to proceed on
                # silence; silence still parked the session in "waiting"
                # for ever, and a session waiting for ever holds its
                # budget, its worker slot and the founder's attention.
                # The deadline is a real wall-clock deadline held by
                # Temporal (workflow.wait_condition's own timeout), which
                # survives a worker restart -- a timer thread here would
                # not, and would also be non-deterministic inside the
                # workflow sandbox.
                #
                # It halts rather than denies on purpose: "denied" ends
                # the session and throws the work away, and an unanswered
                # request usually means the founder was in a meeting, not
                # that he refused. Halted keeps the state and still needs
                # a signed act to leave.
                deadline = (
                    timedelta(minutes=self._approval_timeout_min)
                    if self._approval_timeout_min
                    else None
                )
                timed_out = False
                while True:
                    try:
                        await workflow.wait_condition(
                            lambda: (
                                self._decision is not None
                                or self._stop_requested
                                or bool(self._pending_receipts)
                            ),
                            timeout=deadline,
                        )
                    except asyncio.TimeoutError:
                        timed_out = True
                        break
                    if self._pending_receipts:
                        await self._drain_pending_receipts()
                        continue
                    break

                if timed_out and self._decision is None and not self._stop_requested:
                    self.status = "halted"
                    self.reason = "default-deny"
                    self.updated_at = workflow.now().isoformat()
                    await self._receipt("halt", "engine", self.reason)
                    await self._notify()
                    return self._state()

                if self._stop_requested:
                    self.status = "stopped"
                    self._fsm_terminate()
                    await self._receipt(
                        "stop", self.stopped_by or "unknown", self.reason
                    )
                    return self._state()

                if self._decision == "deny":
                    self.status = "denied"
                    self._fsm_terminate()
                    await self._receipt("deny", self._decision_by, "")
                    return self._state()

                # approve: continue the loop for the next step
                self.status = "running"
                self.asking = None
                await self._receipt(
                    "approve", self._decision_by, self._decision_attestation
                )
                self._decision = None
                self._decision_by = ""
                self._decision_attestation = ""
                continue

            if result.get("done"):
                self.status = "done"
                self.asking = None
                self._fsm_terminate()
                await self._receipt("done", "engine", "")
                return self._state()

            # neither ask nor done: loop for another step
            continue
