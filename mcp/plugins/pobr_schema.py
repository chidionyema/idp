#!/usr/bin/env python3
"""
pobr-schema.py — Bayesian reasoning trace schema.

Extends PAD-017's reasoning Merkle tree with Bayesian-specific fields.
Produces a canonical, JCS-serializable, recomputable receipt.

Dependencies:
    pip install cryptography   # Ed25519 signatures
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Canonicalization (RFC 8785 JCS-compatible for our subset)
# ---------------------------------------------------------------------------

def canonical_json(obj: Any) -> str:
    """Canonical JSON: sorted keys, no whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Merkle tree over reasoning steps
# ---------------------------------------------------------------------------

@dataclass
class ReasoningStep:
    """One inference step in the reasoning trace."""
    step_id: str
    description: str
    input_hash: str
    output_hash: str
    timestamp: float
    confidence: float  # 0..1

    def leaf_hash(self) -> str:
        payload = canonical_json({
            "step_id": self.step_id,
            "description": self.description,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
        })
        return sha256_hex(payload)


def merkle_root(leaves: list[str]) -> str:
    """Standard binary Merkle root. Handles odd counts by promoting."""
    if not leaves:
        return sha256_hex("")
    level = list(leaves)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [sha256_hex(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


# ---------------------------------------------------------------------------
# Bayesian primitives
# ---------------------------------------------------------------------------

@dataclass
class Hypothesis:
    id: str
    statement: str
    prior: float
    prior_justification: str
    prior_source: str

    def validate(self) -> None:
        if not (0.0 < self.prior <= 1.0):
            raise ValueError(f"{self.id}: prior must be in (0, 1], got {self.prior}")
        if not self.prior_justification.strip():
            raise ValueError(f"{self.id}: prior_justification required")
        if not self.prior_source.strip():
            raise ValueError(f"{self.id}: prior_source required (must cite evidence)")


@dataclass
class Likelihood:
    data_point_id: str
    hypothesis_id: str
    probability: float
    justification: str

    def validate(self) -> None:
        if not (0.0 <= self.probability <= 1.0):
            raise ValueError(
                f"P({self.data_point_id}|{self.hypothesis_id}) = {self.probability} "
                "outside [0,1]"
            )


@dataclass
class DataPoint:
    id: str
    source: str
    captured_at: float
    content_hash: str
    relevance: float
    reason: str = ""  # for excluded points

    def validate(self) -> None:
        if not (0.0 <= self.relevance <= 1.0):
            raise ValueError(f"{self.id}: relevance must be in [0,1]")


# ---------------------------------------------------------------------------
# Bayesian update (discrete hypotheses)
# ---------------------------------------------------------------------------

def bayesian_update(
    hypotheses: list[Hypothesis],
    likelihoods: list[Likelihood],
) -> dict[str, float]:
    """
    P(H_i | D) ∝ P(D | H_i) * P(H_i)

    Handles multiple data points: assumes conditional independence,
    P(D | H_i) = ∏_d P(d | H_i).
    """
    log_posteriors: dict[str, float] = {}

    for h in hypotheses:
        lp = float("-inf") if h.prior <= 0 else math.log(h.prior)
        for lk in likelihoods:
            if lk.hypothesis_id == h.id:
                if lk.probability <= 0:
                    lp = float("-inf")
                    break
                lp += math.log(lk.probability)
        log_posteriors[h.id] = lp

    m = max(log_posteriors.values())
    if m == float("-inf"):
        raise ValueError("all posteriors are zero — check likelihoods")

    scaled = {k: math.exp(v - m) for k, v in log_posteriors.items()}
    total = sum(scaled.values())
    return {k: v / total for k, v in scaled.items()}


# ---------------------------------------------------------------------------
# Calibration metrics
# ---------------------------------------------------------------------------

def expected_calibration_error(
    predictions: list[float],
    outcomes: list[bool],
    n_bins: int = 10,
) -> float:
    """ECE: bin predictions, compare mean confidence to empirical accuracy."""
    if len(predictions) != len(outcomes):
        raise ValueError("predictions and outcomes must match length")
    n = len(predictions)
    if n == 0:
        return 0.0
    bins: list[list[tuple[float, bool]]] = [[] for _ in range(n_bins)]
    for p, y in zip(predictions, outcomes):
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx].append((p, y))
    ece = 0.0
    for b in bins:
        if not b:
            continue
        mean_conf = sum(p for p, _ in b) / len(b)
        mean_acc = sum(1 for _, y in b if y) / len(b)
        ece += (len(b) / n) * abs(mean_conf - mean_acc)
    return ece


def brier_score(predictions: list[float], outcomes: list[bool]) -> float:
    """Brier: mean squared error between predicted probability and outcome."""
    if len(predictions) != len(outcomes):
        raise ValueError("predictions and outcomes must match length")
    if not predictions:
        return 0.0
    return sum((p - (1.0 if y else 0.0)) ** 2 for p, y in zip(predictions, outcomes)) / len(predictions)


def credible_interval(
    mean: float, variance: float, z: float = 1.96
) -> tuple[float, float]:
    """95% credible interval from mean and variance."""
    sd = variance ** 0.5
    return (max(0.0, mean - z * sd), min(1.0, mean + z * sd))


# ---------------------------------------------------------------------------
# Prior sensitivity sweep
# ---------------------------------------------------------------------------

def prior_sweep(
    hypotheses: list[Hypothesis],
    likelihoods: list[Likelihood],
    multipliers: tuple[float, ...] = (0.5, 1.0, 2.0),
) -> dict[str, dict[str, float]]:
    """
    For each multiplier m, scale every prior by m, renormalize,
    and recompute posteriors.
    """
    results: dict[str, dict[str, float]] = {}
    for m in multipliers:
        scaled = [
            Hypothesis(
                id=h.id,
                statement=h.statement,
                prior=h.prior * m,
                prior_justification=h.prior_justification,
                prior_source=h.prior_source,
            )
            for h in hypotheses
        ]
        total = sum(h.prior for h in scaled)
        for h in scaled:
            h.prior = h.prior / total
        results[f"{m}x"] = bayesian_update(scaled, likelihoods)
    return results


def rank_stable_across_sweep(sweep: dict[str, dict[str, float]]) -> bool:
    """Top hypothesis must be identical across all prior multipliers."""
    if not sweep:
        return False
    rankings = [sorted(ps, key=ps.get, reverse=True) for ps in sweep.values()]
    return all(r[0] == rankings[0][0] for r in rankings)


# ---------------------------------------------------------------------------
# Counterfactual commitment
# ---------------------------------------------------------------------------

@dataclass
class CounterfactualCommitment:
    hypothesis_id: str
    would_be_falsified_if: str
    verifiable_by: str
    committed_at: float

    def validate(self) -> None:
        if not self.would_be_falsified_if.strip():
            raise ValueError("counterfactual must state falsification condition")
        if not self.verifiable_by.strip():
            raise ValueError("counterfactual must state who can verify")


# ---------------------------------------------------------------------------
# Faithfulness (stochastic variance across inference passes)
# ---------------------------------------------------------------------------

@dataclass
class Faithfulness:
    inference_passes: int
    posterior_variance: float
    rank_consistent: bool
    divergence_flagged: bool

    ELITE_VARIANCE = 0.01

    def is_faithful(self) -> bool:
        return (
            self.rank_consistent
            and not self.divergence_flagged
            and self.posterior_variance < self.ELITE_VARIANCE
        )


# ---------------------------------------------------------------------------
# The receipt
# ---------------------------------------------------------------------------

@dataclass
class PoBRReceipt:
    schema: str = "pobr/v1"
    agent_id: str = ""
    session_id: str = ""
    task: str = ""
    issued_at: float = field(default_factory=time.time)

    data_points_consulted: list[DataPoint] = field(default_factory=list)
    data_points_excluded: list[DataPoint] = field(default_factory=list)
    exhaustiveness_claim: str = ""

    hypotheses: list[Hypothesis] = field(default_factory=list)
    likelihoods: list[Likelihood] = field(default_factory=list)
    posterior: dict[str, float] = field(default_factory=dict)
    posterior_method: str = "discrete Bayesian update, independent data points"

    calibration: dict[str, Any] = field(default_factory=dict)
    prior_sweep: dict[str, dict[str, float]] = field(default_factory=dict)
    rank_stable: bool = False

    counterfactual: Optional[CounterfactualCommitment] = None
    faithfulness: Optional[Faithfulness] = None

    reasoning_steps: list[ReasoningStep] = field(default_factory=list)
    merkle_root: str = ""
    signature: str = ""
    external_anchor: str = ""
    verification_instructions: str = ""

    def canonical_dict(self) -> dict:
        """Ordered dict for canonicalization. Excludes signature and anchor."""
        return {
            "schema": self.schema,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "task": self.task,
            "issued_at": self.issued_at,
            "data_points_consulted": [asdict(d) for d in self.data_points_consulted],
            "data_points_excluded": [asdict(d) for d in self.data_points_excluded],
            "exhaustiveness_claim": self.exhaustiveness_claim,
            "hypotheses": [asdict(h) for h in self.hypotheses],
            "likelihoods": [asdict(lk) for lk in self.likelihoods],
            "posterior": self.posterior,
            "posterior_method": self.posterior_method,
            "calibration": self.calibration,
            "prior_sweep": self.prior_sweep,
            "rank_stable": self.rank_stable,
            "counterfactual": asdict(self.counterfactual) if self.counterfactual else None,
            "faithfulness": asdict(self.faithfulness) if self.faithfulness else None,
            "reasoning_steps": [asdict(s) for s in self.reasoning_steps],
        }

    def compute_root(self) -> str:
        """Merkle root over: reasoning step leaves + the canonical dict hash."""
        leaves = [s.leaf_hash() for s in self.reasoning_steps]
        if not leaves:
            leaves = [sha256_hex("no-steps")]
        canonical_hash = sha256_hex(canonical_json(self.canonical_dict()))
        leaves.append(canonical_hash)
        return merkle_root(leaves)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class PoBRValidationError(Exception):
    pass


def validate_receipt(r: PoBRReceipt) -> None:
    """Structural and semantic validation. Raises on any failure."""
    if r.schema != "pobr/v1":
        raise PoBRValidationError(f"unsupported schema: {r.schema}")
    if not r.agent_id:
        raise PoBRValidationError("agent_id required")
    if not r.task.strip():
        raise PoBRValidationError("task required")

    if not (2 <= len(r.hypotheses) <= 8):
        raise PoBRValidationError(f"hypotheses count must be 2..8, got {len(r.hypotheses)}")

    ids = [h.id for h in r.hypotheses]
    if len(ids) != len(set(ids)):
        raise PoBRValidationError("duplicate hypothesis ids")

    prior_sum = sum(h.prior for h in r.hypotheses)
    if abs(prior_sum - 1.0) > 0.05:
        raise PoBRValidationError(f"priors sum {prior_sum:.3f}, must be ~1.0")

    for h in r.hypotheses:
        h.validate()

    for lk in r.likelihoods:
        lk.validate()
        if lk.hypothesis_id not in ids:
            raise PoBRValidationError(f"likelihood references unknown hypothesis {lk.hypothesis_id}")

    for d in r.data_points_consulted + r.data_points_excluded:
        d.validate()

    if not r.exhaustiveness_claim.strip():
        raise PoBRValidationError("exhaustiveness_claim required")

    if not r.posterior:
        raise PoBRValidationError("posterior required")

    post_sum = sum(r.posterior.values())
    if abs(post_sum - 1.0) > 0.01:
        raise PoBRValidationError(f"posterior sums to {post_sum:.4f}, must be 1.0")

    if r.counterfactual:
        r.counterfactual.validate()

    if r.faithfulness and not r.faithfulness.is_faithful():
        raise PoBRValidationError("faithfulness failed")


# ---------------------------------------------------------------------------
# Builder (fluent API used by the orchestrator)
# ---------------------------------------------------------------------------

class ReceiptBuilder:
    def __init__(self, agent_id: str, task: str):
        self.r = PoBRReceipt(
            agent_id=agent_id,
            session_id=f"sess-{uuid.uuid4().hex[:12]}",
            task=task,
        )

    def consulted(self, dp: DataPoint) -> "ReceiptBuilder":
        self.r.data_points_consulted.append(dp)
        return self

    def excluded(self, dp: DataPoint) -> "ReceiptBuilder":
        self.r.data_points_excluded.append(dp)
        return self

    def exhaustiveness(self, claim: str) -> "ReceiptBuilder":
        self.r.exhaustiveness_claim = claim
        return self

    def hypothesis(self, h: Hypothesis) -> "ReceiptBuilder":
        self.r.hypotheses.append(h)
        return self

    def likelihood(self, lk: Likelihood) -> "ReceiptBuilder":
        self.r.likelihoods.append(lk)
        return self

    def step(self, s: ReasoningStep) -> "ReceiptBuilder":
        self.r.reasoning_steps.append(s)
        return self

    def counterfactual(self, c: CounterfactualCommitment) -> "ReceiptBuilder":
        self.r.counterfactual = c
        return self

    def faithfulness(self, f: Faithfulness) -> "ReceiptBuilder":
        self.r.faithfulness = f
        return self

    def calibration(self, metrics: dict) -> "ReceiptBuilder":
        self.r.calibration = metrics
        return self

    def finalize(self) -> PoBRReceipt:
        """Compute posterior, sweep, root. Validate. Return receipt."""
        # 1. Bayesian update
        self.r.posterior = bayesian_update(self.r.hypotheses, self.r.likelihoods)

        # 2. Prior sweep
        self.r.prior_sweep = prior_sweep(self.r.hypotheses, self.r.likelihoods)
        self.r.rank_stable = rank_stable_across_sweep(self.r.prior_sweep)

        # 3. Merkle root
        self.r.merkle_root = self.r.compute_root()

        # 4. Verify
        validate_receipt(self.r)
        return self.r


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------

def sign_receipt(receipt: PoBRReceipt, private_key_pem: bytes) -> str:
    """Sign the merkle root with Ed25519. Returns base64 signature."""
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    import base64

    key = load_pem_private_key(private_key_pem, password=None)
    signature = key.sign(receipt.merkle_root.encode("utf-8"))
    return base64.b64encode(signature).decode("ascii")


def verify_signature(receipt: PoBRReceipt, public_key_pem: bytes) -> bool:
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.exceptions import InvalidSignature
    import base64

    try:
        key = load_pem_public_key(public_key_pem)
        sig = base64.b64decode(receipt.signature)
        key.verify(sig, receipt.merkle_root.encode("utf-8"))
        return True
    except (InvalidSignature, Exception):
        return False
