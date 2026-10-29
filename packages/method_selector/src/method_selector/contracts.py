"""Typed contracts for the estate's adaptive problem-solving method selector (SF-1).

This module is pure data and pure validation. It holds no authority, performs no IO and
executes nothing: a selection is a recommendation that the estate's existing decision layer
may accept, refuse or override (OPERATIONAL_SPEC.md v0.1, "Integration topology", step 2).

Everything here is deterministic. The same request bytes produce the same fingerprint, the
same selection and the same trace id, which is what makes the selector safe to run in shadow
and what makes a replay provably free of a second side effect.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "method_selector.request.v1"
SELECTION_VERSION = "method_selector.selection.v1"
FINGERPRINT_VERSION = "fp.v1"

PROBLEM_KINDS: Tuple[str, ...] = (
    "regression",
    "incident",
    "formal",
    "performance",
    "architecture",
    "optimisation",
    "uncertain",
    "strategy",
    "novel",
    "adaptive",
)

RISK_TIERS: Tuple[str, ...] = ("low", "medium", "high", "critical")
RISK_ORDER: Dict[str, int] = {"low": 0, "medium": 1, "high": 2, "critical": 3}

AUTHORITIES: Tuple[str, ...] = ("developer", "maintainer", "operator", "sre", "founder")

FRESHNESS: Tuple[str, ...] = ("fresh", "stale", "unknown")

POLICY_DECISIONS: Tuple[str, ...] = (
    "ALLOW",
    "REQUIRE_AUTHORIZATION",
    "REASSESS",
    "ABSTAIN",
    "REFUSE",
)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


class ContractError(ValueError):
    """A request that does not satisfy the contract. Never a guess, never a default."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {"reason_code": self.reason_code, "message": self.message}


@dataclass(frozen=True)
class EvidenceRef:
    """One typed observation the selector is allowed to reason from.

    The shape is deliberately the context substrate's source shape (source type, immutable
    revision or observation time, freshness, verification) so that `estate_context_resolve_v1`
    can feed the selector later without a second evidence vocabulary.
    """

    source_id: str
    source_type: str
    kind: str
    revision: Optional[str] = None
    observed_at: Optional[str] = None
    freshness: str = "unknown"
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "kind": self.kind,
            "revision": self.revision,
            "observed_at": self.observed_at,
            "freshness": self.freshness,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class Budget:
    """What the caller is willing to spend. Exhausted budget schedules nothing."""

    max_attempts: int = 1
    max_cost_usd: float = 1.0
    max_wall_seconds: int = 900
    exhausted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_attempts": self.max_attempts,
            "max_cost_usd": self.max_cost_usd,
            "max_wall_seconds": self.max_wall_seconds,
            "exhausted": self.exhausted,
        }


@dataclass(frozen=True)
class ProblemRequest:
    """The input contract, versioned. Every field is checked; nothing is invented."""

    schema_version: str
    problem_id: str
    kind: str
    source_revision: str
    evidence_refs: Tuple[EvidenceRef, ...]
    risk_tier: str
    budget: Budget
    uncertainty: float
    authority: str
    deadline: str
    idempotency_key: str
    provenance: Dict[str, Any]
    contradictions: Tuple[str, ...] = ()
    unavailable_dependencies: Tuple[str, ...] = ()
    authorized_actions: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "problem_id": self.problem_id,
            "kind": self.kind,
            "source_revision": self.source_revision,
            "evidence_refs": [e.to_dict() for e in self.evidence_refs],
            "risk_tier": self.risk_tier,
            "budget": self.budget.to_dict(),
            "uncertainty": self.uncertainty,
            "authority": self.authority,
            "deadline": self.deadline,
            "idempotency_key": self.idempotency_key,
            "provenance": dict(self.provenance),
            "contradictions": list(self.contradictions),
            "unavailable_dependencies": list(self.unavailable_dependencies),
            "authorized_actions": list(self.authorized_actions),
        }

    def fingerprint(self) -> str:
        """A stable hash over the decision-relevant content of the request.

        `deadline` and `idempotency_key` are excluded on purpose: they describe *when* the
        caller asked and *which* replay it is, not *what* the problem is. Two requests that
        differ only in those two fields must select the same method, or the idempotency
        guarantee in the spec is a lie.
        """
        material = self.to_dict()
        material.pop("deadline", None)
        material.pop("idempotency_key", None)
        material["fingerprint_version"] = FINGERPRINT_VERSION
        blob = json.dumps(material, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MethodSelection:
    """The output contract. A recommendation, never an authorization."""

    method_id: Optional[str]
    method_version: Optional[str]
    rank: int
    reason_codes: Tuple[str, ...]
    prerequisites_checked: Dict[str, str]
    expected_evidence: Tuple[str, ...]
    estimated_cost: Optional[float]
    risk: Optional[str]
    decider: str
    policy_decision: str
    trace_id: str
    fingerprint: str
    fingerprint_version: str = FINGERPRINT_VERSION
    selection_version: str = SELECTION_VERSION
    authority: str = ""
    abstained: bool = False
    probe_request: Optional[Dict[str, Any]] = None
    alternatives: Tuple[Dict[str, Any], ...] = ()
    contradictions: Tuple[str, ...] = ()
    evaluation_status: str = "UNVERIFIED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.selection_version,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "rank": self.rank,
            "reason_codes": list(self.reason_codes),
            "prerequisites_checked": dict(self.prerequisites_checked),
            "expected_evidence": list(self.expected_evidence),
            "estimated_cost": self.estimated_cost,
            "risk": self.risk,
            "decider": self.decider,
            "policy_decision": self.policy_decision,
            "trace_id": self.trace_id,
            "fingerprint": self.fingerprint,
            "fingerprint_version": self.fingerprint_version,
            "authority": self.authority,
            "abstained": self.abstained,
            "probe_request": self.probe_request,
            "alternatives": [dict(a) for a in self.alternatives],
            "contradictions": list(self.contradictions),
            "evaluation_status": self.evaluation_status,
        }


