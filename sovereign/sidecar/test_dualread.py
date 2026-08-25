"""unittest for sovereign/sidecar/dualread.py (cp10). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.sidecar.test_dualread -v

Never opens maestro's real database -- every test builds its own
disposable sqlite3 file, same pattern as test_sidecar.py.
"""
from __future__ import annotations

import sqlite3
import statistics
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sovereign import config
from sovereign.engine import receipts
from sovereign.sidecar import core as sidecar_core
from sovereign.sidecar import dualread

_FIXED_KEY = b"\x04" * 32


class DualReadTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.dag_dir = root / "dag"
        self.heads_dir = root / "heads"
        for name, val in (
            ("SB_RECEIPTS", root / "receipts.jsonl"),
            ("RECEIPTS_HEAD", root / "receipts.head"),
            ("SHADOW_HEADS_DIR", self.heads_dir),
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

    def _receipts_of_kind(self, kind: str) -> list[dict]:
        return [r for r in receipts.read_all() if r.get("kind") == kind]


class DualReadPropertyTest(DualReadTestBase):
    def test_property_1000_drained_reads_all_match_and_p95_overhead_is_under_budget(self) -> None:
        overheads: list[float] = []
        for i in range(1000):
            rowid = self._insert(f"ep-{i}", "ops", f"note-{i}")
            self.sc.drain()
            result = dualread.read(self.conn, "episodes", rowid, dag_dir=self.dag_dir)
            self.assertTrue(result["match"], f"row {rowid} must match once drained")
            overheads.append(result["overhead_ms"])

        p95 = statistics.quantiles(overheads, n=100)[94]
        self.assertLess(
            p95, config.DUALREAD_MAX_OVERHEAD_MS, f"p95 router overhead {p95:.3f}ms over budget {config.DUALREAD_MAX_OVERHEAD_MS}ms"
        )

        write_receipts = self._receipts_of_kind("dualread")
        self.assertEqual(len(write_receipts), 1000)
        self.assertTrue(all(r["match"] for r in write_receipts))

    def test_a_deleted_row_matches_as_both_sides_none(self) -> None:
        rowid = self._insert("ep-del", "ops", "gone soon")
        self.sc.drain()
        self.conn.execute("DELETE FROM episodes WHERE id = 'ep-del'")
        self.conn.commit()
        self.sc.drain()

        result = dualread.read(self.conn, "episodes", rowid, dag_dir=self.dag_dir)
        self.assertIsNone(result["row"])
        self.assertTrue(result["match"], "legacy None and DAG-deleted None must match, not silently skip")


class DualReadIncidentTest(DualReadTestBase):
    def test_incident_cp10_no_shadow_head_yet_reports_mismatch_not_a_crash(self) -> None:
        # Written but never drained -- .estate/heads/shadow_main does not
        # exist yet. The router must not raise, and must not report a
        # false match by swallowing the missing-head case into "row=None
        # equals row=None" by accident (legacy_row is NOT None here).
        rowid = self._insert("ep-undrained", "ops", "not drained yet")
        self.assertFalse(shadow_root_head_exists(self.heads_dir))

        result = dualread.read(self.conn, "episodes", rowid, dag_dir=self.dag_dir)

        self.assertIsNotNone(result["row"], "legacy read must still succeed")
        self.assertFalse(result["match"], "an undrained row is a real mismatch, not a silent pass")
        degraded = self._receipts_of_kind("dualread")
        self.assertEqual(len(degraded), 1)
        self.assertFalse(degraded[0]["match"])


def shadow_root_head_exists(heads_dir: Path) -> bool:
    return (heads_dir / "shadow_main").exists()


if __name__ == "__main__":
    unittest.main()
