"""unittest for cp11 -- consensus check (alert on mismatch, `sb consensus`).
Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.sidecar.test_consensus -v

Never opens maestro's real database -- every test builds its own
disposable sqlite3 file, same pattern as test_dualread.py.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sovereign import config
from sovereign.engine import receipts
from sovereign.sidecar import core as sidecar_core
from sovereign.sidecar import dualread

_FIXED_KEY = b"\x06" * 32


class ConsensusTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.dag_dir = root / "dag"
        self.inbox_path = root / "alerts" / "inbox.jsonl"
        for name, val in (
            ("SB_RECEIPTS", root / "receipts.jsonl"),
            ("RECEIPTS_HEAD", root / "receipts.head"),
            ("SHADOW_HEADS_DIR", root / "heads"),
            ("ESTATE_ALERT_INBOX", self.inbox_path),
        ):
            p = patch.object(config, name, val)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(receipts, "get_or_create_key", lambda: (_FIXED_KEY, "software_file"))
        p.start()
        self.addCleanup(p.stop)

        self.db_path = root / "legacy.db"
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("CREATE TABLE episodes (id TEXT PRIMARY KEY, lane TEXT, note TEXT)")
        self.conn.commit()
        self.addCleanup(self.conn.close)
        self.sc = sidecar_core.attach(self.conn, "episodes", dag_dir=self.dag_dir)

    def _insert(self, row_id: str, lane: str, note: str) -> int:
        cur = self.conn.execute("INSERT INTO episodes (id, lane, note) VALUES (?, ?, ?)", (row_id, lane, note))
        self.conn.commit()
        return cur.lastrowid

    def _inbox_lines(self) -> list[dict]:
        if not self.inbox_path.exists():
            return []
        return [json.loads(line) for line in self.inbox_path.read_text().splitlines() if line.strip()]


class ConsensusPropertyTest(ConsensusTestBase):
    def test_property_summary_counts_match_the_reads_that_produced_them(self) -> None:
        # 7 matched reads (drained first) + 3 mismatched reads (not drained).
        for i in range(7):
            rowid = self._insert(f"ep-match-{i}", "ops", f"m{i}")
            self.sc.drain()
            dualread.read(self.conn, "episodes", rowid, dag_dir=self.dag_dir)
        for i in range(3):
            rowid = self._insert(f"ep-miss-{i}", "ops", f"x{i}")
            dualread.read(self.conn, "episodes", rowid, dag_dir=self.dag_dir)  # never drained -> mismatch

        result = dualread.summary()
        self.assertEqual(result, {"reads": 10, "matches": 7, "mismatches": 3, "rate": 0.7})

    def test_summary_on_zero_reads_is_a_vacuous_rate_of_one(self) -> None:
        self.assertEqual(dualread.summary(), {"reads": 0, "matches": 0, "mismatches": 0, "rate": 1.0})

    def test_a_match_writes_no_alert(self) -> None:
        rowid = self._insert("ep-ok", "ops", "fine")
        self.sc.drain()
        dualread.read(self.conn, "episodes", rowid, dag_dir=self.dag_dir)
        self.assertEqual(self._inbox_lines(), [])


class ConsensusIncidentTest(ConsensusTestBase):
    def test_incident_cp11_mismatch_alerts_but_never_freezes(self) -> None:
        # Written but never drained -- guaranteed mismatch (cp10's own
        # incident case). The point of cp11: this must reach the Inbox
        # with both hashes and the query, the legacy answer must still
        # come back to the caller, and nothing about this call may raise
        # or otherwise behave like a stopped service.
        rowid = self._insert("ep-undrained", "ops", "not drained yet")

        result = dualread.read(self.conn, "episodes", rowid, dag_dir=self.dag_dir)  # must not raise

        self.assertIsNotNone(result["row"], "the legacy answer is still returned to the caller")
        self.assertFalse(result["match"])

        alerts = self._inbox_lines()
        self.assertEqual(len(alerts), 1, "exactly one alert reaches the Inbox")
        alert = alerts[0]
        self.assertEqual(alert["kind"], "consensus_mismatch")
        self.assertIn("legacy_hash", alert)
        self.assertIn("dag_hash", alert)
        self.assertNotEqual(alert["legacy_hash"], alert["dag_hash"])
        self.assertEqual(alert["query"], {"table": "episodes", "rowid": rowid})

        # No service is stopped: the CLI-equivalent aggregation still
        # works right after, in the same process, no restart needed.
        summary = dualread.summary()
        self.assertEqual(summary["reads"], 1)
        self.assertEqual(summary["mismatches"], 1)


if __name__ == "__main__":
    unittest.main()
