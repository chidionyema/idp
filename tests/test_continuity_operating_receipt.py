"""Operational yield is a reconciled observed effect, not an agent adjective."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform" / "estate"))
from continuity import InvalidTransition, MissionStore, StaleFenceError  # noqa: E402


def staged(tmp_path):
    store = MissionStore(tmp_path / "custody.sqlite")
    store.accept_mission(
        {
            "mission_id": "m-test",
            "instruction_id": "idp#7443",
            "mandate_id": "founder",
            "goal": "live operational acceptance",
            "acceptance_contract_digest": "a" * 64,
            "risk_class": "HIGH",
        }
    )
    store.transition("m-test", "READY", "estate", "dispatch")
    lease = store.acquire_lease(
        "m-test",
        {
            "agent_adapter": "legion",
            "provider": "test",
            "model": "test",
            "execution_host": "cloud",
            "failure_domain": "runner",
            "worktree_id": "test",
            "base_sha": "a" * 40,
        },
        lease_seconds=600,
    )
    for stage in ("EXECUTING", "VERIFYING", "PROMOTING", "DEPLOY_VERIFY"):
        store.transition(
            "m-test",
            stage,
            "executor-a",
            "phase",
            attempt_id=lease["attempt_id"],
            lease_epoch=lease["lease_epoch"],
        )
    return store, lease


def effect(store, lease, *, reconciled=True, verifier="observer-b"):
    intent = store.record_effect_intent(
        "m-test",
        lease["attempt_id"],
        lease["lease_epoch"],
        "external-test",
        "example.invalid",
        "test-once",
        {"expected": "ok"},
    )
    store.record_receipt(
        intent["effect_id"],
        {"observed": "ok"},
        verified_by=verifier,
        reconciliation_status="RECONCILED" if reconciled else "AMBIGUOUS",
    )
    return intent["effect_id"]


def operating(store, lease, evidence="", actor="executor-a"):
    return store.transition(
        "m-test",
        "OPERATING",
        actor,
        "claimed operational",
        evidence=evidence,
        attempt_id=lease["attempt_id"],
        lease_epoch=lease["lease_epoch"],
    )


@pytest.mark.parametrize("assertion", ["", "tests green", "merged", "effect:missing"])
def test_unverified_words_cannot_settle(tmp_path, assertion):
    store, lease = staged(tmp_path)
    with pytest.raises(InvalidTransition):
        operating(store, lease, assertion)
    assert store.get_mission("m-test")["state"] == "DEPLOY_VERIFY"
    store.close()


def test_ambiguous_effect_cannot_settle(tmp_path):
    store, lease = staged(tmp_path)
    eid = effect(store, lease, reconciled=False)
    with pytest.raises(InvalidTransition, match="reconciled"):
        operating(store, lease, "effect:" + eid)
    store.close()


def test_executor_cannot_self_certify(tmp_path):
    store, lease = staged(tmp_path)
    eid = effect(store, lease, verifier="executor-a")
    with pytest.raises(InvalidTransition, match="executor"):
        operating(store, lease, "effect:" + eid)
    store.close()


def test_reconciled_observation_is_linked_to_event_and_terminal(tmp_path):
    store, lease = staged(tmp_path)
    eid = effect(store, lease)
    assert operating(store, lease, "effect:" + eid)["state"] == "OPERATING"
    row = store.db.execute(
        "SELECT evidence, created_at FROM mission_events "
        "WHERE mission_id='m-test' AND to_state='OPERATING'"
    ).fetchone()
    assert row["evidence"] == "effect:" + eid and row["created_at"] > 0
    with pytest.raises((InvalidTransition, StaleFenceError)):
        operating(store, lease, "effect:" + eid)
    store.close()


def test_operating_is_not_yield_or_settlement(tmp_path):
    store, lease = staged(tmp_path)
    eid = effect(store, lease)
    operating(store, lease, "effect:" + eid)
    assert store.get_mission("m-test")["state"] == "OPERATING"
    with pytest.raises(InvalidTransition, match="yield"):
        store.transition(
            "m-test",
            "YIELD_PROVEN",
            "executor-a",
            "declared yield",
            attempt_id=lease["attempt_id"],
            lease_epoch=lease["lease_epoch"],
        )
    assert store.get_mission("m-test")["state"] == "OPERATING"
    store.close()


def test_measured_yield_requires_distinct_certifiers(tmp_path):
    store, lease = staged(tmp_path)
    eid = effect(store, lease)
    operating(store, lease, "effect:" + eid)
    with pytest.raises(InvalidTransition, match="target not met"):
        store.record_yield_proof(
            "m-test",
            lease["attempt_id"],
            lease["lease_epoch"],
            eid,
            "completed_jobs",
            0,
            0,
            1,
            "external:jobs",
            "optimus-b",
        )
    with pytest.raises(InvalidTransition, match="effect observer"):
        store.record_yield_proof(
            "m-test",
            lease["attempt_id"],
            lease["lease_epoch"],
            eid,
            "completed_jobs",
            0,
            2,
            1,
            "external:jobs",
            "observer-b",
        )
    proof = store.record_yield_proof(
        "m-test",
        lease["attempt_id"],
        lease["lease_epoch"],
        eid,
        "completed_jobs",
        0,
        2,
        1,
        "external:jobs",
        "optimus-b",
    )
    with pytest.raises(InvalidTransition, match="independent"):
        store.transition(
            "m-test",
            "YIELD_PROVEN",
            "optimus-b",
            "self-declared",
            evidence="yield:" + proof["proof_id"],
            attempt_id=lease["attempt_id"],
            lease_epoch=lease["lease_epoch"],
        )
    assert (
        store.transition(
            "m-test",
            "YIELD_PROVEN",
            "executor-a",
            "measured",
            evidence="yield:" + proof["proof_id"],
            attempt_id=lease["attempt_id"],
            lease_epoch=lease["lease_epoch"],
        )["state"]
        == "YIELD_PROVEN"
    )
    with pytest.raises(InvalidTransition, match="separate independent"):
        store.transition(
            "m-test",
            "SETTLED",
            "optimus-b",
            "self-certification",
            evidence="yield:" + proof["proof_id"],
            attempt_id=lease["attempt_id"],
            lease_epoch=lease["lease_epoch"],
        )
    assert (
        store.transition(
            "m-test",
            "SETTLED",
            "auditor-c",
            "independent settlement",
            evidence="yield:" + proof["proof_id"],
            attempt_id=lease["attempt_id"],
            lease_epoch=lease["lease_epoch"],
        )["state"]
        == "SETTLED"
    )
    assert (
        store.db.execute(
            "SELECT settled_by FROM mission_yield_proofs WHERE proof_id=?",
            (proof["proof_id"],),
        ).fetchone()["settled_by"]
        == "auditor-c"
    )
    store.close()
