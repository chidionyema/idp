"""Genesis Anti-Entropy Doctrine: one pure failure-class prevention decider.

The trusted FCR/independent verifier owns identity, exact receipts and real
effects. This module NEVER grants authority or marks an incident operational.
Its public banner is reused by onboarding and live fleet-client reminders;
the banner is not evidence of prevention.
"""
from __future__ import annotations

from typing import Any

VERSION = "entropy.prevention.v1"
MOTTO = (
    "HOW TO MANAGE ENTROPY: eliminate a known failure class at its root "
    "cause the FIRST time. Reproduce it, prevent it across every affected "
    "surface, independently prove the correction, and make all agents "
    "inherit it. Recurrence is PREVENTION_GAP, not a fresh investigation."
)
REMINDER_SECONDS = 600  # same cadence as FLOW meaningful-progress watch

REQUIRED = (
    "class_id", "root_cause", "fcr_ref", "control_version",
    "failing_reproducer_ref", "passing_regression_ref",
    "independent_witness_ref", "independent_witness_id", "implementer_id",
    "real_effect_ref", "scope_inventory", "scope_adoption",
    "cross_agent_probe_ref", "residual_risk",
)


def doctrine_banner(boundary: str = "SESSION_START") -> str:
    """An unprivileged notice; NEVER a founder instruction or an effect receipt."""
    allowed = {
        "SESSION_START", "CONTEXT_REFRESH", "FLOW_TRANSITION",
        "GREENLANE", "DOF_LEASE", "RECOVERY", "PEER_WATCH", "INBOX",
    }
    scope = boundary if boundary in allowed else "CONTEXT_REFRESH"
    return f"[GENESIS DOF / FLOW / GREENLANE | {scope} | {VERSION}] {MOTTO}"


def evaluate_prevention(record: Any) -> dict:
    """Conservative, content-only preflight; external FCR verifies all evidence.

    Allowed results: PREVENTION_GAP / INVESTIGATE_ONCE /
    CANDIDATE_READY_FOR_INDEPENDENT_VERIFICATION. A dict cannot certify its
    own signatures, runtime effects or complete scope.
    """
    result = {
        "protocol": VERSION,
        "state": "PREVENTION_GAP",
        "release_authority": False,
        "independently_verified": False,
        "missing": [],
        "next_action": "",
    }
    if not isinstance(record, dict):
        result["missing"] = ["typed record"]
        result["next_action"] = "CLASSIFY_WITH_EXISTING_FCR"
        return result
    if type(record.get("known_class")) is not bool:
        result["state"] = "BLIND"
        result["missing"] = ["trusted known_class classification"]
        result["next_action"] = "QUERY_EXISTING_FCR_FOR_CLASS"
        return result
    if record["known_class"] is False:
        result["state"] = "INVESTIGATE_ONCE"
        result["next_action"] = "REPRODUCE_CLASS_AND_REGISTER_FCR"
        return result
    if type(record.get("recurrence_observed")) is not bool:
        result["state"] = "BLIND"
        result["missing"] = ["independently observed recurrence status"]
        result["next_action"] = "QUERY_EXISTING_FCR_FOR_RECURRENCE"
        return result
    if record["recurrence_observed"] is True:
        result["missing"] = ["previous prevention control failed in real operation"]
        result["next_action"] = "OPEN_PREVENTION_GAP_AND_SELECT_NEW_HYPOTHESIS"
        return result

    missing = []
    for field in REQUIRED:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            # The two inventory arrays are checked separately below.
            if field not in ("scope_inventory", "scope_adoption"):
                missing.append(field)
    scope = record.get("scope_inventory")
    adoption = record.get("scope_adoption")
    if not isinstance(scope, list) or not scope or any(not isinstance(x, str) or not x for x in scope):
        missing.append("scope_inventory")
    if not isinstance(adoption, list) or any(not isinstance(x, str) or not x for x in adoption):
        missing.append("scope_adoption")
    if (isinstance(scope, list) and isinstance(adoption, list)
            and all(isinstance(x, str) for x in scope + adoption)):
        if len(scope) != len(set(scope)) or len(adoption) != len(set(adoption)):
            missing.append("duplicate scope")
        if set(scope) != set(adoption):
            missing.append("unadopted cross-estate surfaces")
    if record.get("regression_failed_before") is not True:
        missing.append("real failing repro before correction")
    if record.get("regression_passed_after") is not True:
        missing.append("real passing repro after correction")
    if record.get("founder_visible") is not True:
        missing.append("founder readback")
    if record.get("implementer_id") and record.get("implementer_id") == record.get("independent_witness_id"):
        missing.append("independent witness distinct from implementer")
    for field in ("failing_reproducer_ref", "passing_regression_ref",
                  "independent_witness_ref", "real_effect_ref", "cross_agent_probe_ref",
                  "fcr_ref"):
        value = record.get(field)
        if isinstance(value, str) and not (
            value.startswith("https://github.com/") or value.startswith("fcr://")
            or value.startswith("receipt://")
        ):
            missing.append(field + " (no source locator)")
    result["missing"] = sorted(set(missing))
    if result["missing"]:
        result["next_action"] = "REPAIR_KNOWN_FAILURE_CLASS_WITH_EXISTING_FCR"
        return result
    result["state"] = "CANDIDATE_READY_FOR_INDEPENDENT_VERIFICATION"
    result["next_action"] = "INDEPENDENTLY_VERIFY_RECEIPTS_THROUGH_EXISTING_FCR_ACTION_DOOR"
    return result
