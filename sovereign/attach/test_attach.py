"""unittest for sovereign/attach/ (cp21). Run:
    ESTATE_HOME=<scratch> PYTHONPATH=<idp> \
      sovereign/.venv/bin/python -m unittest sovereign.attach.test_attach -v
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from sovereign.attach import core
from sovereign.attach.policy import (
    classify,
    requires_quorum_and_hardware_signature,
    requires_receipt_commit,
    scaffold_policy_text,
)


class PolicyClassificationTest(unittest.TestCase):
    def test_reads_are_allowed(self) -> None:
        for cmd in ("cat file.py", "grep -n foo .", "git log", "git diff", "ls -la"):
            self.assertEqual(classify(cmd), "read", cmd)
            self.assertFalse(requires_receipt_commit(classify(cmd)))

    def test_writes_require_a_receipt_commit(self) -> None:
        self.assertEqual(classify("edit file.py"), "write")
        self.assertTrue(requires_receipt_commit(classify("edit file.py")))
        self.assertFalse(requires_quorum_and_hardware_signature(classify("edit file.py")))

    def test_git_writes_require_a_receipt_commit(self) -> None:
        self.assertEqual(classify("git commit -m x"), "git_write")
        self.assertTrue(requires_receipt_commit(classify("git commit -m x")))

    def test_destructive_requires_quorum_and_hardware_signature(self) -> None:
        for cmd in ("rm -rf /", "git push --force origin main", "git reset --hard", "DROP TABLE users"):
            classification = classify(cmd)
            self.assertEqual(classification, "destructive", cmd)
            self.assertTrue(requires_quorum_and_hardware_signature(classification))
            self.assertTrue(requires_receipt_commit(classification))

    def test_destructive_pattern_inside_a_git_command_still_wins(self) -> None:
        # "git push --force" contains both a git-write verb (push) and a
        # destructive pattern; destructive must classify, not git_write --
        # this is the property cp21's quorum rule actually depends on.
        self.assertEqual(classify("git push --force origin main"), "destructive")

    def test_scaffolded_policy_names_the_destructive_patterns_and_quorum(self) -> None:
        text = scaffold_policy_text()
        self.assertIn("rm -rf", text)
        self.assertIn("git push --force", text)
        self.assertIn("2/3", text)


class NodeCountingAndHashTest(unittest.TestCase):
    def _init_git_repo(self, tmp: Path) -> Path:
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=tmp, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, check=True)
        (tmp / "a.py").write_text("x = 1\n")
        (tmp / "b.py").write_text("y = 2\n")
        subprocess.run(["git", "add", "a.py", "b.py"], cwd=tmp, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp, check=True)
        return tmp

    def test_root_hash_is_deterministic_across_repeated_computation(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = self._init_git_repo(Path(d))
            nodes1 = core.list_nodes(root)
            nodes2 = core.list_nodes(root)
            self.assertEqual(nodes1, nodes2)
            self.assertEqual(core.compute_root_hash(root, nodes1), core.compute_root_hash(root, nodes2))

    def test_root_hash_changes_when_a_tracked_file_changes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = self._init_git_repo(Path(d))
            nodes = core.list_nodes(root)
            before = core.compute_root_hash(root, nodes)
            (root / "a.py").write_text("x = 999\n")
            after = core.compute_root_hash(root, nodes)
            self.assertNotEqual(before, after)

    def test_git_repo_counts_only_tracked_files(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = self._init_git_repo(Path(d))
            (root / "untracked.py").write_text("z = 3\n")
            nodes = core.list_nodes(root)
            self.assertEqual(len(nodes), 2)
            self.assertNotIn("untracked.py", nodes)

    def test_non_git_directory_walks_minus_ignored_dirnames(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "keep.py").write_text("1\n")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "dep.js").write_text("2\n")
            nodes = core.list_nodes(root)
            self.assertEqual(nodes, ["keep.py"])


if __name__ == "__main__":
    unittest.main()
