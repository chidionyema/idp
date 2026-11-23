"""Operational yield is a reconciled observed effect, not an agent adjective."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform" / "estate"))
from continuity import (  # noqa: E402
    DuplicateEffect,
    InvalidTransition,
    MissionStore,
    StaleFenceError,
)


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


@pytest.mark.parametrize("verifier", ["executor-a", "legion"])
def test_executor_cannot_self_certify(tmp_path, verifier):
    store, lease = staged(tmp_path)
    eid = effect(store, lease, verifier=verifier)
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


def test_ambiguous_observation_can_be_reconciled_and_settled(tmp_path):
    store, lease = staged(tmp_path)
    eid = effect(store, lease, reconciled=False)
    with pytest.raises(InvalidTransition, match="reconciled"):
        operating(store, lease, "effect:" + eid)
    result = store.record_receipt(
        eid,
        {"observed": "ok"},
        verified_by="observer-b",
        reconciliation_status="RECONCILED",
    )
    assert result["duplicate"] is False
    row = store.db.execute(
        "SELECT state, reconciliation_status FROM external_effects WHERE effect_id=?",
        (eid,),
    ).fetchone()
    assert (row["state"], row["reconciliation_status"]) == ("OBSERVED", "RECONCILED")
    assert operating(store, lease, "effect:" + eid)["state"] == "OPERATING"
    store.close()


def test_certified_effect_receipt_is_immutable_and_idempotent(tmp_path):
    store, lease = staged(tmp_path)
    eid = effect(store, lease)
    original = store.db.execute(
        "SELECT external_receipt, verified_by, observed_at FROM external_effects"
        " WHERE effect_id=?",
        (eid,),
    ).fetchone()
    assert store.record_receipt(
        eid, {"observed": "ok"}, verified_by="observer-b"
    )["duplicate"] is True
    for receipt, verifier, reconciliation in [
        ({"observed": "different"}, "observer-b", "RECONCILED"),
        ({"observed": "ok"}, "executor-a", "RECONCILED"),
        ({"observed": "ok"}, "observer-b", "AMBIGUOUS"),
    ]:
        with pytest.raises(DuplicateEffect, match="immutable reconciled"):
            store.record_receipt(
                eid, receipt, verified_by=verifier,
                reconciliation_status=reconciliation,
            )
    final = store.db.execute(
        "SELECT external_receipt, verified_by, observed_at FROM external_effects"
        " WHERE effect_id=?",
        (eid,),
    ).fetchone()
    assert tuple(final) == tuple(original)
    store.close()


def test_recovery_must_not_erase_observed_and_reconciled_yield(tmp_path):
    store, lease = staged(tmp_path)
    eid = effect(store, lease)
    original = tuple(store.db.execute(
        "SELECT state, reconciliation_status, external_receipt, verified_by"
        " FROM external_effects WHERE effect_id=?", (eid,)
    ).fetchone())
    for outcome in ("NOT_STARTED", "AMBIGUOUS", "UNRECOGNISED"):
        with pytest.raises(DuplicateEffect):
            store.reconcile_effect(eid, "ignored", outcome)
    final = tuple(store.db.execute(
        "SELECT state, reconciliation_status, external_receipt, verified_by"
        " FROM external_effects WHERE effect_id=?", (eid,)
    ).fetchone())
    assert final == original
    assert operating(store, lease, "effect:" + eid)["state"] == "OPERATING"
    store.close()


def test_ambiguous_recovery_can_observe_real_completion(tmp_path):
    store, lease = staged(tmp_path)
    intent = store.record_effect_intent(
        "m-test", lease["attempt_id"], lease["lease_epoch"],
        "external-test", "example.invalid", "recover-once",
        {"expected": "ok"},
    )
    eid = intent["effect_id"]
    store.reconcile_effect(eid, "unmeasured", "AMBIGUOUS")
    assert store.pending_effects("m-test")[0]["effect_id"] == eid
    completed = store.reconcile_effect(
        eid, "observed-external-transaction", "COMPLETED"
    )
    assert completed["state"] == "OBSERVED" and not completed["duplicate"]
    assert store.pending_effects("m-test") == []
    assert operating(store, lease, "effect:" + eid)["state"] == "OPERATING"
    store.close()


def test_not_started_and_unknown_effects_are_not_false_success(tmp_path):
    store, lease = staged(tmp_path)
    intent = store.record_effect_intent(
        "m-test", lease["attempt_id"], lease["lease_epoch"],
        "external-test", "example.invalid", "not-started-once",
        {"expected": "ok"},
    )
    eid = intent["effect_id"]
    first = store.reconcile_effect(eid, "negative-observation", "NOT_STARTED")
    assert first["state"] == "ABANDONED" and not first["duplicate"]
    again = store.reconcile_effect(eid, "negative-observation", "NOT_STARTED")
    assert again["duplicate"] is True
    with pytest.raises(InvalidTransition):
        operating(store, lease, "effect:" + eid)
    for outcome in ("NOT_STARTED", "AMBIGUOUS"):
        with pytest.raises(DuplicateEffect, match="unknown effect"):
            store.reconcile_effect("e-missing", "", outcome)
    store.close()


def _progress_clock(store, lease):
    return store.db.execute(
        "SELECT last_progress_at FROM mission_attempts WHERE attempt_id=?",
        (lease["attempt_id"],),
    ).fetchone()["last_progress_at"]


def test_narration_cannot_extend_progress_clock(tmp_path):
    store, lease = staged(tmp_path)
    initial = _progress_clock(store, lease)
    for evidence in ("working", "tests passed", "merged", "effect:missing"):
        with pytest.raises(InvalidTransition):
            store.report_progress(
                "m-test", lease["attempt_id"], lease["lease_epoch"], evidence
            )
    assert _progress_clock(store, lease) == initial
    assert store.get_mission("m-test")["last_verified_progress_at"] is None
    store.close()


def test_verified_external_progress_can_only_be_counted_once(tmp_path):
    store, lease = staged(tmp_path)
    eid = effect(store, lease)
    args = ("m-test", lease["attempt_id"], lease["lease_epoch"], "effect:" + eid)
    first = store.report_progress(*args)
    assert first["evidence"] == "effect:" + eid
    clock = _progress_clock(store, lease)
    assert clock == first["progress_at"]
    with pytest.raises(InvalidTransition, match="same external effect"):
        store.report_progress(*args, now=first["progress_at"] + 1)
    assert _progress_clock(store, lease) == clock
    events = store.db.execute(
        "SELECT COUNT(*) AS n FROM mission_events"
        " WHERE mission_id='m-test' AND cause='verified external progress'"
    ).fetchone()["n"]
    assert events == 1
    store.close()


def test_checkpoint_is_durable_custody_not_verified_progress(tmp_path):
    store, lease = staged(tmp_path)
    initial = _progress_clock(store, lease)
    store.write_checkpoint(
        "m-test", lease["attempt_id"], lease["lease_epoch"],
        {
            "source_revision": "a" * 40,
            "next_admissible_action": "verify an external effect",
            "completed_work": ["wrote another report"],
        },
    )
    assert _progress_clock(store, lease) == initial
    assert store.get_mission("m-test")["last_checkpoint_digest"]
    store.close()


def test_future_dated_observer_cannot_settle_or_reset_clock(tmp_path):
    store, lease = staged(tmp_path)
    eid = effect(store, lease)
    store.db.execute(
        "UPDATE external_effects SET observed_at=? WHERE effect_id=?",
        (time.time() + 3600, eid),
    )
    with pytest.raises(InvalidTransition, match="future"):
        operating(store, lease, "effect:" + eid)
    with pytest.raises(InvalidTransition, match="future"):
        store.report_progress(
            "m-test", lease["attempt_id"], lease["lease_epoch"], "effect:" + eid
        )
    assert store.get_mission("m-test")["state"] == "DEPLOY_VERIFY"
    store.close()
