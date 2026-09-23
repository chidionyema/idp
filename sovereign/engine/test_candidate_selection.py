"""idp#3525 CP4, VER-02 (eval suite) / VER-04 (property test).

Binds sovereign/engine/candidate_selection.py against the spec's own ACCEPT lines.
"""

from __future__ import annotations

import pytest

from sovereign.engine.candidate_selection import (
    MAX_UNVERIFIED_N,
    assert_selection_policy,
    has_real_verifier,
    resolve_candidate_volume,
)
from sovereign.engine.routing_matrix import RoutingMatrixError


# ---------------------------------------------------------------------------
# VER-02 -- eval suite: weighted-vote/multi-verifier honored for verified
# domains, plain best-of-N disallowed there.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["patch.py", "manifest.yaml", "schema.sql"])
def test_a_z3_scored_domain_reports_a_real_verifier(path: str) -> None:
    assert has_real_verifier(path) is True


def test_an_unverifiable_domain_reports_no_real_verifier() -> None:
    assert has_real_verifier("notes.md") is False


@pytest.mark.parametrize("method", ["weighted_vote", "multi_verifier"])
def test_the_harness_honors_verifier_backed_selection_for_a_verified_domain(
    method: str,
) -> None:
    cell = {"candidate_volume": 3, "selection_method": method}
    assert assert_selection_policy("patch.py", cell) is None  # does not raise


def test_plain_best_of_n_is_disallowed_where_a_real_verifier_exists() -> None:
    cell = {"candidate_volume": 3, "selection_method": "gate"}
    with pytest.raises(RoutingMatrixError, match="noisy selector is disallowed"):
        assert_selection_policy("patch.py", cell)


def test_a_single_candidate_needs_no_selection_among_candidates() -> None:
    cell = {"candidate_volume": 1, "selection_method": "gate"}
    assert assert_selection_policy("patch.py", cell) is None  # does not raise


def test_selection_policy_is_not_enforced_on_an_unverifiable_domain() -> None:
    cell = {"candidate_volume": 5, "selection_method": "gate"}
    assert assert_selection_policy("notes.md", cell) is None  # does not raise


# ---------------------------------------------------------------------------
# VER-04 -- property test: N is capped at MAX_UNVERIFIED_N for an unverifiable
# domain regardless of the requested/config value, and untouched for a
# verified one.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("requested_n", [1, 2, 3, 4, 5, 10, 50, 1000])
def test_n_is_capped_on_an_unverifiable_domain_regardless_of_config(
    requested_n: int,
) -> None:
    resolved = resolve_candidate_volume("notes.md", requested_n)
    assert resolved <= MAX_UNVERIFIED_N
    assert resolved == min(requested_n, MAX_UNVERIFIED_N)


@pytest.mark.parametrize("requested_n", [1, 2, 3, 4, 5, 10, 50, 1000])
def test_n_passes_through_unchanged_on_a_verified_domain(requested_n: int) -> None:
    assert resolve_candidate_volume("patch.py", requested_n) == requested_n


def test_no_config_value_can_raise_n_above_the_declared_constant() -> None:
    # The declared constant, not a config knob: even a config asking for the largest N this
    # module will accept still comes back capped.
    for requested_n in range(0, 10_000, 137):
        assert (
            resolve_candidate_volume("unverifiable.md", requested_n) <= MAX_UNVERIFIED_N
        )
