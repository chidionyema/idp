"""The proof this proposal claims it carries, run in the sterile tree.

The execution stage writes this next to the proposal as `test_supplied.py` and runs
pytest there. Whatever this says is the verdict -- not anything the proposing agent
declared about it.
"""

from proposal import main


def test_the_proposal_does_the_thing_it_claims() -> None:
    assert main() == 0
