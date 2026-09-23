"""unittest for sovereign/engine/dag.py (R15). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.engine.test_dag -v

Rungs (AGENTS.md "How to test"):
  * property  -- materialize folds diffs from genesis over random chains,
                 and a node's name is a function of its body alone.
  * incident  -- the dangling `heads/shadow_main` pointer at a deleted tmp
                 dir. Proved BOTH ways in one run: the write outside the
                 root is refused, the write inside it succeeds. A guard
                 only ever seen refusing has never been shown to permit,
                 and a guard that refuses correct work is an outage.
  * incident  -- the same defect at its source: a sidecar attached to a
                 foreign dag_dir must not move the estate's head.
  * static    -- no module except dag.py may write a head file, so the
                 guard cannot be bypassed by the next module that wants a
                 branch pointer.

Every test builds its own disposable estate; none reads or writes the
founder's real ~/.estate.
"""
from __future__ import annotations

import json
import random
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sovereign
from sovereign import config
from sovereign.engine import dag, receipts

_FIXED_KEY = b"\x05" * 32


class DagTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.dag_dir = self.root / "dag"
        self.heads_dir = self.root / "heads"
        self.outside = self.root / "elsewhere" / "dag"
        for name, val in (
            ("SB_RECEIPTS", self.root / "receipts.jsonl"),
            ("RECEIPTS_HEAD", self.root / "receipts.head"),
            ("RECEIPTS_COUNTER", self.root / "receipts.counter"),
            ("SHADOW_HEADS_DIR", self.heads_dir),
            ("SIDECAR_DAG_DIR", self.dag_dir),
            ("INTERVENTIONS_DIR", self.root / "interventions"),
            ("SHADOW_LEGACY_HEADS_DIRS", []),
        ):
            p = patch.object(config, name, val)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(receipts, "get_or_create_key", lambda: (_FIXED_KEY, "software_file"))
        p.start()
        self.addCleanup(p.stop)

    def _node(self, diff: dict, parent: str = dag.GENESIS, dag_dir: Path | None = None) -> str:
        return dag.write_node(diff, parent, timestamp=0, dag_dir=dag_dir)[0]


class DagPropertyTest(DagTestBase):
    def test_property_materialize_folds_every_diff_from_genesis(self) -> None:
        """The DAG stores diffs, not snapshots (spec 3.1), so the only
        proof it is a DAG and not a snapshot store is that folding the
        chain reproduces a state no single node contains."""
        rng = random.Random(20260825)
        for _ in range(40):
            expected: dict[str, object] = {}
            parent = dag.GENESIS
            for _ in range(rng.randint(1, 12)):
                diff: dict[str, object] = {}
                for _ in range(rng.randint(1, 4)):
                    key = "k" + str(rng.randint(0, 5))
                    if expected and rng.random() < 0.25:
                        diff[key] = None
                    else:
                        diff[key] = rng.randint(0, 999)
                parent = self._node(diff, parent)
                last_diff = diff
                for k, v in diff.items():
                    if v is None:
                        expected.pop(k, None)
                    else:
                        expected[k] = v
            self.assertEqual(dag.materialize(parent), expected)
            body = dag.read_node(parent)
            assert body is not None
            self.assertEqual(body["diff"], last_diff, "a node stores the diff it was given, never the folded state")

    def test_property_a_node_is_named_by_its_body_and_nothing_else(self) -> None:
        rng = random.Random(4242)
        seen: dict[str, dict] = {}
        for _ in range(60):
            diff = {"k": rng.randint(0, 9)}
            parent = rng.choice([dag.GENESIS, "a" * config.RECEIPTS_HASH_HEX_LEN])
            h = self._node(diff, parent)
            body = dag.read_node(h)
            assert body is not None
            self.assertEqual(h, dag.node_hash_of(body))
            if h in seen:
                self.assertEqual(seen[h], body, "two different bodies must not share a name")
            seen[h] = body


