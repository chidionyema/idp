"""Genesis MORPH regression tests for existing IDP continuity contract #7790.

Hermetic tests cover deterministic risk decisions and real SQLite fencing.
They do not assert deployed provider adapters, KMS, QUAD or Temporal coverage.
"""
from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import tempfile
import threading
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "platform/queue/continuity_admission.py"
spec = importlib.util.spec_from_file_location("continuity_admission_morph", SOURCE)
import sys
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
m = module


def life(remaining=600.0, burn=1.0, *, name="context", observed=100.0,
         provenance="provider_api", evidence="verified:provider/123", deadline=None,
         failed=False):
    return m.LifeSignal(name, observed, provenance, evidence,
                        remaining, burn, deadline, failed)


class MorphRiskTests(unittest.TestCase):
    def setUp(self):
        self.budget = m.MorphBudget(5, 10, 4, 6, 120, 300, frozenset({"context"}))

    def evaluate(self, signals, checkpoint=10, **kwargs):
        return m.assess_morph_risk(
            signals, now=100, budget=self.budget,
            checkpoint_age_seconds=checkpoint, **kwargs
        )

    def test_healthy_is_not_an_authorization(self):
        value = self.evaluate([life()])
        self.assertEqual((value.schema, value.state, value.action),
                         ("genesis.morph.risk.v1", "HEALTHY", "CONTINUE"))
        self.assertFalse(value.permits_privileged_effects)
        self.assertEqual(value.runway_seconds, 600)
        self.assertEqual(value.recovery_budget_seconds, 25)

    def test_early_pressure_prepares_destination(self):
        value = self.evaluate([life(40)])
        self.assertEqual((value.state, value.action),
                         ("PRESSURED", "PREPARE_DESTINATION"))

    def test_risk_triggers_before_loss_of_recovery_runway(self):
        value = self.evaluate([life(20)])
        self.assertEqual((value.state, value.action),
                         ("AT_RISK", "CHECKPOINT_AND_MORPH"))
        self.assertIn("RECOVERY_RUNWAY_INSUFFICIENT", value.reason_codes)

    def test_critical_stops_new_risky_effects(self):
        value = self.evaluate([life(4)])
        self.assertEqual((value.state, value.action),
                         ("CRITICAL", "STOP_RISKY_EFFECTS_AND_RECOVER"))

    def test_verified_resource_failure_triggers_critical(self):
        value = self.evaluate([life(failed=True)])
        self.assertEqual(value.state, "CRITICAL")

    def test_never_wait_for_600s_if_resource_expiring(self):
        value = self.evaluate([life(3)])
        self.assertEqual(value.state, "CRITICAL")

    def test_hard_deadline_shortens_runway(self):
        value = self.evaluate([life(3000, 1, deadline=112)])
        self.assertEqual(value.runway_seconds, 12)
        self.assertEqual(value.state, "AT_RISK")

    def test_minimum_runway_across_resources(self):
        value = self.evaluate([life(600), life(2, name="disk")])
        self.assertEqual(value.state, "CRITICAL")
        self.assertEqual(value.runway_seconds, 2)

    def test_missing_signals_remain_unknown(self):
        value = self.evaluate([])
        self.assertEqual(value.state, "UNKNOWN")
        self.assertEqual(value.action, "CHECKPOINT_AND_PROBE")
        self.assertIn("NO_RESOURCE_TELEMETRY", value.reason_codes)


    def test_undeclared_resource_scope_cannot_be_green(self):
        value = m.assess_morph_risk(
            [life()], now=100, budget=m.MorphBudget(5, 10, 4, 6),
            checkpoint_age_seconds=10,
        )
        self.assertEqual(value.state, "UNKNOWN")
        self.assertIn("UNDECLARED_RESOURCE_COVERAGE", value.reason_codes)

    def test_missing_required_resource_cannot_be_green(self):
        value = m.assess_morph_risk(
            [life()], now=100,
            budget=m.MorphBudget(5, 10, 4, 6,
                                 required_resources=frozenset({"context", "storage"})),
            checkpoint_age_seconds=10,
        )
        self.assertEqual(value.state, "UNKNOWN")
        self.assertIn("storage", value.unknown_resources)

    def test_missing_resource_cannot_downgrade_critical_risk(self):
        value = m.assess_morph_risk(
            [life(2)], now=100,
            budget=m.MorphBudget(5, 10, 4, 6,
                                 required_resources=frozenset({"context", "storage"})),
            checkpoint_age_seconds=10,
        )
        self.assertEqual(value.state, "CRITICAL")
        self.assertIn("storage", value.unknown_resources)

    def test_stale_signal_is_not_treated_as_healthy(self):
        value = self.evaluate([life(observed=-50)])
        self.assertEqual(value.state, "UNKNOWN")
        self.assertIn("context", value.unknown_resources)

    def test_future_signal_is_unknown(self):
        value = self.evaluate([life(observed=101)])
        self.assertEqual(value.state, "UNKNOWN")

    def test_untrusted_signal_is_unknown(self):
        value = self.evaluate([life(provenance="model_self_report")])
        self.assertEqual(value.state, "UNKNOWN")

    def test_no_evidence_ref_is_unknown(self):
        value = self.evaluate([life(evidence="")])
        self.assertEqual(value.state, "UNKNOWN")

    def test_zero_burn_does_not_prove_infinite_runway(self):
        value = self.evaluate([life(3000, 0)])
        self.assertEqual(value.state, "UNKNOWN")

    def test_mixed_known_and_missing_is_not_false_healthy(self):
        value = self.evaluate([life(), life(200, 0, name="quota")])
        self.assertEqual(value.state, "UNKNOWN")
        self.assertIn("quota", value.unknown_resources)

    def test_absent_checkpoint_makes_even_good_runway_at_risk(self):
        value = self.evaluate([life()], checkpoint=None)
        self.assertEqual(value.state, "AT_RISK")
        self.assertIn("NO_VERIFIED_CHECKPOINT", value.reason_codes)

    def test_old_checkpoint_requires_recovery(self):
        value = self.evaluate([life()], checkpoint=301)
        self.assertEqual(value.state, "AT_RISK")
        self.assertIn("CHECKPOINT_TOO_OLD", value.reason_codes)

    def test_hysteresis_requires_two_clear_observations(self):
        first = self.evaluate([life()], previous_state="AT_RISK",
                              consecutive_clear_observations=1)
        second = self.evaluate([life()], previous_state="AT_RISK",
                               consecutive_clear_observations=2)
        self.assertEqual(first.state, "PRESSURED")
        self.assertEqual(second.state, "HEALTHY")

    def test_rejects_invalid_recovery_budget(self):
        with self.assertRaisesRegex(m.Refused, "INVALID_MORPH_EVALUATION"):
            m.assess_morph_risk([life()], now=100,
                                budget=m.MorphBudget(float("nan"), 10, 4, 6),
                                checkpoint_age_seconds=0)

    def test_rejects_duplicate_resource_ambiguity(self):
        with self.assertRaisesRegex(m.Refused, "DUPLICATE_MORPH_RESOURCE"):
            self.evaluate([life(), life(100)])

    def test_rejects_bool_as_nonnegative_clearance_counter(self):
        with self.assertRaisesRegex(m.Refused, "INVALID_MORPH_EVALUATION"):
            self.evaluate([life()], consecutive_clear_observations=True)


class MorphCustodyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(pathlib.Path(self.temp.name) / "queue.db")
        self.secret = b"test-only-broker-verifier-key"
        self.sign = lambda message: hashlib.sha256(self.secret + message).digest()
        self.store = m.LeaseStore(self.path, handover_verifier=lambda msg, proof:
                                  self.sign(msg) == proof)
        self.mission = "morph-test"
        self.old = "agent-a"
        self.new = "agent-b"
        self.epoch = self.store.claim(self.mission, self.old, 100, 100)
        self.ciphertext = b"fixture-ciphertext-untrusted-until-decrypted"
        self.digest = hashlib.sha256(self.ciphertext).hexdigest()
        self.uri = "oci://test-bucket/morph-test"
        self.store.heartbeat(self.mission, self.old, self.epoch,
                             105, 100, 1, self.digest, self.uri)
        self.beats = m.HeartbeatRegistry(str(pathlib.Path(self.temp.name) / "beats.db"))
        self.beats.observe(
            m.WorkerOffer(self.new, "provider-b", frozenset({"python"}), True,
                          109, 1, True, 1000, 0.2, 50, .9),
            trusted_actor=self.new, broker_now=109, sequence=1,
            adapter="agent-host", provider="test-provider", host="host-b",
            capacity_source="provider_api", capacity_evidence="verified:provider/capacity"
        )
        self.req = m.Requirement(frozenset({"python"}), 1, 100, "provider-a")
        self.verdict = m.assess_morph_risk(
            [life(15)], now=100, budget=m.MorphBudget(5, 10, 4, 6, required_resources=frozenset({"context"})),
            checkpoint_age_seconds=1
        )

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self, mission_id, uri, ciphertext):
        if mission_id != self.mission or uri != self.uri or ciphertext != self.ciphertext:
            raise ValueError("wrong restoration")
        return {
            "schema": "genesis.mission.checkpoint.v1",
            "mission_id": mission_id, "source_sha": "a" * 40,
            "resume_cursor": "next-step",
        }

    def propose(self, *, ciphertext=None, decryptor=None, req=None):
        return m.prepare_preemptive_morph(
            self.mission, self.store, self.beats,
            self.req if req is None else req, self.verdict, 110,
            lambda uri: self.ciphertext if ciphertext is None else ciphertext,
            self.manifest if decryptor is None else decryptor,
        )

    def proof(self, new_worker=None, *, digest=None, now=111, ttl=100):
        new = new_worker or self.new
        digest = digest or self.digest
        message = (f"genesis.morph.handover.v1\n{self.mission}\n{self.old}\n"
                   f"{self.epoch}\n{new}\n{digest}\n{self.uri}\n"
                   f"{now:.6f}\n{ttl:.6f}\n").encode()
        return self.sign(message)

    def handover(self, *, proof=None, new=None, digest=None, now=111, ttl=100):
        return self.store.preemptive_handover(
            self.mission, self.old, self.epoch, new or self.new, now, ttl,
            digest or self.digest, self.uri,
            handover_proof=self.proof(new, digest=digest, now=now, ttl=ttl)
            if proof is None else proof,
        )

    def test_preparation_only_proposes_no_authorization(self):
        result = self.propose()
        self.assertEqual(result["state"], "READY_FOR_SIGNED_HANDOVER")
        self.assertEqual(result["old_epoch"], 1)
        self.assertEqual(result["new_worker"], self.new)
        self.assertFalse(result["authorization_granted"])
        self.assertFalse(result["runtime_dispatch_verified"])
        self.assertEqual(self.store.snapshot(self.mission)[0], self.old)

    def test_invalid_ciphertext_blocks_morph(self):
        self.assertEqual(self.propose(ciphertext=b"tampered")["reason"],
                         "CHECKPOINT_DIGEST_MISMATCH")

    def test_invalid_manifest_blocks_morph(self):
        self.assertEqual(
            self.propose(decryptor=lambda mission, uri, data:
                         {"schema": "genesis.mission.checkpoint.v1",
                          "mission_id": mission, "source_sha": "wrong",
                          "resume_cursor": "cursor"})["reason"],
            "INVALID_DECRYPTED_MANIFEST",
        )

    def test_absent_capacity_remains_pending(self):
        result = self.propose(req=m.Requirement(frozenset({"unavailable"}), 1, 100))
        self.assertEqual(result["reason"], "NO_ELIGIBLE_CAPACITY")

    def test_morph_not_triggered_by_good_runway(self):
        healthy = m.assess_morph_risk(
            [life()], now=100, budget=m.MorphBudget(5, 10, 4, 6, required_resources=frozenset({"context"})),
            checkpoint_age_seconds=1,
        )
        result = m.prepare_preemptive_morph(
            self.mission, self.store, self.beats, self.req, healthy, 110,
            lambda uri: self.ciphertext, self.manifest
        )
        self.assertEqual(result["state"], "NOT_TRIGGERED")

    def test_preemptive_transfer_fences_live_old_owner(self):
        self.assertEqual(self.propose()["state"], "READY_FOR_SIGNED_HANDOVER")
        next_epoch = self.handover()
        self.assertEqual(next_epoch, 2)
        with self.assertRaisesRegex(m.Refused, "STALE_FENCING_LEASE"):
            self.store.authorize_effect(self.mission, self.old, self.epoch, 112)
        self.store.authorize_effect(self.mission, self.new, next_epoch, 112)

    def test_new_owner_must_reconcile_before_privileged_effects(self):
        # Effect reservations still require a live owner/epoch and the real DoF door
        # must independently authorize every downstream side effect.
        self.handover()
        with self.assertRaisesRegex(m.Refused, "STALE_FENCING_LEASE"):
            self.store.reserve_effect(self.mission, "github-push", self.old,
                                      self.epoch, 112)

    def test_fake_handover_proof_denied(self):
        with self.assertRaisesRegex(m.Refused, "INVALID_INDEPENDENT_HANDOVER_PROOF"):
            self.handover(proof=b"forged")

    def test_proof_cannot_change_target_worker(self):
        with self.assertRaisesRegex(m.Refused, "INVALID_INDEPENDENT_HANDOVER_PROOF"):
            self.handover(new="agent-c", proof=self.proof(self.new))

    def test_proof_cannot_change_ttl(self):
        with self.assertRaisesRegex(m.Refused, "INVALID_INDEPENDENT_HANDOVER_PROOF"):
            self.handover(ttl=30, proof=self.proof(ttl=100))

    def test_proof_cannot_change_checkpoint_digest(self):
        with self.assertRaisesRegex(m.Refused, "INVALID_INDEPENDENT_HANDOVER_PROOF"):
            self.handover(digest="f"*64, proof=self.proof())

    def test_unacknowledged_checkpoint_refused(self):
        with self.assertRaisesRegex(m.Refused, "CHECKPOINT_NOT_DURABLY_ACKNOWLEDGED"):
            self.handover(digest="f"*64, proof=self.proof(digest="f"*64))

    def test_preemptive_morph_replay_denied_by_cas(self):
        self.handover()
        with self.assertRaisesRegex(m.Refused, "STALE_FENCING_LEASE"):
            self.handover()

    def test_live_pending_external_effect_blocks_transfer(self):
        self.store.reserve_effect(self.mission, "deploy", self.old, self.epoch, 107)
        self.assertEqual(self.propose()["reason"],
                         "PENDING_RECONCILIATION_REQUIRED")
        with self.assertRaisesRegex(m.Refused, "PENDING_RECONCILIATION_REQUIRED"):
            self.handover()

    def test_unconfigured_verifier_cannot_approve_transfer(self):
        no_verifier = m.LeaseStore(self.path)
        with self.assertRaisesRegex(m.Refused, "INDEPENDENT_HANDOVER_PROOF_REQUIRED"):
            no_verifier.preemptive_handover(
                self.mission, self.old, self.epoch, self.new, 111, 100,
                self.digest, self.uri, handover_proof=b"anything"
            )

    def test_expired_owner_must_use_recovery_takeover(self):
        with self.assertRaisesRegex(m.Refused, "STALE_FENCING_LEASE"):
            self.handover(now=206)

    def test_same_worker_cannot_assume_different_epoch_via_morph(self):
        with self.assertRaisesRegex(m.Refused, "INVALID_PREEMPTIVE_HANDOVER"):
            self.handover(new=self.old, proof=self.proof(self.old))

    def test_concurrent_handover_has_one_winner(self):
        results = []
        lock = threading.Lock()
        def contender():
            try:
                result = self.handover()
            except m.Refused as exc:
                result = str(exc)
            with lock:
                results.append(result)
        t1, t2 = threading.Thread(target=contender), threading.Thread(target=contender)
        t1.start(); t2.start(); t1.join(); t2.join()
        self.assertEqual(sorted(map(str, results)), ["2", "STALE_FENCING_LEASE"])


if __name__ == "__main__":
    unittest.main()
