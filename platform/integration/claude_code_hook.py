#!/usr/bin/env python3
"""Claude Code integration hook for idp verification stack."""

import json
import logging
import os
import sqlite3
import sys
import importlib.util
from datetime import datetime

from tests.verification.harness import VerificationHarness
from tests.verification.gates import default_gates

logger = logging.getLogger(__name__)


def _load_judge_worker():
    """platform/ has no __init__.py (idp#3564: it collides with the stdlib
    `platform` module the moment anything imports it bare). Loading
    platform.eval.judge_worker/judge_drift by file path and seeding
    sys.modules under their real dotted names sidesteps that collision."""
    idp_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    for dotted, rel in [
        ("platform.eval", "platform/eval/__init__.py"),
        ("platform.eval.judge_drift", "platform/eval/judge_drift.py"),
        ("platform.eval.judge_worker", "platform/eval/judge_worker.py"),
    ]:
        if dotted in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(
            dotted, os.path.join(idp_root, rel)
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[dotted] = module
        spec.loader.exec_module(module)
    from platform.eval.judge_worker import JudgeWorker

    return JudgeWorker


DEFAULT_JUDGE_DB = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
    "state",
    "verification.db",
)


class ClaudeCodeVerificationHook:
    """Hook that Claude Code calls after each agent turn.

    Runs the full default gate suite (tests/verification/gates.py:
    default_gates) -- transcript-complete, no-loop, no-fault-flags,
    judge-calibrated, red-team-clean, honesty-check -- against a real
    platform.eval.judge_worker.JudgeWorker backed by `db_path`, not the
    3-gate subset this hook shipped with before idp#3564. LAW: no agent
    output on this platform is trusted without a passing verdict from this
    hook, or an explicit, logged override.
    """

    def __init__(self, db_path: str = DEFAULT_JUDGE_DB):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        JudgeWorker = _load_judge_worker()
        self.judge = JudgeWorker(db_path=db_path)
        self.harness = VerificationHarness(gates=default_gates(judge=self.judge))
        self.turn_count = 0
        self.failed_gates = []

    def _persist_spans(self, transcript_id: str, spans: list[dict]) -> None:
        """Write incoming spans into the judge's own schema so
        JudgeWorker.evaluate(transcript_id) has real data to score, instead
        of the "no spans found" neutral verdict it returns for an unknown id."""
        with sqlite3.connect(self.judge.db_path) as conn:
            for i, span_data in enumerate(spans):
                span_id = span_data.get("span_id") or f"{transcript_id}_{i}"
                payload = {
                    "tool_name": span_data.get("tool_name"),
                    "arguments": span_data.get("args", {}),
                    "error": span_data.get("error"),
                }
                conn.execute(
                    """
                    INSERT OR IGNORE INTO transcript_spans
                    (transcript_id, span_id, span_kind, payload)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        transcript_id,
                        span_id,
                        span_data.get("span_kind", "tool_call"),
                        json.dumps(payload),
                    ),
                )
            conn.commit()

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
                transcript_id = transcript_data.get("transcript_id")
                result.transcript.transcript_id = transcript_id
                result.transcript.loop_detected = transcript_data.get(
                    "loop_detected", False
                )
                result.transcript.circuit_breaker_tripped = transcript_data.get(
                    "circuit_breaker_tripped", False
                )

                span_dicts = transcript_data.get("spans", [])
                if transcript_id and span_dicts:
                    self._persist_spans(transcript_id, span_dicts)

                # Create spans from transcript
                spans = []
                for span_data in span_dicts:
                    span = MagicMock()
                    span.span_kind = span_data.get("span_kind")
                    span.fault_flags = span_data.get("fault_flags")
                    span.content = {
                        "tool_name": span_data.get("tool_name"),
                        "args": span_data.get("args", {}),
                    }
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
