"""idp#3525 CP5, ORCH-02: sovereign/shadow/branching.params()'s new,
purely-additive `tier` argument.

cp1-cp4's branching.params() call sites (sb branch, sovereign/cli.py,
sovereign/tests/bdd/test_cp27.py) never pass tier -- the first test below
is the regression guarantee that none of them silently changed.
"""

from __future__ import annotations

import pytest

from sovereign.shadow import branching


def test_omitting_tier_leaves_count_exactly_as_before() -> None:
    from sovereign import config

    p = branching.params("task", runner="codex", repo=None, budget=1000)
    assert p["count"] == int(config.get("branch.count").value)


def test_explicit_count_still_wins_even_with_a_tier_given() -> None:
    p = branching.params(
        "task",
        runner="codex",
        repo=None,
        budget=1000,
        count=7,
        tier="flat_rate_apple_silicon",
    )
    assert p["count"] == 7


def test_flat_rate_tier_derives_count_from_the_time_box_not_budget_pct() -> None:
    p = branching.params(
        "task",
        runner="codex",
        repo=None,
        budget=1000,
        tier="flat_rate_apple_silicon",
        time_box_s=3600,
        step_s=300,
    )
    assert p["count"] == 12  # 3600 // 300, independent of branch.budget_pct


def test_metered_tier_derives_count_from_the_dollar_budget() -> None:
    p = branching.params(
        "task",
        runner="codex",
        repo=None,
        budget=100,
        tier="router_metered",
        time_box_s=1,  # deliberately tiny: must not move the result on a metered tier
        step_s=300,
        cost_per_candidate_usd=2.0,
    )
    from sovereign import config

    budget_pct = int(config.get("branch.budget_pct").value)
    assert p["count"] == max(1, int(100 * budget_pct / 100 // 2.0))


def test_tier_without_a_time_box_or_step_is_refused() -> None:
    with pytest.raises(ValueError):
        branching.params(
            "task",
            runner="codex",
            repo=None,
            budget=1000,
            tier="flat_rate_apple_silicon",
        )
