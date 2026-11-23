import hashlib
import unittest
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from lib.founder_admission import AdmissionDenied, admit, digest, preserve_instruction, _canonical


class FounderAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 23, tzinfo=timezone.utc)
        self.binding = dict(instruction_id="i", claim_id="c", target="production", revision="abc", environment="prod")
        self.keys = {k: Ed25519PrivateKey.generate() for k in ("discovery", "execution", "effect", "independent_verification", "certifier")}
        self.roots = {k: {"role": "discovery" if k == "discovery" else "certifier" if k == "certifier" else "proof",
                          "public_key_hex": v.public_key().public_bytes(
                              serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()}
                      for k, v in self.keys.items()}
        self.discovery = self.sign("discovery", dict(self.binding, searched_sources=["estate-graph", "runtime"],
                          contradictions=[], expires_at="2026-11-24T00:00:00Z"))
        self.proofs = [self.sign(k, dict(self.binding, kind=k, observed=True, evidence_uri="https://example.org/"+k,
                          evidence_digest=hashlib.sha256(k.encode()).hexdigest(), expires_at="2026-11-24T00:00:00Z"))
                       for k in ("execution", "effect", "independent_verification")]
        self.claim = dict(self.binding)
        self.refresh_certificate()

    def sign(self, key, payload):
        return dict(key_id=key, payload=payload, signature_hex=self.keys[key].sign(_canonical(payload)).hex())

    def refresh_certificate(self):
        self.claim["certificate"] = self.sign("certifier", dict(self.binding, decision="ALLOW",
            expires_at="2026-11-24T00:00:00Z",
            discovery_digest=digest(_canonical(self.discovery["payload"])),
            proof_digests=sorted(digest(_canonical(p["payload"])) for p in self.proofs)))

    def check(self):
        admit(self.claim, self.discovery, self.proofs, now=self.now, trust_roots=self.roots)

    def test_valid_signed_evidence(self):
        self.check()

    def test_missing_discovery(self):
        self.discovery = {}
        with self.assertRaises(AdmissionDenied):
            self.check()

    def test_missing_proof(self):
        self.proofs.pop()
        with self.assertRaises(AdmissionDenied):
            self.check()

    def test_forged_proof(self):
        self.proofs[0]["payload"]["observed"] = False
        with self.assertRaises(AdmissionDenied):
            self.check()

    def test_same_issuer(self):
        self.proofs[2] = self.proofs[1]
        with self.assertRaises(AdmissionDenied):
            self.check()

    def test_wrong_revision(self):
        self.proofs[2] = self.sign("independent_verification", dict(self.proofs[2]["payload"], revision="other"))
        with self.assertRaises(AdmissionDenied):
            self.check()

    def test_contradiction(self):
        self.discovery = self.sign("discovery", dict(self.discovery["payload"], contradictions=["HTTP 525"]))
        with self.assertRaises(AdmissionDenied):
            self.check()

    def test_self_attestation_rejected(self):
        self.proofs[0] = dict(self.proofs[0], signature_hex="00"*64, verified=True)
        with self.assertRaises(AdmissionDenied):
            self.check()

    def test_untrusted_root(self):
        self.roots.pop("effect")
        with self.assertRaises(AdmissionDenied):
            self.check()

    def test_certificate_mismatch(self):
        self.claim["certificate"]["payload"]["proof_digests"] = []
        with self.assertRaises(AdmissionDenied):
            self.check()

    def test_verbatim_bytes(self):
        raw = b"Agent must be force to discover reality before contacting founder"
        preserve_instruction(raw, digest(raw))
        with self.assertRaises(AdmissionDenied):
            preserve_instruction(raw.replace(b"before", b"prior to"), digest(raw))


if __name__ == "__main__":
    unittest.main()
