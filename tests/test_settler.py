"""Regression canaries for independent instruction settlement."""

import pytest

from settler import Custody, MockProbe, Probe, ProbeReceipt


def test_worker_and_supervisor_cannot_settle():
    world = {}
    c = Custody(MockProbe(world))
    c.admit("W1", "GET /health==200")
    c.lease("W1", expected_commit_sha="aaa")
    assert c.on_worker_exit("W1", "MISSION_COMPLETE") == "DELIVERED"
    assert c.on_supervisor_verdict("W1", True) == "DELIVERED"
    world["W1"] = dict(epoch=1, sha="aaa", effect_present=False)
    assert c.record_yield("W1", agent_claim="done") == "DELIVERED"
    world["W1"]["effect_present"] = True
    assert c.record_yield("W1") == "SETTLED"
    assert c.record_yield("W1") == "SETTLED"
    assert len(c._settled_keys) == 1


def test_stale_epoch_and_wrong_revision():
    world = {}
    c = Custody(MockProbe(world))
    c.admit("W2", "effect")
    c.lease("W2", expected_commit_sha="old")
    c.lease("W2", expected_commit_sha="new")
    world["W2"] = dict(epoch=1, sha="old", effect_present=True)
    assert c.record_yield("W2") == "LEASED"
    assert c.on_worker_exit("W2", "done", epoch=1) == "LEASED"
    world["W2"]["epoch"] = 2
    assert c.record_yield("W2") == "LEASED"
    world["W2"]["sha"] = "new"
    assert c.record_yield("W2") == "SETTLED"


def test_capability_exhaustion_retains_obligation():
    c = Custody(MockProbe({}))
    c.admit("W3", "effect")
    assert c.on_capability_exhausted("W3") == "RECOVERING"
    assert c.lease("W3", expected_commit_sha="aaa") == 1


def test_terminal_states_and_duplicate_admission():
    world = {"W4": dict(epoch=1, sha="aaa", effect_present=True)}
    c = Custody(MockProbe(world), authorize_cancel=lambda *args: True)
    c.admit("W4", "effect")
    c.lease("W4", expected_commit_sha="aaa")
    assert c.record_yield("W4") == "SETTLED"
    assert c.on_capability_exhausted("W4") == "SETTLED"
    assert c.cancel("W4", "signature") == "SETTLED"
    with pytest.raises(ValueError):
        c.lease("W4")
    with pytest.raises(ValueError):
        c.admit("W4", "replacement")


def test_cancel_requires_authorizer_and_cannot_resurrect():
    world = {"W5": dict(epoch=1, sha="aaa", effect_present=True)}
    c = Custody(MockProbe(world))
    c.admit("W5", "effect")
    assert c.cancel("W5", "not-a-signature") == "ADMITTED"
    c = Custody(
        MockProbe(world),
        authorize_cancel=lambda iid, epoch, sig: (
            (iid, epoch, sig) == ("W5", 1, "test-proof")
        ),
    )
    c.admit("W5", "effect")
    c.lease("W5", expected_commit_sha="aaa")
    assert c.cancel("W5", "bad") == "LEASED"
    assert c.cancel("W5", "test-proof") == "CANCELLED"
    assert c.record_yield("W5") == "CANCELLED"
    assert c.on_capability_exhausted("W5") == "CANCELLED"


def test_unbound_revision_cannot_settle():
    world = {"W6": dict(epoch=1, sha="aaa", effect_present=True)}
    c = Custody(MockProbe(world))
    c.admit("W6", "effect")
    assert c.record_yield("W6") == "ADMITTED"
    c.lease("W6")
    assert c.record_yield("W6") == "LEASED"


def test_wrong_instruction_and_probe_exception():
    class WrongProbe(Probe):
        def verify(self, iid):
            return ProbeReceipt("other", 1, "aaa", True)

    class FailedProbe(Probe):
        def verify(self, iid):
            raise OSError("unreachable")

    for probe in (WrongProbe(), FailedProbe()):
        c = Custody(probe)
        c.admit("W7", "effect")
        c.lease("W7", expected_commit_sha="aaa")
        assert c.record_yield("W7") == "LEASED"


def test_lease_change_during_probe_is_fenced():
    class RacingProbe(Probe):
        def verify(self, iid):
            c.lease(iid, expected_commit_sha="new")
            return ProbeReceipt(iid, 1, "old", True)

    c = Custody(RacingProbe())
    c.admit("W8", "effect")
    c.lease("W8", expected_commit_sha="old")
    assert c.record_yield("W8") == "LEASED"
    assert c.instr["W8"]["epoch"] == 2
