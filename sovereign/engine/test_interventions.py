"""unittest for sovereign/engine/interventions.py (R17). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.engine.test_interventions -v

Rungs: property (every intervention written is named for its own counter
and hash and is byte-identical to the chain line it mirrors) and one
incident case (an existing file is never rewritten -- append-only means
the second write fails, it does not win).

R17 is deliberately not a second log: the signed chain in
engine/receipts.py stays the source of truth and this directory is the
spec's 3.1 view of it, so there is nothing to keep in step.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sovereign import config
from sovereign.engine import interventions, receipts

_FIXED_KEY = b"\x07" * 32


class InterventionsTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        for name, val in (
            ("SB_RECEIPTS", root / "receipts.jsonl"),
            ("RECEIPTS_HEAD", root / "receipts.head"),
            ("RECEIPTS_COUNTER", root / "receipts.counter"),
            ("INTERVENTIONS_DIR", root / "interventions"),
        ):
            p = patch.object(config, name, val)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(receipts, "get_or_create_key", lambda: (_FIXED_KEY, "software_file"))
        p.start()
        self.addCleanup(p.stop)


class InterventionsPropertyTest(InterventionsTestBase):
    def test_property_every_file_is_named_for_its_line_and_matches_it_byte_for_byte(self) -> None:
        kinds = list(config.INTERVENTIONS_KINDS)
        for i, kind in enumerate(kinds * 3):
            interventions.record(kind, by="founder", text=f"n{i}")
        # engine bookkeeping goes in the chain and not in this directory
        receipts.append({"kind": "step", "by": "engine", "text": "not an intervention"})

        rows = interventions.read_all()
        self.assertEqual(len(rows), len(kinds) * 3)
        by_counter = {int(r["counter"]): r for r in receipts.read_all()}
        for row in rows:
            path = interventions.directory() / interventions.filename_for(int(row["counter"]), str(row["hash"]))
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text()), by_counter[int(row["counter"])])
        self.assertTrue(interventions.verify()["ok"])
        self.assertEqual(interventions.verify()["entries"], len(kinds) * 3)

    def test_property_counters_in_the_directory_are_strictly_increasing(self) -> None:
        for i in range(12):
            interventions.record("steer", by="founder", text=str(i))
        counters = [int(r["counter"]) for r in interventions.read_all()]
        self.assertEqual(counters, sorted(counters))
        self.assertEqual(len(set(counters)), len(counters))


class InterventionsIncidentTest(InterventionsTestBase):
    def test_incident_an_existing_file_is_never_rewritten(self) -> None:
        res = interventions.record("stop", by="founder")
        with self.assertRaises(interventions.NotAppendOnly):
            interventions.mirror(res["line"])

    def test_a_tampered_file_fails_verification(self) -> None:
        res = interventions.record("approve", by="founder", text="ok")
        path = Path(str(res["path"]))
        line = json.loads(path.read_text())
        line["by"] = "someone else"
        path.write_text(json.dumps(line, sort_keys=True))
        out = interventions.verify()
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "diverged")

    def test_backfill_is_idempotent(self) -> None:
        for i in range(4):
            receipts.append({"kind": "refill", "by": "founder", "text": str(i)})
        first = interventions.backfill()
        self.assertEqual(first["written"], 4)
        second = interventions.backfill()
        self.assertEqual(second["written"], 0)
        self.assertEqual(second["skipped"], 4)
        self.assertTrue(interventions.verify()["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
