#!/usr/bin/env python3
"""Falsifiers for prove-no-loss.py: it must pass when every tip is recoverable, and FAIL when one
is not. A verifier that cannot fail proves nothing."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("pnl", Path(__file__).with_name("prove-no-loss.py"))
pnl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pnl)


def sh(*a: str, cwd: Path) -> str:
    p = subprocess.run(a, cwd=cwd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise AssertionError(f"{a} failed: {p.stderr[:300]}")
    return p.stdout


class ProveTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.remote = self.root / "r.git"
        self.repo = self.root / "w"
        sh("git", "init", "-q", "--bare", str(self.remote), cwd=self.root)
        sh("git", "init", "-q", "-b", "main", str(self.repo), cwd=self.root)
        sh("git", "config", "user.email", "t@t", cwd=self.repo)
        sh("git", "config", "user.name", "t", cwd=self.repo)
        (self.repo / "f").write_text("x\n")
        sh("git", "add", ".", cwd=self.repo)
        sh("git", "commit", "-qm", "base", cwd=self.repo)
        sh("git", "remote", "add", "origin", str(self.remote), cwd=self.repo)
        sh("git", "push", "-q", "origin", "main", cwd=self.repo)
        self.sha = sh("git", "rev-parse", "HEAD", cwd=self.repo).strip()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_inv(self, branch: str, sha: str) -> None:
        p = self.repo / ".genesis" / "archive-inventory.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"entries": [{"branch": branch, "sha": sha}]}))

    def test_passes_when_the_archive_ref_holds_the_tip(self) -> None:
        sh("git", "push", "-q", "origin", f"{self.sha}:refs/archive/gone", cwd=self.repo)
        self.write_inv("gone", self.sha)
        r = pnl.prove(self.repo, "origin", drill=False)
        self.assertTrue(r["ok"], r)

    def test_fails_when_the_archive_ref_is_missing(self) -> None:
        self.write_inv("gone", self.sha)
        r = pnl.prove(self.repo, "origin", drill=False)
        self.assertFalse(r["ok"])
        self.assertIn("gone", r["failed"])

    def test_fails_when_the_archive_ref_points_elsewhere(self) -> None:
        sh("git", "push", "-q", "origin", f"{self.sha}:refs/archive/gone", cwd=self.repo)
        self.write_inv("gone", "0" * 40)
        r = pnl.prove(self.repo, "origin", drill=False)
        self.assertFalse(r["ok"])

    def test_drill_restores_verifies_and_cleans_up(self) -> None:
        sh("git", "push", "-q", "origin", f"{self.sha}:refs/archive/gone", cwd=self.repo)
        self.write_inv("gone", self.sha)
        r = pnl.prove(self.repo, "origin", drill=True)
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["drill"]["verified"])
        self.assertNotIn("refs/heads/gone-restore-drill",
                         sh("git", "ls-remote", "origin", cwd=self.repo))


if __name__ == "__main__":
    unittest.main(verbosity=2)