class HeadGuardIncidentTest(DagTestBase):
    def test_incident_head_outside_the_dag_root_is_refused_and_inside_it_is_written(self) -> None:
        """The incident: ~/.estate/.estate/heads/shadow_main pointed at
        /var/folders/.../T/tmp59q5f9jp/dag, a unittest temp dir the OS had
        already reaped, so the estate's shadow root named history that no
        longer existed. Class: a head may name a DAG directory outside the
        configured root.

        Both directions, one run."""
        self.outside.mkdir(parents=True)
        h_out = self._node({"a": 1}, dag_dir=self.outside)
        with self.assertRaises(dag.HeadOutsideDagRootError):
            dag.write_head("shadow_main", h_out, self.outside)
        self.assertEqual(dag.list_heads(), [], "the refused write must leave no head behind")

        h_in = self._node({"a": 1})
        written = dag.write_head("shadow_main", h_in, self.dag_dir)
        self.assertTrue(written.is_file(), "the guard must still permit a head inside the root (LAW 38)")
        self.assertEqual(dag.read_head("shadow_main"), {"root": h_in, "dag_dir": str(self.dag_dir)})

        default = dag.write_head("main", h_in)
        self.assertTrue(default.is_file(), "omitting dag_dir means the configured root, which is always inside itself")

    def test_incident_a_sidecar_on_a_foreign_dag_dir_cannot_move_the_estate_head(self) -> None:
        """The same defect at the place it actually happened: sidecar
        drain() -> _write_node -> update_head with the test's own dag_dir.
        The refusal is recorded as a receipt, because a guard that fires
        silently is indistinguishable from one that never fired."""
        from sovereign.sidecar import core as sidecar_core

        self.outside.mkdir(parents=True)
        conn = sqlite3.connect(str(self.root / "legacy.db"))
        self.addCleanup(conn.close)
        conn.execute("CREATE TABLE episodes (id TEXT PRIMARY KEY, note TEXT)")
        conn.commit()
        sc = sidecar_core.attach(conn, "episodes", dag_dir=self.outside)
        conn.execute("INSERT INTO episodes VALUES ('e1', 'hello')")
        conn.commit()
        sc.drain()

        self.assertEqual(dag.list_heads(), [], "no head may name the foreign dag dir")
        kinds = [r.get("kind") for r in receipts.read_all()]
        self.assertIn("head_refused", kinds, "the refusal must be auditable")

    def test_sweep_reports_a_dangling_head_then_removes_it(self) -> None:
        """Report mode first (AGENTS.md "Smallest diff"), and --fix only
        ever removes a broken pointer."""
        self.heads_dir.mkdir(parents=True)
        (self.heads_dir / "shadow_main").write_text(
            json.dumps({"root": "e" * config.RECEIPTS_HASH_HEX_LEN, "dag_dir": str(self.outside)})
        )
        report = dag.scan_heads()
        self.assertEqual(report["count"], 1)
        self.assertFalse(report["ok"])
        self.assertEqual(report["dangling"][0]["problem"], "outside_root")
        self.assertEqual(report["removed"], [], "report mode removes nothing")

        fixed = dag.scan_heads(fix=True)
        self.assertEqual(len(fixed["removed"]), 1)
        self.assertTrue(dag.scan_heads()["ok"])

    def test_sweep_leaves_a_healthy_head_alone(self) -> None:
        h = self._node({"a": 1})
        dag.write_head("main", h)
        report = dag.scan_heads(fix=True)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["removed"], [])
        self.assertEqual(dag.list_heads(), ["main"])


class HeadWriterStaticGuardTest(unittest.TestCase):
    """LAW 45 step 5: the guard has to sit somewhere a session cannot walk
    past. dag.write_head is the only writer, so this test fails the moment
    a new module reaches for the heads directory directly."""

    ALLOWED = {"dag.py", "config.py", "config_keys.py"}

    def _sources(self) -> list[Path]:
        root = Path(sovereign.__file__).resolve().parent
        return [
            p
            for p in root.rglob("*.py")
            if ".venv" not in p.parts and not p.name.startswith("test_")
        ]

    def test_only_dag_py_touches_the_heads_directory(self) -> None:
        offenders = []
        for path in self._sources():
            if path.name in self.ALLOWED:
                continue
            text = path.read_text()
            if "SHADOW_HEADS_DIR" in text or "heads_dir()" in text:
                offenders.append(str(path))
        self.assertEqual(offenders, [], "these modules must go through dag.write_head instead")

    def test_the_guard_would_notice(self) -> None:
        """Proves the scan can fail -- a guard whose failing branch has
        never run is a guard nobody has tested."""
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "rogue.py"
            bad.write_text("from sovereign import config\nconfig.SHADOW_HEADS_DIR.mkdir()\n")
            with patch.object(HeadWriterStaticGuardTest, "_sources", lambda self: [bad]):
                with self.assertRaises(AssertionError):
                    self.test_only_dag_py_touches_the_heads_directory()


if __name__ == "__main__":
    unittest.main(verbosity=2)
