"""unittest for sovereign/engine/cross_stack.py (cp15). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.engine.test_cross_stack -v

Never opens maestro's real database or the real repo's git history --
every test builds its own disposable sqlite3 file for db_root and
patches subprocess for code_root, same isolation pattern as
sovereign/engine/test_flip.py and sovereign/engine/test_projection.py.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sovereign import config
from sovereign.engine import cross_stack, receipts
from sovereign.sidecar import core as sidecar_core

_FIXED_KEY = b"\x0f" * 32


def _fake_run(sha: str):
    def run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=f"{sha}\n", stderr="")
    return run


class CrossStackTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        for name, val in (
            ("SB_RECEIPTS", root / "receipts.jsonl"),
            ("RECEIPTS_HEAD", root / "receipts.head"),
            ("SIDECAR_DAG_DIR", root / "dag"),
            ("SHADOW_HEADS_DIR", root / "heads"),
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
        self.sc = sidecar_core.attach(self.conn, "episodes")

        self._git_patch = patch("subprocess.run", _fake_run("aaaa000011112222"))
        self._git_patch.start()
        self.addCleanup(self._git_patch.stop)

    def _drain_one_row(self, row_id: str) -> None:
        self.conn.execute("INSERT INTO episodes (id, lane, note) VALUES (?, 'ops', 'n')", (row_id,))
        self.conn.commit()
        self.sc.drain()


class CrossStackPropertyTest(CrossStackTestBase):
    def test_property_root_reports_all_four_named_children(self) -> None:
        self._drain_one_row("seed")
        res = cross_stack.root()
        for key in ("root", "code_root", "db_root", "policy_root", "ai_policy_root"):
            self.assertIn(key, res)
        self.assertEqual(res["code_root"], "aaaa000011112222")
        self.assertIsNotNone(res["db_root"])

    def test_property_composite_root_changes_when_code_root_changes(self) -> None:
        self._drain_one_row("seed")
        before = cross_stack.root()
        with patch("subprocess.run", _fake_run("bbbb999988887777")):
            after = cross_stack.root()
        self.assertNotEqual(before["code_root"], after["code_root"])
        self.assertNotEqual(before["root"], after["root"])
        self.assertEqual(before["db_root"], after["db_root"])
        self.assertEqual(before["policy_root"], after["policy_root"])
        self.assertEqual(before["ai_policy_root"], after["ai_policy_root"])

    def test_property_composite_root_changes_when_policy_root_changes(self) -> None:
        self._drain_one_row("seed")
        before = cross_stack.root()
        with patch.dict(os.environ, {"SB_ATTACH_QUORUM": "3/3"}):
            after = cross_stack.root()
        self.assertNotEqual(before["policy_root"], after["policy_root"])
        self.assertNotEqual(before["root"], after["root"])
        self.assertEqual(before["code_root"], after["code_root"])
        self.assertEqual(before["ai_policy_root"], after["ai_policy_root"])

    def test_property_composite_root_changes_when_ai_policy_root_changes(self) -> None:
        self._drain_one_row("seed")
        before = cross_stack.root()
        with patch.dict(os.environ, {"SB_TRUST_PRESENCE_TIMEOUT_S": "999"}):
            after = cross_stack.root()
        self.assertNotEqual(before["ai_policy_root"], after["ai_policy_root"])
        self.assertNotEqual(before["root"], after["root"])
        self.assertEqual(before["code_root"], after["code_root"])
        self.assertEqual(before["policy_root"], after["policy_root"])


class CrossStackIncidentTest(CrossStackTestBase):
    def test_incident_cp15_composite_root_changes_when_db_root_changes(self) -> None:
        """cp15's own safety bar, the exact line the feature file states:
        "changing any child changes the root". db_root is the one child
        that moves on its own (every drained write advances it, cp9), so
        this is also the one most likely to be silently left out of the
        composite hash by a future edit that forgets it -- a code_root/
        policy_root/ai_policy_root-only composite would still satisfy the
        other three property tests above."""
        self._drain_one_row("a")
        before = cross_stack.root()
        self._drain_one_row("b")
        after = cross_stack.root()
        self.assertNotEqual(before["db_root"], after["db_root"], "precondition: the DB actually advanced")
        self.assertNotEqual(before["root"], after["root"], "the composite root must move with db_root")


if __name__ == "__main__":
    unittest.main()
