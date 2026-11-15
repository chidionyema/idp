"""Regression cases for producer-side admission; run python3 -m unittest tests/test_estate_admission_preflight.py."""
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "bin" / "estate-admission-preflight"
loader = importlib.machinery.SourceFileLoader("estate_admission_preflight", str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
HEAD = "a" * 40
BODY = "BDD-PROOF\nhead: " + HEAD + "\n5 passed in 0.12s\nEND-BDD-PROOF"
STAMP = "Fix\n\nX-Idp-Signed: valid-local-stamp\n"

class AdmissionTests(unittest.TestCase):
    def test_valid_local_submission(self):
        self.assertEqual(module.validate(HEAD, STAMP, "dev@example.org", BODY), [])
    def test_missing_stamp_rejected_before_remote(self):
        self.assertIn("COMMIT_UNSTAMPED", module.validate(HEAD, "Fix", "dev@example.org", BODY))
    def test_missing_proof_rejected(self):
        self.assertIn("BDD_BLOCK_MISSING", module.validate(HEAD, STAMP, "dev@example.org", "Fix"))
    def test_stale_proof_rejected(self):
        self.assertIn("BDD_HEAD_MISMATCH", module.validate(HEAD, STAMP, "dev@example.org", BODY.replace(HEAD, "b"*40)))
    def test_prose_is_not_runner_evidence(self):
        self.assertIn("BDD_RUN_EVIDENCE_MISSING", module.validate(HEAD, STAMP, "dev@example.org", BODY.replace("5 passed in 0.12s", "all tests passed")))
    def test_blind_merge_rejected(self):
        self.assertIn("BLIND_MERGE", module.validate(HEAD, STAMP + "X-Idp-Merge-Strategy: theirs\n", "dev@example.org", BODY))
    def test_github_server_commit_without_local_hook(self):
        self.assertEqual(module.validate(HEAD, "Fix", "noreply@github.com", BODY), [])
    def test_author_is_not_credential(self):
        self.assertIn("COMMIT_UNSTAMPED", module.validate(HEAD, "Fix", "founder@example.org", BODY))
    def test_no_pr_body_does_not_claim_pr_proof(self):
        self.assertEqual(module.validate(HEAD, STAMP, "dev@example.org", None), [])

if __name__ == "__main__":
    unittest.main()
