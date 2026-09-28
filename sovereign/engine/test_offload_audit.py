"""idp#3525 CP5, OFF-01 (trace audit).

Binds sovereign/engine/offload_audit.py against the spec's own ACCEPT
line: "static scan of traces shows zero model tokens attributable to
deterministic ops."
"""

from __future__ import annotations

import pytest

from sovereign.engine.offload_audit import audit_traces, classify_op


@pytest.mark.parametrize(
    "op,expected",
    [
        ("math.add", "math"),
        ("sum_rows", "aggregation"),
        ("str.concat", "string"),
        ("format_report", "string"),
        ("date.parse", "date"),
        ("strftime_iso", "date"),
        ("count_items", "aggregation"),
    ],
)
def test_deterministic_ops_classify_into_one_of_the_four_named_classes(
    op: str, expected: str
) -> None:
    assert classify_op(op) == expected


@pytest.mark.parametrize(
    "op", ["llm.generate", "tool_call.search_web", "vision.caption", "", "unknown_op"]
)
def test_non_deterministic_or_unrecognized_ops_classify_as_none(op: str) -> None:
    assert classify_op(op) is None


def test_a_clean_trace_set_produces_no_violations() -> None:
    traces = [
        {"op": "math.add", "tokens": 0},
        {"op": "llm.generate", "tokens": 512},
        {"op": "str.concat", "tokens": 0},
    ]
    assert audit_traces(traces) == []


def test_a_deterministic_op_that_burned_model_tokens_is_a_violation() -> None:
    traces = [
        {"op": "math.add", "tokens": 0},
        {"op": "sum_rows", "tokens": 40},
        {"op": "llm.generate", "tokens": 512},
    ]
    violations = audit_traces(traces)
    assert len(violations) == 1
    assert violations[0].op == "sum_rows"
    assert violations[0].op_class == "aggregation"
    assert violations[0].tokens == 40


def test_missing_or_zero_tokens_fields_are_read_as_no_violation() -> None:
    assert audit_traces([{"op": "math.add"}]) == []
    assert audit_traces([{"op": "math.add", "tokens": None}]) == []
