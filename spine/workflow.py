"""The observer workflow: a workflow that suspends on a signal and wakes on an event.

The build kit's rule, kept: do not call continue-as-new from inside a signal handler. The
handler here only records the payload; the main loop does the work, so a signal that arrives
while the workflow is continuing as new is buffered by Temporal and delivered to the new run
rather than lost.

The workflow does not poll. It waits on a condition, exactly as the kit says, and the only
thing that wakes it is an event the bridge delivered.

The verification itself is an activity, and the activity is a state fetch: the workflow that
runs the check is the trigger, not the decider (the estate's decision register,
dec:spine-woken-verification).
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, Dict, List

from temporalio import workflow

from .activities import emit_receipt, verify_reconciliation
from .observer import COMPLETE, GAP, build_receipt, decide, timeout_receipt

# How long the workflow waits for an event before it says so. An hour is the kit's number and
# it is a sane one: long enough that a busy cluster does not time out, short enough that a
# missing event is a fact somebody hears about the same day.
WAIT_TIMEOUT_S = 3600
# How many events one run handles before it continues as new. The kit's rule is "on
# GetContinueAsNewSuggested"; this SDK's Info has no such field, so the history is bounded
# by a count instead -- the same intent, one mechanism fewer to depend on.
MAX_EVENTS_PER_RUN = 100
# The activity timeouts. A status read is a GET; thirty seconds is generous and a hang is
# visible.
ACTIVITY_TIMEOUT_S = 30


@workflow.defn(name="ObserverWorkflow")
class ObserverWorkflow:
    """Waits for a reconcile event, checks the reconcile, and leaves a receipt."""

    def __init__(self) -> None:
        self._signals: List[Dict[str, Any]] = []
        self._seen: set = set()

    @workflow.run
    async def run(self, target: Dict[str, Any]) -> Dict[str, Any]:
        handled = 0
        while True:
            try:
                await workflow.wait_condition(
                    lambda: bool(self._signals),
                    timeout=timedelta(seconds=WAIT_TIMEOUT_S),
                    timeout_summary="waiting for a flux reconcile event",
                )
            except asyncio.TimeoutError:
                receipt = timeout_receipt(target, WAIT_TIMEOUT_S)
                written = await workflow.execute_activity(
                    emit_receipt,
                    receipt,
                    start_to_close_timeout=timedelta(seconds=ACTIVITY_TIMEOUT_S),
                )
                return {
                    "status": "timeout",
                    "outcome": GAP,
                    "receipt": receipt,
                    "ingested": bool(written.get("ingested")),
                }

            payload = self._signals.pop(0)
            event_id = str(payload.get("eventId") or "")
            if event_id and event_id in self._seen:
                # The same event, signalled twice. Temporal delivers a signal that was sent
                # twice, and the bridge may signalled before it crashed and recorded the
                # dedup. Ignoring the second copy is the whole point of the id.
                continue
            if event_id:
                self._seen.add(event_id)

            verdict = await workflow.execute_activity(
                verify_reconciliation,
                payload,
                start_to_close_timeout=timedelta(seconds=ACTIVITY_TIMEOUT_S),
            )
            outcome = decide(verdict)
            receipt = build_receipt(payload, verdict, outcome)
            written = await workflow.execute_activity(
                emit_receipt,
                receipt,
                start_to_close_timeout=timedelta(seconds=ACTIVITY_TIMEOUT_S),
            )
            receipt["ingested"] = bool(written.get("ingested"))
            if outcome == COMPLETE:
                return {
                    "status": "verified",
                    "outcome": outcome,
                    "receipt": receipt,
                    "ingested": receipt["ingested"],
                }

            handled += 1
            if handled >= MAX_EVENTS_PER_RUN or self._continue_as_new_suggested():
                # Continue as new from the main loop, never from the signal handler.
                workflow.continue_as_new(target)

    @workflow.signal(name="flux.reconciled")
    async def on_reconciled(self, payload: Dict[str, Any]) -> None:
        """Record the event. The work happens in the main loop."""
        self._signals.append(payload or {})

    @staticmethod
    def _continue_as_new_suggested() -> bool:
        """The SDK's own suggestion, when this version of the SDK has one."""
        info = getattr(workflow, "info", None)
        return bool(getattr(info, "continue_as_new_suggested", False))
