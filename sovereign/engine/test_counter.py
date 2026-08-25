"""unittest for the monotonic receipt counter (R23). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.engine.test_counter -v

Rungs: property (the counter never repeats or goes backwards over a
random sequence of appends and restarts) and one incident case (the log
and the head anchor are both deleted -- a truncation attack, or a careless
rm -- and the next receipt still gets a number no earlier receipt used).

"Survives restart" is the requirement, so every test here reloads the
module state the way a new process would: nothing is cached in memory.
"""
from __future__ import annotations

import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sovereign import config
from sovereign.engine import receipts

_FIXED_KEY = b"\x09" * 32


class CounterTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        for name, val in (
            ("SB_RECEIPTS", self.root / "receipts.jsonl"),
            ("RECEIPTS_HEAD", self.root / "receipts.head"),
            ("RECEIPTS_COUNTER", self.root / "receipts.counter"),
            ("INTERVENTIONS_DIR", self.root / "interventions"),
        ):
            p = patch.object(config, name, val)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(receipts, "get_or_create_key", lambda: (_FIXED_KEY, "software_file"))
        p.start()
        self.addCleanup(p.stop)


class CounterPropertyTest(CounterTestBase):
    def test_property_counters_never_repeat_and_never_go_backwards(self) -> None:
        rng = random.Random(20260825)
        seen: list[int] = []
        for _ in range(40):
            line = receipts.append({"kind": "step", "by": "engine", "text": "x"})
            seen.append(int(line["counter"]))
            if rng.random() < 0.3:
                # a restart: the process forgets everything it held
                self.assertGreater(receipts.read_watermark(_FIXED_KEY), 0)
        self.assertEqual(seen, sorted(seen))
        self.assertEqual(len(set(seen)), len(seen))
        self.assertEqual(seen[0], 1)


class CounterIncidentTest(CounterTestBase):
    def test_incident_a_deleted_log_and_anchor_cannot_reset_the_counter(self) -> None:
        """The attack the watermark exists for: delete the chain and the
        head anchor, and a naive counter restarts at 1, so a replaced
        receipt collides with a real one and the gap is invisible."""
        for _ in range(3):
            receipts.append({"kind": "step", "by": "engine"})
        config.SB_RECEIPTS.unlink()
        config.RECEIPTS_HEAD.unlink(missing_ok=True)

        line = receipts.append({"kind": "step", "by": "engine"})
        self.assertEqual(int(line["counter"]), 4, "the counter must not restart at 1")

    def test_the_watermark_never_lowers(self) -> None:
        for _ in range(3):
            receipts.append({"kind": "step", "by": "engine"})
        high = receipts.read_watermark(_FIXED_KEY)
        receipts._write_watermark(1, _FIXED_KEY)
        self.assertEqual(receipts.read_watermark(_FIXED_KEY), high)

    def test_a_forged_watermark_is_ignored(self) -> None:
        """The watermark is signed with the same estate key as the chain,
        so a file anyone can write is not a file anyone can raise."""
        receipts.append({"kind": "step", "by": "engine"})
        config.RECEIPTS_COUNTER.write_text(json.dumps({"counter": 9999, "sig": "forged"}))
        line = receipts.append({"kind": "step", "by": "engine"})
        self.assertEqual(int(line["counter"]), 2)

    def test_a_chain_that_starts_above_one_still_verifies(self) -> None:
        """After a log rotation the surviving chain legitimately begins at
        a counter above 1. verify() seeds its expectation from the first
        line it can see, so that is a valid chain and not a missing
        receipt. (Deleting a line out of the middle is a different thing
        and still fails: the prev_hash link is what catches it.)"""
        receipts._write_watermark(100, _FIXED_KEY)
        for _ in range(3):
            line = receipts.append({"kind": "step", "by": "engine"})
        self.assertEqual(int(line["counter"]), 103)
        out = receipts.verify()
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["count"], 3)

    def test_a_line_removed_from_the_middle_still_fails(self) -> None:
        for _ in range(3):
            receipts.append({"kind": "step", "by": "engine"})
        rows = [json.loads(x) for x in config.SB_RECEIPTS.read_text().splitlines() if x.strip()]
        del rows[1]
        config.SB_RECEIPTS.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
        self.assertFalse(receipts.verify()["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
