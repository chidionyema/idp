"""unittest for sovereign/engine/shadow_root.py (cp9). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.engine.test_shadow_root -v

Never opens maestro's real database -- every test builds its own
disposable sqlite3 file, same pattern as sovereign/sidecar/test_sidecar.py.
"""
from __future__ import annotations

import json
import random
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sovereign import config
from sovereign.engine import receipts, shadow_root
from sovereign.sidecar import core as sidecar_core

_FIXED_KEY = b"\x03" * 32


class ShadowRootTestBase(unittest.TestCase):
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


class ShadowRootPropertyTest(ShadowRootTestBase):
    def test_property_root_advances_once_per_write_and_walk_reproduces_the_legacy_db(self) -> None:
        rng = random.Random(20260825)
        roots_seen: list[str] = []
        expected: dict[str, tuple] = {}
        for i in range(30):
            row_id = f"ep-{i}"
            lane = rng.choice(["build", "research", "ops"])
            note = f"note-{i}"
            self.conn.execute("INSERT INTO episodes (id, lane, note) VALUES (?, ?, ?)", (row_id, lane, note))
            self.conn.commit()
            processed = self.sc.drain()
            self.assertEqual(processed, 1, "one write drained per iteration")
            head = json.loads(shadow_root.head_path().read_text())
            roots_seen.append(head["root"])
            expected[row_id] = (row_id, lane, note)

        self.assertEqual(len(roots_seen), 30, "shadow_main changed once per write")
        self.assertEqual(len(set(roots_seen)), 30, "every advance is to a distinct root")

        result = shadow_root.verify()
        self.assertTrue(result["verified"])
        self.assertEqual(result["root"], roots_seen[-1])
        self.assertEqual(result["nodes"], 30, "walking genesis to shadow_main crosses every node once")

        # Walking the DAG from genesis to shadow_main reproduces the
        # legacy DB exactly: replay every INSERT node in chain order.
        node_hash = result["root"]
        replayed: dict[str, tuple] = {}
        while node_hash and node_hash != shadow_root.GENESIS_NODE_HASH:
            body = json.loads((self.dag_dir / f"{node_hash}.json").read_text())
            row = body["row"]
            replayed.setdefault(row["id"], (row["id"], row["lane"], row["note"]))
            node_hash = body["prev_node_hash"]
        self.assertEqual(replayed, expected)

    def test_no_head_file_fails_closed(self) -> None:
        result = shadow_root.verify()
        self.assertEqual(result, {"root": None, "parent": None, "nodes": 0, "verified": False})


class ShadowRootTamperTest(ShadowRootTestBase):
    def test_incident_cp9_a_deleted_node_breaks_verify_not_a_silent_pass(self) -> None:
        for i in range(3):
            self.conn.execute(
                "INSERT INTO episodes (id, lane, note) VALUES (?, 'ops', ?)", (f"ep-{i}", f"n{i}")
            )
            self.conn.commit()
            self.sc.drain()

        self.assertTrue(shadow_root.verify()["verified"])

        # Delete the middle node -- the tail-truncation-shaped defect this
        # module exists to catch (cp19's own bug, one hop over): a broken
        # link in the *middle* of the walk, not just the tail.
        head = json.loads(shadow_root.head_path().read_text())
        node_hash = head["root"]
        body = json.loads((self.dag_dir / f"{node_hash}.json").read_text())
        middle_hash = body["prev_node_hash"]
        (self.dag_dir / f"{middle_hash}.json").unlink()

        result = shadow_root.verify()
        self.assertFalse(result["verified"], "a missing node must fail closed, never a silent pass")


if __name__ == "__main__":
    unittest.main()