@dataclass(frozen=True)
class SelectionOutcome:
    """The outcome contract (SF-1 defines it; SF-2/SF-5 fill it in).

    `verdict` is the independent verifier's word, never the agent's self-report, and
    `switch_reason` is what makes a method change explainable after the fact.
    """

    attempt_id: str
    artifact_refs: Tuple[str, ...]
    verifier: str
    verdict: str
    counterexamples: Tuple[str, ...]
    actual_cost: Optional[float]
    elapsed: Optional[float]
    switch_reason: Optional[str]
    next_fingerprint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "artifact_refs": list(self.artifact_refs),
            "verifier": self.verifier,
            "verdict": self.verdict,
            "counterexamples": list(self.counterexamples),
            "actual_cost": self.actual_cost,
            "elapsed": self.elapsed,
            "switch_reason": self.switch_reason,
            "next_fingerprint": self.next_fingerprint,
        }


def assess_outcome(outcome: SelectionOutcome) -> str:
    """The verdict the estate may record for an outcome.

    An outcome with no independent verifier stays `UNVERIFIED`, whatever the agent said
    about it: no agent self-certifies its own outcome (hard invariant 4).
    """
    if not outcome.verifier:
        return "UNVERIFIED"
    return outcome.verdict


def _require(condition: bool, reason_code: str, message: str) -> None:
    if not condition:
        raise ContractError(reason_code, message)


def _string(payload: Dict[str, Any], key: str, reason_code: str) -> str:
    value = payload.get(key)
    _require(
        isinstance(value, str) and bool(value),
        reason_code,
        "%s must be a non-empty string" % key,
    )
    return value


def _identifier(payload: Dict[str, Any], key: str, reason_code: str) -> str:
    value = _string(payload, key, reason_code)
    _require(
        bool(_ID_RE.match(value)),
        reason_code,
        "%s must match %s" % (key, _ID_RE.pattern),
    )
    return value


def _number_in_range(
    payload: Dict[str, Any],
    key: str,
    low: float,
    high: float,
    reason_code: str,
) -> float:
    value = payload.get(key)
    _require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        reason_code,
        "%s must be a number" % key,
    )
    _require(
        low <= float(value) <= high,
        reason_code,
        "%s must be between %s and %s" % (key, low, high),
    )
    return float(value)


def _int_in_range(
    payload: Dict[str, Any],
    key: str,
    low: int,
    high: int,
    reason_code: str,
) -> int:
    value = payload.get(key)
    _require(
        isinstance(value, int) and not isinstance(value, bool),
        reason_code,
        "%s must be an integer" % key,
    )
    _require(
        low <= value <= high,
        reason_code,
        "%s must be between %s and %s" % (key, low, high),
    )
    return value


def _string_tuple(
    payload: Dict[str, Any], key: str, reason_code: str
) -> Tuple[str, ...]:
    value = payload.get(key, [])
    _require(isinstance(value, (list, tuple)), reason_code, "%s must be a list" % key)
    for item in value:
        _require(
            isinstance(item, str) and bool(item),
            reason_code,
            "%s must hold non-empty strings" % key,
        )
    return tuple(value)


