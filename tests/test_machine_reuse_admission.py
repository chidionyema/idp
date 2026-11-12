"""GOV-015 adversarial contract: reject invented code without existing capability proof.

Run in the existing estate pytest/unittest suite and the existing law-gate falsifier.
No new scheduler, queue, context store, privilege, or decision engine.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform" / "estate"))
from governance import checks  # noqa: E402

LAW = {"type": "diff_reuse_convergence", "base": "HEAD~1", "head": "HEAD"}


class ReuseAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="reuse-gate-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "law test")
        self.git("config", "user.email", "law-test@localhost")
        self.write(
            "policy/agent-decisions.json",
            json.dumps({
                "schema_version": 1,
                "decisions": [
                    {"id": "dec:submit", "mode": "machine", "decided_by": "cap:intent/lane-submit"},
                    {"id": "dec:human", "mode": "judgment", "decided_by": "founder"},
                ],
            }),
        )
        self.write("bin/lane-submit", "#!/bin/sh\nprintf 'existing machine'\\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")

    def git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.path,
            env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull,
                 "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=True, timeout=15,
        )

    def write(self, filename, content):
        p = self.path / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf8")

    def candidate(self, message, *, source="src/new_executor.py",
                  testfile="tests/test_new_executor.py",
                  add_test=True, add_base_source=False):
        self.write(source, "def execute():\n    return 'candidate'\n")
        if add_test:
            self.write(testfile, "def test_execution():\n    assert True\n")
        if add_base_source:
            self.write("src/invented_owner.py", "def pretend():\n    return 'owner'\n")
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def verdict(self):
        return checks.run_check(str(self.path), LAW)

    def test_reuse_of_registered_decider_base_implementation_and_changed_test_passes(self):
        self.candidate(
            "feat: compose existing owner\n\n"
            "Existing-Capability: cap:intent/lane-submit\n"
            "Existing-Implementation: bin/lane-submit\n"
            "Proof: python3 -m pytest tests/test_new_executor.py\n"
        )
        ok, msg = self.verdict()
        self.assertTrue(ok, msg)
        self.assertIn("runtime yield remains separately verified", msg)

    def test_unattributed_new_code_cannot_enter(self):
        self.candidate("feat: invent scheduler\n\nProof: pytest tests/test_new_executor.py\n")
        ok, msg = self.verdict()
        self.assertFalse(ok)
        self.assertIn("Existing-Capability", msg)

    def test_no_changed_test_means_no_new_runtime_even_with_trailers(self):
        self.candidate(
            "feat: invent\n\nExisting-Capability: cap:intent/lane-submit\n"
            "Existing-Implementation: bin/lane-submit\n"
            "Proof: pytest tests/test_new_executor.py\n",
            add_test=False,
        )
        ok, msg = self.verdict()
        self.assertFalse(ok)
        self.assertIn("no executable falsifier/test", msg)

    def test_unregistered_model_or_ghost_capability_cannot_approve_itself(self):
        self.candidate(
            "feat: invent\n\nExisting-Capability: cap:intent/imagined-agent\n"
            "Existing-Implementation: bin/lane-submit\n"
            "Proof: pytest tests/test_new_executor.py\n",
        )
        ok, msg = self.verdict()
        self.assertFalse(ok)
        self.assertIn("not a registered machine decider", msg)

    def test_new_file_cannot_masquerade_as_preexisting_machine(self):
        self.candidate(
            "feat: copy\n\nExisting-Capability: cap:intent/lane-submit\n"
            "Existing-Implementation: src/invented_owner.py\n"
            "Proof: pytest tests/test_new_executor.py\n",
            add_base_source=True,
        )
        ok, msg = self.verdict()
        self.assertFalse(ok)
        self.assertIn("absent from BASE tree", msg)

    def test_prose_proof_without_a_changed_test_path_is_rejected(self):
        self.candidate(
            "feat: pretend tests ran\n\nExisting-Capability: cap:intent/lane-submit\n"
            "Existing-Implementation: bin/lane-submit\n"
            "Proof: it worked on my laptop\n",
        )
        ok, msg = self.verdict()
        self.assertFalse(ok)
        self.assertIn("Proof must name a changed executable test", msg)

    def test_new_workflow_is_also_an_executable(self):
        self.candidate(
            "ci: add workflow\n\nExisting-Capability: cap:intent/lane-submit\n"
            "Existing-Implementation: bin/lane-submit\n"
            "Proof: pytest tests/test_new_executor.py\n",
            source=".github/workflows/duplicate-runner.yml",
        )
        ok, msg = self.verdict()
        self.assertTrue(ok, msg)

    def test_documentation_or_test_only_changes_do_not_block_research(self):
        self.write("docs/notes.md", "# research\n")
        self.write("tests/test_new_executor.py", "def test_research(): assert True\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "test: isolated falsification")
        ok, msg = self.verdict()
        self.assertTrue(ok, msg)
        self.assertIn("no newly introduced executable", msg)


if __name__ == "__main__":
    unittest.main()
