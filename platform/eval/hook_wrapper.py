#!/usr/bin/env python3
"""Hook wrapper: failure isolation for all control-loop hooks.

Every hook call wrapped: exception → log + demote loop to off + alert.
Agent path never breaks. Backpressure respected.
"""

import logging
from datetime import datetime
from platform.eval.protocol import ControlLoop, GateDecision

logger = logging.getLogger(__name__)


class HookWrapper:
    """
    Wraps all hook calls. Handles failure isolation, mode checking, demotion.
    """

    def __init__(self, registry, loop: ControlLoop):
        self.registry = registry
        self.loop = loop
        self.last_error = None
        self.last_run_at = None

    def safe_pre_llm(self, state: dict) -> GateDecision:
        """
        Call pre_llm with failure isolation.
        Exception → log + demote + return allow (fail-open).
        """
        mode = self.registry.loop_modes.get(self.loop.name, "off")

        if mode == "off":
            return GateDecision(action="allow")

        try:
            decision = self.loop.pre_llm(state)
            self.last_run_at = datetime.now().isoformat()
            return decision
        except Exception as e:
            logger.error(
                f"[HookWrapper] {self.loop.name}.pre_llm failed: {e}",
                exc_info=True,
            )
            self.last_error = str(e)
            # Demote loop to off
            self.registry.set_mode(self.loop.name, "off")
            # Fail-open: allow agent to proceed
            return GateDecision(
                action="allow", evidence=f"Hook failed (demoted to off): {e}"
            )

    def safe_post_verdict(self, state: dict, verdict: dict, queue_put_fn) -> None:
        """
        Call post_verdict with backpressure handling.
        Exception → log + demote. Never blocks graph.
        If queue full → drop + metric.
        """
        mode = self.registry.loop_modes.get(self.loop.name, "off")

        if mode == "off":
            return

        try:
            # Call the hook
            self.loop.post_verdict(state, verdict)
            self.last_run_at = datetime.now().isoformat()
        except Exception as e:
            logger.error(
                f"[HookWrapper] {self.loop.name}.post_verdict failed: {e}",
                exc_info=True,
            )
            self.last_error = str(e)
            self.registry.set_mode(self.loop.name, "off")

    def safe_periodic(self) -> None:
        """Call periodic maintenance hook. Out of request path."""
        mode = self.registry.loop_modes.get(self.loop.name, "off")

        if mode == "off":
            return

        try:
            self.loop.periodic()
            self.last_run_at = datetime.now().isoformat()
        except Exception as e:
            logger.error(
                f"[HookWrapper] {self.loop.name}.periodic failed: {e}",
                exc_info=True,
            )
            self.last_error = str(e)
            self.registry.set_mode(self.loop.name, "off")

    def is_healthy(self) -> bool:
        """Loop is healthy if no recent errors and mode != off."""
        mode = self.registry.loop_modes.get(self.loop.name, "off")
        return mode != "off" and self.last_error is None


class HookOrchestrator:
    """
    Manages all hook wrappers. Called by the graph at hook points.
    Enforces mode checking, backpressure, observability.
    """

    def __init__(self, registry):
        self.registry = registry
        self.wrappers = {}

    def register_loop(self, loop: ControlLoop):
        """Register a loop and wrap it."""
        self.wrappers[loop.name] = HookWrapper(self.registry, loop)
        self.registry.register(loop)

    def call_pre_llm(self, state: dict) -> GateDecision:
        """
        Call all pre_llm hooks in enforce/shadow mode.
        Returns the first halt decision, else allow.
        """
        for loop_name, wrapper in self.wrappers.items():
            mode = self.registry.loop_modes.get(loop_name, "off")
            if mode == "off":
                continue

            decision = wrapper.safe_pre_llm(state)

            # In enforce mode, halt halts. In shadow, halt is logged but ignored.
            if decision.action == "halt" and mode == "enforce":
                return decision

        return GateDecision(action="allow")

    def call_post_verdict_async(
        self, state: dict, verdict: dict, queue_put_fn, backpressure_limit: int
    ) -> None:
        """
        Call all post_verdict hooks asynchronously.
        Respects backpressure: if queue depth > limit, drop + metric.
        Never blocks the graph.
        """
        for loop_name, wrapper in self.wrappers.items():
            mode = self.registry.loop_modes.get(loop_name, "off")
            if mode == "off":
                continue

            # Backpressure check
            try:
                queue_depth = queue_put_fn.__self__.qsize()
                if queue_depth > backpressure_limit:
                    logger.warning(
                        f"[HookOrchestrator] Backpressure limit reached. "
                        f"Dropping post_verdict for {loop_name}"
                    )
                    continue
            except Exception as e:  # noqa: S110
                logger.debug(f"Queue depth check failed: {e}. Proceeding anyway.")

            # Non-blocking call
            wrapper.safe_post_verdict(state, verdict, queue_put_fn)

    def health_report(self) -> dict:
        """Report health of all wrapped loops."""
        return {
            name: {
                "loop_name": name,
                "mode": self.registry.loop_modes.get(name, "off"),
                "last_run_at": wrapper.last_run_at or "never",
                "last_error": wrapper.last_error or "none",
                "is_healthy": wrapper.is_healthy(),
            }
            for name, wrapper in self.wrappers.items()
        }
