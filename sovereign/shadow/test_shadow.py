"""Property tests for sovereign/shadow (rung 2). Run:
    cd sovereign && python -m pytest shadow/test_shadow.py -q

Rung 1 is the type: ShadowAuth.op is NonDestructiveOp, so a destructive
auto-authorization is a pyright error. What is left for a test is the
rule the type enforces at runtime, and the arithmetic of prediction and
confidence -- each as one property over every configured op or a swept
range, never as example cases.
"""
from __future__ import annotations

import random

import pytest

from sovereign import config
from sovereign.engine import ops
from sovereign.shadow import config_keys as ck
from sovereign.shadow import preauth


def _boundary(op_name: str) -> preauth.Boundary:
    return preauth.Boundary(
        kind=preauth.normalize_op(op_name), op=preauth.classify(op_name), remaining=0,
        predicted_costs=(1,), hit_at_step=1, refill=1000, steps_covered=1,
    )


def test_property_no_destructive_or_unknown_op_is_ever_shadow_authorized() -> None:
    """At confidence 1.0 -- higher than any threshold -- every destructive
    op and every unknown op still comes back as an Ask."""
    names = list(config.OPS_DESTRUCTIVE) + ["git push --force", "rm -rf /", "", "not_in_any_table"]
    for name in names:
        verdict = preauth.decide(_boundary(name), 1.0, 0.0)
        assert isinstance(verdict, preauth.Ask), name
        assert verdict.reason in (ops.DESTRUCTIVE, ops.UNKNOWN_CLASS)


def test_property_every_nondestructive_op_is_shadow_authorized_only_above_threshold() -> None:
    threshold = float(config.get("shadow.min_confidence").value)
    for name in config.OPS_NONDESTRUCTIVE:
        above = preauth.decide(_boundary(name), threshold, threshold)
        below = preauth.decide(_boundary(name), threshold - 1e-9, threshold)
        assert isinstance(above, preauth.ShadowAuth), name
        assert isinstance(below, preauth.Ask) and below.reason == "low_confidence", name


def test_runtime_backstop_refuses_a_destructive_op_smuggled_past_the_type() -> None:
    fake = preauth.NonDestructiveOp("git_push_force", 100)  # what a cast would produce
    with pytest.raises(TypeError):
        preauth.ShadowAuth(_boundary("fs_commit"), fake, 1.0)


def test_property_prediction_finds_a_boundary_exactly_when_the_horizon_costs_more_than_remaining() -> None:
    rng = random.Random(26)
    horizon = int(ck.get("shadow.horizon_steps"))
    round_to = int(ck.get("shadow.refill_round_to"))
    for _ in range(500):
        remaining = rng.randint(0, 20_000)
        costs = [rng.randint(0, 8_000) for _ in range(rng.randint(0, horizon + 2))]
        boundary = preauth.predict(remaining, costs, horizon)
        window = costs[:horizon]
        if sum(window) <= remaining:
            assert boundary is None
        else:
            assert boundary is not None
            assert remaining + boundary.refill >= sum(window), "the refill covers the whole trajectory"
            assert boundary.refill % round_to == 0
            assert 1 <= boundary.hit_at_step <= len(window)
            assert boundary.steps_covered == len(window)
            assert isinstance(boundary.op, preauth.NonDestructiveOp), "a refill is a budget movement, not a destructive act"


def test_property_confidence_is_zero_below_min_samples_and_monotonic_in_approvals() -> None:
    minimum = int(ck.get("shadow.min_samples"))
    for samples in range(0, minimum):
        assert preauth.confidence(preauth.History("x", samples, 0)) == 0.0
    last = 0.0
    for approvals in range(minimum, minimum + 200):
        c = preauth.confidence(preauth.History("x", approvals, 0))
        assert c >= last and c < 1.0
        last = c
    assert preauth.confidence(preauth.History("x", minimum, 0)) >= float(config.get("shadow.min_confidence").value)
    assert preauth.confidence(preauth.History("x", minimum, 1)) < preauth.confidence(preauth.History("x", minimum, 0))


def test_property_op_names_fold_onto_the_table_form() -> None:
    for raw, folded in (("git push --force", "git_push_force"), (" FS_COMMIT ", "fs_commit"), ("db drop", "db_drop")):
        assert preauth.normalize_op(raw) == folded
        assert preauth.classify(raw).name == folded
