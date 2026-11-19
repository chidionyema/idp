"""Falsifiers for the recovery policy and real SQLite custody mixins.

No cloud, credential, production deletion or external-provider calls.
"""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'platform' / 'estate'))
from continuity.effects import EffectsMixin
from continuity.fields import DuplicateEffect, InvalidTransition, LeaseNotAcquired, StaleFenceError
from continuity.leases import LeaseMixin
from continuity.recovery import RecoveryMixin
from continuity.recovery_policy import RULES, RecoveryRefused, plan_recovery

REV = 'a' * 40
DIGEST = 'b' * 64
NOW = 1000.0


def snapshot(kind='WORKER_LOST', *, now=NOW, epoch=0, attempt=None):
    capability, required = RULES[kind]
    fresh = {'observed_at': now-1, 'expires_at': now+60}
    worker = {'agent_adapter': 'legion', 'provider': 'cloud', 'model': 'deterministic', 'execution_host': 'host1', 'failure_domain': 'cloud1', 'worktree_id': 'wt', 'base_sha': REV}
    return {**fresh, 'kind': kind, 'mission_id': 'm', 'fault_id': 'f', 'revision': REV,
            'mandate_version': 1, 'revocation_epoch': 0, 'lease_epoch': epoch, 'attempt_id': attempt,
            'failed_domains': ['failed'], 'target': {'identity': 'requested-target', 'kind': 'Deployment', 'namespace': 'llm', 'name': 'router', 'uid': 'uid-1', 'resource_version': '12', 'substrate': 'arm-k3s'},
            'proofs': {p: DIGEST for p in ('topology_complete', 'current_authority', 'scope_authorized', *required)},
            'nodes': {n: {**fresh, 'domain': domain, 'health': 'OK', 'requires': deps, 'host_kind': 'cloud'} for n, domain, deps in [('runner', 'cloud1', ['vault']), ('judge', 'cloud2', []), ('vault', 'separate', [])]},
            'offers': [{**fresh, **worker, 'node': 'runner', 'principal': 'executor', 'capability': capability, 'role': 'executor', 'cost': 0, 'capacity': True, 'authorized': True},
                       {**fresh, 'node': 'judge', 'principal': 'oracle', 'failure_domain': 'cloud2', 'capability': capability, 'role': 'verifier', 'cost': 0, 'capacity': True, 'authorized': True}]}


def signed(s):
    """Test-only oracle binds the complete snapshot, not an asserted flag."""
    expected = hashlib.sha256(json.dumps(s, sort_keys=True).encode()).hexdigest()
    return lambda observed: hashlib.sha256(json.dumps(observed, sort_keys=True).encode()).hexdigest() == expected


def plan(s):
    return plan_recovery(s, signed(s), now=NOW, mission_id='m')


@pytest.mark.parametrize('kind', RULES)
def test_each_failure_has_bounded_distinct_worker_and_oracle(kind):
    s = snapshot(kind)
    got = plan(s)
    assert got.action == RULES[kind][0]
    assert got.executor['principal'] != got.verifier['principal']
    assert len(got.key) == 64


@pytest.mark.parametrize('mutation', [
    lambda s: s['nodes']['vault'].update(domain='failed'),
    lambda s: s['nodes']['vault'].update(requires=['runner']),
    lambda s: s['nodes']['vault'].update(host_kind='mac'),
    lambda s: s['nodes']['vault'].update(health='UNKNOWN'),
    lambda s: s['nodes']['vault'].update(expires_at=NOW),
    lambda s: s['nodes'].pop('vault'),
    lambda s: s['nodes']['judge'].update(requires=['runner']),
    lambda s: s['offers'][1].update(principal='executor'),
    lambda s: s['offers'][0].update(cost=1),
    lambda s: s['offers'][0].update(capacity=False),
    lambda s: s['offers'][0].update(authorized=False),
    lambda s: s['offers'][0].update(base_sha='0'*40),
    lambda s: s['proofs'].pop('checkpoint_verified'),
    lambda s: s.update(expires_at=NOW),
    lambda s: s.update(mission_id='other'),
    lambda s: s.update(lease_epoch=True),
])
def test_denies_broken_dependencies_stale_or_unbound_admission(mutation):
    s = snapshot()
    mutation(s)
    with pytest.raises(RecoveryRefused):
        plan(s)


def test_signed_snapshot_cannot_be_changed_after_admission():
    s = snapshot()
    verify = signed(s)
    s['target']['identity'] = 'different-target'
    with pytest.raises(RecoveryRefused):
        plan_recovery(s, verify, now=NOW, mission_id='m')


@pytest.mark.parametrize('kind', ['PersistentVolumeClaim', 'Secret', 'Namespace', 'StatefulSet'])
def test_orphan_pruning_refuses_data_and_protected_resources(kind):
    s = snapshot('VERIFIED_ORPHAN')
    s['target']['kind'] = kind
    with pytest.raises(RecoveryRefused):
        plan(s)