def validate_request(payload: Dict[str, Any]) -> ProblemRequest:
    """Validate a request payload. Unknown versions and malformed fields are refused.

    Nothing here guesses a default: an unknown schema version is a refusal, not an
    invitation to read the fields you happen to recognise.
    """
    _require(
        isinstance(payload, dict), "MALFORMED_REQUEST", "request must be an object"
    )
    version = payload.get("schema_version")
    _require(
        version == SCHEMA_VERSION,
        "UNKNOWN_SCHEMA_VERSION",
        "schema_version must be %s, got %r" % (SCHEMA_VERSION, version),
    )

    problem_id = _identifier(payload, "problem_id", "MALFORMED_REQUEST")
    kind = _string(payload, "kind", "MALFORMED_REQUEST")
    _require(
        kind in PROBLEM_KINDS,
        "UNKNOWN_PROBLEM_KIND",
        "kind must be one of %s" % (", ".join(PROBLEM_KINDS)),
    )
    source_revision = _string(payload, "source_revision", "MALFORMED_REQUEST")
    risk_tier = _string(payload, "risk_tier", "MALFORMED_REQUEST")
    _require(
        risk_tier in RISK_TIERS,
        "UNKNOWN_RISK_TIER",
        "risk_tier must be one of %s" % (", ".join(RISK_TIERS)),
    )
    authority = _string(payload, "authority", "MALFORMED_REQUEST")
    _require(
        authority in AUTHORITIES,
        "UNKNOWN_AUTHORITY",
        "authority must be one of %s" % (", ".join(AUTHORITIES)),
    )
    deadline = _string(payload, "deadline", "MALFORMED_REQUEST")
    idempotency_key = _identifier(payload, "idempotency_key", "MALFORMED_REQUEST")
    uncertainty = _number_in_range(
        payload, "uncertainty", 0.0, 1.0, "OUT_OF_RANGE_UNCERTAINTY"
    )

    raw_evidence = payload.get("evidence_refs", [])
    _require(
        isinstance(raw_evidence, (list, tuple)),
        "MALFORMED_EVIDENCE",
        "evidence_refs must be a list",
    )
    evidence: List[EvidenceRef] = []
    for item in raw_evidence:
        _require(
            isinstance(item, dict),
            "MALFORMED_EVIDENCE",
            "each evidence ref must be an object",
        )
        freshness = item.get("freshness", "unknown")
        _require(
            freshness in FRESHNESS,
            "MALFORMED_EVIDENCE",
            "freshness must be one of %s" % (", ".join(FRESHNESS)),
        )
        verified = item.get("verified", False)
        _require(
            isinstance(verified, bool),
            "MALFORMED_EVIDENCE",
            "verified must be a boolean",
        )
        evidence.append(
            EvidenceRef(
                source_id=_identifier(item, "source_id", "MALFORMED_EVIDENCE"),
                source_type=_string(item, "source_type", "MALFORMED_EVIDENCE"),
                kind=_string(item, "kind", "MALFORMED_EVIDENCE"),
                revision=item.get("revision"),
                observed_at=item.get("observed_at"),
                freshness=freshness,
                verified=verified,
            )
        )

    raw_budget = payload.get("budget")
    _require(
        isinstance(raw_budget, dict), "MALFORMED_BUDGET", "budget must be an object"
    )
    exhausted = raw_budget.get("exhausted", False)
    _require(
        isinstance(exhausted, bool),
        "MALFORMED_BUDGET",
        "budget.exhausted must be a boolean",
    )
    budget = Budget(
        max_attempts=_int_in_range(
            raw_budget, "max_attempts", 0, 1000, "OUT_OF_RANGE_BUDGET"
        ),
        max_cost_usd=_number_in_range(
            raw_budget, "max_cost_usd", 0.0, 100000.0, "OUT_OF_RANGE_BUDGET"
        ),
        max_wall_seconds=_int_in_range(
            raw_budget, "max_wall_seconds", 0, 86400, "OUT_OF_RANGE_BUDGET"
        ),
        exhausted=exhausted,
    )

    provenance = payload.get("provenance", {})
    _require(
        isinstance(provenance, dict),
        "MALFORMED_PROVENANCE",
        "provenance must be an object",
    )

    return ProblemRequest(
        schema_version=version,
        problem_id=problem_id,
        kind=kind,
        source_revision=source_revision,
        evidence_refs=tuple(evidence),
        risk_tier=risk_tier,
        budget=budget,
        uncertainty=uncertainty,
        authority=authority,
        deadline=deadline,
        idempotency_key=idempotency_key,
        provenance=provenance,
        contradictions=_string_tuple(payload, "contradictions", "MALFORMED_REQUEST"),
        unavailable_dependencies=_string_tuple(
            payload, "unavailable_dependencies", "MALFORMED_REQUEST"
        ),
        authorized_actions=_string_tuple(
            payload, "authorized_actions", "MALFORMED_REQUEST"
        ),
    )


__all__ = [
    "AUTHORITIES",
    "Budget",
    "ContractError",
    "EvidenceRef",
    "FINGERPRINT_VERSION",
    "FRESHNESS",
    "MethodSelection",
    "POLICY_DECISIONS",
    "PROBLEM_KINDS",
    "ProblemRequest",
    "RISK_ORDER",
    "RISK_TIERS",
    "SCHEMA_VERSION",
    "SELECTION_VERSION",
    "SelectionOutcome",
    "assess_outcome",
    "validate_request",
]
