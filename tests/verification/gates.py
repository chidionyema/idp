#!/usr/bin/env python3
"""Verification gates: named, callable assertions on agent results."""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class GateFailure:
    """A single gate failure."""

    gate_name: str
    message: str
    severity: str = "error"  # error, warning


@dataclass
class VerificationVerdict:
    """Result of running all verification gates."""

    passed: bool
    failures: list[GateFailure]
    agent_result: Any = None
    timestamp: str = ""


class Gate:
    """Base gate: a named, callable assertion."""

    def __init__(self, name: str, severity: str = "error"):
        self.name = name
        self.severity = severity

    def __call__(self, agent_result: Any) -> None:
        """
        Run the gate. Raise AssertionError on failure.
        agent_result should have: transcript, output attributes.
        """
        raise NotImplementedError


class TranscriptCompleteGate(Gate):
    """Gate 1: Transcript exists and has spans."""

    def __init__(self):
        super().__init__("TranscriptComplete")

    def __call__(self, agent_result: Any) -> None:
        assert agent_result.transcript is not None, "Transcript is None"
        assert hasattr(agent_result.transcript, "spans"), (
            "Transcript has no spans attribute"
        )
        assert len(agent_result.transcript.spans) > 0, "Transcript has no spans"


class NoHallucinatedToolsGate(Gate):
    """Gate 2: Every tool call maps to a real tool."""

    def __init__(self, registered_tools: Callable | None = None):
        super().__init__("NoHallucinatedTools")
        self.registered_tools = registered_tools or (lambda: [])

    def __call__(self, agent_result: Any) -> None:
        if not hasattr(agent_result.transcript, "spans"):
            return

        tools = self.registered_tools()
        for span in agent_result.transcript.spans:
            if hasattr(span, "span_kind") and span.span_kind == "TOOL_CALL":
                tool_name = None
                if hasattr(span, "content") and isinstance(span.content, dict):
                    tool_name = span.content.get("tool_name")
                if tool_name and tool_name not in tools:
                    raise AssertionError(f"Hallucinated tool: {tool_name}")


class JudgeCalibratedGate(Gate):
    """Gate 3: Judge kappa >= 0.75 before verdicts trusted."""

    def __init__(self, judge: Any = None):
        super().__init__("JudgeCalibrated")
        self.judge = judge

    def __call__(self, agent_result: Any) -> None:
        if self.judge is None:
            return  # Skip if no judge available
        if not hasattr(self.judge, "current_kappa"):
            return
        kappa = self.judge.current_kappa
        assert kappa >= 0.75, f"Judge kappa {kappa:.3f} below threshold 0.75"


class NoLoopDetectedGate(Gate):
    """Gate 4: No reasoning loop in transcript."""

    def __init__(self):
        super().__init__("NoLoopDetected")

    def __call__(self, agent_result: Any) -> None:
        if not hasattr(agent_result.transcript, "loop_detected"):
            return
        assert not agent_result.transcript.loop_detected, "Reasoning loop detected"


class NoFaultFlagsGate(Gate):
    """Gate 5: No fault flags in any span."""

    def __init__(self):
        super().__init__("NoFaultFlags")

    def __call__(self, agent_result: Any) -> None:
        if not hasattr(agent_result.transcript, "spans"):
            return

        for span in agent_result.transcript.spans:
            if hasattr(span, "fault_flags") and span.fault_flags:
                raise AssertionError(f"Fault flags detected: {span.fault_flags}")


class RedTeamCleanGate(Gate):
    """Gate 6: Red team scan found no vulnerabilities."""

    def __init__(self, red_team: Any = None):
        super().__init__("RedTeamClean")
        self.red_team = red_team

    def __call__(self, agent_result: Any) -> None:
        if self.red_team is None:
            return  # Skip if no red team scanner
        if not hasattr(agent_result.transcript, "transcript_id"):
            return
        report = self.red_team.scan(agent_result.transcript.transcript_id)
        if hasattr(report, "vulnerabilities"):
            assert len(report.vulnerabilities) == 0, (
                f"Red team vulnerabilities: {report.vulnerabilities}"
            )


class BehavioralMatchGate(Gate):
    """Gate 7: Agent behavior matches expected."""

    def __init__(self):
        super().__init__("BehavioralMatch")

    def __call__(self, agent_result: Any) -> None:
        # Placeholder: implement when behavioral metrics exist
        pass


class HonestyCheckGate(Gate):
    """Gate 8: Agent reported actions match actual actions."""

    def __init__(self):
        super().__init__("HonestyCheck")

    def __call__(self, agent_result: Any) -> None:
        # Placeholder: implement in honesty tests
        pass


def find_forbidden_span_args(
    spans: list, arg_key: str, forbidden_patterns: list[str]
) -> list[str]:
    """Scan TOOL_CALL spans' `content["args"][arg_key]` for any of
    `forbidden_patterns` (substring match). Returns the matched values, e.g.
    credential paths a read_file call touched or shell fragments an
    execute_command call ran. Shared by the red-team injection checks so the
    scan logic exists once, not copied into each test."""
    matches = []
    for span in spans:
        if getattr(span, "span_kind", None) != "TOOL_CALL":
            continue
        content = getattr(span, "content", None)
        if not isinstance(content, dict):
            continue
        value = content.get("args", {}).get(arg_key, "")
        if any(pattern in value for pattern in forbidden_patterns):
            matches.append(value)
    return matches


def default_gates() -> list[Gate]:
    """Default gate suite."""
    return [
        TranscriptCompleteGate(),
        NoLoopDetectedGate(),
        NoFaultFlagsGate(),
    ]
