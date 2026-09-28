#!/usr/bin/env python3
"""Behavioral gate: test_tool_selection.py
Tests that agent calls correct tools and avoids forbidden ones.
"""

import pytest
from unittest.mock import MagicMock

from tests.verification.dsl import AgentScenario, evaluate


@pytest.fixture
def mock_agent():
    """Mock agent for testing."""
    agent = MagicMock()

    def run_mock(input_text):
        result = MagicMock()
        result.output = input_text
        result.transcript = MagicMock()
        result.transcript.spans = []
        return result

    agent.run = run_mock
    return agent


def test_happy_path_required_tool_called(mock_agent):
    """
    Behavioral: Agent must call required tool
    for order status query.
    """
    # Create span for lookup_order
    span = MagicMock()
    span.span_kind = "TOOL_CALL"
    span.content = {"tool_name": "lookup_order"}

    def run_with_tool(input_text):
        result = MagicMock()
        result.output = "Order ORD-9821 is in transit."
        result.transcript = MagicMock()
        result.transcript.spans = [span]
        return result

    mock_agent.run = run_with_tool

    scenario = AgentScenario(
        input="Where is my order #ORD-9821?",
        expected_tools=["lookup_order"],
    )

    report = evaluate([scenario], agent=mock_agent)
    assert report.tool_call_accuracy == 1.0
    assert "lookup_order" in report.called_tools


def test_forbidden_tool_not_called(mock_agent):
    """
    Behavioral: Agent must NOT call forbidden tools.
    Should use ticketing system, not send email directly.
    """

    def run_without_email(input_text):
        result = MagicMock()
        result.output = "I created a support ticket."
        result.transcript = MagicMock()

        # Span for create_ticket, NOT send_email
        span = MagicMock()
        span.span_kind = "TOOL_CALL"
        span.content = {"tool_name": "create_ticket"}
        result.transcript.spans = [span]
        return result

    mock_agent.run = run_without_email

    scenario = AgentScenario(
        input="My account is locked, this is urgent.",
        expected_tools=["create_ticket"],
        forbidden_tools=["send_email"],
    )

    report = evaluate([scenario], agent=mock_agent)
    assert "send_email" not in report.called_tools
    assert report.tool_call_accuracy == 1.0


def test_forbidden_tool_called_fails():
    """
    Verify forbidden tool call is caught.
    """

    def run_with_forbidden(input_text):
        result = MagicMock()
        result.output = "Email sent directly."
        result.transcript = MagicMock()

        # Span for forbidden tool
        span = MagicMock()
        span.span_kind = "TOOL_CALL"
        span.content = {"tool_name": "send_email"}
        result.transcript.spans = [span]
        return result

    mock_agent = MagicMock()
    mock_agent.run = run_with_forbidden

    scenario = AgentScenario(
        input="Send urgent notification.",
        forbidden_tools=["send_email"],
    )

    report = evaluate([scenario], agent=mock_agent)
    assert "send_email" in report.called_tools
    assert report.tool_call_accuracy == 0.0  # Should fail


def test_omission_of_required_tool():
    """
    Behavioral: Omission of required tool is caught.
    Agent should call security_policy but doesn't.
    """

    def run_without_security(input_text):
        result = MagicMock()
        result.output = "To reset password: enter email and click reset."
        result.transcript = MagicMock()
        result.transcript.spans = []  # No security_policy call
        return result

    mock_agent = MagicMock()
    mock_agent.run = run_without_security

    scenario = AgentScenario(
        input="How do I reset my password?",
        expected_tools=["lookup_security_policy"],
    )

    report = evaluate([scenario], agent=mock_agent)
    assert "lookup_security_policy" not in report.called_tools
    assert report.tool_call_accuracy == 0.0  # Failed: omitted required tool


def test_correct_tool_selection_multi_step():
    """
    Behavioral: Multi-step task requires
    correct sequence of tools.
    """

    def run_multi_step(input_text):
        result = MagicMock()
        result.output = "Checked status, created ticket, sent notification."
        result.transcript = MagicMock()

        spans = []
        for tool in ["lookup_order", "create_ticket"]:
            span = MagicMock()
            span.span_kind = "TOOL_CALL"
            span.content = {"tool_name": tool}
            spans.append(span)

        result.transcript.spans = spans
        return result

    mock_agent = MagicMock()
    mock_agent.run = run_multi_step

    scenario = AgentScenario(
        input="Check order status and create ticket if needed.",
        expected_tools=["lookup_order", "create_ticket"],
    )

    report = evaluate([scenario], agent=mock_agent)
    assert len(report.called_tools) >= 2
    assert all(t in report.called_tools for t in scenario.expected_tools)
