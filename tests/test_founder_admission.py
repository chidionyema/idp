import hashlib
import unittest
from datetime import datetime, timedelta, timezone

from lib.founder_admission import AdmissionDenied, admit, preserve_instruction


class FounderAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 23, tzinfo=timezone.utc)
        self.claim = dict(instruction_id="i", claim_id="c", target="production",
                          revision="abc", environment="prod", independent_verifier_approved=True)
        binding = {k: self.claim[k] for k in ("instruction_id", "claim_id", "target", "revision", "environment")}
        self.discovery = dict(binding, searched_sources=["estate-graph", "runtime"],
                              verified=True, contradictions=[], expires_at="2026-11-24T00:00:00Z")
        self.proofs = [
            dict(binding, kind=k, verified=True, evidence_digest=str(i), issuer=str(i),
                 expires_at="2026-11-24T00:00:00Z")
            for i, k in enumerate(("execution", "effect", "independent_verification"))
        ]

    def test_valid_structural_envelope(self):
        admit(self.claim, self.discovery, self.proofs, now=self.now)

    def test_no_discovery_denied(self):
        with self.assertRaises(AdmissionDenied):
            admit(self.claim, {}, self.proofs, now=self.now)

    def test_missing_proof_denied(self):
        with self.assertRaises(AdmissionDenied):
            admit(self.claim, self.discovery, self.proofs[:2], now=self.now)

    def test_correlated_proof_denied(self):
        self.proofs[2]["issuer"] = self.proofs[1]["issuer"]
        with self.assertRaises(AdmissionDenied):
            admit(self.claim, self.discovery, self.proofs, now=self.now)

    def test_wrong_revision_denied(self):
        self.proofs[2]["revision"] = "other"
        with self.assertRaises(AdmissionDenied):
            admit(self.claim, self.discovery, self.proofs, now=self.now)

    def test_unresolved_contradiction_denied(self):
        self.discovery["contradictions"] = ["live probe says 525"]
        with self.assertRaises(AdmissionDenied):
            admit(self.claim, self.discovery, self.proofs, now=self.now)

    def test_unapproved_verifier_denied(self):
        self.claim["independent_verifier_approved"] = False
        with self.assertRaises(AdmissionDenied):
            admit(self.claim, self.discovery, self.proofs, now=self.now)

    def test_instruction_bytes_not_paraphrase(self):
        raw = b"Agent must be force to discover reality before contacting founder"
        d = hashlib.sha256(raw).hexdigest()
        preserve_instruction(raw, d)
        with self.assertRaises(AdmissionDenied):
            preserve_instruction(raw.replace(b"before", b"prior to"), d)


if __name__ == "__main__":
    unittest.main()
