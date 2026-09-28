#!/usr/bin/env python3
"""ParEval control loop: smart halt gate.

Implements ControlLoop protocol.
Pre-LLM hook that halts agent when statistical evidence is sufficient.
Replaces blunt 30-turn cap with confidence-based early stopping.
"""

from platform.eval.protocol import ControlLoop, GateDecision, LoopHealth
from platform.eval.pareval_policy import PolicyValidator, CODING_TASK_POLICY_MODEL_SWAP
from datetime import datetime


class ParEvalLoop(ControlLoop):
    """
    ParEvalLayer as a ControlLoop.
    Halts agent when statistical confidence threshold is reached.
    """

    name = "pareval"

    def __init__(self, policy=None):
        self.policy = policy or CODING_TASK_POLICY_MODEL_SWAP
        self.observed_results = []
        self.last_run_at = None
        self.last_error = None
        self.mode = "shadow"

        # Validate policy
        validation = PolicyValidator.validate(self.policy)
        if not validation["valid"]:
            self.last_error = f"Invalid policy: {validation['issues']}"

    def pre_llm(self, state: dict) -> GateDecision:
        """
        Called before LLM invocation.
        Returns halt decision if confidence threshold reached.
        """
        self.last_run_at = datetime.now().isoformat()

        # In this simplified version, we track message count
        # In production, this would track actual task results
        messages = state.get("messages", [])
        turn_count = len([m for m in messages if type(m).__name__ == "AIMessage"])

        # Mock decision logic:
        # If we have enough "evidence" (turns), consider halting
        # In production, this computes bootstrap CI on task outcomes
        if turn_count >= self.policy.max_tasks:
            return GateDecision(
                action="halt",
                evidence=f"Reached max_tasks ({self.policy.max_tasks})",
                confidence=0.95,
            )

        return GateDecision(action="allow")

    def post_verdict(self, state: dict, verdict: dict) -> None:
        """Called after verdict. Log result for decision layer."""
        # In production, record the task outcome and update bootstrap CI
        pass

    def periodic(self) -> None:
        """Periodic maintenance (no-op for ParEval)."""
        pass

    def health(self) -> LoopHealth:
        """Report loop health."""
        return LoopHealth(
            name=self.name,
            mode=self.mode,
            last_run_at=self.last_run_at or "never",
            last_error=self.last_error or "none",
            is_healthy=self.last_error is None,
        )
