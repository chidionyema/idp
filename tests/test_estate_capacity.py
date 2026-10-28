"""The capacity guard's rules, proved offline.

    pytest tests/test_estate_capacity.py

The estate's router died of capacity and the estate was blind to it: the vendor's 400 was
the first anybody read. These tests pin the rules that would have caught it before the
apply -- the live storage against the allowance, the nodes against the allowance, the pool
that cannot be reconciled, and the replica that can never be scheduled.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

IDP = Path(__file__).resolve().parent.parent
DOOR = IDP / "bin/idp-estate-capacity"


def _load():
    loader = importlib.machinery.SourceFileLoader("idp_estate_capacity", str(DOOR))
    spec = importlib.util.spec_from_loader("idp_estate_capacity", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


door = _load()


def _volume(size: int, state: str) -> dict:
    return {"size-in-gbs": size, "lifecycle-state": state}


def _instance(name: str, state: str) -> dict:
    return {
        "display-name": name,
        "lifecycle-state": state,
        "shape": "VM.Standard.A1.Flex",
    }


def test_the_allowance_is_declared_once_in_the_repository():
    allowance = door.load_allowance()
    assert allowance["block_storage_gb"] == 200
    assert allowance["nodes_per_pool"] == 1


def test_a_missing_allowance_is_blind_not_a_default_of_zero():
    with pytest.raises(door.Blind):
        door.load_allowance(IDP / "platform/ladder/does-not-exist.json")


def test_live_storage_over_the_allowance_is_over():
    finding = door.storage_finding([_volume(50, "AVAILABLE")] * 5, 200)
    assert finding["verdict"] == door.OVER
    assert "250GB" in finding["measured"]


def test_live_storage_within_the_allowance_is_ok():
    finding = door.storage_finding([_volume(50, "AVAILABLE")] * 4, 200)
    assert finding["verdict"] == door.OK


def test_dead_volumes_are_counted_apart_from_the_live_ones():
    """A TERMINATED volume cannot be mounted, but it is still listed and the allowance it
    took is still gone. Counting it as live would be wrong; hiding it would be worse."""
    finding = door.storage_finding(
        [_volume(50, "AVAILABLE"), _volume(50, "TERMINATED")], 200
    )
    assert finding["verdict"] == door.OK
    assert "50GB live" in finding["measured"]
    assert "1 dead, 50GB" in finding["measured"]


def test_more_live_nodes_than_the_allowance_is_over():
    finding = door.node_finding(
        [_instance("oke-a-0", "RUNNING"), _instance("oke-a-1", "RUNNING")], 1
    )
    assert finding["verdict"] == door.OVER
    assert "2 live node(s)" in finding["measured"]


def test_a_stopped_node_is_capacity_spent_on_silence():
    finding = door.node_finding(
        [_instance("oke-a-0", "RUNNING"), _instance("oke-a-1", "STOPPED")], 1
    )
    assert finding["verdict"] == door.OK
    assert "1 stopped" in finding["measured"]
    assert "serve nothing" in finding["detail"]


def test_one_live_node_is_ok():
    finding = door.node_finding([_instance("oke-a-0", "RUNNING")], 1)
    assert finding["verdict"] == door.OK


def test_a_pool_that_cannot_be_reconciled_is_blocked():
    """MEASURED 2026-10-28: pool a1 is NEEDS_ATTENTION, and OKE refuses every apply while
    the pool is over the free tier's limit."""
    findings = door.pool_finding(
        [{"name": "a1", "lifecycle-state": "NEEDS_ATTENTION"}], 1
    )
    assert findings[0]["verdict"] == door.BLOCKED
    assert "cannot reconcile" in findings[0]["detail"]


def test_an_active_pool_is_ok():
    findings = door.pool_finding([{"name": "a1", "lifecycle-state": "ACTIVE"}], 1)
    assert findings[0]["verdict"] == door.OK


def test_two_replicas_on_one_node_with_a_hard_spread_is_over():
    """MEASURED 2026-10-28: available=1 desired=2 with a DoNotSchedule spread on a
    one-node pool. The deployment looks healthy and the edge answers 503."""
    finding = door.replica_finding(2, 1)
    assert finding["verdict"] == door.OVER
    assert "never be scheduled" in finding["detail"]


def test_one_replica_on_one_node_is_ok():
    assert door.replica_finding(1, 1)["verdict"] == door.OK


def test_nothing_to_compare_is_ok_not_a_failure():
    assert door.replica_finding(0, 0)["verdict"] == door.OK


def test_the_board_names_every_over_check():
    findings = [
        {
            "check": "block storage",
            "measured": "250GB",
            "allowance": "200GB",
            "verdict": door.OVER,
            "detail": "over",
        },
        {
            "check": "node pool a1",
            "measured": "NEEDS_ATTENTION",
            "allowance": "1",
            "verdict": door.BLOCKED,
            "detail": "blocked",
        },
        {
            "check": "worker nodes",
            "measured": "1",
            "allowance": "1",
            "verdict": door.OK,
            "detail": "",
        },
    ]
    text = door.render(findings)
    assert "OVER" in text
    assert "BLOCK" in text
    assert "-> over" in text


def test_the_manifest_is_asked_for_its_replicas():
    assert door.wanted_replicas() == 2, (
        "the LiteLLM manifest changed: the guard's replica check is against what the "
        "manifest asks for, so a change here must be a change there too"
    )
