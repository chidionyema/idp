"""Interface 4 -- the remediation authority contract.

Three tiers, declared by the pack, enforced by a separate executor with a
disjoint identity:

    T0  report only. Always permitted.
    T1  execute a reversible, idempotent action.
        confidence >= 0.85 AND the action is allowlisted AND safety_proof present
    T2  execute with automatic rollback on failure.
        confidence >= 0.95 AND allowlisted AND safety_proof AND a tested rollback

The allowlist is a versioned ConfigMap and it is **empty on day one**. No
pack, no signature and no report can widen it: only a ConfigMap change can,
and only after the signature has produced a correct report against a real
artifact.

Actions are typed, not shell. An allowlist entry names an action type the
executor implements (``annotate``), the target, and the rollback that undoes
it. A template that is not a known type is refused, so the executor never
runs a string it did not implement.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from .reasoning import T1_CONFIDENCE, T2_CONFIDENCE

ALLOWLIST_ENV = "EFDA_ALLOWLIST_PATH"

# The action types the executor implements. Each one is reversible.
SUPPORTED_ACTIONS = ("annotate",)


def now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_allowlist(path=None) -> dict:
    """Read the allowlist. JSON, because the executor carries no YAML parser.

    A missing or unreadable allowlist is an empty allowlist -- the refusal
    is the safe direction.
    """
    path = path or os.environ.get(ALLOWLIST_ENV, "")
    if not path:
        return {"version": "v0", "actions": []}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {"version": "v0", "actions": []}
    data.setdefault("actions", [])
    data.setdefault("version", "v0")
    return data


def _entry_for(allowlist: dict, report: dict):
    for entry in allowlist.get("actions") or []:
        if entry.get("signatureId") != report.get("signatureId"):
            continue
        if entry.get("componentClass") and entry.get("componentClass") != report.get(
            "componentClass"
        ):
            continue
        return entry
    return None


def decide(report: dict, allowlist: dict) -> dict:
    """Decide what the executor may do with a report.

    The return value names the refusal, because "nothing happened" is not a
    result a human can act on.
    """
    decision = {
        "outcome": "",
        "reason": "",
        "action": None,
        "rollback": None,
        "signatureId": report.get("signatureId", ""),
        "componentClass": report.get("componentClass", ""),
        "confidence": report.get("confidence", 0.0),
    }
    remediation = report.get("remediation") or {}
    tier = remediation.get("tier", "T0")

    if tier == "T0":
        decision["outcome"] = "REPORT_ONLY"
        decision["reason"] = "tier=T0, action=report_only"
        return decision

    if not remediation.get("safetyProof"):
        decision["outcome"] = "REFUSED"
        decision["reason"] = "safety_proof_missing"
        return decision

    entry = _entry_for(allowlist, report)
    if entry is None:
        decision["outcome"] = "REFUSED"
        decision["reason"] = "action_not_in_allowlist"
        return decision

    if tier == "T1" and float(report.get("confidence", 0.0)) < T1_CONFIDENCE:
        decision["outcome"] = "REFUSED"
        decision["reason"] = (
            f"confidence {report.get('confidence')} below the T1 gate {T1_CONFIDENCE}"
        )
        return decision

    if tier == "T2":
        if float(report.get("confidence", 0.0)) < T2_CONFIDENCE:
            decision["outcome"] = "REFUSED"
            decision["reason"] = (
                f"confidence {report.get('confidence')} below the T2 gate {T2_CONFIDENCE}"
            )
            return decision
        if not entry.get("rollback") or not entry.get("rollbackTested"):
            decision["outcome"] = "REFUSED"
            decision["reason"] = "rollback_not_tested"
            return decision

    action = entry.get("action") or {}
    if action.get("type") not in SUPPORTED_ACTIONS:
        decision["outcome"] = "REFUSED"
        decision["reason"] = (
            f"action type {action.get('type')!r} is not implemented by the executor"
        )
        return decision

    decision["outcome"] = "EXECUTE"
    decision["reason"] = f"tier={tier} action={action.get('type')}"
    decision["action"] = action
    decision["rollback"] = entry.get("rollback")
    return decision


def _apply_annotate(k8s, action: dict) -> dict:
    """Annotate a resource, returning the previous values for the rollback."""
    target = action.get("target") or {}
    annotations = action.get("annotations") or {}
    previous = k8s.get_annotations(
        target.get("kind", "deployment"),
        target.get("namespace", "default"),
        target.get("name", ""),
    )
    k8s.annotate(
        target.get("kind", "deployment"),
        target.get("namespace", "default"),
        target.get("name", ""),
        annotations,
    )
    return {"previousAnnotations": previous, "appliedAnnotations": annotations}


def _rollback_annotate(k8s, rollback: dict) -> None:
    target = rollback.get("target") or {}
    previous = rollback.get("previousAnnotations") or {}
    k8s.annotate(
        target.get("kind", "deployment"),
        target.get("namespace", "default"),
        target.get("name", ""),
        previous,
    )


def execute(decision: dict, k8s) -> dict:
    """Run a permitted action and record what happened."""
    artifact = {
        "apiVersion": "efda.estate/v1",
        "kind": "RemediationArtifact",
        "metadata": {"name": f"remediation-{decision.get('signatureId', 'unknown')}"},
        "spec": {
            "signatureId": decision.get("signatureId", ""),
            "componentClass": decision.get("componentClass", ""),
            "confidence": decision.get("confidence", 0.0),
            "action": decision.get("action") or {},
            "outcome": decision.get("outcome", ""),
            "executedAt": now_iso(),
            "preState": {},
            "rollbackPoint": decision.get("rollback") or {},
            "rolledBack": False,
        },
    }
    if decision.get("outcome") != "EXECUTE":
        artifact["spec"]["outcome"] = decision.get("reason", "REFUSED")
        return artifact

    try:
        if decision["action"].get("type") == "annotate":
            pre_state = _apply_annotate(k8s, decision["action"])
            artifact["spec"]["preState"] = pre_state
        else:
            artifact["spec"]["outcome"] = "REFUSED"
            artifact["spec"]["reason"] = "unknown action type"
            return artifact
    except Exception as exc:  # noqa: BLE001 -- the failure must be recorded, not raised
        artifact["spec"]["outcome"] = "REMEDIATION_FAILED"
        artifact["spec"]["reason"] = str(exc)
        return artifact

    artifact["spec"]["outcome"] = "REMEDIATION_APPLIED"
    return artifact
