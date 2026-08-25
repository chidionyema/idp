"""unittest for sovereign/sidecar (cp8). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.sidecar.test_sidecar -v

Never opens maestro's real database -- every test below builds its own
disposable sqlite3 file and points the sidecar at that.
"""
from __future__ import annotations

import json
import os
import random
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sovereign import config
from sovereign.engine import receipts
from sovereign.sidecar import core as sidecar_core

_FIXED_KEY = b"\x02" * 32


class SidecarTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.dag_dir = root / "dag"
        self._sb_receipts_patch = patch.object(config, "SB_RECEIPTS", root / "receipts.jsonl")
        self._head_patch = patch.object(config, "RECEIPTS_HEAD", root / "receipts.head")
        self._key_patch = patch.object(receipts, "get_or_create_key", lambda: (_FIXED_KEY, "software_file"))
        for p in (self._sb_receipts_patch, self._head_patch, self._key_patch):
            p.start()
            self.addCleanup(p.stop)

        self.db_path = root / "legacy.db"
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("CREATE TABLE episodes (id TEXT PRIMARY KEY, lane TEXT, note TEXT)")
        self.conn.commit()
        self.addCleanup(self.conn.close)
        self.sc = sidecar_core.attach(self.conn, "episodes", dag_dir=self.dag_dir)

    def _legacy_row(self, row_id: str) -> tuple | None:
        return self.conn.execute("SELECT id, lane, note FROM episodes WHERE id = ?", (row_id,)).fetchone()

    def _receipts_of_kind(self, kind: str) -> list[dict]:
        return [r for r in receipts.read_all() if r.get("kind") == kind]


class SidecarWriteMirrorTest(SidecarTestBase):
    def test_property_every_write_diff_reproduces_the_row_and_never_alters_the_legacy_table(self) -> None:
        # Property: true for every row in a generated set, not one example
        # -- arbitrary text (quotes, newlines, unicode, None), inserted
        # one row at a time.
        rng = random.Random(20260825)
        expected: dict[str, tuple] = {}
        for i in range(200):
            row_id = f"ep-{i}"
            lane = rng.choice(["build", "research", "ops", None])
            note = "".join(rng.choice("abc XYZ'\"\n\t春日🙂") for _ in range(rng.randint(0, 12)))
            self.conn.execute("INSERT INTO episodes (id, lane, note) VALUES (?, ?, ?)", (row_id, lane, note))
            self.conn.commit()
            expected[row_id] = (row_id, lane, note)

        processed = self.sc.drain()
        self.assertEqual(processed, 200)

        for row_id, want in expected.items():
            self.assertEqual(self._legacy_row(row_id), want, "legacy DB must hold exactly the written row")

        write_receipts = self._receipts_of_kind("sidecar_write")
        self.assertEqual(len(write_receipts), 200, "one receipt per write, no more, no fewer")

        node_files = sorted(p for p in self.dag_dir.glob("*.json") if p.name != config.SIDECAR_HEAD_FILENAME)
        self.assertEqual(len(node_files), 200)
        seen_rows = set()
        for path in node_files:
            node = json.loads(path.read_text())
            row = tuple(node["row"][c] for c in ("id", "lane", "note"))
            self.assertEqual(row, expected[node["row"]["id"]], "the DAG node's row must reproduce the write exactly")
            seen_rows.add(node["row"]["id"])
        self.assertEqual(seen_rows, set(expected))

    def test_a_write_to_another_table_on_the_same_connection_is_ignored(self) -> None:
        self.conn.execute("CREATE TABLE other (id TEXT PRIMARY KEY)")
        self.conn.execute("INSERT INTO other (id) VALUES ('x')")
        self.conn.commit()
        self.assertEqual(self.sc.drain(), 0, "no trigger fired for a table this sidecar was never attached to")
        self.assertEqual(self._receipts_of_kind("sidecar_write"), [])
        self.assertEqual(list(self.dag_dir.glob("*.json")) if self.dag_dir.exists() else [], [])


class SidecarDegradedTest(SidecarTestBase):
    def test_incident_cp8_sidecar_never_blocks_the_legacy_write(self) -> None:
        # The exact scenario: the DAG directory exists but is read-only
        # (mount gone read-only, disk full, permissions) when a write
        # comes through. The legacy write must still succeed.
        self.dag_dir.mkdir(parents=True)
        os.chmod(self.dag_dir, stat.S_IREAD | stat.S_IEXEC)
        self.addCleanup(lambda: os.chmod(self.dag_dir, stat.S_IRWXU))

        self.conn.execute("INSERT INTO episodes (id, lane, note) VALUES ('ep-1', 'ops', 'degraded')")
        self.conn.commit()
        processed = self.sc.drain()

        self.assertEqual(
            self._legacy_row("ep-1"), ("ep-1", "ops", "degraded"), "legacy write must succeed even when the sidecar cannot"
        )
        self.assertEqual(processed, 0, "the DAG write failed, so nothing was processed this drain")
        self.assertEqual(self.sc.missed, 1)
        self.assertEqual(self._receipts_of_kind("sidecar_write"), [])
        self.assertEqual(self._receipts_of_kind("sidecar_degraded"), [], "not degraded yet -- still unwritable")

        os.chmod(self.dag_dir, stat.S_IRWXU)
        recovered = self.sc.recover_if_writable()

        self.assertTrue(recovered)
        self.assertEqual(
            self._legacy_row("ep-1"), ("ep-1", "ops", "degraded"), "row was never lost, only delayed -- it drains once writable"
        )
        write_receipts = self._receipts_of_kind("sidecar_write")
        self.assertEqual(len(write_receipts), 1, "the once-missed write is drained, not dropped, once the DAG is writable again")
        degraded = self._receipts_of_kind("sidecar_degraded")
        self.assertEqual(len(degraded), 1)
        self.assertEqual(degraded[0]["missed"], 1)
        self.assertEqual(degraded[0]["table"], "episodes")

    def test_recovery_via_the_next_drain_also_flushes_degraded(self) -> None:
        self.dag_dir.mkdir(parents=True)
        os.chmod(self.dag_dir, stat.S_IREAD | stat.S_IEXEC)
        self.addCleanup(lambda: os.chmod(self.dag_dir, stat.S_IRWXU))
        self.conn.execute("INSERT INTO episodes (id, lane, note) VALUES ('ep-1', 'ops', 'a')")
        self.conn.commit()
        self.sc.drain()
        self.assertEqual(self.sc.missed, 1)

        os.chmod(self.dag_dir, stat.S_IRWXU)
        self.conn.execute("INSERT INTO episodes (id, lane, note) VALUES ('ep-2', 'ops', 'b')")
        self.conn.commit()
        processed = self.sc.drain()

        self.assertEqual(processed, 2, "ep-1 (queued) and ep-2 (new) both drain in the one pass")
        self.assertEqual(self.sc.missed, 0)
        self.assertEqual(len(self._receipts_of_kind("sidecar_degraded")), 1)
        self.assertEqual(len(self._receipts_of_kind("sidecar_write")), 2, "both ep-1 and ep-2 -- neither write was truly lost")


if __name__ == "__main__":
    unittest.main()
