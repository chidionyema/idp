"""Isolated SQLite falsifiers for the continuity recovery transaction.

The minimal schema exercises the real RecoveryMixin; it is not an estate integration test.
"""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from continuity.recovery import RecoveryMixin  # noqa: E402


class Store(RecoveryMixin):
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None, timeout=5)
        self.db.row_factory = sqlite3.Row

    def _event(self, mission_id, to_state, actor, cause, evidence, *, attempt_id, lease_epoch, from_state, cur):
        cur.execute("INSERT INTO events VALUES(?,?,?,?)", (mission_id, to_state, attempt_id, lease_epoch))


@pytest.fixture
def fixture(tmp_path):
    path = tmp_path / "state.sqlite"
    s = Store(path)
    s.db.executescript("""CREATE TABLE missions(mission_id TEXT PRIMARY KEY,state TEXT,current_attempt_id TEXT,current_lease_epoch INTEGER,created_at REAL);
    CREATE TABLE mission_attempts(attempt_id TEXT PRIMARY KEY,state TEXT,lease_expires_at REAL,last_progress_at REAL,failure_class TEXT);
    CREATE TABLE failure_classes(failure_class_id TEXT PRIMARY KEY,fingerprint TEXT UNIQUE,first_seen REAL,occurrence_count INTEGER,owner TEXT,status TEXT);
    CREATE TABLE events(mission_id TEXT,state TEXT,attempt_id TEXT,epoch INTEGER);
    INSERT INTO missions VALUES('m','EXECUTING','a',1,100);
    INSERT INTO mission_attempts VALUES('a','RUNNING',2000,100,NULL);""")
    yield s, path
    s.db.close()


@pytest.mark.parametrize("state", ["LEASED", "EXECUTING", "CHECKPOINTING", "VERIFYING", "PROMOTING", "DEPLOY_VERIFY"])
def test_boundary(fixture, state):
    s, _ = fixture
    s.db.execute("UPDATE missions SET state=?", (state,))
    assert not s.recover_stalled("m", 699.99)["transitioned"]
    assert s.recover_stalled("m", 700)["transitioned"]
    assert s.db.execute("SELECT state,current_attempt_id FROM missions").fetchone()[:] == ("RECOVERY_PENDING", None)
    assert s.db.execute("SELECT state FROM mission_attempts").fetchone()[0] == "FAILED"


def test_progress_after_observation(fixture):
    s, _ = fixture
    assert s.needs_takeover("m", 700)["takeover"]
    s.db.execute("UPDATE mission_attempts SET last_progress_at=701")
    assert not s.recover_stalled("m", 702)["transitioned"]
    assert s.db.execute("SELECT state FROM mission_attempts").fetchone()[0] == "RUNNING"


def test_new_lease_after_observation(fixture):
    s, _ = fixture
    assert s.needs_takeover("m", 700)["takeover"]
    s.db.execute("INSERT INTO mission_attempts VALUES('b','RUNNING',1600,701,NULL)")
    s.db.execute("UPDATE missions SET current_attempt_id='b',current_lease_epoch=2")
    assert not s.recover_stalled("m", 702)["transitioned"]
    assert s.db.execute("SELECT state FROM mission_attempts WHERE attempt_id='b'").fetchone()[0] == "RUNNING"


def test_concurrent_wakeups(fixture):
    s, path = fixture

    def run(_):
        t = Store(path)
        try:
            return t.recover_stalled("m", 700)["transitioned"]
        finally:
            t.db.close()

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(run, range(24))) == 1
    assert s.db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    assert s.db.execute("SELECT occurrence_count FROM failure_classes").fetchone()[0] == 1


def test_expired_lease(fixture):
    s, _ = fixture
    s.db.execute("UPDATE mission_attempts SET lease_expires_at=150")
    assert s.recover_stalled("m", 150)["transitioned"]


def test_missing_attempt(fixture):
    s, _ = fixture
    s.db.execute("UPDATE missions SET current_attempt_id=NULL")
    assert s.recover_stalled("m", 150)["transitioned"]


@pytest.mark.parametrize("state", ["ACCEPTED", "READY", "RECOVERY_PENDING", "REASSIGNING", "OPERATING"])
def test_nonworker_stage(fixture, state):
    s, _ = fixture
    s.db.execute("UPDATE missions SET state=?", (state,))
    assert not s.recover_stalled("m", 3000)["transitioned"]
    assert s.db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
