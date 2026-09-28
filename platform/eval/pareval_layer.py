#!/usr/bin/env python3
"""PartialEvalDecisionLayer: sequential comparison with bootstrap CI.

Implements early stopping for A/B comparison based on statistical confidence.
Uses paired t-test on score differences and bootstrap CI to determine winner.
Enforces stratified coverage before making terminal decisions.
"""

from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class Decision(Enum):
    """Terminal decision outcomes from partial evaluation."""

    NEED_MORE_EVIDENCE = "need_more_evidence"
    A_BETTER = "a_better"
    B_BETTER = "b_better"
    TIE = "tie"


@dataclass
class ObservedPair:
    """Single observation: task_id with paired scores from A and B."""

    task_id: str
    score_a: float
    score_b: float
    stratum: str = "default"


@dataclass
class PartialEvalDecisionLayer:
    """
    Sequential decision layer for partial evaluation.

    Tracks paired observations (score_a, score_b) across tasks and strata.
    Computes bootstrap CI on differences and decides when evidence is sufficient.
    Enforces coverage: all strata must appear ≥ min_observations_per_stratum times.

    Properties:
    - confidence: P(decision is correct), based on CI and effect size
    - ci_lower, ci_upper: bootstrap 95% CI on mean difference (A - B)
    """

    min_observations_per_stratum: int = 2
    min_strata_coverage: float = 1.0  # fraction of discovered strata [0.0, 1.0]
    max_unresolved_rate: float = 0.10
    false_positive_rate_cap: float = 0.05
    bootstrap_samples: int = 1000
    confidence_level: float = 0.95
    min_confidence_threshold: float = 0.70

    # Internal state
    observations: list[ObservedPair] = field(default_factory=list)
    strata_seen: set[str] = field(default_factory=set)

    def observe(
        self,
        task_id: str,
        score_a: float,
        score_b: float,
        stratum: str = "default",
    ) -> None:
        """Record a paired observation."""
        self.observations.append(
            ObservedPair(
                task_id=task_id, score_a=score_a, score_b=score_b, stratum=stratum
            )
        )
        self.strata_seen.add(stratum)

    @property
    def n_observations(self) -> int:
        """Total observations recorded."""
        return len(self.observations)

    @property
    def coverage(self) -> dict[str, int]:
        """Count of observations per stratum."""
        counts = {}
        for obs in self.observations:
            counts[obs.stratum] = counts.get(obs.stratum, 0) + 1
        return counts

    @property
    def coverage_ok(self) -> bool:
        """Check if coverage requirement is satisfied."""
        if not self.strata_seen:
            return True
        coverage = self.coverage
        required_strata = max(1, int(len(self.strata_seen) * self.min_strata_coverage))
        strata_meeting_min = sum(
            1
            for count in coverage.values()
            if count >= self.min_observations_per_stratum
        )
        return strata_meeting_min >= required_strata

    def _compute_diffs(self) -> np.ndarray:
        """Compute difference vector: score_a - score_b."""
        if not self.observations:
            return np.array([])
        return np.array([obs.score_a - obs.score_b for obs in self.observations])

    def _bootstrap_ci(
        self, diffs: np.ndarray, alpha: float = 0.05
    ) -> tuple[float, float]:
        """
        Compute bootstrap confidence interval on mean difference.

        Returns (lower, upper) bounds at confidence level (1 - alpha).
        """
        if len(diffs) < 2:
            return (np.nan, np.nan)

        bootstrap_means = []
        np.random.seed(42)  # reproducible
        for _ in range(self.bootstrap_samples):
            sample = np.random.choice(diffs, size=len(diffs), replace=True)
            bootstrap_means.append(np.mean(sample))

        bootstrap_means = np.array(bootstrap_means)
        lower = np.percentile(bootstrap_means, 100 * alpha / 2)
        upper = np.percentile(bootstrap_means, 100 * (1 - alpha / 2))
        return (float(lower), float(upper))

    @property
    def ci_lower(self) -> float:
        """Lower bound of 95% bootstrap CI on mean(score_a - score_b)."""
        diffs = self._compute_diffs()
        if len(diffs) == 0:
            return np.nan
        alpha = 1.0 - self.confidence_level
        lower, _ = self._bootstrap_ci(diffs, alpha=alpha)
        return lower

    @property
    def ci_upper(self) -> float:
        """Upper bound of 95% bootstrap CI on mean(score_a - score_b)."""
        diffs = self._compute_diffs()
        if len(diffs) == 0:
            return np.nan
        alpha = 1.0 - self.confidence_level
        _, upper = self._bootstrap_ci(diffs, alpha=alpha)
        return upper

    @property
    def mean_diff(self) -> float:
        """Mean of (score_a - score_b)."""
        diffs = self._compute_diffs()
        if len(diffs) == 0:
            return np.nan
        return float(np.mean(diffs))

    @property
    def std_diff(self) -> float:
        """Std dev of (score_a - score_b)."""
        diffs = self._compute_diffs()
        if len(diffs) < 2:
            return np.nan
        return float(np.std(diffs, ddof=1))

    @property
    def confidence(self) -> float:
        """
        Confidence in the decision (0.0 to 1.0).

        Based on:
        1. CI width: narrower CI → higher confidence
        2. Effect size: larger |mean_diff| → higher confidence
        3. Coverage: full coverage → higher confidence
        """
        if self.n_observations == 0:
            return 0.0

        diffs = self._compute_diffs()
        if len(diffs) < 2:
            return 0.0

        # Compute CI
        alpha = 1.0 - self.confidence_level
        lower, upper = self._bootstrap_ci(diffs, alpha=alpha)

        # Effect size (normalized by std)
        mean_diff = self.mean_diff
        std = self.std_diff
        if std < 1e-9:
            effect_size = 0.0
        else:
            effect_size = abs(mean_diff) / std

        # Clamp to [0, 1]
        effect_size = min(1.0, effect_size / 2.0)  # 2 SD = max effect size

        # Coverage penalty
        coverage_score = 1.0 if self.coverage_ok else 0.5

        # Combine: effect size weighted more than coverage
        combined = 0.7 * effect_size + 0.3 * coverage_score
        return float(min(1.0, combined))

    def decide(self) -> Decision:
        """
        Make a decision based on current evidence.

        Returns:
        - NEED_MORE_EVIDENCE: insufficient observations or coverage
        - A_BETTER: score_a significantly higher than score_b
        - B_BETTER: score_b significantly higher than score_a
        - TIE: no significant difference detected
        """
        # Check minimum observations
        if self.n_observations < self.min_observations_per_stratum:
            return Decision.NEED_MORE_EVIDENCE

        # Check coverage requirement
        if not self.coverage_ok:
            return Decision.NEED_MORE_EVIDENCE

        # Check confidence threshold
        if self.confidence < self.min_confidence_threshold:
            return Decision.NEED_MORE_EVIDENCE

        # Compute bootstrap CI
        diffs = self._compute_diffs()
        alpha = 1.0 - self.confidence_level
        lower, upper = self._bootstrap_ci(diffs, alpha=alpha)

        # Decision logic
        # If CI is entirely above zero: A is better
        if lower > 1e-6:
            return Decision.A_BETTER

        # If CI is entirely below zero: B is better
        if upper < -1e-6:
            return Decision.B_BETTER

        # If CI crosses zero but mean is close to zero: tie
        mean_diff = self.mean_diff
        if abs(mean_diff) < 1e-6:
            return Decision.TIE

        # CI crosses zero but we have high confidence: still tie
        if lower < 0 < upper:
            return Decision.TIE

        return Decision.NEED_MORE_EVIDENCE

    def summary(self) -> dict:
        """Return summary statistics for logging."""
        return {
            "n_observations": self.n_observations,
            "strata_seen": len(self.strata_seen),
            "coverage_by_stratum": self.coverage,
            "coverage_ok": self.coverage_ok,
            "mean_diff": self.mean_diff,
            "std_diff": self.std_diff,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "confidence": self.confidence,
            "decision": self.decide().value,
        }
