"""Verifier-driven escalation for domains with a real verifier (idp#3525 CP3, ROUTE-03).

"For domains with a real verifier (code/logic/math), escalation SHALL be verifier-driven:
cheapest lane first unconditionally, escalate ONLY on verifier FAIL. No difficulty classifier
gates execution. This makes misroute risk zero by construction (nothing trusted unverified)."

`route_with_verifier()` is the whole rule: it always calls the cheap lane first, unconditionally
-- no pre-check decides whether to try it -- and it calls the expensive lane if and only if the
verifier rejects the cheap answer. There is no third path and no classifier anywhere in this
function; "misroute risk zero by construction" means an unverified cheap answer can never reach
the caller, not that misroutes are rare.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class VerifiedResult:
    escalated: bool
    lane: str
    value: Any


def route_with_verifier(
    cheap_call: Callable[[], Any],
    verify: Callable[[Any], bool],
    expensive_call: Callable[[], Any],
) -> VerifiedResult:
    cheap_answer = cheap_call()
    if verify(cheap_answer):
        return VerifiedResult(escalated=False, lane="cheap", value=cheap_answer)
    return VerifiedResult(escalated=True, lane="expensive", value=expensive_call())
