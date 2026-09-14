"""The proof this proposal claims it carries -- and which does not hold.

The structural stage passes (the bytes compile) and the symbolic stage passes (no
refutable guard is declared). The execution stage runs pytest in a sterile tree and
the test below fails there. So the claim is refused and no attestation is minted.

This is the shape of the incident the module exists for: a proposal that is valid
Python, claims success, and carries no proof -- refused by a grader the proposer does
not write.
"""

from proposal import main


def test_the_proposal_does_the_thing_it_claims() -> None:
    assert main() == 0, "the proposal returns 1; the claim it carries does not hold"
