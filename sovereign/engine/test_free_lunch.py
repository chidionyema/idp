"""idp#3525 CP6: "Any other 'free lunch' claim SHALL be rejected at intake
with its tradeoff named."
"""

from __future__ import annotations

import pytest

from sovereign.engine.free_lunch import FreeLunchClaimRejected, admit_claim


@pytest.mark.parametrize("claim_id", ["FL-01", "FL-02", "FL-03", "FL-04"])
def test_the_four_named_invariants_are_admitted_with_no_tradeoff(claim_id: str) -> None:
    admit_claim(claim_id)  # must not raise


def test_an_unnamed_claim_with_no_tradeoff_is_rejected() -> None:
    with pytest.raises(FreeLunchClaimRejected):
        admit_claim("FL-99")


def test_an_unnamed_claim_is_admitted_once_its_tradeoff_is_named() -> None:
    admit_claim(
        "FL-99", tradeoff="adds 200ms p99 latency for a 10% cost cut"
    )  # must not raise


def test_an_empty_tradeoff_string_still_counts_as_unnamed() -> None:
    with pytest.raises(FreeLunchClaimRejected):
        admit_claim("FL-99", tradeoff="")
