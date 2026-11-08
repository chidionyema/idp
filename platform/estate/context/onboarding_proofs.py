"""Seven-proof onboarding portfolio: a *non-authoritative* evidence contract.

This module belongs to the existing context/admission system (#7794, #7344).
It adds no service, store, gate, permission, approval or autonomous scheduler.
An agent may supply claims; only existing trusted estate verifiers/doors can
authenticate source receipts, graduate DoF or report operational completion.

A fresh session starts with seven NOT_YET_EARNED slots. Missing evidence never
blocks unrelated NOVICE-safe reads, source-only development or permitted repairs.
"""
from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any

VERSION = "genesis.onboarding.proof-portfolio.v1"
KINDS = (
    "continuous_self_improvement",
    "research",
    "optimisation",
    "automation",
    "friction_reduction",
    "reflection",
    "founder_awareness",
)
STATES = frozenset(("NOT_YET_EARNED", "BLIND", "CLAIMED", "NOT_APPLICABLE"))
# Existing #7794 admission stages, *not* a second state machine.
STAGES = frozenset((
    "DISCOVERED", "QUARANTINED", "TOPOLOGY_VERIFIED", "IDENTITY_VERIFIED",
    "READ_ONLY", "MEMORY_VERIFIED", "COLLAB_VERIFIED",
    "CONTINUITY_VERIFIED", "PATCH_READY", "OPERATIONAL",
))
# These are claim fields, not proof that a statement is true.
CLAIM_FIELDS = {
    "continuous_self_improvement": (
        "failure_class_ref", "correction_ref", "regression_ref",
        "independent_adoption_refs", "recurrence_observation_ref",
    ),
    "research": (
        "research_question", "prior_art_ref", "method_ref", "finding_ref",
        "uncertainty_ref", "decision_ref",
    ),
    "optimisation": (
        "objective", "direction", "before", "after", "unit",
        "method_ref", "constraint_refs", "comparison_ref",
    ),
    "automation": (
        "trigger_ref", "executor_ref", "unattended_run_ref",
        "independent_effect_ref", "failure_drill_ref",
    ),
    "friction_reduction": (
        "metric", "before", "after", "unit", "before_n", "after_n",
        "measurement_method_ref", "same_population_ref",
    ),
    "reflection": (
        "expected_ref", "observed_ref", "gap", "cause",
        "correction_or_followup_ref",
    ),
    "founder_awareness": (
        "source_ref", "decision_ref", "supersession_check_ref",
        "relevance", "effect_on_plan_ref",
    ),
}
_PROHIBITED_CLIENT_KEYS = frozenset((
    "verified", "certified", "operational", "authority_granted",
    "promote", "capability_lease", "founder_approval", "founder_signature",
    "credential", "password", "access_token", "api_key", "secret_value",
))
_TOP_FIELDS = frozenset((
    "contract_version", "instruction_id", "mission_id", "session_id",
    "surface_kind", "context_receipt_ref", "admission_stage",
    "requested_at", "proofs",
))
_SLOT_FIELDS = frozenset((
    "state", "details", "evidence_refs", "reason",
    "next_estate_action", "policy_receipt_ref",
))
_CITATION_FIELDS = frozenset(("kind", "ref", "version_or_observed_at"))
_HEX = re.compile(r"^[0-9a-fA-F]{40,64}$")


def fresh_portfolio(
    instruction_id: str,
    mission_id: str,
    session_id: str,
    surface_kind: str,
    context_receipt_ref: str,
    requested_at: str,
) -> dict[str, Any]:
    """A bounded admission view; no agent gets a proof or authority by default."""
    return {
        "contract_version": VERSION,
        "instruction_id": instruction_id,
        "mission_id": mission_id,
        "session_id": session_id,
        "surface_kind": surface_kind,
        "context_receipt_ref": context_receipt_ref,
        "admission_stage": "QUARANTINED",
        "requested_at": requested_at,
        "proofs": {
            k: {"state": "NOT_YET_EARNED", "details": {}, "evidence_refs": []}
            for k in KINDS
        },
    }


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 1024


