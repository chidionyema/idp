#!/usr/bin/env python3
"""Claude Code integration hook for idp verification stack."""

import logging
from datetime import datetime

from tests.verification.harness import VerificationHarness

logger = logging.getLogger(__name__)


class ClaudeCodeVerificationHook:
    """Hook that Claude Code calls after each agent turn."""

    def __init__(self):
        self.harness = VerificationHarness()
        self.turn_count = 0
        self.failed_gates = []

    def verify_agent_result(self, agent_result: dict) -> dict:
        """
        Called by Claude Code after agent execution.

        Args:
            agent_result: {
                "transcript_id": str,
                "transcript": {...},
                "output": str,
                "verdict": str
            }

        Returns:
            {
                "passed": bool,
                "failures": [...],
                "halt": bool,
                "timestamp": str
            }
        """
        self.turn_count += 1

        try:
            # Convert dict to mock object for harness
            from unittest.mock import MagicMock

            result = MagicMock()
            result.transcript = MagicMock()

            # Populate transcript from dict
            if agent_result.get("transcript"):
                transcript_data = agent_result["transcript"]
                result.transcript.transcript_id = transcript_data.get("transcript_id")
                result.transcript.loop_detected = transcript_data.get(
                    "loop_detected", False
                )
                result.transcript.circuit_breaker_tripped = transcript_data.get(
                    "circuit_breaker_tripped", False
                )

                # Create spans from transcript
                spans = []
                for span_data in transcript_data.get("spans", []):
                    span = MagicMock()
                    span.span_kind = span_data.get("span_kind")
                    span.fault_flags = span_data.get("fault_flags")
                    spans.append(span)

                result.transcript.spans = spans

            result.output = agent_result.get("output", "")

            # Run verification
            verdict = self.harness.verify(result)

            # Track failures
            if not verdict.passed:
                self.failed_gates.extend([f.gate_name for f in verdict.failures])

            return {
                "passed": verdict.passed,
                "failures": [
                    {"gate": f.gate_name, "message": f.message}
                    for f in verdict.failures
                ],
                "halt": not verdict.passed,
                "timestamp": datetime.now().isoformat(),
                "turn": self.turn_count,
            }

        except Exception as e:
            logger.error(f"Verification hook failed: {e}", exc_info=True)
            return {
                "passed": False,
                "failures": [{"gate": "hook_error", "message": str(e)}],
                "halt": False,
                "timestamp": datetime.now().isoformat(),
                "turn": self.turn_count,
            }

    def get_summary(self) -> dict:
        """Get verification summary."""
        return {
            "total_turns": self.turn_count,
            "failed_gates": list(set(self.failed_gates)),
            "halt_on_failure": True,
        }


# Global hook instance
_hook = None


def get_hook() -> ClaudeCodeVerificationHook:
    """Get or create verification hook."""
    global _hook
    if _hook is None:
        _hook = ClaudeCodeVerificationHook()
    return _hook


def verify(agent_result: dict) -> dict:
    """Entry point for Claude Code."""
    return get_hook().verify_agent_result(agent_result)
