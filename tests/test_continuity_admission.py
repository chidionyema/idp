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
        self.store = c.LeaseStore(str(pathlib.Path(self.temp.name) / "queue.db"))
        self.epoch = self.store.claim("mission", "owner-a", 100, 20)

    def tearDown(self):
        self.temp.cleanup()

    def test_pending_effect_never_replays_blindly(self):
        self.store.reserve_effect("mission", "github-push-sha", "owner-a", self.epoch, 105)
        with self.assertRaisesRegex(c.Refused, "PENDING_RECONCILIATION_REQUIRED"):
            self.store.reserve_effect("mission", "github-push-sha", "owner-a", self.epoch, 106)

    def test_independent_proof_needed_to_confirm(self):
        self.store.reserve_effect("mission", "publish", "owner-a", self.epoch, 105)
        with self.assertRaisesRegex(c.Refused, "INDEPENDENT_PROOF_REQUIRED"):
            self.store.confirm_effect("mission", "publish", "owner-a", self.epoch, 106, "a" * 64)
        self.store.confirm_effect("mission", "publish", "owner-a", self.epoch, 106, "a" * 64,
                                  verified_by_independent_broker=True)
        self.assertEqual(self.store.effect_snapshot("mission", "publish")[2:], ("CONFIRMED", "a" * 64))
        with self.assertRaisesRegex(c.Refused, "ALREADY_CONFIRMED"):
            self.store.reserve_effect("mission", "publish", "owner-a", self.epoch, 107)

    def test_zombie_cannot_finalize_or_reserve_effect(self):
        self.store.reserve_effect("mission", "deploy", "owner-a", self.epoch, 105)
        new_epoch = self.store.claim("mission", "owner-b", 121, 20)
        with self.assertRaisesRegex(c.Refused, "STALE_FENCING_LEASE"):
            self.store.confirm_effect("mission", "deploy", "owner-a", self.epoch, 122, "c" * 64,
                                      verified_by_independent_broker=True)
        with self.assertRaisesRegex(c.Refused, "STALE_FENCING_LEASE"):
            self.store.reserve_effect("mission", "new-task", "owner-a", self.epoch, 122)
        with self.assertRaisesRegex(c.Refused, "PENDING_RECONCILIATION_REQUIRED"):
            self.store.reserve_effect("mission", "deploy", "owner-b", new_epoch, 122)

    def test_invalid_digest_and_unreserved_effect_refused(self):
        with self.assertRaisesRegex(c.Refused, "INVALID_RECEIPT_DIGEST"):
            self.store.confirm_effect("mission", "unknown", "owner-a", self.epoch, 106,
                                      "bad", verified_by_independent_broker=True)
        with self.assertRaisesRegex(c.Refused, "EFFECT_NOT_RESERVED_BY_OWNER"):
            self.store.confirm_effect("mission", "unknown", "owner-a", self.epoch, 106,
                                      "a" * 64, verified_by_independent_broker=True)

    def test_effect_state_survives_restart(self):
        self.store.reserve_effect("mission", "billing", "owner-a", self.epoch, 105)
        second = c.LeaseStore(self.store.path)
        with self.assertRaisesRegex(c.Refused, "PENDING_RECONCILIATION_REQUIRED"):
            second.reserve_effect("mission", "billing", "owner-a", self.epoch, 106)


if __name__ == '__main__':
    unittest.main()