def _number(value: Any) -> bool:
    return (
        isinstance(value, (float, int)) and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _citations(evidence: Any, prefix: str, errors: list[str]) -> None:
    if not isinstance(evidence, list) or len(evidence) > 32:
        errors.append(f"{prefix}: evidence_refs must be a bounded list")
        return
    for i, row in enumerate(evidence):
        if not isinstance(row, Mapping):
            errors.append(f"{prefix}.evidence_refs[{i}]: expected source reference")
            continue
        if set(row) != _CITATION_FIELDS:
            errors.append(f"{prefix}.evidence_refs[{i}]: source must carry kind/ref/version_or_observed_at")
        elif not all(_text(v) for v in row.values()):
            errors.append(f"{prefix}.evidence_refs[{i}]: empty/oversized source pointer")


def assess_portfolio(packet: Any) -> dict[str, Any]:
    """Validate *shape only*. Never sign evidence, infer independent yield or grant DoF.

    The trusted context broker resolves citations to real immutable receipts.
    The separate trusted admission/action door verifies principal, scope and
    policy, and alone decides whether an effect can run. Client strings in this
    portfolio confer zero authority, even if they resemble a Git SHA or receipt.
    """
    errors: list[str] = []
    states: dict[str, str] = {}
    if not isinstance(packet, Mapping):
        return {
            "verdict": "INVALID", "errors": ["portfolio: expected object"],
            "proof_states": {}, "authority_granted": False,
            "effect_verified": False,
        }
    extra = set(packet) - _TOP_FIELDS
    if extra:
        errors.append(f"portfolio: unknown/untrusted fields {sorted(map(str, extra))}")
    if packet.get("contract_version") != VERSION:
        errors.append("portfolio: unsupported contract_version")
    for field in ("instruction_id", "mission_id", "session_id",
                  "surface_kind", "context_receipt_ref", "requested_at"):
        if not _text(packet.get(field)):
            errors.append(f"portfolio.{field}: required bounded nonempty string")
    if packet.get("admission_stage") not in STAGES:
        errors.append("portfolio.admission_stage: not an existing admission stage")
    proofs = packet.get("proofs")
    if not isinstance(proofs, Mapping):
        errors.append("portfolio.proofs: expected seven kind-keyed slots")
        proofs = {}
    if set(proofs) != set(KINDS):
        errors.append("portfolio.proofs: exactly seven canonical proof kinds required")
    for kind in KINDS:
        slot = proofs.get(kind)
        if not isinstance(slot, Mapping):
            errors.append(f"{kind}: missing evidence slot")
            continue
        unknown = set(slot) - _SLOT_FIELDS
        if unknown:
            errors.append(f"{kind}: untrusted/unknown fields {sorted(map(str, unknown))}")
        state = slot.get("state")
        if state not in STATES:
            errors.append(f"{kind}: forbidden state (agents cannot self-certify VERIFIED)")
            continue
        states[kind] = state
        details = slot.get("details", {})
        if not isinstance(details, Mapping):
            errors.append(f"{kind}: details must be an object")
            details = {}
        if any(field in _PROHIBITED_CLIENT_KEYS for field in details):
            errors.append(f"{kind}: privileged/secret fields are never proof input")
        _citations(slot.get("evidence_refs", []), kind, errors)
        if state == "BLIND":
            if not _text(slot.get("reason")) or not _text(slot.get("next_estate_action")):
                errors.append(f"{kind}: BLIND requires reason and safe estate next action")
        if state == "NOT_APPLICABLE" and not _text(slot.get("policy_receipt_ref")):
            errors.append(f"{kind}: a policy receipt, not agent preference, determines applicability")
        if state != "CLAIMED":
            continue
        if not slot.get("evidence_refs"):
            errors.append(f"{kind}: CLAIMED requires source references for independent verification")
        for field in CLAIM_FIELDS[kind]:
            value = details.get(field)
            if field in ("before", "after", "before_n", "after_n"):
                if not _number(value):
                    errors.append(f"{kind}.{field}: requires numeric measurement")
            elif field.endswith("_refs"):
                if not isinstance(value, list) or not value or not all(_text(v) for v in value):
                    errors.append(f"{kind}.{field}: requires nonempty bounded references")
            elif not _text(value):
                errors.append(f"{kind}.{field}: missing required claim or source pointer")
        if kind == "continuous_self_improvement":
            adopted = details.get("independent_adoption_refs")
            if isinstance(adopted, list) and len(set(map(str, adopted))) < 2:
                errors.append(f"{kind}: cross-session adoption needs two distinct receipt refs")
        if kind == "optimisation" and details.get("direction") not in ("MINIMISE", "MAXIMISE"):
            errors.append("optimisation.direction: expected MINIMISE or MAXIMISE")
        if kind == "friction_reduction":
            for field in ("before_n", "after_n"):
                v = details.get(field)
                if _number(v) and (v < 1 or int(v) != v):
                    errors.append(f"friction_reduction.{field}: positive sample size required")
    # "VALID" would imply trust. Even a perfectly formed claim is unverified,
    # and no absent proof may obstruct source-only/diagnostic work.
    return {
        "verdict": "STRUCTURALLY_VALID_UNVERIFIED" if not errors else "INVALID",
        "errors": errors,
        "proof_states": states,
        "trusted_evidence_resolve_required": [
            kind for kind, state in states.items()
            if state in ("CLAIMED", "NOT_APPLICABLE")
        ],
        "authority_granted": False,
        "effect_verified": False,
    }
