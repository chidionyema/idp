#!/usr/bin/env python3
"""ComparisonPolicy: configuration for partial evaluation decisions.

Specifies parameters that control when PartialEvalDecisionLayer makes a decision.
Used by LangGraph state graphs to orchestrate evaluation loops.
"""

from dataclasses import dataclass


@dataclass
class ComparisonPolicy:
    """
    Configuration for partial evaluation decision making.

    Controls confidence thresholds, false positive rate caps, coverage requirements,
    and bootstrap sampling for computing confidence intervals on paired scores.
    """

    min_confidence_threshold: float = 0.70
    """Minimum confidence [0.0, 1.0] required to make a decision."""

    max_unresolved_rate: float = 0.10
    """Maximum fraction of observations that can remain unresolved [0.0, 1.0]."""

    bootstrap_samples: int = 1000
    """Number of bootstrap resamples for CI computation."""

    coverage_requirement: float = 1.0
    """Minimum fraction of discovered strata that must be observed [0.0, 1.0]."""

    def __post_init__(self) -> None:
        """Validate policy parameters."""
        if not 0.0 <= self.min_confidence_threshold <= 1.0:
            raise ValueError("min_confidence_threshold must be in [0.0, 1.0]")

        if not 0.0 <= self.max_unresolved_rate <= 1.0:
            raise ValueError("max_unresolved_rate must be in [0.0, 1.0]")

        if self.bootstrap_samples < 100:
            raise ValueError("bootstrap_samples must be >= 100 for valid CI")

        if not 0.0 <= self.coverage_requirement <= 1.0:
            raise ValueError("coverage_requirement must be in [0.0, 1.0]")
