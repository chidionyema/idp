"""Adversarial first-tranche tests for #7790, actual SQLite transactions, no mocks."""
import importlib.util
import pathlib
import tempfile
import threading
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / 'platform/queue/continuity_admission.py'
spec = importlib.util.spec_from_file_location('continuity_admission', SOURCE)
import sys
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
c = module


def offer(wid, domain, *, auth=True, at=100, slots=1, quota=True,
          context=1000, cost=0, latency=50, completed=0.9,
          caps=frozenset({'python', 'github'})):
    return c.WorkerOffer(wid, domain, caps, auth, at, slots, quota, context,
                         cost, latency, completed)


class CapacityTests(unittest.TestCase):
    def setUp(self):
        self.req = c.Requirement(frozenset({'github'}), 5, 500, 'arm-a')

    def test_unverified_identity_denied(self):
        self.assertEqual(c.eligible(offer('fake', 'arm-b', auth=False), self.req, 110)[1], 'UNAUTHENTICATED_OFFER')

    def test_expired_or_future_offer_denied(self):
        self.assertFalse(c.eligible(offer('x', 'arm-b', at=-20), self.req, 110)[0])
        self.assertFalse(c.eligible(offer('x', 'arm-b', at=200), self.req, 110)[0])

    def test_no_quota_or_slots_denied(self):
        for item in (offer('x', 'b', quota=False), offer('x', 'b', slots=0)):
            self.assertFalse(c.eligible(item, self.req, 110)[0])

    def test_context_and_tool_scope_denied(self):
        self.assertFalse(c.eligible(offer('x', 'b', context=1), self.req, 110)[0])
        self.assertFalse(c.eligible(offer('x', 'b', caps=frozenset()), self.req, 110)[0])

    def test_budget_and_nan_denied(self):
        self.assertFalse(c.eligible(offer('x', 'b', cost=6), self.req, 110)[0])
        self.assertFalse(c.eligible(offer('x', 'b', completed=float('nan')), self.req, 110)[0])

    def test_independent_failure_domain_prefers_different_host(self):
        chosen = c.select_worker([offer('same', 'arm-a', completed=1),
                                  offer('other', 'gh-b', completed=.7)], self.req, 110)
        self.assertEqual(chosen.worker_id, 'other')

    def test_no_eligible_capacity_stays_unassigned(self):
        self.assertIsNone(c.select_worker([offer('x', 'a', quota=False)], self.req, 110))

    def test_excluded_owner_cannot_reclaim(self):
        got = c.select_worker([offer('old', 'gh-b'), offer('new', 'gh-c')], self.req, 110,
                              excluded_workers=frozenset({'old'}))
        self.assertEqual(got.worker_id, 'new')


class LeaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = c.LeaseStore(str(pathlib.Path(self.temp.name) / 'queue.db'))

    def tearDown(self):
        self.temp.cleanup()

    def test_claim_expires_and_fences_stale_worker(self):
        e1 = self.store.claim('m1', 'kimi', 100, 20)
        self.assertEqual(e1, 1)
        with self.assertRaisesRegex(c.Refused, 'ACTIVE_OWNER'):
            self.store.claim('m1', 'claude', 110, 20)
        e2 = self.store.claim('m1', 'claude', 120, 20)
        self.assertEqual(e2, 2)
        with self.assertRaisesRegex(c.Refused, 'STALE_FENCING_LEASE'):
            self.store.authorize_effect('m1', 'kimi', e1, 125)
        self.store.authorize_effect('m1', 'claude', e2, 125)

    def test_expired_epoch_cannot_write_without_handover(self):
        e = self.store.claim('m1', 'kimi', 100, 20)
        with self.assertRaisesRegex(c.Refused, 'STALE_FENCING_LEASE'):
            self.store.authorize_effect('m1', 'kimi', e, 120)

    def test_heartbeat_replay_refused(self):
        e = self.store.claim('m1', 'kimi', 100, 20)
        self.store.heartbeat('m1', 'kimi', e, 110, 20, sequence=1)
        with self.assertRaisesRegex(c.Refused, 'REPLAY_OR_CLOCK_REGRESSION'):
            self.store.heartbeat('m1', 'kimi', e, 111, 20, sequence=1)

    def test_heartbeat_cannot_revive_expired_owner(self):
        e = self.store.claim('m1', 'kimi', 100, 20)
        with self.assertRaisesRegex(c.Refused, 'STALE_FENCING_LEASE'):
            self.store.heartbeat('m1', 'kimi', e, 121, 20, sequence=1)

    def test_checkpoint_requires_real_digest_shape_and_uri(self):
        e = self.store.claim('m1', 'kimi', 100, 20)
        with self.assertRaisesRegex(c.Refused, 'BAD_CHECKPOINT'):
            self.store.heartbeat('m1', 'kimi', e, 110, 20, 1, 'sha256:chk_98e', 'oci://x')
        self.store.heartbeat('m1', 'kimi', e, 110, 20, 1, 'a'*64, 'oci://vault/m1')
        self.assertEqual(self.store.snapshot('m1')[-2:], ('a'*64, 'oci://vault/m1'))

    def test_clock_regression_refused(self):
        self.store.claim('m1', 'kimi', 100, 20)
        with self.assertRaisesRegex(c.Refused, 'CLOCK_REGRESSION'):
            self.store.claim('m1', 'other', 99, 20)

    def test_real_sqlite_concurrent_claims_have_one_winner(self):
        results, lock = [], threading.Lock()
        def contender(worker):
            try:
                r = self.store.claim('m1', worker, 100, 20)
            except c.Refused as exc:
                r = str(exc)
            with lock:
                results.append(r)
        t1 = threading.Thread(target=contender, args=('kimi',))
        t2 = threading.Thread(target=contender, args=('claude',))
        t1.start(); t2.start(); t1.join(); t2.join()
        self.assertEqual(sorted(map(str, results)), ['1', 'ACTIVE_OWNER'])

    def test_restart_retains_epoch(self):
        self.store.claim('m1', 'kimi', 100, 20)
        restarted = c.LeaseStore(self.store.path)
        self.assertEqual(restarted.claim('m1', 'claude', 120, 20), 2)



class EffectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        import hashlib
        self.sign = lambda message: hashlib.sha256(b"fixture-only-key" + message).digest()
        self.store = c.LeaseStore(str(pathlib.Path(self.temp.name) / "queue.db"),
                                  receipt_verifier=lambda message, proof:
                                      self.sign(message) == proof)
        self.epoch = self.store.claim("mission", "owner-a", 100, 20)

    def tearDown(self):
        self.temp.cleanup()

    def proof(self, action, digest, *, worker="owner-a", epoch=None):
        epoch = self.epoch if epoch is None else epoch
        message = (f"genesis.effect.v1\nmission\n{action}\n{worker}\n"
                   f"{epoch}\n{digest}\n").encode()
        return self.sign(message)

    def test_pending_effect_never_replays_blindly(self):
        self.store.reserve_effect("mission", "github-push-sha", "owner-a", self.epoch, 105)
        with self.assertRaisesRegex(c.Refused, "PENDING_RECONCILIATION_REQUIRED"):
            self.store.reserve_effect("mission", "github-push-sha", "owner-a", self.epoch, 106)

    def test_independent_proof_needed_to_confirm(self):
        self.store.reserve_effect("mission", "publish", "owner-a", self.epoch, 105)
        with self.assertRaisesRegex(c.Refused, "INVALID_INDEPENDENT_RECEIPT"):
            self.store.confirm_effect("mission", "publish", "owner-a", self.epoch, 106, "a" * 64)
        self.store.confirm_effect("mission", "publish", "owner-a", self.epoch, 106, "a" * 64,
                                  receipt_proof=self.proof("publish", "a" * 64))
        self.assertEqual(self.store.effect_snapshot("mission", "publish")[2:], ("CONFIRMED", "a" * 64))
        with self.assertRaisesRegex(c.Refused, "ALREADY_CONFIRMED"):
            self.store.reserve_effect("mission", "publish", "owner-a", self.epoch, 107)

    def test_zombie_cannot_finalize_or_reserve_effect(self):
        self.store.reserve_effect("mission", "deploy", "owner-a", self.epoch, 105)
        new_epoch = self.store.claim("mission", "owner-b", 121, 20)
        with self.assertRaisesRegex(c.Refused, "STALE_FENCING_LEASE"):
            self.store.confirm_effect("mission", "deploy", "owner-a", self.epoch, 122, "c" * 64,
                                      receipt_proof=self.proof("deploy", "c" * 64))
        with self.assertRaisesRegex(c.Refused, "STALE_FENCING_LEASE"):
            self.store.reserve_effect("mission", "new-task", "owner-a", self.epoch, 122)
        with self.assertRaisesRegex(c.Refused, "PENDING_RECONCILIATION_REQUIRED"):
            self.store.reserve_effect("mission", "deploy", "owner-b", new_epoch, 122)

    def test_invalid_digest_and_unreserved_effect_refused(self):
        with self.assertRaisesRegex(c.Refused, "INVALID_RECEIPT_DIGEST"):
            self.store.confirm_effect("mission", "unknown", "owner-a", self.epoch, 106,
                                      "bad", receipt_proof=b"ignored")
        with self.assertRaisesRegex(c.Refused, "EFFECT_NOT_RESERVED_BY_OWNER"):
            self.store.confirm_effect("mission", "unknown", "owner-a", self.epoch, 106,
                                      "a" * 64, receipt_proof=self.proof("unknown", "a" * 64))

    def test_effect_state_survives_restart(self):
        self.store.reserve_effect("mission", "billing", "owner-a", self.epoch, 105)
        second = c.LeaseStore(self.store.path)
        with self.assertRaisesRegex(c.Refused, "PENDING_RECONCILIATION_REQUIRED"):
            second.reserve_effect("mission", "billing", "owner-a", self.epoch, 106)

    def test_wrong_proof_fails_even_with_fresh_lease(self):
        self.store.reserve_effect("mission", "publish", "owner-a", self.epoch, 105)
        with self.assertRaisesRegex(c.Refused, "INVALID_INDEPENDENT_RECEIPT"):
            self.store.confirm_effect("mission", "publish", "owner-a", self.epoch,
                                      106, "a" * 64, receipt_proof=b"forged")

    def test_no_verifier_cannot_self_certify(self):
        second = c.LeaseStore(self.store.path)
        with self.assertRaisesRegex(c.Refused, "INDEPENDENT_PROOF_REQUIRED"):
            second.confirm_effect("mission", "publish", "owner-a", self.epoch,
                                  106, "a" * 64, receipt_proof=b"anything")

    def test_receipt_cannot_be_replayed_for_another_action(self):
        self.store.reserve_effect("mission", "deploy", "owner-a", self.epoch, 105)
        with self.assertRaisesRegex(c.Refused, "INVALID_INDEPENDENT_RECEIPT"):
            self.store.confirm_effect("mission", "deploy", "owner-a", self.epoch, 106,
                                      "b" * 64, receipt_proof=self.proof("publish", "b" * 64))


class HeartbeatRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.beats = c.HeartbeatRegistry(str(pathlib.Path(self.temp.name) / "beats.db"))

    def tearDown(self):
        self.temp.cleanup()

    def feed(self, *, worker="cloud-a", now=100, seq=1, quota=True,
             slots=1, cap_source="provider_api", digest=None, actor=None):
        self.beats.observe(offer(worker, "provider-a", at=now, quota=quota,
                                 slots=slots), trusted_actor=actor or worker,
                           broker_now=now, sequence=seq, adapter="GH Actions",
                           provider="vendor-a", host="host-a",
                           capacity_source=cap_source, capacity_evidence="verified:run/123",
                           progress_digest=digest)

    def test_absent_web_surface_remains_unknown(self):
        row = self.beats.observed(150, expected_workers=["gemini-web"])["gemini-web"]
        self.assertEqual(row["status"], "UNKNOWN")
        self.assertIsNone(row["offer"])

    def test_real_authenticated_observation_is_eligible(self):
        self.feed()
        r = self.beats.observed(110)["cloud-a"]
        self.assertEqual(r["status"], "READY")
        self.assertEqual(r["offer"].worker_id, "cloud-a")

    def test_unverified_worker_principal_cannot_claim_identity(self):
        with self.assertRaisesRegex(c.Refused, "UNAUTHENTICATED_HEARTBEAT"):
            self.feed(actor="other-actor")

    def test_replay_or_clock_regression_rejected(self):
        self.feed()
        with self.assertRaisesRegex(c.Refused, "HEARTBEAT_REPLAY_OR_CLOCK_REGRESSION"):
            self.feed(now=101, seq=1)
        with self.assertRaisesRegex(c.Refused, "HEARTBEAT_REPLAY_OR_CLOCK_REGRESSION"):
            self.feed(now=99, seq=2)

    def test_stale_beat_is_unknown_not_alive(self):
        self.feed()
        self.assertEqual(self.beats.observed(201, ttl=90)["cloud-a"]["status"], "UNKNOWN")

    def test_self_reported_capacity_is_not_ready_for_critical_work(self):
        self.feed(cap_source="authenticated_runtime")
        self.assertEqual(self.beats.observed(110)["cloud-a"]["status"], "PROVISIONAL")

    def test_worker_exhaustion_disables_capacity(self):
        self.feed(quota=False)
        self.assertEqual(self.beats.observed(105)["cloud-a"]["status"], "EXHAUSTED")

    def test_progress_stall_distinct_from_liveness(self):
        self.feed(digest="a" * 64)
        self.feed(now=101, seq=2, digest="a" * 64)
        self.assertEqual(self.beats.observed(400, ttl=500, max_progress_age=200)["cloud-a"]["status"], "STALLED")
        self.feed(now=401, seq=3, digest="b" * 64)
        self.assertEqual(self.beats.observed(402, ttl=500, max_progress_age=200)["cloud-a"]["status"], "READY")

    def test_invalid_client_timestamp_refused(self):
        with self.assertRaisesRegex(c.Refused, "UNTRUSTED_CLOCK_OR_SEQUENCE"):
            self.beats.observe(offer("cloud-a", "d", at=90), trusted_actor="cloud-a",
                               broker_now=100, sequence=1, adapter="GH", provider="x",
                               host="h", capacity_source="provider_api",
                               capacity_evidence="verification")



class TakeoverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        path = str(pathlib.Path(self.temp.name) / "queue.db")
        self.store, self.beats = c.LeaseStore(path), c.HeartbeatRegistry(path)
        self.old_epoch = self.store.claim("mission", "old", 100, 20)
        self.payload = b"encrypted-checkpoint-ciphertext"
        import hashlib
        self.digest = hashlib.sha256(self.payload).hexdigest()
        self.uri = "oci://estate-checkpoints/mission/blob"
        self.objects = {self.uri: self.payload}
        self.store.heartbeat("mission", "old", self.old_epoch, 110, 20,
                             sequence=1, checkpoint_sha256=self.digest, checkpoint_uri=self.uri)
        self.beats.observe(offer("cloud-new", "gh-independent", at=200), trusted_actor="cloud-new",
                           broker_now=200, sequence=1, adapter="GH", provider="provider-b",
                           host="host-b", capacity_source="provider_api", capacity_evidence="run:success")
        self.req = c.Requirement(frozenset({"github"}), 5, 500, "old-domain")

    def tearDown(self):
        self.temp.cleanup()

    def takeover(self, now=201, decrypt=None):
        if decrypt is None:
            decrypt = lambda mission, uri, content: {
                "schema": "genesis.mission.checkpoint.v1",
                "mission_id": mission, "source_sha": "a" * 40,
                "resume_cursor": "next-verified-step",
            }
        return c.attempt_verified_takeover(
            "mission", self.store, self.beats, self.req, now, 30,
            lambda uri: self.objects[uri], decrypt
        )

    def test_good_checkpoint_and_capacity_transfers_fenced_ownership(self):
        result = self.takeover()
        self.assertEqual(result["state"], "CUSTODY_TRANSFERRED")
        self.assertEqual(result["worker_id"], "cloud-new")
        self.assertGreater(result["lease_epoch"], self.old_epoch)
        with self.assertRaisesRegex(c.Refused, "STALE_FENCING_LEASE"):
            self.store.authorize_effect("mission", "old", self.old_epoch, 202)

    def test_unexpired_owner_cannot_be_preempted(self):
        result = self.takeover(now=125)
        self.assertEqual(result["reason"], "OWNER_LEASE_STILL_ACTIVE")

    def test_corrupt_checkpoint_refuses_takeover(self):
        self.objects[self.uri] = b"tampered"
        result = self.takeover()
        self.assertEqual(result["reason"], "CHECKPOINT_DIGEST_MISMATCH")
        self.assertEqual(self.store.snapshot("mission")[0], "old")

    def test_no_healthy_replacement_preserves_mission(self):
        result = self.takeover(now=401)
        self.assertEqual(result["reason"], "NO_ELIGIBLE_CAPACITY")
        self.assertEqual(self.store.snapshot("mission")[0], "old")

    def test_duplicate_takeover_does_not_spawn_another_owner(self):
        first = self.takeover()
        second = self.takeover(now=202)
        self.assertEqual(first["state"], "CUSTODY_TRANSFERRED")
        self.assertEqual(second["state"], "RECOVERY_PENDING")
        self.assertEqual(second["reason"], "OWNER_LEASE_STILL_ACTIVE")

    def test_unreconciled_effect_is_carried_to_new_owner_as_blocker(self):
        self.store.reserve_effect("mission", "billing", "old", self.old_epoch, 111)
        result = self.takeover()
        self.assertEqual(result["pending_effects_requiring_reconciliation"], ["billing"])
        self.assertEqual(result["state"], "RECONCILIATION_REQUIRED")
        self.assertEqual(result["scope"], "READ_AND_RECONCILE")

    def test_remote_read_exception_is_not_a_success(self):
        self.objects.clear()
        result = self.takeover()
        self.assertEqual(result["reason"], "CHECKPOINT_READ_FAILED")

    def test_missing_decryptor_does_not_transfer_custody(self):
        got = c.attempt_verified_takeover(
            "mission", self.store, self.beats, self.req, 201, 30,
            lambda uri: self.objects[uri],
        )
        self.assertEqual(got["reason"], "AUTHENTICATED_DECRYPTOR_UNAVAILABLE")
        self.assertEqual(self.store.snapshot("mission")[0], "old")

    def test_decrypt_failure_does_not_transfer_custody(self):
        def decrypt(mission, uri, ciphertext):
            raise RuntimeError("KMS unavailable")
        got = self.takeover(decrypt=decrypt)
        self.assertEqual(got["reason"], "CHECKPOINT_DECRYPT_OR_VALIDATION_FAILED")
        self.assertEqual(self.store.snapshot("mission")[0], "old")

    def test_decrypted_wrong_mission_refuses_takeover(self):
        got = self.takeover(decrypt=lambda m, uri, blob: {
            "schema": "genesis.mission.checkpoint.v1",
            "mission_id": "forged-mission", "source_sha": "a" * 40,
            "resume_cursor": "action",
        })
        self.assertEqual(got["reason"], "INVALID_DECRYPTED_MANIFEST")
        self.assertEqual(self.store.snapshot("mission")[0], "old")

    def test_decrypted_short_sha_refuses_takeover(self):
        got = self.takeover(decrypt=lambda m, uri, blob: {
            "schema": "genesis.mission.checkpoint.v1",
            "mission_id": m, "source_sha": "da1536c7",
            "resume_cursor": "action",
        })
        self.assertEqual(got["reason"], "INVALID_DECRYPTED_MANIFEST")
        self.assertEqual(self.store.snapshot("mission")[0], "old")

    def test_takeover_is_never_operational_certification(self):
        result = self.takeover()
        self.assertFalse(result["operationally_complete"])
        self.assertFalse(result["runtime_dispatch_verified"])
        self.assertEqual(result["scope"], "PENDING_DOF_AUTHORIZATION")


if __name__ == '__main__':
    unittest.main()
