"""The sandboxed match-logic evaluator."""

from __future__ import annotations

import time

import pytest

from efda.match import (
    Budget,
    BudgetExceeded,
    MatchError,
    matches,
    parse,
    regex_complexity,
)


def artifact(failure_class="exit_nonzero", kinds=("checkpoint",)):
    return {
        "failure_boundary": {"failure_class": failure_class},
        "raw_evidence": {
            "capture_method": "supervisor_wrapper",
            "payloads": [{"kind": kind} for kind in kinds],
        },
    }


def test_a_field_comparison_fires():
    assert matches('failure_boundary.failure_class == "exit_nonzero"', artifact())


def test_a_field_comparison_does_not_fire():
    assert not matches('failure_boundary.failure_class == "oomkill"', artifact())


def test_a_wildcard_path_resolves_to_every_value():
    expression = 'raw_evidence.payloads[*].kind == "log_tail"'
    assert matches(expression, artifact(kinds=("checkpoint", "log_tail")))
    assert not matches(expression, artifact(kinds=("checkpoint",)))


def test_boolean_operators_work():
    expression = (
        'failure_boundary.failure_class == "exit_nonzero" and '
        'raw_evidence.capture_method == "supervisor_wrapper"'
    )
    assert matches(expression, artifact())


def test_not_inverts():
    assert matches('not (failure_boundary.failure_class == "oomkill")', artifact())


def test_contains_and_matches_work():
    assert matches('failure_boundary.failure_class contains "exit"', artifact())
    assert matches('failure_boundary.failure_class matches "^exit_.*"', artifact())


def test_an_unparseable_expression_is_refused():
    with pytest.raises(MatchError):
        parse("failure_boundary.failure_class == ")
    with pytest.raises(MatchError):
        parse("")


def test_a_nested_quantifier_regex_is_high_complexity():
    assert regex_complexity("(a+)+$") == "high"
    assert regex_complexity("(a|b)+") == "moderate"
    assert regex_complexity("(a|b)") == "low"
    assert regex_complexity("^exit_[a-z]+$") == "low"


def test_a_catastrophic_regex_is_refused_by_the_ceiling():
    budget = Budget(max_wall_clock_ms=1000, max_regex_complexity="low")
    with pytest.raises(BudgetExceeded):
        matches('failure_boundary.failure_class matches "(a+)+$"', artifact(), budget)


def test_the_wall_clock_budget_stops_a_runaway():
    budget = Budget(max_wall_clock_ms=1)
    time.sleep(0.01)
    with pytest.raises(BudgetExceeded):
        matches('failure_boundary.failure_class == "exit_nonzero"', artifact(), budget)


def test_the_step_budget_stops_a_runaway():
    budget = Budget(max_steps=1)
    with pytest.raises(BudgetExceeded):
        matches(
            'failure_boundary.failure_class == "exit_nonzero" and '
            'raw_evidence.capture_method == "supervisor_wrapper"',
            artifact(),
            budget,
        )


def test_there_is_no_eval_anywhere_in_the_evaluator():
    import inspect

    import efda.match as module

    source = inspect.getsource(module)
    assert "eval(" not in source
    assert "exec(" not in source
