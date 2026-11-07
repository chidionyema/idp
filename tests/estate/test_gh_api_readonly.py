"""Regression tests: gh-api's read-only claim must remain true for hostile inputs."""
from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
INTENT = ROOT / "platform/estate/intents/gh-api.yaml"


class GitHubReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.intent = yaml.safe_load(INTENT.read_text())
        self.command = self.intent["steps"][0]["cmd"]
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        fake = root / "gh"
        fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$GH_ARGS"\n')
        fake.chmod(0o700)
        self.env = dict(
            os.environ,
            PATH=str(root) + os.pathsep + os.environ.get("PATH", ""),
            GH_ARGS=str(root / "args"),
        )
        self.args_path = root / "args"

    def tearDown(self):
        self.tmp.cleanup()

    def invoke(self, path):
        # The existing intent executor shell-quotes each {{path}} substitution.
        cmd = self.command.replace("{{path}}", shlex.quote(path))
        return subprocess.run(
            ["bash", "-c", cmd], text=True, capture_output=True, env=self.env, timeout=8
        )

    def test_read_contract_cannot_change_method(self):
        self.assertEqual(self.intent["class"], "read")
        self.assertEqual(set(self.intent["args"]), {"path"})
        self.assertIn("gh api --method GET", self.command)
        self.assertNotIn("{{params}}", self.command)

    def test_allowed_get_is_repo_scoped(self):
        result = self.invoke("issues/7443/comments")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.args_path.read_text().splitlines(),
            ["api", "--method", "GET", "repos/chidionyema/idp/issues/7443/comments"],
        )

    def test_untrusted_paths_cannot_inject_gh_flags_or_shell(self):
        bad = (
            "issues/1?x=2",
            "../repos/elsewhere",
            "issues/1 -X POST",
            "issues/1; touch /tmp/owned",
            "issues/1\n-X POST",
            "issues/1&&echo hi",
            "issues/1/../../git/refs",
            "",
        )
        for path in bad:
            with self.subTest(path=path):
                self.args_path.unlink(missing_ok=True)
                result = self.invoke(path)
                self.assertEqual(result.returncode, 4, (path, result.stderr))
                self.assertFalse(self.args_path.exists(), path)


if __name__ == "__main__":
    unittest.main()
