"""Disagreement-driven escalation for NL-judgment domains with no verifier (idp#3525 CP3,
ROUTE-04).

"For NL-judgment domains with no verifier, escalation SHALL be signaled by disagreement between
two cheap independent models. No classifier is built for these domains."

`route_with_disagreement()` always calls both cheap models -- there is no classifier deciding
whether to bother -- and escalates iff they disagree, by the caller's own `agree` predicate
(default: exact equality; a caller with a similarity metric passes one in). Agreement is the
only signal; there is nothing else in this function that could gate escalation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class DisagreementResult:
    escalated: bool
    lane: str
    value: Any
    model_a_answer: Any
    model_b_answer: Any


def route_with_disagreement(
    model_a_call: Callable[[], Any],
    model_b_call: Callable[[], Any],
    escalate_call: Callable[[], Any],
    agree: Callable[[Any, Any], bool] = lambda a, b: a == b,
) -> DisagreementResult:
    answer_a = model_a_call()
    answer_b = model_b_call()
    if agree(answer_a, answer_b):
        return DisagreementResult(
            escalated=False,
            lane="cheap",
            value=answer_a,
            model_a_answer=answer_a,
            model_b_answer=answer_b,
        )
    return DisagreementResult(
        escalated=True,
        lane="expensive",
        value=escalate_call(),
        model_a_answer=answer_a,
        model_b_answer=answer_b,
    )
