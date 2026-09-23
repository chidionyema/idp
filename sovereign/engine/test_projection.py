"""unittest for sovereign/engine/projection.py (cp14). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.engine.test_projection -v

Never opens maestro's real database -- every test builds its own
disposable sqlite3 file and points config.SIDECAR_DAG_DIR /
config.SHADOW_HEADS_DIR / config.PROJECTION_STORE_PATH at a temp dir,
same pattern as sovereign/sidecar/test_sidecar.py and
sovereign/engine/test_flip.py.
"""
from __future__ import annotations

import random
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sovereign import config
from sovereign.engine import projection, receipts, shadow_root
from sovereign.sidecar import core as sidecar_core

_FIXED_KEY = b"\x0e" * 32


class ProjectionTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        for name, val in (
            ("SB_RECEIPTS", root / "receipts.jsonl"),
            ("RECEIPTS_HEAD", root / "receipts.head"),
            ("SIDECAR_DAG_DIR", root / "dag"),
            ("SHADOW_HEADS_DIR", root / "heads"),
            ("PROJECTION_STORE_PATH", root / "projection.json"),
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
        # no dag_dir override -- relies on the patched config.SIDECAR_DAG_DIR
        # above, so this sidecar and projection.rebuild() agree on where
        # the DAG nodes live, exactly the way sovereign.sidecar.core's
        # own default (dag_dir or config.SIDECAR_DAG_DIR) already works.
        self.sc = sidecar_core.attach(self.conn, "episodes")

    def _insert(self, row_id: str, lane: str, note: str) -> None:
        self.conn.execute("INSERT INTO episodes (id, lane, note) VALUES (?, ?, ?)", (row_id, lane, note))
        self.conn.commit()

    def _update(self, row_id: str, note: str) -> None:
        self.conn.execute("UPDATE episodes SET note = ? WHERE id = ?", (note, row_id))
        self.conn.commit()

    def _delete(self, row_id: str) -> None:
        self.conn.execute("DELETE FROM episodes WHERE id = ?", (row_id,))
        self.conn.commit()

    def _legacy_rows(self) -> dict[str, dict]:
        rows = self.conn.execute("SELECT rowid, id, lane, note FROM episodes").fetchall()
        return {str(r[0]): {"id": r[1], "lane": r[2], "note": r[3]} for r in rows}


class ProjectionPropertyTest(ProjectionTestBase):
    def test_property_rebuild_from_scratch_matches_legacy_state_for_any_op_sequence(self) -> None:
        rng = random.Random(1787631900)
        for trial in range(20):
            row_id = f"r{trial}"
            self._insert(row_id, "ops", f"note-{trial}")
            if rng.random() < 0.5:
                self._update(row_id, f"note-{trial}-edited")
            if rng.random() < 0.3:
                self._delete(row_id)
            self.sc.drain()

        result = projection.rebuild(by="test")
        self.assertTrue(result["verified"], "a clean DAG chain must always verify")
        self.assertEqual(result["root"], shadow_root.verify()["root"])

        legacy = self._legacy_rows()
        for rowid, row in legacy.items():
            self.assertEqual(projection.read("episodes", rowid), row)

        last = receipts.read_all()[-1]
        self.assertEqual(last["kind"], "rebuild")
        self.assertEqual(last["text"], config.REBUILD_RECEIPT_TEMPLATE.format(root=result["root"]))

    def test_property_deleted_store_rebuilds_to_the_exact_same_state(self) -> None:
        for row_id, lane, note in (("a", "ops", "n1"), ("b", "ops", "n2")):
            self._insert(row_id, lane, note)
        self._delete("a")
        self.sc.drain()

        first = projection.rebuild(by="test")
        before_text = config.PROJECTION_STORE_PATH.read_text()

        config.PROJECTION_STORE_PATH.unlink()
        self.assertIsNone(projection.current_view_root())

        second = projection.rebuild(by="test")
        after_text = config.PROJECTION_STORE_PATH.read_text()

        self.assertEqual(first["root"], second["root"])
        self.assertEqual(before_text, after_text, "the views match the root hash: rebuild is deterministic")
        legacy = self._legacy_rows()
        for rowid, row in legacy.items():
            self.assertEqual(projection.read("episodes", rowid), row, "every read answers as before")


class ProjectionBootCheckTest(ProjectionTestBase):
    def test_incident_cp14_boot_check_rebuilds_when_a_write_landed_after_the_last_rebuild(self) -> None:
        """cp14's own safety bar: `sb up`'s boot check (ensure_fresh) must
        detect that the DAG head moved since the projection store was last
        built and rebuild before anything reads it -- if that comparison
        were ever skipped or hardcoded, a session started after boot would
        silently serve pre-boot state for a row that already landed."""
        self._insert("seed", "ops", "n0")
        self.sc.drain()
        projection.rebuild(by="test")
        self.assertEqual(projection.read("episodes", "1"), {"id": "seed", "lane": "ops", "note": "n0"})

        # a write lands after the last rebuild -- exactly the boot
        # scenario: something wrote to the DAG while the store was stale
        self._insert("late", "ops", "n1")
        self.sc.drain()

        stale_read = projection.read("episodes", "2")
        self.assertIsNone(stale_read, "precondition: the store has not been rebuilt yet")

        boot_result = projection.ensure_fresh(by="boot")
        self.assertTrue(boot_result["rebuilt"], "the head moved since the last rebuild")
        self.assertEqual(projection.read("episodes", "2"), {"id": "late", "lane": "ops", "note": "n1"})

    def test_ensure_fresh_is_a_noop_when_already_current(self) -> None:
        self._insert("seed", "ops", "n0")
        self.sc.drain()
        projection.rebuild(by="test")
        before = config.PROJECTION_STORE_PATH.read_text()

        result = projection.ensure_fresh(by="boot")
        self.assertFalse(result["rebuilt"])
        self.assertEqual(config.PROJECTION_STORE_PATH.read_text(), before)


if __name__ == "__main__":
    unittest.main()
