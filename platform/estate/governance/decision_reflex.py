#!/usr/bin/env python3
"""Meridian decision reflex v1: a portable, NON-AUTHORISING decision-stage adapter.

Emits bounded decision-context cues at every lifecycle boundary and compares
candidate actions against a frozen set of founder-derived preferences. This is
NOT a second policy engine and NEVER grants effect authority. QUAD/Greenlane
remain authoritative; an agent's own VERIFIED claims are not attestations.

CLI:
  python decision_reflex.py seed session_start
  python decision_reflex.py select envelope.json
  python decision_reflex.py review observation.json

Exit: 0 = useful answer, 2 = malformed/missing data. Outputs JSON only.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from founder_method import decide, validate

VERSION = "meridian-decision-reflex/1"
# These are INGEST / PLAN / EFFECT / LEARN boundaries, NOT another scheduler.
STAGES = {
    "instruction_intake": ("Record a durable obligation before admission", "instruction_id", "custody_receipt"),
    "session_start": ("Recover the live mission and falsified approaches", "instruction_id", "prior_evidence"),
    "context_retrieval": ("Read current sources and name missing dependencies", "source_sha", "unknowns"),
    "hypothesis": ("Compare causal explanations and the cheapest discriminating probe", "alternatives", "falsifier"),
    "planning": ("Choose leverage over activity; preserve fallback and handoff", "alternatives", "predicted_unlocks"),
    "capacity_admission": ("Prove provider, tool, quota and authority independently", "capacity_receipt", "authority_receipt"),
    "before_effect": ("Revalidate scope, cost, custody and independent proof", "authority_receipt", "evidence_refs"),
    "tool_result": ("Compare actual effect with prediction; do not self-certify", "observed_effect", "evidence_refs"),
    "failure": ("Retain obligation; classify UNKNOWN separately from exhausted", "failure_fingerprint", "counterexample"),
    "recovery": ("Reject repeated unchanged failed attempts; find another route", "failure_fingerprint", "new_evidence"),
    "handoff": ("Transfer checkpoint, ownership and next authorised action", "checkpoint_ref", "successor_claim"),
    "settlement": ("Require independent operational and causal closure", "independent_receipt", "causal_debt"),
    "session_end": ("Persist lessons and unclosed obligations outside this session", "checkpoint_ref", "next_action"),
}

def seed(stage: str) -> dict:
    if stage not in STAGES:
        raise ValueError("unknown decision stage")
    purpose, first, second = STAGES[stage]
    return {
        "schema": VERSION, "stage": stage, "purpose": purpose,
        "required_evidence": [first, second],
        "default": "UNKNOWN; observe or take a safe read-only diagnostic, never invent VERIFIED",
        "decision_law": "Prefer proven shared-capacity leverage; retain custody; attack alternatives; learn from reality",
        "effect_authority": "External QUAD/Greenlane authority and independent verifier required",
    }


def select(envelope: dict) -> dict:
    """Recommend a move but NEVER grant permission for a real-world effect.

    Evidence statuses supplied by a model are UNTRUSTED input; no output can
    become an effect authorisation without a separate trusted verifier.
    Historical falsifications are external observations, not self-declared wins.
    """
    if not isinstance(envelope, dict) or not isinstance(envelope.get("candidates"), list):
        raise ValueError("candidates array required")
    if not isinstance(envelope.get("instruction_id"), str) or not envelope["instruction_id"].strip():
        raise ValueError("durable instruction_id required")
    facts = envelope.get("falsified", [])
    if not isinstance(facts, list) or any(not isinstance(x, dict) or not isinstance(x.get("candidate_id"), str) or not isinstance(x.get("fingerprint"), str) or not x.get("evidence_ref") for x in facts):
        raise ValueError("falsifications need candidate_id, fingerprint and evidence_ref")
    fingerprint = envelope.get("failure_fingerprint", "")
    if not isinstance(fingerprint, str):
        raise ValueError("failure_fingerprint must be a string")
    repeat = {x["candidate_id"] for x in facts if x["fingerprint"] == fingerprint and fingerprint}
    candidates = envelope["candidates"]
    for c in candidates:
        validate(c)
    eligible = [c for c in candidates if c["id"] not in repeat]
    v = decide(eligible) if eligible else {"decision": "REFUSED" if candidates else "BLIND", "selected": None, "reason": "ALL_ALTERNATIVES_FALSIFIED" if candidates else "NO_CANDIDATES"}
    if repeat:
        v["held_against_recurrence"] = sorted(repeat)
    # A model's VERIFIED statuses do not constitute proof. Select only a
    # hypothesis / proposed next action. External gates own effect admission.
    if v["decision"] == "SELECTED_FOR_EXECUTION":
        v["decision"] = "PROPOSED_EFFECT_NOT_AUTHORISED"
    v["instruction_id"] = envelope["instruction_id"]
    v["schema"] = VERSION
    v["requires"] = "Separate independently verified QUAD/effect-door admission"
    canonical = json.dumps({"instruction_id": envelope["instruction_id"], "fingerprint": fingerprint, "candidate_ids": [c["id"] for c in candidates], "falsified": facts},sort_keys=True,separators=(",", ":")).encode()
    v["input_sha256"] = hashlib.sha256(canonical).hexdigest()
    return v


def review(record: dict) -> dict:
    """Compare intention to observed outcome; unknown is never a successful effect."""
    for k in ("instruction_id", "decision_sha256", "predicted", "observed", "independent_receipt"):
        if k not in record:
            raise ValueError("missing review field: " + k)
    pred, observed = record["predicted"], record["observed"]
    if not isinstance(pred, list) or not isinstance(observed, list):
        raise ValueError("predicted and observed must be lists")
    if not isinstance(record["independent_receipt"], str):
        raise ValueError("independent_receipt must be a string")
    if not record["independent_receipt"]:
        verdict = "UNVERIFIED"
    elif set(pred).issubset(set(observed)):
        verdict = "OBSERVED_MATCH_PENDING_RECEIPT_AUTHENTICATION"
    else:
        verdict = "PREDICTION_FALSIFIED"
    return {"schema": VERSION, "instruction_id": record["instruction_id"],
            "verdict": verdict, "new_unknowns": sorted(set(pred)-set(observed)),
            "next": "Update the hypothesis, preserve the observation, and choose a different action" if verdict == "PREDICTION_FALSIFIED" else "Authenticate the verifier receipt before settlement"}


def main(argv: list[str]) -> int:
    try:
        if len(argv) != 2 or argv[0] not in ("seed", "select", "review"):
            raise ValueError("usage: decision_reflex.py seed STAGE | select FILE | review FILE")
        mode, arg = argv
        value = seed(arg) if mode == "seed" else (select if mode == "select" else review)(json.loads(Path(arg).read_text()))
        print(json.dumps(value, sort_keys=True, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"schema": VERSION, "decision": "BLIND", "reason": str(exc)[:300]}, sort_keys=True))
        return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))