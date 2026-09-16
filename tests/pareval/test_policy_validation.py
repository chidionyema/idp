#!/usr/bin/env python3
"""ParEvalLayer policy validation tests.
Verifies that partial evaluation decisions match full-run decisions, against
the real PartialEvalDecisionLayer (platform/eval/pareval_layer.py), not a
MagicMock standing in for behaviour nothing here ever calls.
"""

import os
import random
import sys
import importlib.util


def _load_pareval_layer():
    """platform/ has no __init__.py (idp#3564: it collides with the stdlib
    `platform` module the moment anything imports it bare, which pytest itself
    does at startup). Loading platform.eval.pareval_layer by file path and
    seeding sys.modules under its real dotted name sidesteps that collision."""
    idp_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    for dotted, rel in [
        ("platform.eval", "platform/eval/__init__.py"),
        ("platform.eval.pareval_layer", "platform/eval/pareval_layer.py"),
    ]:
        if dotted in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(
            dotted, os.path.join(idp_root, rel)
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[dotted] = module
        spec.loader.exec_module(module)


_load_pareval_layer()

from platform.eval.pareval_layer import PartialEvalDecisionLayer, Decision  # noqa: E402


def test_partial_decision_matches_full_at_20_percent():
    """
    Contract for ParEvalLayer: A decision issued once evidence is sufficient
    must match the direction of a clear, consistent underlying advantage.
    """
    layer = PartialEvalDecisionLayer()
    # A consistently, substantially better than B across two strata.
    for i in range(20):
        layer.observe(f"t_{i}", 0.9, 0.5, stratum="small")
        layer.observe(f"t_{i}", 0.85, 0.55, stratum="large")

    decision = layer.decide()
    assert decision == Decision.A_BETTER, (
        f"Expected A_BETTER for a consistent advantage, got {decision}"
    )
    assert layer.ci_lower > 0, "CI should exclude zero when A is clearly better"


def test_coverage_requirement_enforced():
    """
    Contract for ParEvalLayer: Decision must not be issued
    until every observed stratum has been observed at least
    min_observations_per_stratum times.
    """
    layer = PartialEvalDecisionLayer()
    for i in range(20):
        layer.observe(f"t_{i}", 0.9, 0.5, stratum="small")
    # Only one observation in the "large" stratum, below the default minimum of 2.
    layer.observe("t_large_1", 0.9, 0.5, stratum="large")

    assert not layer.coverage_ok, "Under-covered stratum should fail coverage_ok"
    assert layer.decide() == Decision.NEED_MORE_EVIDENCE, (
        "Decision issued without full stratum coverage"
    )


def test_false_positive_rate_within_target():
    """
    Contract for ParEvalLayer: False positive rate
    (declaring 'better' when A and B are drawn from the same distribution)
    must be <= 5%.
    """
    random.seed(7)
    trials = 60
    false_positives = 0

    for _ in range(trials):
        layer = PartialEvalDecisionLayer()
        for i in range(20):
            # No real difference: both scores drawn from the same distribution.
            a = 0.7 + random.uniform(-0.1, 0.1)
            b = 0.7 + random.uniform(-0.1, 0.1)
            layer.observe(f"t_{i}", a, b, stratum="small" if i % 2 == 0 else "large")
        if layer.decide() in (Decision.A_BETTER, Decision.B_BETTER):
            false_positives += 1

    fp_rate = false_positives / trials
    assert fp_rate <= 0.05, f"FP rate {fp_rate:.3f} > 0.05 over {trials} null trials"


def test_unresolved_rate_within_target():
    """
    Contract for ParEvalLayer: Abstain/unresolved (NEED_MORE_EVIDENCE) rate
    must be <= 10% once every trial has full coverage and enough
    observations to reach a real decision under a clear effect.
    """
    random.seed(11)
    trials = 40
    unresolved = 0

    for _ in range(trials):
        layer = PartialEvalDecisionLayer()
        for i in range(20):
            a = 0.9 + random.uniform(-0.02, 0.02)
            b = 0.5 + random.uniform(-0.02, 0.02)
            layer.observe(f"t_{i}", a, b, stratum="small" if i % 2 == 0 else "large")
        if layer.decide() == Decision.NEED_MORE_EVIDENCE:
            unresolved += 1

    unresolved_rate = unresolved / trials
    assert unresolved_rate <= 0.10, (
        f"Unresolved rate {unresolved_rate:.3f} > 0.10 over {trials} clear-effect trials"
    )


def test_stratified_task_ordering():
    """
    Contract for ParEvalLayer: coverage must reflect observations from every
    stratum actually sampled, not just the first one -- a decision layer that
    only ever saw one stratum must not report full coverage across several.
    """
    layer = PartialEvalDecisionLayer()
    for i in range(10):
        layer.observe(f"t_{i}", 0.9, 0.5, stratum="small")

    # Only "small" has been sampled; the layer has no way to know "medium" and
    # "large" strata exist at all, so its own coverage tracking must say so.
    assert layer.strata_seen == {"small"}, (
        f"Sampling only one stratum should be reflected as such, got {layer.strata_seen}"
    )

    layer.observe("t_med_0", 0.8, 0.6, stratum="medium")
    layer.observe("t_large_0", 0.7, 0.7, stratum="large")

    assert layer.strata_seen == {"small", "medium", "large"}, (
        f"Coverage should track every stratum sampled: {layer.strata_seen}"
    )


def test_bootstrap_confidence_interval():
    """
    Contract for ParEvalLayer: Compute 95% CI on decision confidence.
    Decision should only be issued if CI excludes the indifference boundary
    (a mean difference of zero).
    """
    layer = PartialEvalDecisionLayer()
    for i in range(20):
        layer.observe(f"t_{i}", 0.9, 0.5, stratum="small")
        layer.observe(f"t_{i}", 0.85, 0.55, stratum="large")

    indifference_boundary = 0.0
    assert layer.ci_lower > indifference_boundary, (
        f"CI [{layer.ci_lower}, {layer.ci_upper}] includes the indifference "
        "boundary, decision should not be confident"
    )
    assert layer.decide() != Decision.NEED_MORE_EVIDENCE
