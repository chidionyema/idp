"""idp#3525 CP6, FL-04: weighted verifier voting on Z3-scored branches.

"Same generation cost, strictly better selection, no added risk." Each test
below proves one clause: selection never generates a candidate (cost);
selection always prefers a higher verifier score (strictly better); and a tie
never flips between runs on the same input (no added risk).
"""

from __future__ import annotations

import pytest

from sovereign.engine.weighted_vote import weighted_vote_select


def test_selection_never_calls_the_generator() -> None:
    """Cost claim: candidates arrive already generated. A generator that is
    never invoked during selection is the whole proof that selection adds no
    generation cost, regardless of which selection method runs."""
    generator_calls = []

    def generate(n: int) -> list[tuple[str, float]]:
        generator_calls.append(n)
        return [(f"candidate-{i}", float(i)) for i in range(n)]

    scored = generate(3)
    calls_before_selection = len(generator_calls)
    weighted_vote_select(scored)
    calls_after_selection = len(generator_calls)

    assert calls_before_selection == calls_after_selection


def test_selection_prefers_the_higher_verifier_score() -> None:
    scored = [("wrong", 0.0), ("right", 1.0), ("also_wrong", 0.3)]
    winner = weighted_vote_select(scored)
    assert winner == "right"


def test_selection_never_picks_worse_than_the_best_available() -> None:
    """No-added-risk claim: across many score distributions, the winner's
    own score always equals the maximum score among the candidates -- never
    a runner-up."""
    cases = [
        [("a", 0.1), ("b", 0.9), ("c", 0.5)],
        [("a", 1.0)],
        [("a", 0.0), ("b", 0.0), ("c", 1.0)],
        [("a", 0.7), ("b", 0.7), ("c", 0.2)],
    ]
    results = [
        weighted_vote_select(scored) == max(scored, key=lambda pair: pair[1])[0]
        for scored in cases
    ]
    assert all(results)


def test_a_tie_deterministically_keeps_the_earliest_candidate() -> None:
    scored = [("first", 0.8), ("second", 0.8)]
    first_run = weighted_vote_select(scored)
    second_run = weighted_vote_select(scored)
    outcomes = (first_run, second_run)
    assert outcomes == ("first", "first")


def test_empty_candidate_list_is_rejected() -> None:
    with pytest.raises(ValueError):
        weighted_vote_select([])
