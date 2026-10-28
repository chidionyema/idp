"""The deterministic method selector (SF-1).

This is a pure function over a validated request. It recommends; it never executes, never
authorises, never writes and never reaches the network. Its job is to answer one question
honestly: *given what we actually know, which method should the estate try next, and what
would have to be true for that answer to be wrong?*

The stages follow the founder's operational contract:

* Stage 0 - policy, authority, data validity and risk gate.
* Stage 1 - classify the problem and list the observations with provenance.
* Stage 2 - filter the catalogue by applicability, prerequisites and limits.
* Stage 3 - rank with a documented baseline heuristic (never a claim of optimality).
* Stage 4 - price the value of gathering more evidence before spending on a method.

Stages 5 and 6 (governed execution, independent verification, learning) are not this
library's business: they belong to the estate's executor, verifier and memory, which
already exist.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .catalog import METHODS, PREREQUISITE_SATISFIERS, MethodSpec
from .contracts import (
    FINGERPRINT_VERSION,
    RISK_ORDER,
    ContractError,
    MethodSelection,
    ProblemRequest,
    validate_request,
)

DECIDER = "method_selector.deterministic.v1"

# Which risk tiers a method of a given risk may be recommended under. A method above the
# tier's allowance is never silently downgraded: it is excluded, with a reason.
RISK_ALLOWANCE: Dict[str, Tuple[str, ...]] = {
    "low": ("low",),
    "medium": ("low", "medium"),
    "high": ("low", "medium", "high"),
    "critical": ("low", "medium", "high", "critical"),
}

# Documented ranking weights. These are a baseline heuristic chosen for legibility and
# determinism, not a learned model and not a proof of optimality.
W_EVIDENCE_FIT = 0.55
W_COST_FIT = 0.25
W_PRIORITY = 0.20


class _Candidate:
    """A method that survived the filters, with the reasons it survived."""

    __slots__ = (
        "spec",
        "score",
        "reason_codes",
        "prerequisites_checked",
        "needs_authorization",
    )

    def __init__(
        self,
        spec: MethodSpec,
        score: float,
        reason_codes: List[str],
        prerequisites_checked: Dict[str, str],
        needs_authorization: bool,
    ) -> None:
        self.spec = spec
        self.score = score
        self.reason_codes = reason_codes
        self.prerequisites_checked = prerequisites_checked
        self.needs_authorization = needs_authorization


def _evidence_kinds(request: ProblemRequest) -> Tuple[str, ...]:
    return tuple(sorted({ref.kind for ref in request.evidence_refs}))


def _satisfied_prerequisites(
    spec: MethodSpec, available: Tuple[str, ...]
) -> Tuple[Dict[str, str], Tuple[str, ...]]:
    """Map every prerequisite to SATISFIED or MISSING. A missing one is never assumed."""
    checked: Dict[str, str] = {}
    missing: List[str] = []
    for prereq in spec.prerequisites:
        satisfiers = PREREQUISITE_SATISFIERS.get(prereq, ())
        if any(kind in satisfiers for kind in available):
            checked[prereq] = "SATISFIED"
        else:
            checked[prereq] = "MISSING"
            missing.append(prereq)
    return checked, tuple(missing)


def _dependency_blocked(
    spec: MethodSpec, unavailable: Tuple[str, ...]
) -> Optional[str]:
    """The unavailable dependency that blocks this method, if any."""
    for dependency in unavailable:
        for scope in spec.tool_scopes:
            if scope == dependency or scope.startswith(dependency + "."):
                return dependency
        if spec.family == dependency:
            return dependency
    return None


def _cost_fit(spec: MethodSpec, max_cost_usd: float) -> float:
    if max_cost_usd <= 0:
        return 0.0
    return max(0.0, 1.0 - (spec.cost_per_attempt_usd / max_cost_usd))


def _score(spec: MethodSpec, evidence_fit: float, max_cost_usd: float) -> float:
    value = (
        W_EVIDENCE_FIT * evidence_fit
        + W_COST_FIT * _cost_fit(spec, max_cost_usd)
        + W_PRIORITY * (spec.baseline_priority / 100.0)
    )
    return round(value, 6)


def _trace_id(fingerprint: str) -> str:
    return "ms-" + fingerprint.split(":", 1)[-1][:16]


def _selection(
    request: ProblemRequest,
    method_id: Optional[str],
    method_version: Optional[str],
    decision: str,
    reason_codes: Tuple[str, ...],
    prerequisites_checked: Dict[str, str],
    expected_evidence: Tuple[str, ...],
    estimated_cost: Optional[float],
    risk: Optional[str],
    alternatives: Tuple[Dict[str, Any], ...],
    abstained: bool = False,
    probe_request: Optional[Dict[str, Any]] = None,
) -> MethodSelection:
    fingerprint = request.fingerprint()
    return MethodSelection(
        method_id=method_id,
        method_version=method_version,
        rank=1 if method_id else 0,
        reason_codes=reason_codes,
        prerequisites_checked=prerequisites_checked,
        expected_evidence=expected_evidence,
        estimated_cost=estimated_cost,
        risk=risk,
        decider=DECIDER,
        policy_decision=decision,
        trace_id=_trace_id(fingerprint),
        fingerprint=fingerprint,
        fingerprint_version=FINGERPRINT_VERSION,
        authority=request.authority,
        abstained=abstained,
        probe_request=probe_request,
        alternatives=alternatives,
        contradictions=request.contradictions,
    )


def _probe_request(
    request: ProblemRequest,
    excluded: List[Tuple[MethodSpec, str, Tuple[str, ...]]],
) -> Optional[Dict[str, Any]]:
    """The cheapest bounded probe that could change the answer.

    A probe is a *request* for evidence, never an invented prerequisite and never an
    action: it names what is missing, bounds its cost by what is left in the budget, and
    asks the estate's governed executor to gather it.
    """
    candidates = [e for e in excluded if e[1] == "MISSING_PREREQUISITE"]
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda item: (len(item[2]), -item[0].baseline_priority, item[0].method_id),
    )
    spec, _reason, missing = ranked[0]
    remaining_attempts = max(0, request.budget.max_attempts - 1)
    if remaining_attempts <= 0:
        return None
    return {
        "probe_id": "probe-" + spec.method_id,
        "method_id": spec.method_id,
        "missing_prerequisites": list(missing),
        "max_attempts": min(remaining_attempts, 1),
        "max_cost_usd": round(
            min(spec.cost_per_attempt_usd, request.budget.max_cost_usd), 4
        ),
        "requires_authorization": spec.requires_authorization,
        "governed_by": "estate.executor",
        "reason_code": "MISSING_PREREQUISITE",
    }


def select(payload: Dict[str, Any]) -> MethodSelection:
    """Select a method for a validated request.

    Raises `ContractError` when the request does not satisfy the contract: an unknown
    schema version or a malformed field is refused, never guessed at.
    """
    request = validate_request(payload)
    return select_request(request)


def select_request(request: ProblemRequest) -> MethodSelection:
    """The selection itself, over an already validated request."""
    available = _evidence_kinds(request)

    # -- Stage 0: policy, authority, data validity, risk ------------------------
    budget = request.budget
    if budget.exhausted or budget.max_attempts <= 0 or budget.max_cost_usd <= 0:
        return _selection(
            request,
            None,
            None,
            "REFUSE",
            ("BUDGET_EXHAUSTED", "NO_METHOD_SCHEDULED"),
            {},
            (),
            None,
            None,
            (),
        )

    if not request.evidence_refs:
        return _selection(
            request,
            None,
            None,
            "ABSTAIN",
            ("NO_EVIDENCE", "PROBE_REQUESTED"),
            {},
            (),
            None,
            None,
            (),
            abstained=True,
            probe_request={
                "probe_id": "probe-evidence",
                "method_id": None,
                "missing_prerequisites": ["observed_evidence"],
                "max_attempts": 1,
                "max_cost_usd": round(min(budget.max_cost_usd, 0.05), 4),
                "requires_authorization": False,
                "governed_by": "estate.executor",
                "reason_code": "NO_EVIDENCE",
            },
        )

    fresh = [ref for ref in request.evidence_refs if ref.freshness == "fresh"]
    if not fresh:
        return _selection(
            request,
            None,
            None,
            "ABSTAIN",
            ("STALE_EVIDENCE", "PROBE_REQUESTED"),
            {},
            (),
            None,
            None,
            (),
            abstained=True,
            probe_request={
                "probe_id": "probe-fresh-evidence",
                "method_id": None,
                "missing_prerequisites": ["fresh_evidence"],
                "max_attempts": 1,
                "max_cost_usd": round(min(budget.max_cost_usd, 0.05), 4),
                "requires_authorization": False,
                "governed_by": "estate.executor",
                "reason_code": "STALE_EVIDENCE",
            },
        )

    # -- Stages 1 and 2: classify, filter ---------------------------------------
    eligible: List[_Candidate] = []
    excluded: List[Tuple[MethodSpec, str, Tuple[str, ...]]] = []
    alternatives: List[Dict[str, Any]] = []
    tier = RISK_ORDER[request.risk_tier]

    for spec in METHODS:
        if request.kind not in spec.problem_kinds:
            continue
        if spec.disqualifying_kinds and any(
            kind in spec.disqualifying_kinds for kind in available
        ):
            excluded.append((spec, "ANTI_PATTERN", ()))
            alternatives.append(
                {
                    "method_id": spec.method_id,
                    "eligible": False,
                    "reason": "ANTI_PATTERN",
                }
            )
            continue
        dependency = _dependency_blocked(spec, request.unavailable_dependencies)
        if dependency is not None:
            excluded.append((spec, "DEPENDENCY_UNAVAILABLE", ()))
            alternatives.append(
                {
                    "method_id": spec.method_id,
                    "eligible": False,
                    "reason": "DEPENDENCY_UNAVAILABLE:" + dependency,
                }
            )
            continue
        checked, missing = _satisfied_prerequisites(spec, available)
        if missing:
            excluded.append((spec, "MISSING_PREREQUISITE", missing))
            alternatives.append(
                {
                    "method_id": spec.method_id,
                    "eligible": False,
                    "reason": "MISSING_PREREQUISITE",
                    "missing_prerequisites": list(missing),
                }
            )
            continue
        if spec.typical_attempts > budget.max_attempts:
            excluded.append((spec, "ATTEMPT_LIMIT", ()))
            alternatives.append(
                {
                    "method_id": spec.method_id,
                    "eligible": False,
                    "reason": "ATTEMPT_LIMIT",
                }
            )
            continue
        if spec.cost_per_attempt_usd > budget.max_cost_usd:
            excluded.append((spec, "COST_LIMIT", ()))
            alternatives.append(
                {"method_id": spec.method_id, "eligible": False, "reason": "COST_LIMIT"}
            )
            continue
        if RISK_ORDER[spec.risk] > tier:
            excluded.append((spec, "RISK_ABOVE_TIER", ()))
            alternatives.append(
                {
                    "method_id": spec.method_id,
                    "eligible": False,
                    "reason": "RISK_ABOVE_TIER",
                }
            )
            continue
        needs_authorization = False
        if spec.requires_authorization:
            authorized = (
                spec.method_id in request.authorized_actions
                or "*" in request.authorized_actions
            )
            if not authorized:
                excluded.append((spec, "AUTHORIZATION_REQUIRED", ()))
                alternatives.append(
                    {
                        "method_id": spec.method_id,
                        "eligible": False,
                        "reason": "AUTHORIZATION_REQUIRED",
                    }
                )
                continue
            needs_authorization = True
        prereq_count = len(spec.prerequisites) or 1
        evidence_fit = (prereq_count - len(missing)) / float(prereq_count)
        eligible.append(
            _Candidate(
                spec=spec,
                score=_score(spec, evidence_fit, budget.max_cost_usd),
                reason_codes=["KIND_MATCH", "PREREQUISITES_SATISFIED"],
                prerequisites_checked=checked,
                needs_authorization=needs_authorization,
            )
        )

    # -- Stage 3: rank by the documented heuristic ------------------------------
    eligible.sort(key=lambda c: (-c.score, c.spec.method_id))
    for index, candidate in enumerate(eligible, start=1):
        alternatives.append(
            {
                "method_id": candidate.spec.method_id,
                "eligible": True,
                "rank": index,
                "score": candidate.score,
                "reason_codes": list(candidate.reason_codes),
            }
        )
    alternatives.sort(key=lambda row: (not row.get("eligible"), row["method_id"]))

    if not eligible:
        authorization_blocked = any(
            reason == "AUTHORIZATION_REQUIRED" for _spec, reason, _missing in excluded
        )
        dependency_blocked = any(
            reason == "DEPENDENCY_UNAVAILABLE" for _spec, reason, _missing in excluded
        )
        reasons: List[str] = []
        if authorization_blocked:
            reasons.append("AUTHORIZATION_REQUIRED")
        if dependency_blocked:
            reasons.append("DEPENDENCY_UNAVAILABLE")
        reasons.append("NO_ELIGIBLE_METHOD")
        # A probe is pointless while a dependency is down or a human has not authorised
        # anything: the probe would need exactly what is missing. Those cases refuse.
        probe = None
        if not authorization_blocked and not dependency_blocked:
            probe = _probe_request(request, excluded)
        if probe is not None:
            reasons.append("PROBE_REQUESTED")
            return _selection(
                request,
                None,
                None,
                "ABSTAIN",
                tuple(reasons),
                {},
                (),
                None,
                None,
                tuple(alternatives),
                abstained=True,
                probe_request=probe,
            )
        return _selection(
            request,
            None,
            None,
            "REFUSE",
            tuple(reasons),
            {},
            (),
            None,
            None,
            tuple(alternatives),
        )

    best = eligible[0]
    reason_codes = list(best.reason_codes) + ["RANKED_BY_DOCUMENTED_HEURISTIC"]
    reason_codes.append("RECOMMENDATION_ONLY")
    decision = "ALLOW"
    if best.needs_authorization:
        decision = "REQUIRE_AUTHORIZATION"
        reason_codes.append("AUTHORIZATION_REQUIRED")
    if request.contradictions:
        decision = "REASSESS"
        reason_codes.append("CONTRADICTORY_OBSERVATIONS")

    return _selection(
        request,
        best.spec.method_id,
        best.spec.version,
        decision,
        tuple(reason_codes),
        dict(best.prerequisites_checked),
        best.spec.expected_evidence,
        best.spec.cost_per_attempt_usd,
        best.spec.risk,
        tuple(alternatives),
    )


def select_safe(payload: Dict[str, Any]) -> MethodSelection:
    """Selection that never raises: a malformed request becomes a refusal.

    The refusal names the reason code and carries no method, so a caller that pipes
    nonsense into the selector gets a decision it can log rather than a traceback.
    """
    try:
        return select(payload)
    except ContractError as error:
        fingerprint = "sha256:" + "0" * 64
        return MethodSelection(
            method_id=None,
            method_version=None,
            rank=0,
            reason_codes=(error.reason_code, "CONTRACT_REJECTED"),
            prerequisites_checked={},
            expected_evidence=(),
            estimated_cost=None,
            risk=None,
            decider=DECIDER,
            policy_decision="REFUSE",
            trace_id=_trace_id(fingerprint),
            fingerprint=fingerprint,
            fingerprint_version=FINGERPRINT_VERSION,
            authority="",
            abstained=False,
        )


__all__ = ["DECIDER", "RISK_ALLOWANCE", "select", "select_request", "select_safe"]
