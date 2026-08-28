"""unittest for sovereign/engine/receipts.py (cp19). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.engine.test_receipts -v

One rung-4 incident test: a hash chain's prev_hash links prove nothing
about rows removed from its own tail (nothing downstream exists to notice
the missing link), so the naive chain-walk in verify() reported ok=True
after phase1.sh's `grep -v '"kind": "halt"'` happened to drop the tail
receipt. Fixed by a signed head anchor rewritten on every append() and
checked by verify() against the last line actually on disk.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sovereign import config
from sovereign.engine import receipts

_FIXED_KEY = b"\x01" * 32


class ReceiptsChainTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self._sb_receipts_patch = patch.object(config, "SB_RECEIPTS", root / "receipts.jsonl")
        self._head_patch = patch.object(config, "RECEIPTS_HEAD", root / "receipts.head")
        self._key_patch = patch.object(receipts, "get_or_create_key", lambda: (_FIXED_KEY, "software_file"))
        self._sb_receipts_patch.start()
        self._head_patch.start()
        self._key_patch.start()
        self.addCleanup(self._sb_receipts_patch.stop)
        self.addCleanup(self._head_patch.stop)
        self.addCleanup(self._key_patch.stop)

    def _append(self, **fields: object) -> dict[str, object]:
        return receipts.append(fields)

    def test_untampered_chain_verifies_ok(self) -> None:
        self._append(kind="start", session_id="s1")
        self._append(kind="step", session_id="s1")
        self._append(kind="halt", session_id="s1")
        result = receipts.verify()
        self.assertEqual(result["ok"], True)
        self.assertEqual(result["count"], 3)
        self.assertIsNone(result["reason"])

    def test_mid_chain_edit_is_caught_by_the_chain_itself(self) -> None:
        self._append(kind="start", session_id="s1")
        self._append(kind="step", session_id="s1")
        self._append(kind="halt", session_id="s1")
        lines = config.SB_RECEIPTS.read_text().splitlines()
        row = json.loads(lines[1])
        row["by"] = "mallory"
        lines[1] = json.dumps(row, sort_keys=True)
        config.SB_RECEIPTS.write_text("\n".join(lines) + "\n")
        result = receipts.verify()
        self.assertEqual(result["ok"], False)
        self.assertEqual(result["reason"], "broken")

    def test_incident_cp19_tail_truncation(self) -> None:
        # The exact defect: three lines appended, the LAST one deleted
        # (phase1.sh's `grep -v '"kind": "halt"'` when halt is the tail),
        # every remaining prev_hash link is still internally consistent,
        # so a chain-only verify must not be allowed to say ok=True.
        self._append(kind="start", session_id="s1")
        self._append(kind="step", session_id="s1")
        self._append(kind="halt", session_id="s1")
        lines = config.SB_RECEIPTS.read_text().splitlines()
        self.assertEqual(len(lines), 3)
        config.SB_RECEIPTS.write_text("\n".join(lines[:2]) + "\n")

        result = receipts.verify()

        self.assertEqual(result["ok"], False, "tail-truncated chain must never verify as ok")
        self.assertEqual(result["reason"], "truncated")

    def test_missing_anchor_fails_closed_not_silently(self) -> None:
        self._append(kind="start", session_id="s1")
        config.RECEIPTS_HEAD.unlink()
        result = receipts.verify()
        self.assertEqual(result["ok"], False)
        self.assertEqual(result["reason"], "no_anchor")

    def test_anchor_tampered_in_place_is_also_caught(self) -> None:
        self._append(kind="start", session_id="s1")
        self._append(kind="halt", session_id="s1")
        anchor = json.loads(config.RECEIPTS_HEAD.read_text())
        anchor["counter"] = 1
        config.RECEIPTS_HEAD.write_text(json.dumps(anchor, sort_keys=True))
        result = receipts.verify()
        self.assertEqual(result["ok"], False)
        self.assertEqual(result["reason"], "truncated")


if __name__ == "__main__":
    unittest.main()


class SignedLineVerifiesTest(ReceiptsChainTest):
    """Incident (2026-08-25, cp33/cp34 first run): a record appended with
    signed=True gained hw_sig/hw_backend after its hash was computed, and
    verify() then recomputed the hash over a body that included them, so
    every signed line -- every rewind, every signed refill -- read as
    "broken". The rule: the fields the hash does not cover are one tuple
    shared by append() and verify()."""

    def test_incident_signed_line_still_verifies(self) -> None:
        from unittest.mock import patch as _patch

        from sovereign.engine.receipts import HardwareTrustAnchor

        with _patch.object(HardwareTrustAnchor, "sign", lambda self, digest: ("ab" * 32, "software_key")):
            self._append(kind="plain")
            line = self._append(kind="rewind", signed=True)
            self._append(kind="plain")
        self.assertEqual(line["hw_backend"], "software_key")
        self.assertEqual(receipts.verify()["ok"], True, receipts.verify())

