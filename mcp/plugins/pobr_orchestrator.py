#!/usr/bin/env python3
"""
pobr-orchestrator.py — the pipeline that wires it all.

Captures reasoning, elicits priors, computes likelihoods, does the
Bayesian update, runs prior sensitivity sweep, computes calibration
metrics, checks faithfulness, emits a signed receipt, and anchors it.

This is the ~300 lines that make PoBR usable. Everything else is a
library.

Usage:
    python3 pobr-orchestrator.py \\
        --agent-id urn:aid:oke:research-agent \\
        --key ~/.estate/keys/research-agent.pem \\
        --task "why does litellm-upstream ExternalSecret fail to sync?" \\
        --data-file data_points.json \\
        --hypotheses-file hypotheses.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import uuid
from pathlib import Path
from typing import Any

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
ReceiptBuilder = pobr_schema.ReceiptBuilder
sign_receipt = pobr_schema.sign_receipt
sha256_hex = pobr_schema.sha256_hex
bayesian_update = pobr_schema.bayesian_update
expected_calibration_error = pobr_schema.expected_calibration_error
brier_score = pobr_schema.brier_score


# ---------------------------------------------------------------------------
# Reasoning trace capture
# ---------------------------------------------------------------------------

def capture_reasoning_step(
    description: str,
    input_data: str,
    output_data: str,
    confidence: float = 0.9,
) -> ReasoningStep:
    return ReasoningStep(
        step_id=f"step-{uuid.uuid4().hex[:8]}",
        description=description,
        input_hash=sha256_hex(input_data),
        output_hash=sha256_hex(output_data),
        timestamp=time.time(),
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Faithfulness: run inference N times, measure variance
# ---------------------------------------------------------------------------

def run_faithfulness(
    hypotheses: list[Hypothesis],
    likelihoods: list[Likelihood],
    passes: int = 3,
    jitter: float = 0.02,
) -> Faithfulness:
    """
    Re-run Bayesian update with jittered likelihoods to model stochastic
    inference. Checks whether rankings stay stable across passes.
    """
    posteriors: list[dict[str, float]] = []
    for _ in range(passes):
        jittered = [
            Likelihood(
                data_point_id=lk.data_point_id,
                hypothesis_id=lk.hypothesis_id,
                probability=max(0.0, min(1.0, lk.probability + random.uniform(-jitter, jitter))),
                justification=lk.justification,
            )
            for lk in likelihoods
        ]
        posteriors.append(bayesian_update(hypotheses, jittered))

    ids = list(posteriors[0].keys())
    variances = []
    for hid in ids:
        values = [p[hid] for p in posteriors]
        mean_val = sum(values) / len(values)
        var = sum((v - mean_val) ** 2 for v in values) / len(values)
        variances.append(var)
    mean_variance = sum(variances) / len(variances)

    rankings = [sorted(p, key=p.get, reverse=True) for p in posteriors]
    rank_consistent = all(r[0] == rankings[0][0] for r in rankings)

    return Faithfulness(
        inference_passes=passes,
        posterior_variance=mean_variance,
        rank_consistent=rank_consistent,
        divergence_flagged=(not rank_consistent),
    )


# ---------------------------------------------------------------------------
# Calibration: evaluate posteriors against ground truth on a held-out set
# ---------------------------------------------------------------------------

def compute_calibration(
    hypothesis_ids: list[str],
    predictions: list[dict[str, float]],
    outcomes: list[str],
) -> dict[str, Any]:
    """
    predictions: list of posterior distributions (one per held-out case)
    outcomes:    list of ground-truth hypothesis ids (one per case)

    Uses top-pick confidence for ECE and Brier.
    """
    if len(predictions) != len(outcomes):
        raise ValueError("predictions and outcomes must match length")
    if not predictions:
        return {"expected_calibration_error": 0.0, "brier_score": 0.0, "n_held_out": 0}

    confidences = [max(p.values()) for p in predictions]
    top_picks = [max(p, key=p.get) for p in predictions]
    correct = [tp == outcome for tp, outcome in zip(top_picks, outcomes)]

    ece = expected_calibration_error(confidences, correct)
    brier = brier_score(confidences, correct)

    return {
        "expected_calibration_error": round(ece, 4),
        "brier_score": round(brier, 4),
        "n_held_out": len(outcomes),
    }


# ---------------------------------------------------------------------------
# External anchoring (Aevum PACR placeholder)
# ---------------------------------------------------------------------------

def anchor_via_aevum(root: str, agent_id: str, anchor_dir: Path) -> str:
    """
    Anchor the Merkle root externally. In production this calls Aevum's
    sigchain. For now, write a JSON anchor file with a timestamp.

    The anchor directory is itself committed to OCI Object Storage via
    a separate cron job, which provides the external timestamp.
    """
    anchor_dir.mkdir(parents=True, exist_ok=True)
    anchor_file = anchor_dir / f"{root}.json"
    anchor_file.write_text(json.dumps({
        "root": root,
        "agent_id": agent_id,
        "anchored_at": time.time(),
        "method": "aevum-pacr-local",
        "external_witness": "oci-objectstorage://pobr-anchors/",
    }, indent=2))
    return f"aevum://{anchor_file}"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def orchestrate(
    agent_id: str,
    private_key_path: Path,
    task: str,
    data_points: list[dict],
    hypotheses: list[dict],
    likelihoods: list[dict],
    reasoning_steps: list[dict],
    counterfactual: dict,
    exhaustiveness_claim: str,
    calibration_data: dict,
    anchor_dir: Path,
) -> PoBRReceipt:
    """
    Run the full pipeline. Returns a signed, anchored receipt.
    """
    builder = ReceiptBuilder(agent_id=agent_id, task=task)

    # Data points
    for dp in data_points:
        builder.consulted(DataPoint(**dp))

    builder.exhaustiveness(exhaustiveness_claim)

    # Hypotheses
    hyp_objs = []
    for h in hypotheses:
        ho = Hypothesis(**h)
        builder.hypothesis(ho)
        hyp_objs.append(ho)

    # Likelihoods
    lk_objs = []
    for lk in likelihoods:
        lo = Likelihood(**lk)
        builder.likelihood(lo)
        lk_objs.append(lo)

    # Reasoning steps
    for s in reasoning_steps:
        builder.step(ReasoningStep(**s))

    # Counterfactual
    builder.counterfactual(CounterfactualCommitment(**counterfactual))

    # Faithfulness
    faith = run_faithfulness(hyp_objs, lk_objs)
    builder.faithfulness(faith)

    # Calibration
    cal = compute_calibration(
        hypothesis_ids=[h.id for h in hyp_objs],
        predictions=calibration_data["predictions"],
        outcomes=calibration_data["outcomes"],
    )
    builder.calibration(cal)

    # Finalize (computes posterior, sweep, root, validates)
    receipt = builder.finalize()

    # Sign
    priv = private_key_path.read_bytes()
    receipt.signature = sign_receipt(receipt, priv)

    # Anchor
    receipt.external_anchor = anchor_via_aevum(
        receipt.merkle_root, agent_id, anchor_dir
    )

    receipt.verification_instructions = (
        "Recompute merkle_root from canonical_dict() + reasoning_steps; "
        "verify Ed25519 signature against registered public key; "
        f"fetch anchor from {receipt.external_anchor} and compare root."
    )

    return receipt


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text())


def main() -> int:
    ap = argparse.ArgumentParser(description="PoBR orchestrator")
    ap.add_argument("--agent-id", required=True)
    ap.add_argument("--key", required=True, help="Ed25519 private key PEM")
    ap.add_argument("--task", required=True)
    ap.add_argument("--data-file", required=True, help="JSON: list of data points")
    ap.add_argument("--hypotheses-file", required=True, help="JSON: list of hypotheses")
    ap.add_argument("--likelihoods-file", required=True, help="JSON: list of likelihoods")
    ap.add_argument("--steps-file", required=True, help="JSON: list of reasoning steps")
    ap.add_argument("--counterfactual-file", required=True, help="JSON: counterfactual commitment")
    ap.add_argument("--exhaustiveness", required=True, help="exhaustiveness claim string")
    ap.add_argument("--calibration-file", required=True, help="JSON: {predictions, outcomes}")
    ap.add_argument("--anchor-dir", default=os.path.expanduser("~/.estate/anchors"))
    ap.add_argument("--out", default="-", help="output receipt path, - for stdout")
    args = ap.parse_args()

    receipt = orchestrate(
        agent_id=args.agent_id,
        private_key_path=Path(args.key),
        task=args.task,
        data_points=_load_json(args.data_file),
        hypotheses=_load_json(args.hypotheses_file),
        likelihoods=_load_json(args.likelihoods_file),
        reasoning_steps=_load_json(args.steps_file),
        counterfactual=_load_json(args.counterfactual_file),
        exhaustiveness_claim=args.exhaustiveness,
        calibration_data=_load_json(args.calibration_file),
        anchor_dir=Path(args.anchor_dir),
    )

    payload = receipt.canonical_dict()
    payload["merkle_root"] = receipt.merkle_root
    payload["signature"] = receipt.signature
    payload["external_anchor"] = receipt.external_anchor
    payload["verification_instructions"] = receipt.verification_instructions

    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.out == "-":
        print(text)
    else:
        Path(args.out).write_text(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
