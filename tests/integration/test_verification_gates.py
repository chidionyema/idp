#!/usr/bin/env python3
"""Integration tests: end-to-end verification gates.
The full gate suite that must pass before any agent output is trusted.
"""

import pytest
from unittest.mock import MagicMock

from tests.verification.harness import VerificationHarness
from tests.verification.gates import (
    TranscriptCompleteGate,
    NoHallucinatedToolsGate,
    NoLoopDetectedGate,
    NoFaultFlagsGate,
)


@pytest.fixture
def harness():
    """Create a verification harness with default gates."""
    return VerificationHarness()


@pytest.fixture
def mock_agent_result():
    """Mock agent result with complete transcript."""
    result = MagicMock()
    result.output = "Task completed successfully."

    # Create transcript with spans
    result.transcript = MagicMock()

    span = MagicMock()
    span.span_kind = "TOOL_CALL"
    span.content = {"tool_name": "query_database"}
    span.fault_flags = None

    result.transcript.spans = [span]
    result.transcript.loop_detected = False

    return result


def test_gate_1_transcript_complete(harness, mock_agent_result):
    """Gate 1: Transcript exists and has spans."""
    gate = TranscriptCompleteGate()
    # Should not raise
    gate(mock_agent_result)


def test_gate_1_fails_on_missing_transcript(harness):
    """Gate 1 failure: transcript is None."""
    result = MagicMock()
    result.transcript = None

    gate = TranscriptCompleteGate()
    with pytest.raises(AssertionError):
        gate(result)


def test_gate_2_no_hallucinated_tools(harness, mock_agent_result):
    """Gate 2: Tool calls map to real tools."""

    def registered_tools():
        return ["query_database", "create_ticket", "send_email"]

    gate = NoHallucinatedToolsGate(registered_tools=registered_tools)
    # Should not raise
    gate(mock_agent_result)


def test_gate_2_detects_hallucinated_tool(harness):
    """Gate 2 failure: hallucinated tool detected."""
    result = MagicMock()
    result.transcript = MagicMock()

    span = MagicMock()
    span.span_kind = "TOOL_CALL"
    span.content = {"tool_name": "nonexistent_tool"}
    result.transcript.spans = [span]

    def registered_tools():
        return ["query_database"]

    gate = NoHallucinatedToolsGate(registered_tools=registered_tools)
    with pytest.raises(AssertionError, match="Hallucinated"):
        gate(result)


def test_gate_4_no_loop_detected(harness, mock_agent_result):
    """Gate 4: No reasoning loop in transcript."""
    gate = NoLoopDetectedGate()
    # Should not raise
    gate(mock_agent_result)


def test_gate_4_detects_loop(harness):
    """Gate 4 failure: loop detected."""
    result = MagicMock()
    result.transcript = MagicMock()
    result.transcript.loop_detected = True

    gate = NoLoopDetectedGate()
    with pytest.raises(AssertionError, match="loop"):
        gate(result)


def test_gate_5_no_fault_flags(harness, mock_agent_result):
    """Gate 5: No fault flags in any span."""
    gate = NoFaultFlagsGate()
    # Should not raise
    gate(mock_agent_result)


def test_gate_5_detects_fault_flags(harness):
    """Gate 5 failure: fault flags present."""
    result = MagicMock()
    result.transcript = MagicMock()

    span = MagicMock()
    span.span_kind = "TOOL_CALL"
    span.fault_flags = ["loop_detected", "timeout"]
    result.transcript.spans = [span]

    gate = NoFaultFlagsGate()
    with pytest.raises(AssertionError, match="Fault flags"):
        gate(result)


def test_harness_all_gates_pass(harness, mock_agent_result):
    """All gates pass on clean result."""
    verdict = harness.verify(mock_agent_result)

    assert verdict.passed, f"Gates failed: {verdict.failures}"
    assert len(verdict.failures) == 0


def test_harness_detects_first_failure(harness):
    """Harness detects and reports first gate failure."""
    result = MagicMock()
    result.transcript = None  # Gate 1 will fail

    verdict = harness.verify(result)

    assert not verdict.passed
    assert len(verdict.failures) == 1
    assert verdict.failures[0].gate_name == "TranscriptComplete"


def test_harness_multiple_failures(harness):
    """Harness detects multiple gate failures."""
    result = MagicMock()
    result.transcript = MagicMock()
    result.transcript.spans = []  # Empty spans
    result.transcript.loop_detected = True  # Loop present

    verdict = harness.verify(result)

    assert not verdict.passed
    # Should detect loop failure
    loop_failures = [f for f in verdict.failures if "Loop" in f.gate_name]
    assert len(loop_failures) > 0


def test_harness_gate_registry(harness):
    """Harness gate registry operations."""
    gate_names = harness.gate_names()

    assert "TranscriptComplete" in gate_names
    assert "NoLoopDetected" in gate_names
    assert "NoFaultFlags" in gate_names


def test_harness_add_custom_gate(harness, mock_agent_result):
    """Harness can add custom gates dynamically."""
    from tests.verification.gates import Gate

    class CustomGate(Gate):
        def __call__(self, agent_result):
            assert len(agent_result.output) > 0, "Output is empty"

    harness.add_gate(CustomGate("CustomGate"))

    verdict = harness.verify(mock_agent_result)
    assert verdict.passed

    # Now test with empty output
    result = MagicMock()
    result.output = ""
    result.transcript = MagicMock()
    result.transcript.spans = []
    result.transcript.loop_detected = False

    verdict = harness.verify(result)
    assert not verdict.passed
    assert any("Custom" in f.gate_name for f in verdict.failures)


def test_harness_remove_gate(harness, mock_agent_result):
    """Harness can remove gates."""
    initial_count = len(harness.gate_names())

    harness.remove_gate("NoLoopDetected")

    final_count = len(harness.gate_names())
    assert final_count < initial_count
    assert "NoLoopDetected" not in harness.gate_names()


def test_verdict_timestamp(harness, mock_agent_result):
    """Verdict includes timestamp."""
    verdict = harness.verify(mock_agent_result)

    assert verdict.timestamp
    assert len(verdict.timestamp) > 0
