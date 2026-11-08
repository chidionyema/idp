"""FLOW micro-decision admission PRE-FLIGHT (ADR 0044, #7771 / #7342).

This is a PURE, deliberately non-authoritative classification function. It is
not a new decision engine, approval service, task queue or grant of privileges.
It makes "trivial" actions visible to existing policy before they cause harm.
All fields MUST be furnished from the authenticated gateway; this pure function
CANNOT verify attestations, tenant identity, receipts or effect. Only the
already trusted runtime action gate can admit or execute.
"""
from __future__ import annotations

from typing import Any

VERSION = "flow.micro-decision.v1"

# The hard-coded catalogue is the stable ACTION SHAPE, not a priority ranking.
# Update under the existing constitution/ADR 0044, not by model inference.
BASE_IMPACT = {
    "observe": 0,
    "read": 0,
    "format": 1,
    "test": 1,
    "edit_candidate": 1,
    "create_issue": 2,
    "comment_issue": 2,
    "send_message": 2,
    "commit_candidate": 2,
    "change_dependency": 3,
    "merge": 3,
    "deploy": 3,
    "change_law": 3,
    "grant_permission": 3,
    "delete": 3,
    "spend": 3,
    "broadcast_directive": 3,
}
ALL_FIELDS = {
    "schema", "action", "plan_ref", "plan_sha", "source_sha",
    "principal_ref", "permission_ref", "authority_epoch", "claim_ref",
    "expected_effect", "verification_ref", "idempotency_key",
    "reversible", "rollback_ref", "protected_path", "critical_dependency",
    "cross_tenant", "sensitive_data", "production_effect",
    "historical_topology", "requires_local_infrastructure",
    "incremental_hosting_gbp", "existing_fcr_class", "fcr_correction_ref",
    "evidence_fresh", "scope_verified", "budget_verified",
    "independent_review_ref", "irreversible_authority_ref",
}
REQUIRED_BASE = (
    "plan_ref", "plan_sha", "source_sha", "principal_ref", "permission_ref",
    "claim_ref", "expected_effect", "verification_ref", "idempotency_key",
)
BOOLEAN_FIELDS = (
    "reversible", "protected_path", "critical_dependency", "cross_tenant",
    "sensitive_data", "production_effect", "historical_topology",
    "requires_local_infrastructure", "evidence_fresh",
    "scope_verified", "budget_verified",
)


def preflight(record: Any) -> dict:
    """Conservative decision, never an execution approval.

    An existing vetted plan may pre-authorise many low-risk micro-actions:
    a per-action interactive ceremony is NOT required. The immutable plan
    identity is still present for subsequent audit/replay. Unknown becomes
    OBSERVE, not low risk. Small change + large dependency = high risk.
    """
    out = {
        "schema": VERSION, "state": "NEEDS_EVIDENCE",
        "impact": "UNKNOWN", "release_authority": False,
        "next_action": "RESOLVE_TRUSTED_CONTEXT", "reasons": [],
        "execution": "EXISTING_TRUSTED_ACTION_DOOR_ONLY",
    }
    if not isinstance(record, dict):
        out["reasons"].append("missing typed decision context")
        return out
    unexpected = set(record) - ALL_FIELDS
    if unexpected:
        out["state"] = "REFUSE"
        out["reasons"].append("unknown input fields: " + ", ".join(sorted(unexpected)))
        return out
    if record.get("schema") != VERSION or record.get("action") not in BASE_IMPACT:
        out["state"] = "REFUSE"
        out["reasons"].append("unsupported schema/action type")
        return out
    # Missing a risk fact is not an assumption that the action is safe.
    for field in BOOLEAN_FIELDS:
        if type(record.get(field)) is not bool:
            out["reasons"].append("missing/invalid fact " + field)
    if type(record.get("authority_epoch")) is not int or record.get("authority_epoch", 0) < 1:
        out["reasons"].append("missing authenticated lease epoch")
    for field in REQUIRED_BASE:
        if not isinstance(record.get(field), str) or not record[field].strip():
            out["reasons"].append("missing source-bound " + field)
    price = record.get("incremental_hosting_gbp")
    if type(price) not in (float, int) or price != 0:
        # Includes NaN and positive/negative/unknown prices.
        out["state"] = "REFUSE"
        out["reasons"].append("unapproved/nonzero incremental hosting")
        return out
    if record.get("historical_topology") is True or record.get("requires_local_infrastructure") is True:
        out["state"] = "REFUSE"
        out["reasons"].append("OKE/historical topology or founder-local infrastructure is retired")
        return out
    if out["reasons"]:
        return out

    impact = BASE_IMPACT[record["action"]]
    # Risk propagates through the target/dependent system. No agent can label
    # a privileged action low-risk by naming it a formatting change.
    if record["protected_path"] or record["production_effect"] or record["cross_tenant"]:
        impact = max(impact, 3)
    elif record["critical_dependency"] or record["sensitive_data"]:
        impact = max(impact, 2)
    out["impact"] = ("D0_READ", "D1_BOUNDED", "D2_CROSS_BOUNDARY", "D3_CRITICAL")[impact]

    if not record["scope_verified"] or not record["evidence_fresh"] or not record["budget_verified"]:
        out["reasons"].append("missing verified scope, current evidence or bounded budget")
        return out
    known = record.get("existing_fcr_class")
    if known is not None:
        if not isinstance(known, str) or not known.strip():
            out["reasons"].append("invalid FCR class")
            return out
        if not isinstance(record.get("fcr_correction_ref"), str) or not record["fcr_correction_ref"].strip():
            out["state"] = "PREVENTION_GAP"
            out["next_action"] = "QUERY_EXISTING_FCR_CORRECTION_BEFORE_ACTION"
            out["reasons"].append("known class without inherited corrective protocol")
            return out

    if not record["reversible"] and impact > 0 and not (isinstance(record.get("irreversible_authority_ref"), str) and record["irreversible_authority_ref"].strip()):
        out["state"] = "REQUIRES_TRUSTED_DECISION"
        out["next_action"] = "EXISTING_INDEPENDENT_IRREVERSIBILITY_AUTHORITY"
        out["reasons"].append("irreversible effect requires independently bound authority")
        return out
    if record["reversible"] and impact > 0 and not (isinstance(record.get("rollback_ref"), str) and record["rollback_ref"].strip()):
        out["state"] = "NEEDS_EVIDENCE"
        out["next_action"] = "RESOLVE_TRUSTED_ROLLBACK"
        out["reasons"].append("no rollback locator for proposed reversible effect")
        return out
    if impact >= 2 and not (isinstance(record.get("independent_review_ref"), str) and record["independent_review_ref"].strip()):
        out["state"] = "REQUIRES_TRUSTED_DECISION"
        out["next_action"] = "EXISTING_INDEPENDENT_REVIEW"
        out["reasons"].append("cross-boundary/critical action requires external review")
        return out

    # The runtime must still verify evidence/authorization, not merely the
    # caller's strings or a model-selected threshold.
    out["state"] = "CANDIDATE_FOR_EXISTING_GUARD"
    out["next_action"] = (
        "DETERMINISTIC_PLAN_STEP" if impact < 2 else
        "INDEPENDENT_REVIEW_AND_BOUND_ACTION"
    )
    return out
