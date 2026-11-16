"""i8096 recovery: the checked-in bytes are the founder's bytes, and the symbiont can refuse.

The archive itself lives outside the repository (~/Downloads and the quarantine), so these tests
grade the landed members against the manifest shipped inside the archive and against the
`SHA256SUMS` file, then exercise the two behaviours that need no Genesis database.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAGE = ROOT / "cage/i8096"
MANIFEST = json.loads((CAGE / "MANIFEST.json").read_text(encoding="utf-8"))
SYMBIONT = CAGE / "bin/genesis_realtime_symbiont.py.recovered"


def py310():
    if sys.version_info >= (3, 10):
        return sys.executable
    for name in ("python3.12", "python3.11"):
        found = shutil.which(name)
        if found:
            return found
    return None


class Recovery(unittest.TestCase):
    def test_each_member_matches_the_archive_manifest(self):
        self.assertEqual(len(MANIFEST), 4)
        for rel, meta in MANIFEST.items():
            landed = CAGE / rel
            if not landed.exists():
                landed = CAGE / (rel + ".recovered")
            data = landed.read_bytes()
            self.assertEqual(len(data), meta["bytes"], rel)
            self.assertEqual(hashlib.sha256(data).hexdigest(), meta["sha256"], rel)

    def test_sha256sums_file_agrees_with_the_members(self):
        lines = (CAGE / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 4)
        for line in lines:
            digest, rel = line.split(None, 1)
            rel = rel.strip().lstrip("*")
            self.assertEqual(
                hashlib.sha256((CAGE / rel).read_bytes()).hexdigest(),
                digest,
                rel,
            )

    @unittest.skipUnless(
        py310(), "python >= 3.10 is needed to execute the recovered symbiont"
    )
    def test_emit_userscript_needs_no_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [py310(), str(SYMBIONT), "emit-userscript"],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            emitted = Path(tmp) / "genesis-mycelium.user.js"
            self.assertTrue(emitted.exists())
            body = emitted.read_text(encoding="utf-8")
            self.assertIn("leaseAndExecute", body)
            self.assertIn("EXECUTING_ON_WEB_SURFACE", body)

    @unittest.skipUnless(
        py310(), "python >= 3.10 is needed to execute the recovered symbiont"
    )
    def test_symbiont_refuses_the_legacy_history_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env["GENESIS_DB_PATH"] = str(Path.home() / ".estate/estate.db")
            result = subprocess.run(
                [py310(), str(SYMBIONT), "pack-spore"],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("HISTORY_QUARANTINE_VIOLATION", result.stderr + result.stdout)
            self.assertFalse((Path(tmp) / "GENESIS_SPORE.dna").exists())


if __name__ == "__main__":
    unittest.main()
