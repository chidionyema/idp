"""Fail-closed controls for running private argon's CI on idp's free public runners."""

import re
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/argon-verify.yml"


class ArgonVerifyContract(unittest.TestCase):
    def setUp(self):
        self.s = WORKFLOW.read_text()

    def test_only_trusted_main_obtains_the_app_token(self):
        self.assertIn("if: github.ref == 'refs/heads/main'", self.s)
        self.assertIn("lane: agent-workforce", self.s)
        self.assertNotIn("pull_request:", self.s)
        self.assertNotIn("pull_request_target:", self.s)
        self.assertIn("persist-credentials: false", self.s)

    def test_token_is_confined_to_the_clone_step(self):
        # GH_APP_TOKEN must appear only in the step that clones; the step that runs
        # argon's code must hold no credential and must disable package scripts.
        self.assertEqual(self.s.count("steps.app.outputs.token"), 1)
        run_step = self.s.split("name: Verify argon (no credential")[1]
        self.assertNotIn("GH_APP_TOKEN", run_step)
        self.assertNotIn("steps.app.outputs", run_step)
        self.assertIn("--ignore-scripts", run_step)
        self.assertNotIn("npm install --no-ignore-scripts", run_step)

    def test_git_credentials_are_ephemeral_and_removed(self):
        self.assertIn("GIT_CONFIG_COUNT=1", self.s)
        self.assertIn('rm -rf "${RUNNER_TEMP}/argon/.git"', self.s)
        self.assertNotIn("git clone https://x-access-token:", self.s)
        self.assertNotIn("git config --global credential", self.s)

    def test_private_source_never_becomes_public_output(self):
        self.assertNotIn("upload-artifact", self.s)
        self.assertNotIn("GITHUB_STEP_SUMMARY", self.s)
        self.assertNotIn('cat "$log"', self.s)
        self.assertNotIn('cat "${RUNNER_TEMP}/argon-tests.log"', self.s)
        self.assertIn("ARGON_VERIFY", self.s)

    def test_never_writes_to_argon(self):
        self.assertNotIn("git push", self.s)
        self.assertNotIn("--force", self.s)

    def test_verifies_argon_main_and_the_i8080_app(self):
        self.assertIn("ref: main", self.s)
        self.assertIn("propose/aistudioi8080-f024b8a8", self.s)
        self.assertIn("quarantine/aistudio/i8080-admission-control-plane", self.s)
        self.assertIn("fail-fast: false", self.s)

    def test_every_action_is_pinned_to_a_commit(self):
        for line in self.s.splitlines():
            m = re.match(r"\s*-?\s*uses:\s*(\S+)", line)
            if m and not m.group(1).startswith("./"):
                self.assertRegex(m.group(1), r"@[0-9a-f]{40}$", line)


if __name__ == "__main__":
    unittest.main()
