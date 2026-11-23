"""Operational yield is a reconciled observed effect, not an agent adjective."""

from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform" / "estate"))
from continuity import (  # noqa: E402
    DuplicateEffect,
    InvalidTransition,
    MissionStore,
    RecordRejected,
    StaleFenceError,
)
from continuity.util import effect_receipt_subject  # noqa: E402


def signed_receipt(
    store,
    effect_id,
    receipt,
    *,
    verified_by="observer-b",
    observed_state="OBSERVED",
    reconciliation_status="RECONCILED",
):
    subject = effect_receipt_subject(
        effect_id, receipt, verified_by, observed_state, reconciliation_status
    )
    signer = store._test_signers.get(
        verified_by, store._test_signers["observer-b"]
    )
    signature = base64.b64encode(signer.sign(subject)).decode()
    return store.record_receipt(
        effect_id,
        receipt,
        verified_by=verified_by,
        observed_state=observed_state,
        reconciliation_status=reconciliation_status,
        verifier_signature=signature,
    )


def staged(tmp_path):
    signers = {
        identity: Ed25519PrivateKey.generate()
        for identity in ("observer-b", "executor-a", "legion")
    }
    store = MissionStore(
        tmp_path / "custody.sqlite",
        trusted_verifier_keys={
            identity: signer.public_key().public_bytes_raw()
            for identity, signer in signers.items()
        },
    )
    store._test_signers = signers
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
    signed_receipt(
        store,
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
    with pytest.raises(RecordRejected, match="leased executor"):
        effect(store, lease, verifier=verifier)
    assert store.pending_effects("m-test")[0]["reconciliation_status"] == "PENDING"
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
    result = signed_receipt(
        store,
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
    assert signed_receipt(
        store,
        eid, {"observed": "ok"}, verified_by="observer-b"
    )["duplicate"] is True
    for receipt, verifier, reconciliation in [
        ({"observed": "different"}, "observer-b", "RECONCILED"),
        ({"observed": "ok"}, "executor-a", "RECONCILED"),
        ({"observed": "ok"}, "observer-b", "AMBIGUOUS"),
    ]:
        error = RecordRejected if verifier == "executor-a" else DuplicateEffect
        with pytest.raises(error):
            signed_receipt(
                store,
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
    # Executor-controlled outcome text must not create an independently
    # authenticated effect. An external observer must enter a separate receipt.
    with pytest.raises(DuplicateEffect, match="independent record_receipt"):
        store.reconcile_effect(eid, "unverified-agent-assertion", "COMPLETED")
    assert store.pending_effects("m-test")[0]["effect_id"] == eid
    completed = signed_receipt(
        store,
        eid, {"external": "observed-external-transaction"},
        verified_by="observer-b",
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
    with pytest.raises(DuplicateEffect, match="independent record_receipt"):
        store.reconcile_effect(eid, "I say nothing happened", "NOT_STARTED")
    assert store.pending_effects("m-test")[0]["effect_id"] == eid
    with pytest.raises(RecordRejected, match="signature required"):
        store.record_receipt(
            eid, {"external": "negative-observation"}, "observer-b",
            observed_state="ABANDONED",
        )
    assert store.pending_effects("m-test")[0]["reconciliation_status"] == "PENDING"
    negative = signed_receipt(
        store, eid, {"external": "negative-observation"},
        verified_by="observer-b", observed_state="ABANDONED",
    )
    assert negative["state"] == "ABANDONED" and not negative["duplicate"]
    assert store.pending_effects("m-test") == []
    assert signed_receipt(
        store, eid, {"external": "negative-observation"},
        observed_state="ABANDONED",
    )["duplicate"] is True
    with pytest.raises(InvalidTransition):
        operating(store, lease, "effect:" + eid)
    with pytest.raises(DuplicateEffect, match="independent record_receipt"):
        store.reconcile_effect("e-missing", "", "NOT_STARTED")
    with pytest.raises(DuplicateEffect, match="unknown effect"):
        store.reconcile_effect("e-missing", "", "AMBIGUOUS")
    store.close()


def test_legacy_unsigned_negative_receipt_remains_an_obligation(tmp_path):
    store, lease = staged(tmp_path)
    intent = store.record_effect_intent(
        "m-test", lease["attempt_id"], lease["lease_epoch"],
        "external-test", "example.invalid", "legacy-unverified",
        {"expected": "ok"},
    )
    eid = intent["effect_id"]
    store.db.execute(
        "UPDATE external_effects SET state='ABANDONED',"
        " reconciliation_status='RECONCILED',"
        " external_receipt=?, verified_by=? WHERE effect_id=?",
        (json.dumps({"external": "agent said not started"}), "observer-b", eid),
    )
    pending = store.pending_effects("m-test")
    assert len(pending) == 1
    assert pending[0]["reconciliation_status"] == "UNVERIFIED"
    with pytest.raises(RecordRejected, match="signed reattestation"):
        store.record_receipt(
            eid, {"external": "erase old record"}, "observer-b",
            observed_state="OBSERVED", reconciliation_status="AMBIGUOUS",
        )
    with pytest.raises(InvalidTransition):
        operating(store, lease, "effect:" + eid)
    verified = signed_receipt(
        store, eid, {"external": "independent absence check"},
        observed_state="ABANDONED",
    )
    assert verified["state"] == "ABANDONED" and not verified["duplicate"]
    assert store.pending_effects("m-test") == []
    store.close()


def test_unsigned_reconciliation_status_cannot_erase_pending_effect(tmp_path):
    store, lease = staged(tmp_path)
    intent = store.record_effect_intent(
        "m-test", lease["attempt_id"], lease["lease_epoch"],
        "external-test", "example.invalid", "negative-no-proof",
        {"expected": "ok"},
    )
    eid = intent["effect_id"]
    with pytest.raises(RecordRejected, match="signature required"):
        store.record_receipt(
            eid, {"external": "I said it ended"}, "observer-b",
            observed_state="ABANDONED", reconciliation_status="RECONCILED",
        )
    with pytest.raises(RecordRejected, match="verified observation or abandonment"):
        store.record_receipt(
            eid, {"external": "I said it ended"}, "observer-b",
            observed_state="INTENDED", reconciliation_status="RECONCILED",
        )
    assert store.pending_effects("m-test")[0]["effect_id"] == eid
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


def test_global_idempotency_key_cannot_cross_mission_or_effect_scope(tmp_path):
    store, lease = staged(tmp_path)

    def record(mission_id, active, operation, target, intent):
        return store.record_effect_intent(
            mission_id,
            active["attempt_id"],
            active["lease_epoch"],
            operation,
            target,
            "global-once",
            intent,
        )

    original = record(
        "m-test", lease, "external-test", "example.invalid", {"want": "ok"}
    )
    duplicate = record(
        "m-test", lease, "external-test", "example.invalid", {"want": "ok"}
    )
    assert duplicate["duplicate"] is True
    assert duplicate["effect_id"] == original["effect_id"]
    for operation, target, intent in [
        ("different-op", "example.invalid", {"want": "ok"}),
        ("external-test", "different.invalid", {"want": "ok"}),
        ("external-test", "example.invalid", {"want": "different"}),
    ]:
        with pytest.raises(DuplicateEffect, match="already bound"):
            record("m-test", lease, operation, target, intent)

    store.accept_mission(
        {
            "mission_id": "m-other",
            "instruction_id": "idp#7443-other",
            "mandate_id": "founder",
            "goal": "independent mission custody",
            "acceptance_contract_digest": "b" * 64,
            "risk_class": "HIGH",
        }
    )
    store.transition("m-other", "READY", "estate", "dispatch")
    lease_other = store.acquire_lease(
        "m-other",
        {
            "agent_adapter": "legion",
            "provider": "test",
            "model": "test",
            "execution_host": "cloud",
            "failure_domain": "runner",
            "worktree_id": "test-other",
            "base_sha": "b" * 40,
        },
    )
    with pytest.raises(DuplicateEffect, match="already bound"):
        record(
            "m-other", lease_other, "external-test", "example.invalid",
            {"want": "ok"},
        )
    assert store.db.execute(
        "SELECT COUNT(*) FROM external_effects WHERE idempotency_key='global-once'"
    ).fetchone()[0] == 1
    store.close()


def test_reconciler_cannot_fabricate_independent_completion(tmp_path):
    store, lease = staged(tmp_path)
    intent = store.record_effect_intent(
        "m-test", lease["attempt_id"], lease["lease_epoch"],
        "external-test", "example.invalid", "untrusted-claim-once",
        {"expected": "real observation"},
    )
    eid = intent["effect_id"]
    before = dict(store.db.execute(
        "SELECT state, reconciliation_status, external_receipt, verified_by"
        " FROM external_effects WHERE effect_id=?", (eid,)
    ).fetchone())
    with pytest.raises(DuplicateEffect, match="independent record_receipt"):
        store.reconcile_effect(eid, "I say done", "COMPLETED")
    after = dict(store.db.execute(
        "SELECT state, reconciliation_status, external_receipt, verified_by"
        " FROM external_effects WHERE effect_id=?", (eid,)
    ).fetchone())
    assert after == before
    assert store.pending_effects("m-test")[0]["effect_id"] == eid
    with pytest.raises(InvalidTransition, match="reconciled"):
        operating(store, lease, "effect:" + eid)
    store.close()


def test_unsigned_or_untrusted_receipt_never_certifies_an_effect(tmp_path):
    store, lease = staged(tmp_path)
    intent = store.record_effect_intent(
        "m-test", lease["attempt_id"], lease["lease_epoch"],
        "external-test", "example.invalid", "unsigned-proof",
        {"expected": "external truth"},
    )
    eid = intent["effect_id"]
    with pytest.raises(RecordRejected, match="signature required"):
        store.record_receipt(eid, {"claimed": True}, verified_by="observer-b")
    with pytest.raises(RecordRejected, match="signature not accepted"):
        store.record_receipt(
            eid, {"claimed": True}, verified_by="observer-b",
            verifier_signature=base64.b64encode(b"forged").decode(),
        )
    with pytest.raises(RecordRejected, match="signature not accepted"):
        signed_receipt(
            store, eid, {"claimed": True}, verified_by="unregistered-actor"
        )
    row = store.db.execute(
        "SELECT state, reconciliation_status, external_receipt FROM external_effects"
        " WHERE effect_id=?", (eid,)
    ).fetchone()
    assert row["state"] == "INTENDED"
    assert row["reconciliation_status"] == "PENDING"
    assert row["external_receipt"] is None
    with pytest.raises(InvalidTransition):
        operating(store, lease, "effect:" + eid)
    store.close()


def test_tampered_persisted_signature_fails_at_terminal_and_progress(tmp_path):
    store, lease = staged(tmp_path)
    eid = effect(store, lease)
    stored = json.loads(store.db.execute(
        "SELECT external_receipt FROM external_effects WHERE effect_id=?", (eid,)
    ).fetchone()[0])
    stored["_meridian_verifier"]["signature"] = base64.b64encode(b"fake").decode()
    store.db.execute(
        "UPDATE external_effects SET external_receipt=? WHERE effect_id=?",
        (json.dumps(stored), eid),
    )
    with pytest.raises(InvalidTransition, match="observer seal"):
        operating(store, lease, "effect:" + eid)
    with pytest.raises(InvalidTransition, match="observer seal"):
        store.report_progress(
            "m-test", lease["attempt_id"], lease["lease_epoch"], "effect:" + eid
        )
    store.close()


def test_replayed_signed_receipt_cannot_certify_a_different_effect(tmp_path):
    store, lease = staged(tmp_path)
    original = effect(store, lease)
    observed = store.db.execute(
        "SELECT external_receipt FROM external_effects WHERE effect_id=?",
        (original,),
    ).fetchone()[0]
    second = store.record_effect_intent(
        "m-test", lease["attempt_id"], lease["lease_epoch"],
        "external-test", "example.invalid", "different-effect",
        {"expected": "ok"},
    )
    store.db.execute(
        "UPDATE external_effects SET state='OBSERVED',"
        " reconciliation_status='RECONCILED',"
        " external_receipt=?, observed_at=?, verified_by=?"
        " WHERE effect_id=?",
        (observed, time.time(), "observer-b", second["effect_id"]),
    )
    with pytest.raises(InvalidTransition, match="observer seal"):
        operating(store, lease, "effect:" + second["effect_id"])
    store.close()


def test_legacy_self_signed_external_effect_stays_pending(tmp_path):
    store, lease = staged(tmp_path)
    intent = store.record_effect_intent(
        "m-test", lease["attempt_id"], lease["lease_epoch"],
        "external-test", "example.invalid", "legacy-self-signed",
        {"expected": "independent observer"},
    )
    eid = intent["effect_id"]
    claimed = {"external": "agent wrote this"}
    sig = base64.b64encode(
        store._test_signers["executor-a"].sign(
            effect_receipt_subject(eid, claimed, "executor-a")
        )
    ).decode()
    forged = {
        **claimed,
        "_meridian_verifier": {"key_id": "executor-a", "signature": sig},
    }
    store.db.execute(
        "UPDATE external_effects SET state='OBSERVED',"
        " reconciliation_status='RECONCILED', external_receipt=?,"
        " verified_by=?, observed_at=? WHERE effect_id=?",
        (json.dumps(forged), "executor-a", time.time(), eid),
    )
    assert store.pending_effects("m-test")[0]["reconciliation_status"] == "UNVERIFIED"
    with pytest.raises(InvalidTransition, match="executor"):
        operating(store, lease, "effect:" + eid)
    # An actual independent observer can replace the untrusted historical claim.
    repaired = signed_receipt(
        store, eid, {"external": "observer checked real state"},
        verified_by="observer-b",
    )
    assert repaired["state"] == "OBSERVED"
    assert store.pending_effects("m-test") == []
    store.close()


def test_trusted_verifiers_cannot_share_private_key_material(tmp_path):
    one_key = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    with pytest.raises(ValueError, match="multiple independent verifiers"):
        MissionStore(
            tmp_path / "key-alias.sqlite",
            trusted_verifier_keys={"observer-b": one_key, "legion": one_key},
        )


def test_reconciled_receipt_rejects_ambiguous_rewrite_without_crashing(tmp_path):
    store, lease = staged(tmp_path)
    eid = effect(store, lease)
    with pytest.raises(DuplicateEffect, match="immutable reconciled"):
        signed_receipt(
            store, eid, {"observed": "ok"},
            verified_by="observer-b", reconciliation_status="AMBIGUOUS",
        )
    assert store.pending_effects("m-test") == []
    assert operating(store, lease, "effect:" + eid)["state"] == "OPERATING"
    store.close()


def test_legacy_reconciled_receipt_rejects_unsigned_ambiguous_rewrite(tmp_path):
    store, lease = staged(tmp_path)
    intent = store.record_effect_intent(
        "m-test", lease["attempt_id"], lease["lease_epoch"],
        "external-test", "example.invalid", "legacy-ambiguous-mutation",
        {"expected": "external truth"},
    )
    eid = intent["effect_id"]
    store.db.execute(
        "UPDATE external_effects SET state='ABANDONED',"
        " reconciliation_status='RECONCILED',"
        " external_receipt=?, verified_by=? WHERE effect_id=?",
        (json.dumps({"external": "legacy self-report"}), "observer-b", eid),
    )
    with pytest.raises(RecordRejected, match="signed reattestation"):
        store.record_receipt(
            eid, {"external": "rewrite"}, "observer-b",
            observed_state="OBSERVED", reconciliation_status="AMBIGUOUS",
        )
    assert store.pending_effects("m-test")[0]["reconciliation_status"] == "UNVERIFIED"
    store.close()
