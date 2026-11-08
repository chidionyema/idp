"""Behavioral and negative-path tests: Genesis MORPH integrated broker adapter #7790.

Real SQLite lease and heartbeat stores; deterministic in-memory checkpoint adapter.
Only real deployed OCI/Temporal/DoF and cross-host canaries can certify operation.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from platform.queue import continuity_admission as c
from platform.queue import morph_orchestrator as m


def checkpoint(mission="mission"):
    return {
        "schema": "genesis.mission.checkpoint.v1", "mission_id": mission,
        "source_sha": "a"*40, "resume_cursor": "step-4",
        "instruction_id": "I-902", "workflow_id": "temporal-mission-902",
        "plan_sha256": "b"*64, "bdd_ref": "idp#7790",
        "estate_view_digest": "c"*64, "estate_view_observed_at": 100.0,
        "next_action": "resume bounded test", "verified_effect_refs": [],
        "unresolved_effect_ids": [],
    }


class CheckpointAdapter:
    """An honest store double: never substitutes for actual KMS/OCI proof."""

    def __init__(self, manifest):
        self.manifest = dict(manifest)
        self.written = None
        self.bad_readback = False
        self.corrupt_restore = False
        self.writes = 0

    def write(self, mission, manifest):
        self.writes += 1
        if mission != manifest["mission_id"]:
            raise RuntimeError("cross mission")
        self.written = dict(manifest)
        self.data = json.dumps(manifest, sort_keys=True).encode()
        return SimpleNamespace(uri=f"oci://fixture/{mission}/{self.writes}",
                               sha256=hashlib.sha256(self.data).hexdigest(),
                               source_sha=manifest["source_sha"])

    def read_ciphertext(self, uri):
        return b"corrupt" if self.bad_readback else self.data

    def decrypt_and_validate(self, mission, uri, data):
        if self.corrupt_restore:
            return {**self.written, "source_sha": "f"*40}
        if mission != self.written["mission_id"] or data != self.data:
            raise RuntimeError("integrity")
        return dict(self.written)


class MorphIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.leases = c.LeaseStore(
            str(pathlib.Path(self.temp.name)/"leases.db"),
            handover_verifier=self.verify,
        )
        self.old = "agent-pi-session-01"
        self.new = "agent-cloud-session-02"
        self.epoch = self.leases.claim("mission", self.old, 100, 100)
        self.beats = c.HeartbeatRegistry(str(pathlib.Path(self.temp.name)/"beats.db"))
        self.beats.observe(
            c.WorkerOffer(self.new, "cloud-domain", frozenset({"python"}), True,
                          105, 1, True, 5000, .05, 60, .95),
            trusted_actor=self.new, broker_now=105, sequence=1,
            adapter="trusted-cloud-runner", provider="trusted-provider",
            host="verified-cloud-host", capacity_source="provider_api",
            capacity_evidence="provider:authenticated-capacity/1",
        )
        self.requirement = c.Requirement(
            frozenset({"python"}), 1.0, 500, previous_failure_domain="local-pi"
        )
        self.store = CheckpointAdapter(checkpoint())
        self.events = []
        self.dispatches = []
        self.auth_calls = 0
        self.key = b"hermetic-fixture-verifier"
        self.verdict = c.assess_morph_risk(
            [c.LifeSignal("context", 105, "provider_api",
                          "provider:verified-usage", 10, 1)],
            now=105, budget=c.MorphBudget(
                5, 10, 4, 6, required_resources=frozenset({"context"})
            ), checkpoint_age_seconds=0,
        )
        self.coordinator = m.MorphCoordinator(
            leases=self.leases, beats=self.beats, checkpoint_store=self.store,
            authorize_and_sign=self.authorize,
            durable_event=self.persist_event,
            dispatch_existing_workflow=self.dispatch,
        )

    def tearDown(self):
        self.temp.cleanup()

    def verify(self, message, signature):
        return hashlib.sha256(self.key + message).digest() == signature

    def authorize(self, proposal):
        self.auth_calls += 1
        # Fixture acts as separate trusted broker: production MUST validate
        # issuer identity, DoF, current capacity, current policy and timing.
        message = (
            f"genesis.morph.handover.v1\n{proposal['mission_id']}\n"
            f"{proposal['old_worker']}\n{proposal['old_epoch']}\n"
            f"{proposal['new_worker']}\n{proposal['checkpoint_sha256']}\n"
            f"{proposal['checkpoint_uri']}\n{proposal['now']:.6f}\n"
            f"{proposal['lease_ttl']:.6f}\n"
        ).encode()
        return hashlib.sha256(self.key + message).digest()

    def persist_event(self, event):
        self.events.append(dict(event))
        return f"workflow-event-{len(self.events)}"

    def dispatch(self, proposal):
        self.dispatches.append(dict(proposal))
        return f"temporal-dispatch-{len(self.dispatches)}"

    def run_morph(self, *, manifest=None, coordinator=None, verdict=None,
                  current_worker=None, epoch=None, now=110, sequence=1):
        return (coordinator or self.coordinator).morph(
            mission_id="mission", current_worker=current_worker or self.old,
            epoch=epoch or self.epoch, observed_at=now, lease_ttl=80,
            progress_sequence=sequence,
            verdict=verdict or self.verdict, requirement=self.requirement,
            context=checkpoint() if manifest is None else manifest,
        )

    def test_full_broker_custody_path_fences_zombie_and_dispatches(self):
        result = self.run_morph()
        self.assertEqual(result["state"], "DISPATCH_ACKNOWLEDGED_NOT_VERIFIED")
        self.assertEqual(result["lease_epoch"], 2)
        self.assertEqual([x["kind"] for x in self.events],
                         ["MORPH_PREPARED", "MORPH_CUSTODY_TRANSFERRED"])
        self.assertEqual(len(self.dispatches), 1)
        self.assertTrue(result["reconcile_current_oracle_and_dof"])
        self.assertFalse(result["operationally_complete"])
        self.assertFalse(result["runtime_dispatch_verified"])
        with self.assertRaisesRegex(c.Refused, "STALE_FENCING_LEASE"):
            self.leases.authorize_effect("mission", self.old, 1, 111)
        self.leases.authorize_effect("mission", self.new, 2, 111)

    def test_healthy_state_does_not_morph(self):
        healthy = c.assess_morph_risk(
            [c.LifeSignal("context", 105, "provider_api",
                          "provider:verified-usage", 500, 1)],
            now=105, budget=c.MorphBudget(
                5, 10, 4, 6, required_resources=frozenset({"context"})
            ), checkpoint_age_seconds=0,
        )
        result = self.run_morph(verdict=healthy)
        self.assertEqual(result["state"], "NOT_TRIGGERED")
        self.assertEqual(self.store.writes, 0)

    def test_missing_instruction_rejected_before_write(self):
        data = checkpoint()
        del data["instruction_id"]
        result = self.run_morph(manifest=data)
        self.assertEqual(result["reason"], "MORPH_CHECKPOINT_INCOMPLETE")
        self.assertEqual(self.store.writes, 0)

    def test_missing_oracle_view_rejected_before_write(self):
        data = checkpoint()
        del data["estate_view_digest"]
        self.assertEqual(self.run_morph(manifest=data)["reason"],
                         "MORPH_CHECKPOINT_INCOMPLETE")

    def test_invalid_sha_rejected_before_write(self):
        data = checkpoint()
        data["plan_sha256"] = "short"
        self.assertEqual(self.run_morph(manifest=data)["reason"],
                         "MORPH_CHECKPOINT_INVALID")

    def test_credentials_cannot_travel_in_checkpoint(self):
        data = checkpoint()
        data["access_token"] = "unsafe"
        self.assertEqual(self.run_morph(manifest=data)["reason"],
                         "MORPH_CHECKPOINT_FORBIDDEN_AUTHORITY")

    def test_unknown_external_effect_prevents_morph(self):
        data = checkpoint()
        data["unresolved_effect_ids"] = ["payment-73"]
        self.assertEqual(self.run_morph(manifest=data)["reason"],
                         "MORPH_EFFECTS_REQUIRE_RECONCILIATION")

    def test_tampered_ciphertext_never_advances_epoch(self):
        self.store.bad_readback = True
        result = self.run_morph()
        self.assertEqual(result["reason"], "CHECKPOINT_READBACK_MISMATCH")
        self.assertEqual(self.leases.snapshot("mission")[1], 1)
        self.assertEqual(self.auth_calls, 0)

    def test_semantically_modified_restore_refused(self):
        self.store.corrupt_restore = True
        self.assertEqual(self.run_morph()["reason"], "CHECKPOINT_SEMANTIC_MISMATCH")
        self.assertEqual(self.leases.snapshot("mission")[1], 1)

    def test_unverified_capacity_does_not_claim_transfer(self):
        self.requirement = c.Requirement(frozenset({"absent"}), 1.0, 100)
        result = self.run_morph()
        self.assertEqual(result["reason"], "NO_ELIGIBLE_CAPACITY")
        self.assertEqual(self.leases.snapshot("mission")[1], 1)

    def test_no_signing_authority_preserves_checkpoint_but_not_handover(self):
        self.coordinator.authorize_and_sign = lambda proposal: b""
        result = self.run_morph()
        self.assertEqual(result["reason"], "INDEPENDENT_AUTHORIZATION_MISSING")
        self.assertEqual(self.leases.snapshot("mission")[1], 1)
        self.assertEqual(len(self.dispatches), 0)

    def test_wrong_signer_cannot_take_custody(self):
        self.coordinator.authorize_and_sign = lambda proposal: b"false-proof"
        result = self.run_morph()
        self.assertEqual(result["reason"], "INVALID_INDEPENDENT_HANDOVER_PROOF")
        self.assertEqual(self.leases.snapshot("mission")[1], 1)

    def test_missing_durable_event_refuses_handover(self):
        self.coordinator.durable_event = lambda event: ""
        self.assertEqual(self.run_morph()["reason"],
                         "DURABLE_EVENT_NOT_ACKNOWLEDGED")
        self.assertEqual(self.leases.snapshot("mission")[1], 1)

    def test_dispatch_failure_remains_pending_with_new_fenced_owner(self):
        def bad_dispatch(event):
            raise RuntimeError("Temporal offline")
        self.coordinator.dispatch = bad_dispatch
        result = self.run_morph()
        self.assertEqual(result["state"], "RECOVERY_PENDING")
        self.assertEqual(result["reason"], "FENCED_OWNER_PENDING_WORKFLOW_RECOVERY")
        self.assertEqual(result["lease_epoch"], 2)
        self.assertEqual(self.leases.snapshot("mission")[0], self.new)
        with self.assertRaisesRegex(c.Refused, "STALE_FENCING_LEASE"):
            self.leases.authorize_effect("mission", self.old, 1, 111)

    def test_replay_same_mission_cannot_duplicate_dispatch(self):
        self.assertEqual(self.run_morph()["state"],
                         "DISPATCH_ACKNOWLEDGED_NOT_VERIFIED")
        repeat = self.run_morph(sequence=2)
        self.assertEqual(repeat["reason"], "CURRENT_MISSION_OWNER_NOT_VERIFIED")
        self.assertEqual(len(self.dispatches), 1)

    def test_pending_external_reservation_prevents_owner_change(self):
        self.leases.reserve_effect("mission", "deploy-72", self.old, 1, 109)
        result = self.run_morph()
        self.assertEqual(result["reason"], "PENDING_RECONCILIATION_REQUIRED")
        self.assertEqual(self.leases.snapshot("mission")[1], 1)

    def test_expired_owner_cannot_proactively_transfer(self):
        result = self.run_morph(now=205)
        self.assertEqual(result["reason"], "LEASE_EXPIRED_USE_RECOVERY")
        self.assertEqual(self.leases.snapshot("mission")[1], 1)

    def test_missing_checkpoint_adapter_cannot_morph(self):
        self.coordinator.checkpoints = object()
        self.assertEqual(self.run_morph()["reason"],
                         "ENCRYPTED_OFFHOST_CHECKPOINT_UNAVAILABLE")

    def test_new_worker_same_logical_agent_can_rehydrate(self):
        result = self.run_morph()
        self.assertEqual(result["new_worker"], self.new)
        self.assertEqual(result["source_sha"], "a"*40)


class LifeObserverTests(unittest.TestCase):
    def test_local_disk_observation_does_not_fabricate_depletion(self):
        obs = m.BrokerLifeObserver().sample_storage(".", now=100)
        self.assertEqual(obs.resource, "storage")
        self.assertIsNone(obs.burn_per_second)
        self.assertEqual(obs.source, "host_metrics")
        self.assertGreater(obs.remaining, 0)

    def test_missing_context_quota_network_reports_unknown(self):
        sensor = m.BrokerLifeObserver()
        obs = sensor.sample_storage(".", now=100)
        verdict = sensor.assess(
            {"storage": obs}, now=100,
            budget=c.MorphBudget(5, 10, 4, 6),
            checkpoint_age_seconds=1,
        )
        self.assertEqual(verdict.state, "UNKNOWN")
        self.assertIn("provider_quota", verdict.unknown_resources)
        self.assertIn("network", verdict.unknown_resources)
        self.assertIn("context", verdict.unknown_resources)

    def test_broker_lease_signal_has_real_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = c.LeaseStore(str(pathlib.Path(tmp)/"db.sqlite"))
            store.claim("a", "worker", 100, 50)
            signal = m.BrokerLifeObserver().sample_lease(store, "a", now=101)
            self.assertEqual(signal.deadline, 150)
            self.assertEqual(signal.source, "trusted_supervisor")

    def test_missing_lease_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = c.LeaseStore(str(pathlib.Path(tmp)/"db.sqlite"))
            signal = m.BrokerLifeObserver().sample_lease(store, "absent", now=101)
            self.assertEqual(signal.source, "unknown")

    def test_caller_cannot_pass_unapproved_resource_name(self):
        sensor = m.BrokerLifeObserver()
        with self.assertRaisesRegex(c.Refused, "UNDECLARED_MORPH_OBSERVATION"):
            sensor.assess(
                {"founder": m.Observation("founder", 1, 1, None, 100,
                                          "model_self_report", "fake")},
                now=100, budget=c.MorphBudget(5, 10, 4, 6),
                checkpoint_age_seconds=0,
            )


if __name__ == "__main__":
    unittest.main()
