"""Falsify missed recovery detection for a leased mission; no external effects."""

import sqlite3
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform" / "estate"))
from continuity.recovery import RecoveryMixin


class Probe(RecoveryMixin):
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            "CREATE TABLE mission_attempts (attempt_id TEXT, lease_expires_at REAL, last_progress_at REAL, last_heartbeat_at REAL, state TEXT)"
        )
        self.db.execute(
            "INSERT INTO mission_attempts VALUES ('a', 2000, 100, 699, 'RUNNING')"
        )
        self.mission = {
            "current_attempt_id": "a",
            "state": "EXECUTING",
            "created_at": 100,
        }

    def _require(self, mission_id):
        return self.mission


class RecoveryDeadlineTests(unittest.TestCase):
    def setUp(self):
        self.p = Probe()
        self.addCleanup(self.p.db.close)

    def check(self, expected, now=700):
        self.assertEqual(self.p.needs_takeover("m", now=now)["takeover"], expected)

    def test_exact_boundary_with_fresh_heartbeat(self):
        self.check(False, 699.999)
        self.check(True, 700)

    def test_protected_phases_are_observed(self):
        for state in ("VERIFYING", "PROMOTING", "DEPLOY_VERIFY"):
            with self.subTest(state=state):
                self.p.mission["state"] = state
                self.check(True, 701)

    def test_missing_active_attempt(self):
        self.p.mission["current_attempt_id"] = "absent"
        self.check(True, 101)

    def test_nonrunning_active_attempt(self):
        self.p.db.execute("UPDATE mission_attempts SET state='FAILED'")
        self.check(True, 101)

    def test_healthy_progress(self):
        self.p.db.execute("UPDATE mission_attempts SET last_progress_at=699")
        self.check(False)

    def test_lease_expiry(self):
        self.p.db.execute("UPDATE mission_attempts SET lease_expires_at=103")
        self.check(True, 103)

    def test_nonworker_states_do_not_fence(self):
        for state in (
            "ACCEPTED",
            "READY",
            "RECOVERY_PENDING",
            "REASSIGNING",
            "OPERATING",
        ):
            with self.subTest(state=state):
                self.p.mission["state"] = state
                self.check(False, 5000)

    def test_zero_timestamp_is_valid(self):
        self.p.db.execute("UPDATE mission_attempts SET last_progress_at=0")
        self.check(True, 600)


if __name__ == "__main__":
    unittest.main()
