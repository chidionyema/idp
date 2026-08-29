"""unittest for sovereign/engine/fork.py (cp12). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.engine.test_fork -v

Never opens maestro's real database -- every test builds its own
disposable sqlite3 file and points config.SIDECAR_TARGET at that, same
pattern as sovereign/sidecar/test_sidecar.py and test_dualread.py.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sovereign import config
from sovereign.engine import fork, receipts, shadow_root
from sovereign.sidecar import core as sidecar_core

_FIXED_KEY = b"\x0c" * 32


class ForkTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.db_path = root / "legacy.db"
        for name, val in (
            ("SB_RECEIPTS", root / "receipts.jsonl"),
            ("RECEIPTS_HEAD", root / "receipts.head"),
            ("SHADOW_HEADS_DIR", root / "heads"),
            ("SIDECAR_DAG_DIR", root / "dag"),
            ("SIDECAR_TARGET", f"{self.db_path}#episodes"),
            ("FORK_DIR", root / "forks"),
            ("FORK_WORKING_POINTER", root / "working_branch"),
            ("FORK_MAX_PARALLEL", 3),
            ("FORK_MAX_MS", 1000),
        ):
            p = patch.object(config, name, val)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(receipts, "get_or_create_key", lambda: (_FIXED_KEY, "software_file"))
        p.start()
        self.addCleanup(p.stop)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("CREATE TABLE episodes (id TEXT PRIMARY KEY, lane TEXT, note TEXT)")
        self.conn.commit()
        self.addCleanup(self.conn.close)
        self.prod_dag_dir = root / "dag"
        self.sc = sidecar_core.attach(self.conn, "episodes", dag_dir=self.prod_dag_dir)
        # establish a real, non-genesis production root before any test
        # forks from it
        self.conn.execute("INSERT INTO episodes (id, lane, note) VALUES (?, ?, ?)", ("seed", "ops", "n"))
        self.conn.commit()
        self.sc.drain()

    def _prod_root(self) -> str | None:
        return shadow_root.verify()["root"]

    def _clear_forks(self) -> None:
        for p in list(config.SHADOW_HEADS_DIR.glob("*")):
            if p.name != config.SHADOW_HEAD_FILENAME:
                p.unlink()


class ForkCreationPropertyTest(ForkTestBase):
    def test_property_fork_creation_is_fast_matches_prod_root_and_never_touches_legacy(self) -> None:
        legacy_mtime_before = self.db_path.stat().st_mtime_ns
        prod_root = self._prod_root()
        for i in range(30):
            name = f"fork-{i}"
            result = fork.create(name)
            self.assertLess(result["elapsed_ms"], config.FORK_MAX_MS, "fork under a second")
            self.assertEqual(result["root"], prod_root)
            on_disk = json.loads(fork.fork_head_path(name).read_text())
            self.assertEqual(on_disk["root"], prod_root, ".estate/heads/<name> equals the current root")
        self.assertEqual(
            self.db_path.stat().st_mtime_ns, legacy_mtime_before, "no file under the legacy DB changed"
        )

    def test_property_storage_flips_to_disk_exactly_at_the_cap(self) -> None:
        for cap in (1, 2, 3, 5):
            self._clear_forks()
            with patch.object(config, "FORK_MAX_PARALLEL", cap):
                for i in range(cap):
                    r = fork.create(f"f{cap}-{i}")
                    self.assertEqual(r["storage"], "memory", f"fork {i} under cap {cap} must be memory")
                over = fork.create(f"f{cap}-over")
                self.assertEqual(over["storage"], "disk", "the cap is a key: crossing it flips storage")


class ForkSwitchDropTest(ForkTestBase):
    def test_switch_and_drop_moves_pointer_and_archives_dag_nodes(self) -> None:
        fork.create("staging")
        conn, sc = fork.attach_sidecar("staging", "episodes")
        conn.execute("INSERT INTO episodes (id, lane, note) VALUES (?, ?, ?)", ("s1", "ops", "note"))
        conn.commit()
        sc.drain()
        conn.close()

        dag_files_before = sorted(p.name for p in fork.fork_dag_dir("staging").glob("*.json"))
        self.assertTrue(dag_files_before)

        fork.switch("staging")
        self.assertEqual(fork.current(), "staging", "the working pointer moved")

        fork.drop("staging")
        self.assertNotIn("staging", fork.list_forks(), "the branch is gone from heads/")
        self.assertEqual(fork.current(), config.SHADOW_HEAD_FILENAME, "drop switches back to production")

        dag_files_after = sorted(p.name for p in fork.fork_dag_dir("staging").glob("*.json"))
        self.assertEqual(dag_files_after, dag_files_before, "its DAG nodes remain, archived, never deleted")

    def test_switch_refuses_an_unknown_name(self) -> None:
        with self.assertRaises(fork.UnknownForkError):
            fork.switch("does-not-exist")

    def test_drop_refuses_an_unknown_name(self) -> None:
        with self.assertRaises(fork.UnknownForkError):
            fork.drop("does-not-exist")


class ForkIncidentTest(ForkTestBase):
    def test_incident_cp12_fork_writes_never_reach_production_receipts_or_root(self) -> None:
        """cp12's exact bar (features/sovereign-bus/cp12_ai_sandbox.feature,
        "Agent writes land on the fork only"): ten writes against a fork
        must leave production's root and receipts file untouched, and
        chain into the fork's own receipts file instead -- verifiable on
        its own signed head anchor, independent of production's."""
        prod_root_before = self._prod_root()
        prod_receipts_before = len(receipts.read_all())

        fork.create("staging")
        conn, sc = fork.attach_sidecar("staging", "episodes")
        for i in range(10):
            conn.execute("INSERT INTO episodes (id, lane, note) VALUES (?, ?, ?)", (f"fk-{i}", "ops", "n"))
            conn.commit()
        processed = sc.drain()
        conn.close()

        self.assertEqual(processed, 10)
        self.assertEqual(self._prod_root(), prod_root_before, "production's root is unchanged")
        self.assertEqual(
            len(receipts.read_all()), prod_receipts_before, "production's receipts file gained no rows"
        )

        fork_receipts_path, fork_head_path = fork.fork_receipts_paths("staging")
        write_receipts = [r for r in receipts.read_all(fork_receipts_path) if r.get("kind") == "sidecar_write"]
        self.assertEqual(len(write_receipts), 10, "staging's receipts chained separately, ten entries")

        staging_root = json.loads(fork.fork_head_path("staging").read_text())["root"]
        self.assertNotEqual(staging_root, prod_root_before, "staging's root advanced")

        result = receipts.verify(fork_receipts_path, fork_head_path)
        self.assertTrue(result["ok"], "the fork's own chain verifies on its own signed head anchor")


if __name__ == "__main__":
    unittest.main()
