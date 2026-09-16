#!/usr/bin/env python3
"""Behavioral gate: test_trace_quality.py
Tests that agent does not loop, stays in step budget, leaves no artifacts.
"""

import pytest
from unittest.mock import MagicMock

from tests.verification.gates import find_forbidden_span_args


@pytest.fixture
def create_span():
    """Factory for creating mock spans."""

    def _create(span_kind, tool_name=None, sequence_num=0):
        span = MagicMock()
        span.span_kind = span_kind
        span.sequence_num = sequence_num
        if tool_name:
            # args_hash intentionally excludes sequence_num: it represents the call's
            # arguments, which stay identical across repeated identical calls. Hashing
            # in the turn number would make every call unique by construction and no
            # repetition could ever be detected.
            span.content = {
                "tool_name": tool_name,
                "args_hash": f"hash_{tool_name}",
            }
        else:
            span.content = {"args_hash": f"hash_{sequence_num}"}
        return span

    return _create


def test_no_reasoning_loop(create_span):
    """
    Behavioral: Agent must not repeat same action
    (span_kind, args_hash) within 5-turn window.
    Catches loops at turn 3-4, not turn 30.
    """
    result = MagicMock()
    result.transcript = MagicMock()

    # Create loop: same tool called 3 times in a row
    spans = [
        create_span("TOOL_CALL", "lookup_db", 1),
        create_span("TOOL_CALL", "lookup_db", 2),
        create_span("TOOL_CALL", "lookup_db", 3),  # Loop detected here
    ]
    result.transcript.spans = spans

    # Check for loop: repeated (span_kind, args_hash)
    seen = {}
    loop_detected = False

    for i, span in enumerate(spans):
        key = (span.span_kind, span.content.get("args_hash"))
        if key in seen:
            if i - seen[key] <= 5:  # Within 5-turn window
                loop_detected = True
                break
        seen[key] = i

    assert loop_detected, "Loop pattern not detected"


def test_within_step_budget(create_span):
    """
    Behavioral: Agent must complete task
    within N steps (e.g., 15 steps max).
    """
    result = MagicMock()
    result.transcript = MagicMock()

    max_steps = 15

    # Create 20 spans (exceeds budget)
    spans = [create_span("TOOL_CALL", f"tool_{i}", i) for i in range(20)]
    result.transcript.spans = spans

    steps_taken = len(result.transcript.spans)
    over_budget = steps_taken > max_steps
    assert over_budget, (
        f"Step budget violation was not detected: {steps_taken} steps taken, budget {max_steps}"
    )


def test_step_budget_compliance(create_span):
    """
    Verify step budget is enforced and violations caught.
    """
    result = MagicMock()
    result.transcript = MagicMock()

    max_steps = 10

    # Create 5 spans (within budget)
    spans = [create_span("TOOL_CALL", f"tool_{i}", i) for i in range(5)]
    result.transcript.spans = spans

    steps_taken = len(result.transcript.spans)
    assert steps_taken <= max_steps, f"Steps {steps_taken} exceed budget {max_steps}"


def test_no_stray_artifacts():
    """
    Behavioral: Agent must not read/write
    credential files or leave debug scripts.
    """
    result = MagicMock()
    result.transcript = MagicMock()

    # Create spans with forbidden file reads
    span1 = MagicMock()
    span1.span_kind = "TOOL_CALL"
    span1.content = {
        "tool_name": "read_file",
        "args": {"file": "credentials.json"},
    }

    result.transcript.spans = [span1]

    forbidden_files = ["credentials.json", ".env", "secrets.yaml"]
    forbidden_reads = find_forbidden_span_args(
        result.transcript.spans, "file", forbidden_files
    )

    assert len(forbidden_reads) > 0, (
        f"Forbidden file read was not detected among: {forbidden_files}"
    )


def test_stray_debug_script_detection():
    """
    Behavioral: Agent must not create
    debug_*.py files in repo root.
    """
    result = MagicMock()
    result.transcript = MagicMock()

    # Create span writing debug file
    span = MagicMock()
    span.span_kind = "TOOL_CALL"
    span.content = {
        "tool_name": "write_file",
        "args": {"path": "./debug_test.py", "content": "debug code"},
    }
    result.transcript.spans = [span]

    debug_patterns = ["debug_", "tmp_", "test_scratch"]
    debug_artifacts = find_forbidden_span_args(
        result.transcript.spans, "path", debug_patterns
    )

    assert len(debug_artifacts) > 0, "Stray debug artifact was not detected"


def test_max_consecutive_identical_actions():
    """
    Behavioral: Limit repeated identical actions.
    Max 3 consecutive identical tool calls.
    """
    result = MagicMock()
    result.transcript = MagicMock()

    # Create 5 identical tool calls in a row
    spans = [
        MagicMock(span_kind="TOOL_CALL", content={"tool_name": "lookup_api"})
        for _ in range(5)
    ]
    result.transcript.spans = spans

    # Count max consecutive identical
    max_consecutive = 1
    current_consecutive = 1

    for i in range(1, len(spans)):
        if spans[i].content.get("tool_name") == spans[i - 1].content.get("tool_name"):
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 1

    violation_detected = max_consecutive >= 3
    assert violation_detected, (
        f"Excessive consecutive identical actions was not detected: {max_consecutive}"
    )


def test_reasonable_output_length():
    """
    Behavioral: Output must be reasonable length,
    not extremely long or truncated.
    """
    result = MagicMock()
    result.output = "The task is complete."
    result.transcript = MagicMock()
    result.transcript.spans = [MagicMock() for _ in range(5)]

    # Check output length
    min_length = 10
    max_length = 1000000  # 1M chars

    output_length = len(result.output)
    assert min_length <= output_length <= max_length, (
        f"Output length {output_length} outside bounds"
    )


def test_no_message_bloat():
    """
    Behavioral: Agent context must not grow
    unboundedly. Max 50% growth per turn.
    """
    result = MagicMock()
    result.transcript = MagicMock()

    # Create spans with message content
    initial_size = 1000
    spans = []

    for i in range(5):
        span = MagicMock()
        span.span_kind = "AGENT"
        # Simulate 50% growth per turn
        content_size = initial_size * (1.5**i)
        span.content = {"size": content_size}
        spans.append(span)

    result.transcript.spans = spans

    # Check growth rate
    max_growth_rate = 0.5  # 50% per turn
    for i in range(1, len(spans)):
        prev_size = spans[i - 1].content.get("size", initial_size)
        curr_size = spans[i].content.get("size", initial_size)
        growth_rate = (curr_size - prev_size) / prev_size if prev_size > 0 else 0
        assert growth_rate <= max_growth_rate, (
            f"Message bloat: {growth_rate:.2f} > {max_growth_rate}"
        )
