"""Fail-closed controls for the trusted cross-repository source intake."""

import unittest
from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github/workflows/genesis-aistudio-source-intake.yml"
)


class PrivateIntakeContract(unittest.TestCase):
    def test_only_trusted_main_can_obtain_app_token(self):
        s = WORKFLOW.read_text()
        self.assertIn("branches: [main]", s)
        self.assertIn("if: github.ref == 'refs/heads/main'", s)
        self.assertNotIn("pull_request:", s)
        self.assertNotIn("pull_request_target:", s)
        self.assertIn("lane: agent-workforce", s)
        self.assertIn("persist-credentials: false", s)

    def test_private_archive_never_becomes_public_artifact(self):
        s = WORKFLOW.read_text()
        self.assertNotIn("upload-artifact", s)
        self.assertNotIn("GITHUB_STEP_SUMMARY", s)
        self.assertIn("PRIVATE_ARGON_INTAKE", s)
        self.assertNotIn("cat ops/io/aistudio-import-receipt.json", s)

    def test_exact_private_release_digest_and_pinned_reader(self):
        s = WORKFLOW.read_text()
        self.assertIn("releases/assets/739187944", s)
        self.assertIn(
            "310af77679f440681150a11787966fb9c53e36683d588452a5b4c9aad2dc7389", s
        )
        self.assertIn("3ecc81d097b33ee2a34e5bdad49d36ad28125477", s)
        self.assertIn("5cc44861da3e362a0dc946568f7d0e0657e43284", s)
        self.assertIn("EXISTING_SOURCE_RECEIPT_CONFLICT", s)
        self.assertNotIn("tar -x", s)
        self.assertNotIn("npm ci", s)

    def test_ephemeral_git_credentials_and_pinned_importer_only(self):
        s = WORKFLOW.read_text()
        self.assertIn("GIT_CONFIG_COUNT=1", s)
        self.assertIn("GIT_CONFIG_VALUE_0=", s)
        self.assertIn("git hash-object ops/io/recover_aistudio_preview.py", s)
        self.assertIn("git hash-object ops/io/recover_aistudio_preview.test.py", s)
        self.assertIn("PRIVATE_ARGON_SOURCE_LANE_COMMIT", s)
        self.assertNotIn("git config --global credential", s)
        self.assertNotIn("git clone https://x-access-token:", s)

    def test_no_direct_main_push_and_no_unsafe_override(self):
        s = WORKFLOW.read_text()
        self.assertIn("lane/aistudio-io-import-probe-20261112", s)
        self.assertIn("Integration-State: SOURCE_QUARANTINED_NOT_PRODUCTION", s)
        self.assertNotIn("git push origin HEAD:main", s)
        self.assertNotIn("git push -f", s)
        self.assertNotIn("--force", s)


if __name__ == "__main__":
    unittest.main()
