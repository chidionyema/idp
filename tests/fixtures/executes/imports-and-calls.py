# must-pass fixture for the executes gate, and the exact shape the old word-list regex refused:
# it imports a first-party module and CALLS it, then asserts on the computed value. No process,
# no socket -- the strongest test shape this repository has, and a word list cannot see it.
from fleetview_backend import approvals_adapter as aa


def test_a_staged_ledger_whose_patch_vanished_is_approved() -> None:
    prev = {"L1": frozenset({"pending", "staged"})}
    assert aa._transitions(prev, proposals=set(), staged=set()) == [("L1", "approved")]
