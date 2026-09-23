"""Free-lunch intake gate (idp#3525 CP6, spec section 5b).

"Any other 'free lunch' claim SHALL be rejected at intake with its tradeoff
named." FL-01..04 are the only claims allowed to call themselves free of
downside; anything else must name what it costs before it is admitted.
"""

from __future__ import annotations

FREE_LUNCH_CLAIMS = ("FL-01", "FL-02", "FL-03", "FL-04")


class FreeLunchClaimRejected(Exception):
    pass


def admit_claim(claim_id: str, tradeoff: str | None = None) -> None:
    """Raise unless `claim_id` is one of the four named free-lunch
    invariants, or a tradeoff has been named for it explicitly."""
    if claim_id in FREE_LUNCH_CLAIMS:
        return
    if not tradeoff:
        raise FreeLunchClaimRejected(
            f"{claim_id!r} is not one of {FREE_LUNCH_CLAIMS}; "
            "name its tradeoff to admit it at intake"
        )
