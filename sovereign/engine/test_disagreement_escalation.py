"""Tests for sovereign/engine/disagreement_escalation.py (idp#3525 CP3, ROUTE-04).

ACCEPT, verbatim: "seeded disagreement corpus -> escalate rate tracks disagreement;
agreement cases never escalate."
"""

from __future__ import annotations

from sovereign.engine import disagreement_escalation

# A seeded corpus: (model_a_answer, model_b_answer, seeded_as_disagreement).
SEEDED_CORPUS = [
    ("positive", "positive", False),
    ("negative", "negative", False),
    ("positive", "negative", True),
    ("neutral", "positive", True),
    ("negative", "neutral", True),
    ("neutral", "neutral", False),
]


def test_escalate_rate_tracks_seeded_disagreement_rate() -> None:
    escalations = 0
    for answer_a, answer_b, seeded_disagreement in SEEDED_CORPUS:
        result = disagreement_escalation.route_with_disagreement(
            model_a_call=lambda a=answer_a: a,
            model_b_call=lambda b=answer_b: b,
            escalate_call=lambda: "escalated-answer",
        )
        assert result.escalated is seeded_disagreement
        escalations += result.escalated

    seeded_disagreements = sum(1 for _, _, d in SEEDED_CORPUS if d)
    assert escalations == seeded_disagreements


def test_agreement_cases_never_escalate_and_never_touch_expensive_lane() -> None:
    def escalate_call_that_must_not_run():
        raise AssertionError("escalate lane was called on an agreement case")

    for answer_a, answer_b, seeded_disagreement in SEEDED_CORPUS:
        if seeded_disagreement:
            continue
        result = disagreement_escalation.route_with_disagreement(
            model_a_call=lambda a=answer_a: a,
            model_b_call=lambda b=answer_b: b,
            escalate_call=escalate_call_that_must_not_run,
        )
        assert result.escalated is False
        assert result.value == answer_a


def test_no_classifier_gates_execution_both_models_always_called() -> None:
    calls = {"a": 0, "b": 0}

    def model_a():
        calls["a"] += 1
        return "x"

    def model_b():
        calls["b"] += 1
        return "y"

    disagreement_escalation.route_with_disagreement(
        model_a, model_b, escalate_call=lambda: "z"
    )
    assert calls == {"a": 1, "b": 1}


def test_custom_agree_predicate_is_honored() -> None:
    result = disagreement_escalation.route_with_disagreement(
        model_a_call=lambda: "  Positive ",
        model_b_call=lambda: "positive",
        escalate_call=lambda: "unreachable",
        agree=lambda a, b: a.strip().lower() == b.strip().lower(),
    )
    assert result.escalated is False
