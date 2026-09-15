"""Weighted verifier voting over Z3-scored candidate branches (idp#3525 CP6, FL-04).

"Weighted verifier voting on Z3-scored branches: same generation cost, strictly
better selection, no added risk." The candidates this module selects among are
already generated -- selection here is a pure, in-memory comparison over
scores that were already computed, so it can never trigger another model
call; its own cost is exactly the cost of comparing N floats.
"""

from __future__ import annotations

from typing import Any


def weighted_vote_select(scored: list[tuple[Any, float]]) -> Any:
    """Return the candidate with the highest verifier score. A tie keeps the
    earliest candidate at that score, so the result is deterministic for a
    fixed input -- the "no added risk" half of FL-04: given the same
    evidence, this never behaves differently between two runs."""
    if not scored:
        raise ValueError("weighted_vote_select requires at least one scored candidate")
    best_value, best_score = scored[0]
    for value, score in scored[1:]:
        if score > best_score:
            best_value, best_score = value, score
    return best_value
