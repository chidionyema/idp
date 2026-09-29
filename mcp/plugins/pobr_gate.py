#!/usr/bin/env python3
"""
pobr-gate.py — the admission gate.

Deterministic verifier. No LLM. No heuristics. Every check is a
cryptographic or mathematical assertion. Returns ADMITTED or
REJECTED with structured reason + remediation.

Usage:
    python3 pobr-gate.py receipt.json --pubkey agent.pub.pem
    python3 pobr-gate.py receipt.json --pubkey agent.pub.pem --anchor-dir ~/.estate/anchors
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

# Import from sibling schema module
import importlib.util

schema_path = Path(__file__).parent / "pobr_schema.py"
spec = importlib.util.spec_from_file_location("pobr_schema", schema_path)
pobr_schema = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pobr_schema)

PoBRReceipt = pobr_schema.PoBRReceipt
DataPoint = pobr_schema.DataPoint
Hypothesis = pobr_schema.Hypothesis
Likelihood = pobr_schema.Likelihood
ReasoningStep = pobr_schema.ReasoningStep
CounterfactualCommitment = pobr_schema.CounterfactualCommitment
Faithfulness = pobr_schema.Faithfulness
validate_receipt = pobr_schema.validate_receipt
verify_signature = pobr_schema.verify_signature


class Admission(Enum):
    GRANTED = "ADMITTED"
    REJECTED = "REJECTED"


@dataclass
class GateResult:
    decision: Admission
    reason: str = ""
    detail: str = ""
    remediation: str = ""
    receipt_root: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "decision": self.decision.value,
                "reason": self.reason,
                "detail": self.detail,
                "remediation": self.remediation,
                "receipt_root": self.receipt_root,
            },
            indent=2,
        )


# ---------------------------------------------------------------------------
# Thresholds (elite grade)
# ---------------------------------------------------------------------------

THRESHOLDS = {
    "expected_calibration_error": 0.05,
    "brier_score": 0.15,
    "posterior_variance": 0.01,
    "prior_sensitivity_stable": True,
}


# ---------------------------------------------------------------------------
# Gate checks (each returns None on pass, GateResult on fail)
# ---------------------------------------------------------------------------


def check_structure(receipt: PoBRReceipt) -> Optional[GateResult]:
    try:
        validate_receipt(receipt)
        return None
    except Exception as e:
        return GateResult(
            decision=Admission.REJECTED,
            reason="structural_validation",
            detail=str(e),
            remediation="Fix the receipt structure and resubmit.",
        )


def check_merkle_root(receipt: PoBRReceipt) -> Optional[GateResult]:
    computed = receipt.compute_root()
    if computed != receipt.merkle_root:
        return GateResult(
            decision=Admission.REJECTED,
            reason="merkle_root_mismatch",
            detail=f"claimed={receipt.merkle_root[:16]}... computed={computed[:16]}...",
            remediation="Receipt has been tampered with. Regenerate from source.",
        )
    return None


def check_signature(
    receipt: PoBRReceipt, public_key_pem: bytes
) -> Optional[GateResult]:
    if not verify_signature(receipt, public_key_pem):
        return GateResult(
            decision=Admission.REJECTED,
            reason="signature_invalid",
            detail="Ed25519 signature does not verify against registered public key.",
            remediation="Ensure the agent signs with the key registered to its identity.",
        )
    return None


def check_anchor(
    receipt: PoBRReceipt, anchor_dir: Optional[Path]
) -> Optional[GateResult]:
    if not receipt.external_anchor:
        return GateResult(
            decision=Admission.REJECTED,
            reason="no_external_anchor",
            detail="Receipt does not reference an external anchor.",
            remediation="Anchor the Merkle root via Aevum PACR before submitting.",
        )
    if anchor_dir is None:
        return None  # no anchor dir configured; skip
    anchor_path = anchor_dir / f"{receipt.merkle_root}.json"
    if not anchor_path.exists():
        return GateResult(
            decision=Admission.REJECTED,
            reason="anchor_not_found",
            detail=f"anchor file {anchor_path} does not exist",
            remediation="Re-run anchoring; the receipt root was never externally committed.",
        )
    try:
        anchored = json.loads(anchor_path.read_text())
        if anchored.get("root") != receipt.merkle_root:
            return GateResult(
                decision=Admission.REJECTED,
                reason="anchor_mismatch",
                detail=f"anchor root {anchored.get('root', '?')[:16]}... != receipt root",
                remediation="The receipt root does not match what was anchored. Do not trust it.",
            )
    except Exception as e:
        return GateResult(
            decision=Admission.REJECTED,
            reason="anchor_unreadable",
            detail=str(e),
            remediation="Anchor file is corrupt.",
        )
    return None


def check_calibration(receipt: PoBRReceipt) -> Optional[GateResult]:
    cal = receipt.calibration or {}
    ece = cal.get("expected_calibration_error")
    if ece is None:
        return GateResult(
            decision=Admission.REJECTED,
            reason="calibration_missing",
            detail="Expected Calibration Error not reported.",
            remediation="Compute ECE against held-out data and include it.",
        )
    if ece > THRESHOLDS["expected_calibration_error"]:
        return GateResult(
            decision=Admission.REJECTED,
            reason="calibration_failed",
            detail=f"ECE={ece:.4f} > {THRESHOLDS['expected_calibration_error']}",
            remediation="Posteriors are overconfident. Recalibrate (temperature scaling or richer priors) and resubmit.",
        )
    brier = cal.get("brier_score")
    if brier is None:
        return GateResult(
            decision=Admission.REJECTED,
            reason="brier_missing",
            detail="Brier score not reported.",
            remediation="Compute Brier score against held-out data.",
        )
    if brier > THRESHOLDS["brier_score"]:
        return GateResult(
            decision=Admission.REJECTED,
            reason="brier_failed",
            detail=f"Brier={brier:.4f} > {THRESHOLDS['brier_score']}",
            remediation="Predictions are poorly calibrated. Re-examine priors and likelihoods.",
        )
    return None


def check_prior_sensitivity(receipt: PoBRReceipt) -> Optional[GateResult]:
    if not receipt.rank_stable:
        return GateResult(
            decision=Admission.REJECTED,
            reason="prior_sensitive",
            detail="Top hypothesis changes when priors are swept 0.5x/1x/2x.",
            remediation="Evidence does not overcome prior sensitivity. Gather more discriminating data.",
        )
    return None


def check_faithfulness(receipt: PoBRReceipt) -> Optional[GateResult]:
    f = receipt.faithfulness
    if f is None:
        return GateResult(
            decision=Admission.REJECTED,
            reason="faithfulness_missing",
            detail="No faithfulness check reported.",
            remediation="Run inference at least 3 times and report posterior variance.",
        )
    if not f.rank_consistent:
        return GateResult(
            decision=Admission.REJECTED,
            reason="unfaithful_reasoning",
            detail="Ranking is not consistent across inference passes.",
            remediation="Reasoning is unstable — likely post-hoc rationalization. Re-derive from evidence.",
        )
    if f.divergence_flagged:
        return GateResult(
            decision=Admission.REJECTED,
            reason="divergence_flagged",
            detail="Inference passes diverged beyond threshold.",
            remediation="Same as above. Re-derive.",
        )
    if f.posterior_variance > THRESHOLDS["posterior_variance"]:
        return GateResult(
            decision=Admission.REJECTED,
            reason="posterior_variance_too_high",
            detail=f"variance={f.posterior_variance:.4f} > {THRESHOLDS['posterior_variance']}",
            remediation="Reasoning is not converging. Increase sample count or re-examine priors.",
        )
    return None


def check_counterfactual(receipt: PoBRReceipt) -> Optional[GateResult]:
    if receipt.counterfactual is None:
        return GateResult(
            decision=Admission.REJECTED,
            reason="no_counterfactual_commitment",
            detail="No falsification condition committed.",
            remediation="State explicitly what evidence would falsify your top hypothesis, and who can verify it.",
        )
    if not receipt.counterfactual.verifiable_by.strip():
        return GateResult(
            decision=Admission.REJECTED,
            reason="counterfactual_not_verifiable",
            detail="Counterfactual does not name a verifier.",
            remediation="State who can independently verify the falsification condition.",
        )
    return None


def check_completeness(receipt: PoBRReceipt) -> Optional[GateResult]:
    if not receipt.exhaustiveness_claim.strip():
        return GateResult(
            decision=Admission.REJECTED,
            reason="no_exhaustiveness_claim",
            detail="Receipt does not claim to have enumerated all reachable data points.",
            remediation="Enumerate every source consulted and every source excluded with a reason.",
        )
    return None


# ---------------------------------------------------------------------------
# Main gate
# ---------------------------------------------------------------------------


def gate(
    receipt: PoBRReceipt,
    public_key_pem: bytes,
    anchor_dir: Optional[Path] = None,
) -> GateResult:
    """Run every check in order. Return first failure, or ADMITTED."""
    checks = [
        ("structure", lambda: check_structure(receipt)),
        ("merkle_root", lambda: check_merkle_root(receipt)),
        ("signature", lambda: check_signature(receipt, public_key_pem)),
        ("anchor", lambda: check_anchor(receipt, anchor_dir)),
        ("completeness", lambda: check_completeness(receipt)),
        ("calibration", lambda: check_calibration(receipt)),
        ("prior_sensitivity", lambda: check_prior_sensitivity(receipt)),
        ("faithfulness", lambda: check_faithfulness(receipt)),
        ("counterfactual", lambda: check_counterfactual(receipt)),
    ]
    for _name, fn in checks:
        result = fn()
        if result is not None:
            result.receipt_root = receipt.merkle_root
            return result
    return GateResult(
        decision=Admission.GRANTED,
        reason="all_checks_passed",
        receipt_root=receipt.merkle_root,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def receipt_from_dict(d: dict) -> PoBRReceipt:
    """Deserialize a receipt dict back into a PoBRReceipt."""
    r = PoBRReceipt(
        schema=d.get("schema", "pobr/v1"),
        agent_id=d.get("agent_id", ""),
        session_id=d.get("session_id", ""),
        task=d.get("task", ""),
        issued_at=d.get("issued_at", 0.0),
        exhaustiveness_claim=d.get("exhaustiveness_claim", ""),
        posterior=d.get("posterior", {}),
        posterior_method=d.get("posterior_method", ""),
        calibration=d.get("calibration", {}),
        prior_sweep=d.get("prior_sweep", {}),
        rank_stable=d.get("rank_stable", False),
        merkle_root=d.get("merkle_root", ""),
        signature=d.get("signature", ""),
        external_anchor=d.get("external_anchor", ""),
        verification_instructions=d.get("verification_instructions", ""),
    )
    for x in d.get("data_points_consulted", []):
        r.data_points_consulted.append(DataPoint(**x))
    for x in d.get("data_points_excluded", []):
        r.data_points_excluded.append(DataPoint(**x))
    for x in d.get("hypotheses", []):
        r.hypotheses.append(Hypothesis(**x))
    for x in d.get("likelihoods", []):
        r.likelihoods.append(Likelihood(**x))
    for x in d.get("reasoning_steps", []):
        r.reasoning_steps.append(ReasoningStep(**x))
    if d.get("counterfactual"):
        r.counterfactual = CounterfactualCommitment(**d["counterfactual"])
    if d.get("faithfulness"):
        r.faithfulness = Faithfulness(**d["faithfulness"])
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="PoBR admission gate")
    ap.add_argument("receipt", help="path to receipt.json")
    ap.add_argument("--pubkey", required=True, help="path to agent public key PEM")
    ap.add_argument("--anchor-dir", default=os.path.expanduser("~/.estate/anchors"))
    args = ap.parse_args()

    r = receipt_from_dict(json.loads(Path(args.receipt).read_text()))
    pubkey = Path(args.pubkey).read_bytes()
    anchor_dir = Path(args.anchor_dir) if args.anchor_dir else None

    result = gate(r, pubkey, anchor_dir)
    print(result.to_json())
    return 0 if result.decision == Admission.GRANTED else 1


if __name__ == "__main__":
    sys.exit(main())