def test_orphan_requires_uid_and_resource_version():
    s = snapshot('VERIFIED_ORPHAN')
    del s['target']['uid']
    with pytest.raises(RecoveryRefused):
        plan(s)


def test_expiry_is_bounded_by_transitive_dependency():
    s = snapshot()
    s['nodes']['vault']['expires_at'] = NOW+3
    assert plan(s).expires_at == NOW+3


def test_idempotency_across_worker_replacement_and_new_observations():
    s = snapshot()
    first = plan(s).key
    s['offers'][0]['principal'] = 'another-executor'
    s['lease_epoch'] = 7
    assert plan(s).key == first
    s['revocation_epoch'] = 1
    assert plan(s).key != first


class Store(EffectsMixin, LeaseMixin, RecoveryMixin):
    # Actual SQLite transactions and real mixins; sensor/dispatcher are test adapters.
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS missions(mission_id TEXT PRIMARY KEY,state TEXT,current_attempt_id TEXT,current_lease_epoch INT,created_at REAL,retry_budget_remaining INT,mandate_version INT,revocation_epoch INT);
        CREATE TABLE IF NOT EXISTS mission_attempts(attempt_id TEXT PRIMARY KEY,mission_id TEXT,agent_adapter TEXT,provider TEXT,model TEXT,execution_host TEXT,failure_domain TEXT,worktree_id TEXT,base_sha TEXT,started_at REAL,lease_epoch INT,lease_expires_at REAL,last_heartbeat_at REAL,last_progress_at REAL,state TEXT,failure_class TEXT);
        CREATE TABLE IF NOT EXISTS external_effects(effect_id TEXT PRIMARY KEY,mission_id TEXT,attempt_id TEXT,lease_epoch INT,mandate_version INT,operation TEXT,target TEXT,idempotency_key TEXT UNIQUE,intent_digest TEXT,state TEXT,reconciliation_status TEXT DEFAULT 'PENDING',external_receipt TEXT,observed_at REAL,verified_by TEXT);
        CREATE TABLE IF NOT EXISTS failure_classes(failure_class_id TEXT PRIMARY KEY,fingerprint TEXT UNIQUE,first_seen REAL,occurrence_count INT,owner TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS events(mission_id TEXT,state TEXT);
        INSERT OR IGNORE INTO missions VALUES('m','READY',NULL,0,0,3,1,0);
        ''')
    def _require(self, mission_id):
        return dict(self.db.execute('SELECT * FROM missions WHERE mission_id=?', (mission_id,)).fetchone())
    def _event(self, mission_id, state, *args, cur, **kwargs):
        cur.execute('INSERT INTO events VALUES(?,?)',(mission_id,state))
    def transition(self, mission_id, state, actor, cause, **kwargs):
        with self.db:
            cur = self.db.execute('BEGIN IMMEDIATE')
            if self._require(mission_id)['state'] != 'RECOVERY_PENDING' or state != 'REASSIGNING':
                raise InvalidTransition('not pending')
            cur.execute('UPDATE missions SET state=? WHERE mission_id=?',(state,mission_id))
    def close(self): self.db.close()


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path/'missions.db')
    yield s
    s.close()


def ack(payload): return {**payload, 'accepted': True}


def tick(store, s, dispatch=ack, verify=lambda a,p: True, now=NOW):
    return store.reconcile_fault('m', s, signed(s), dispatch, verify, now=now)


def test_lost_dispatch_ack_recovers_after_durable_restart_without_replay(tmp_path):
    db = tmp_path/'recover.db'
    s = Store(db)
    calls = []
    def lost(payload):
        calls.append(payload)
        raise TimeoutError('response lost after submission')
    first = tick(s, snapshot(), lost)
    assert first['status'] == 'DISPATCH_UNCONFIRMED'
    assert len(calls) == 1
    s.close()
    s = Store(db)
    try:
        assert tick(s, snapshot(), lost)['status'] != 'DISPATCH_ACCEPTED'
        assert len(calls) == 1
        fresh = snapshot(now=NOW+61, epoch=1, attempt=first['lease']['attempt_id'])
        second = tick(s, fresh, now=NOW+61)
        assert second['status'] == 'DISPATCH_ACCEPTED'
        assert second['lease']['lease_epoch'] == 2
        assert second['plan_key'] == first['plan_key']
        assert s._require('m')['retry_budget_remaining'] == 2
        with pytest.raises(StaleFenceError):
            s.assert_fence('m', first['lease']['attempt_id'], 1, now=NOW+62)
        assert s._require('m')['state'] == 'LEASED'  # not fabricated yield
    finally:
        s.close()


def test_stale_detector_cannot_fence_a_recovered_attempt(store):
    a = store.acquire_lease('m', plan(snapshot()).worker, lease_seconds=2000, now=100)
    assert store.needs_takeover('m', now=700)['takeover']
    store.db.execute('UPDATE mission_attempts SET last_progress_at=699')
    with pytest.raises(InvalidTransition):
        store.begin_recovery('m','WORKER_LOST','f',now=700,expected_epoch=1,expected_attempt=a['attempt_id'])
    assert store._require('m')['current_attempt_id'] == a['attempt_id']


def test_budget_exhaustion_preserves_pending_obligation(store):
    a = tick(store, snapshot())['lease']
    store.db.execute('UPDATE missions SET retry_budget_remaining=0')
    r = tick(store,snapshot(now=NOW+61,epoch=1,attempt=a['attempt_id']),now=NOW+61)
    assert r['status'] == 'HOLD'
    assert store._require('m')['state'] == 'REASSIGNING'
    assert store._require('m')['current_attempt_id'] is None


def test_predecessor_side_effect_blocks_new_mutation_until_reconciled(store):
    a = tick(store,snapshot())['lease']
    e = store.record_effect_intent('m',a['attempt_id'],1,'deploy','router','key',{'rev':REV},now=NOW+1)
    calls = []
    def dispatch(payload):
        calls.append(payload)
        return ack(payload)
    b = tick(store,snapshot(now=NOW+61,epoch=1,attempt=a['attempt_id']),dispatch,now=NOW+61)['lease']
    assert calls[0]['reconcile_only'] is True
    with pytest.raises(DuplicateEffect):
        store.record_effect_intent('m',b['attempt_id'],2,'deploy','router','new-key',{'rev':REV},now=NOW+62)
    assert store.record_effect_intent('m',b['attempt_id'],2,'deploy','router','key',{'rev':REV},now=NOW+62)['duplicate']
    store.reconcile_effect(e['effect_id'],'independently observed missing','NOT_STARTED')
    assert not store.record_effect_intent('m',b['attempt_id'],2,'deploy','router','new-key',{'rev':REV},now=NOW+62)['duplicate']
    with pytest.raises(DuplicateEffect):
        store.reconcile_effect(e['effect_id'],'unknown','AMBIGUOUS')


def test_ack_must_be_independently_verified_and_exact(store):
    r = tick(store,snapshot(),lambda p: {**ack(p),'plan_key':'fake'})
    assert r['status'] == 'DISPATCH_UNCONFIRMED'
    assert store._require('m')['state'] == 'LEASED'


def test_mandate_drift_refuses_dispatch(store):
    s = snapshot()
    store.db.execute('UPDATE missions SET mandate_version=2')
    assert tick(store,s)['status'] == 'HOLD'
    assert store._require('m')['state'] == 'READY'


def test_cannot_acquire_an_expired_lease_without_recovery(store):
    worker = plan(snapshot()).worker
    store.acquire_lease('m', worker, lease_seconds=1, now=1)
    with pytest.raises(LeaseNotAcquired):
        store.acquire_lease('m', worker, now=3)


def test_stale_mandate_cannot_fence_current_attempt(store):
    a = store.acquire_lease('m', plan(snapshot()).worker, lease_seconds=1, now=100)
    store.db.execute('UPDATE missions SET mandate_version=2')
    with pytest.raises(InvalidTransition):
        store.begin_recovery('m', 'WORKER_LOST', 'f', now=102,
                             expected_epoch=1, expected_attempt=a['attempt_id'],
                             expected_authority=(1, 0))
    assert store._require('m')['current_attempt_id'] == a['attempt_id']


def test_ack_cannot_change_target_or_action(store):
    r = tick(store, snapshot(), lambda p: {**ack(p), 'action': 'unapproved'})
    assert r['status'] == 'DISPATCH_UNCONFIRMED'


def test_clock_regression_cannot_fence_worker(store):
    store.acquire_lease('m', plan(snapshot()).worker, now=1000)
    assert not store.needs_takeover('m', now=999)['takeover']


def test_concurrent_dispatch_acquires_only_one_lease(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    db = tmp_path/'concurrent.db'
    Store(db).close()
    barrier = Barrier(2)
    def attempt():
        s = Store(db)
        try:
            barrier.wait(timeout=5)
            return tick(s, snapshot())['status']
        finally:
            s.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(lambda _: attempt(), range(2)))
    assert result.count('DISPATCH_ACCEPTED') == 1


def test_killed_worker_is_replaced_after_expiry(tmp_path):
    import subprocess
    db = tmp_path/'killed.db'
    s = Store(db)
    process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    try:
        a = tick(s, snapshot())['lease']
        process.kill()
        assert process.wait(timeout=5) != 0
        s.close()
        s = Store(db)
        b = tick(s, snapshot(now=NOW+61, epoch=1, attempt=a['attempt_id']), now=NOW+61)['lease']
        assert b['lease_epoch'] == 2 and b['attempt_id'] != a['attempt_id']
        with pytest.raises(StaleFenceError):
            s.assert_fence('m', a['attempt_id'], 1, now=NOW+62)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        s.close()
