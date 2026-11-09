#!/usr/bin/env python3
"""Falsifiers for infra/hygiene/estate-hygiene.py. Run: python3 -m unittest infra/hygiene/test_estate_hygiene.py"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "hyg", Path(__file__).with_name("estate-hygiene.py"))
hyg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hyg)


def sh(*args: str, cwd: Path) -> str:
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise AssertionError(f"{args} failed: {p.stderr[:300]}")
    return p.stdout


class HygieneTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.remote = self.root / "remote.git"
        self.repo = self.root / "repo"
        sh("git", "init", "-q", "--bare", str(self.remote), cwd=self.root)
        sh("git", "init", "-q", "-b", "main", str(self.repo), cwd=self.root)
        sh("git", "config", "user.email", "t@t", cwd=self.repo)
        sh("git", "config", "user.name", "t", cwd=self.repo)
        (self.repo / "f.txt").write_text("base\n")
        sh("git", "add", ".", cwd=self.repo)
        sh("git", "commit", "-qm", "base", cwd=self.repo)
        sh("git", "remote", "add", "origin", str(self.remote), cwd=self.repo)
        sh("git", "push", "-q", "origin", "main", cwd=self.repo)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def remote_branches(self) -> dict[str, str]:
        out = sh("git", "ls-remote", "--heads", "origin", cwd=self.repo)
        return {l.split("\t")[1][len("refs/heads/"):]: l.split("\t")[0] for l in out.splitlines() if l}

    def remote_matching(self, prefix: str) -> list[str]:
        out = sh("git", "ls-remote", "origin", prefix, cwd=self.repo)
        return [l.split("\t")[1] for l in out.splitlines() if l]

    def test_snapshot_saves_a_dirty_tree_without_touching_it(self) -> None:
        (self.repo / "f.txt").write_text("uncommitted work\n")
        rows = hyg.snapshot(self.repo, "origin", apply=True)
        self.assertEqual(len(rows), 1)
        self.assertIn("snapshot ->", rows[0]["action"])
        self.assertEqual((self.repo / "f.txt").read_text(), "uncommitted work\n")
        self.assertEqual(sh("git", "status", "--porcelain", cwd=self.repo).strip(), "M f.txt")
        self.assertTrue(self.remote_matching("refs/wip/guard/*"), "the snapshot ref must exist on the remote")

    def test_archive_preserves_then_deletes_and_keeps_the_keep_set(self) -> None:
        sh("git", "checkout", "-qb", "stale", cwd=self.repo)
        (self.repo / "g.txt").write_text("stale work\n")
        sh("git", "add", ".", cwd=self.repo)
        sh("git", "commit", "-qm", "stale commit", cwd=self.repo)
        stale_sha = sh("git", "rev-parse", "HEAD", cwd=self.repo).strip()
        sh("git", "push", "-q", "origin", "stale", cwd=self.repo)
        sh("git", "checkout", "-q", "main", cwd=self.repo)
        sh("git", "push", "-q", "origin", "main:lane/keep-me", cwd=self.repo)

        rows = hyg.archive(self.repo, "origin", {"lane/keep-me"}, apply=True)
        archived = {r["branch"]: r for r in rows}
        self.assertIn("stale", archived)
        self.assertEqual(archived["stale"]["action"], "archived+deleted")
        self.assertNotIn("lane/keep-me", archived)

        branches = self.remote_branches()
        self.assertNotIn("stale", branches, "the archived branch must be gone from heads")
        self.assertIn("lane/keep-me", branches, "the keep set must be untouched")
        refs = self.remote_matching("refs/archive/stale")
        self.assertEqual(len(refs), 1, "the archive ref must exist before/after the delete")
        self.assertEqual(sh("git", "ls-remote", "origin", "refs/archive/stale", cwd=self.repo).split("\t")[0], stale_sha)

    def test_dry_run_changes_nothing(self) -> None:
        sh("git", "push", "-q", "origin", "main:lane/dry", cwd=self.repo)
        rows = hyg.archive(self.repo, "origin", set(), apply=False)
        self.assertTrue(all(r["action"] == "would archive+delete" for r in rows))
        self.assertIn("lane/dry", self.remote_branches())
        self.assertEqual(self.remote_matching("refs/archive/*"), [])

    def test_inventory_lists_what_was_archived_with_its_restore(self) -> None:
        sh("git", "push", "-q", "origin", "main:old/lane", cwd=self.repo)
        rows = hyg.archive(self.repo, "origin", set(), apply=True)
        inv = hyg.write_inventory(self.repo, "origin", rows)
        data = __import__("json").loads(inv.read_text())
        entry = [e for e in data["entries"] if e["branch"] == "old/lane"][0]
        self.assertTrue(entry["sha"])
        self.assertIn("refs/heads/old/lane", entry["restore"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
