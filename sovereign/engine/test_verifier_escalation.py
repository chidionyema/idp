"""Tests for sovereign/engine/verifier_escalation.py (idp#3525 CP3, ROUTE-03).

ACCEPT, verbatim: "adversarial misroute suite: wrong-cheap-answer attempts escalate;
right-cheap-answer passes without touching expensive lanes."
"""

from __future__ import annotations

import pytest

from sovereign.engine import verifier_escalation

# An adversarial misroute suite: each cheap answer, whether the verifier accepts it, and
# whether that means an escalation should have happened.
ADVERSARIAL_SUITE = [
    ("2 + 2 = 4", True, False),
    ("2 + 2 = 5", False, True),
    ("def f(): return 1", True, False),
    ("def f(): return 1 / 0  # never evaluated, verifier is static", False, True),
]


@pytest.mark.parametrize(
    "cheap_answer,verifier_accepts,expect_escalation", ADVERSARIAL_SUITE
)
def test_adversarial_suite_escalates_iff_verifier_rejects(
    cheap_answer, verifier_accepts, expect_escalation
) -> None:
    expensive_calls = []
    result = verifier_escalation.route_with_verifier(
        cheap_call=lambda: cheap_answer,
        verify=lambda _answer: verifier_accepts,
        expensive_call=lambda: expensive_calls.append(1) or "expensive-answer",
    )
    assert result.escalated is expect_escalation
    if expect_escalation:
        assert result.lane == "expensive"
        assert expensive_calls == [1]
    else:
        assert result.lane == "cheap"
        assert result.value == cheap_answer
        assert expensive_calls == []  # never touched, not just "not returned"


def test_right_cheap_answer_never_touches_expensive_lane() -> None:
    def expensive_call_that_must_not_run():
        raise AssertionError("expensive lane was called on a right cheap answer")

    result = verifier_escalation.route_with_verifier(
        cheap_call=lambda: "correct",
        verify=lambda _answer: True,
        expensive_call=expensive_call_that_must_not_run,
    )
    assert result.escalated is False
    assert result.value == "correct"


def test_cheap_lane_is_always_called_unconditionally_first() -> None:
    """No difficulty classifier gates execution: the cheap lane runs even when we already
    know, from the test's own setup, that the verifier will reject it."""
    cheap_calls = []
    verifier_escalation.route_with_verifier(
        cheap_call=lambda: cheap_calls.append(1) or "wrong",
        verify=lambda _answer: False,
        expensive_call=lambda: "expensive-answer",
    )
    assert cheap_calls == [1]
