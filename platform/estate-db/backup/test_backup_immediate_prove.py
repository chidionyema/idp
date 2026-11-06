"""Guard the existing estate DB recovery lane's event and credential boundary.

The protected copy service must verify changes immediately after promotion,
without allowing a branch, fork or unreviewed dispatch to mint cloud credentials.
"""
from pathlib import Path
import unittest


WORKFLOW = (
    Path(__file__).resolve().parents[3] / ".github/workflows/estate-db-backup.yml"
)


class BackupTriggerContract(unittest.TestCase):
    def setUp(self):
        self.source = WORKFLOW.read_text(encoding="utf-8")

    def test_accepted_main_change_starts_immediate_copy(self):
        self.assertIn("  push:\n    branches: [main]\n", self.source)
        self.assertIn("      - .github/workflows/estate-db-backup.yml", self.source)
        self.assertIn("      - platform/estate-db/backup/**", self.source)
        self.assertIn("  schedule:\n", self.source)
        self.assertIn("  workflow_dispatch:\n", self.source)

    def test_unreviewed_refs_cannot_mint_oci(self):
        self.assertIn("    if: github.ref == 'refs/heads/main'", self.source)
        self.assertNotIn("\n  pull_request:\n", self.source)
        self.assertNotIn("\n  pull_request_target:\n", self.source)
        self.assertNotIn("\n    branches: ['*']", self.source)
        self.assertLess(
            self.source.index("    if: github.ref == 'refs/heads/main'"),
            self.source.index("      - name: OCI session token from the GitHub OIDC token")
        )

    def test_no_loss_of_backup_chain_and_copy_safety(self):
        for step in (
            "verify recovery source selection against offline adversarial fixtures",
            "fetch the dump that really carries the estate database",
            "restore it into PostgreSQL 18",
            "dump it again",
            "publish the copy, then the receipt",
            "the receipt, graded from the backend",
        ):
            self.assertIn(step, self.source)


if __name__ == "__main__":
    unittest.main()
