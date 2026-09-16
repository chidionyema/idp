#!/usr/bin/env python3
"""ParEvalLayer comparison policy selection and defaults for coding tasks.

Policy must be chosen before evaluation begins.
Defaults are tuned for SWE-bench-style coding task evaluation.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class ComparisonPolicy:
    """
    Deterministic comparison policy for partial evaluation.
    Specifies required evidence to declare "better", "not better", or "abstain".
    """

    required_margin: float = 0.05  # percentage points
    task_order: Literal["random", "stratified_random", "difficulty_ascending"] = (
        "stratified_random"
    )
    min_strata_coverage: float = 1.0  # [0.0, 1.0]
    min_observations_per_stratum: int = 2
    false_positive_target: float = 0.05  # max acceptable FP rate
    false_negative_target: float = 0.10  # max acceptable FN rate
    allowed_unresolved_rate: float = 0.10  # max abstain rate
    max_tasks: int = 100
    max_wall_clock_minutes: int = 120
    confidence_level: float = 0.95  # for CI computation


# === DEFAULTS FOR CODING TASKS ===

CODING_TASK_POLICY_PROMPT_ITERATION = ComparisonPolicy(
    required_margin=0.03,  # 3pp; small prompt changes
    task_order="stratified_random",
    min_strata_coverage=1.0,
    min_observations_per_stratum=2,
    false_positive_target=0.05,
    false_negative_target=0.10,
    allowed_unresolved_rate=0.10,
    max_tasks=50,
    max_wall_clock_minutes=60,
)

CODING_TASK_POLICY_MODEL_SWAP = ComparisonPolicy(
    required_margin=0.08,  # 8pp; larger expected effect
    task_order="stratified_random",
    min_strata_coverage=1.0,
    min_observations_per_stratum=2,
    false_positive_target=0.05,
    false_negative_target=0.10,
    allowed_unresolved_rate=0.10,
    max_tasks=75,
    max_wall_clock_minutes=90,
)

CODING_TASK_POLICY_ARCHITECTURE_CHANGE = ComparisonPolicy(
    required_margin=0.12,  # 12pp; high cost, require strong evidence
    task_order="stratified_random",
    min_strata_coverage=1.0,
    min_observations_per_stratum=3,
    false_positive_target=0.02,  # stricter for major changes
    false_negative_target=0.10,
    allowed_unresolved_rate=0.05,
    max_tasks=100,
    max_wall_clock_minutes=120,
)

CODING_TASK_POLICY_SAFETY_GATE = ComparisonPolicy(
    required_margin=0.00,  # no regression tolerance
    task_order="stratified_random",
    min_strata_coverage=1.0,
    min_observations_per_stratum=5,  # more evidence for safety
    false_positive_target=0.01,  # very strict
    false_negative_target=0.05,
    allowed_unresolved_rate=0.02,
    max_tasks=100,
    max_wall_clock_minutes=120,
)


class PolicyValidator:
    """Validates policy choices against engineering constraints."""

    @staticmethod
    def validate(policy: ComparisonPolicy) -> dict:
        """
        Validate policy parameters. Return dict with status and any issues.
        """
        issues = []

        if policy.required_margin < 0 or policy.required_margin > 0.5:
            issues.append("required_margin must be in [0.0, 0.5]")

        if policy.min_strata_coverage < 0 or policy.min_strata_coverage > 1.0:
            issues.append("min_strata_coverage must be in [0.0, 1.0]")

        if policy.false_positive_target + policy.false_negative_target > 0.2:
            issues.append(
                "Sum of FP + FN targets exceeds 20% (leaves < 80% confidence)"
            )

        if policy.allowed_unresolved_rate > 0.3:
            issues.append("allowed_unresolved_rate > 30% makes decisions unreliable")

        if policy.max_tasks < 20:
            issues.append("max_tasks should be >= 20 for statistical validity")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "policy_type": policy.__class__.__name__,
        }

    @staticmethod
    def select_policy(change_type: str) -> ComparisonPolicy:
        """
        Select appropriate policy based on change type.
        """
        policies = {
            "prompt_iteration": CODING_TASK_POLICY_PROMPT_ITERATION,
            "model_swap": CODING_TASK_POLICY_MODEL_SWAP,
            "architecture": CODING_TASK_POLICY_ARCHITECTURE_CHANGE,
            "safety": CODING_TASK_POLICY_SAFETY_GATE,
        }
        return policies.get(change_type, CODING_TASK_POLICY_MODEL_SWAP)
