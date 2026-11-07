"""Adversarial Ed25519 recovery-certificate tests against real verifier code.

Hermetic fixture keys are NEVER deployable roots. These tests establish
parsing and refusal semantics only, not OCI runtime recovery.
"""
from __future__ import annotations

import base64
import importlib.util
import json
import pathlib
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "recovery_evidence.py"
spec = importlib.util.spec_from_file_location("recovery_evidence_under_test", SOURCE)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class CertificateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.key = Ed25519PrivateKey.generate()  # test-only, ephemeral
        self.pub = base64.b64encode(self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )).decode()
        self.rows = [
            {"service": "llm-router", "leg": "router-a", "provider": "oracle",
             "verdict": "MEASURED_OK", "probe_kind": "functional",
             "url": "https://llm.example.test/v1/models"},
            {"service": "llm-router", "leg": "router-b", "provider": "cloudflare",
             "verdict": "MEASURED_OK", "probe_kind": "functional",
             "url": "https://edge.example.test/v1/models"},
        ]
        self.now = 1000.0
        self.payload = {
            "schema": "genesis.recovery.v1",
            "service": "llm-router",
            "observer": "independent:github-actions-test-fixture",
            "deployment_sha": "a" * 40,
            "run_id": "12345",
            "issued_at": 995.0,
            "expires_at": 1100.0,
            "observations": [
                {"leg": r["leg"], "provider": r["provider"],
                 "url": r["url"], "check": "authenticated-functional:model-inference",
                 "result": "FUNCTIONAL_READY", "evidence_sha256": "b" * 64,
                 "observed_at": stamp}
                for r in self.rows for stamp in (900.0, 960.0)
            ],
        }

    def seal(self, *, payload=None, key=None):
        p = self.payload if payload is None else payload
        signer = self.key if key is None else key
        b = json.dumps(p, sort_keys=True, separators=(",", ":")).encode("utf-8")
        envelope = {
            "format": "genesis.recovery.ed25519.v1",
            "payload_b64": base64.b64encode(b).decode(),
            "signature_b64": base64.b64encode(signer.sign(b)).decode(),
        }
        pathlib.Path(self.tmp.name, "llm-router.json").write_text(
            json.dumps(envelope), encoding="utf-8"
        )

    def verify(self, *, rows=None, key=None, service="llm-router", now=None):
        return verifier.verify_recovery_receipt(
            service, self.rows if rows is None else rows,
            receipt_dir=self.tmp.name,
            verifier_key_b64=self.pub if key is None else key,
            now=self.now if now is None else now,
        )

    def test_valid_signed_recovery_certificate(self):
        self.seal()
        self.assertEqual(self.verify(), (True, "SIGNED_RECOVERY_PROVEN"))

    def test_receipt_not_present(self):
        self.assertFalse(self.verify()[0])

    def test_missing_external_public_key(self):
        self.seal()
        self.assertEqual(self.verify(key="")[1],
                         "INDEPENDENT_RECOVERY_TRUST_NOT_CONFIGURED")

    def test_wrong_key_is_not_trusted(self):
        self.seal()
        other = Ed25519PrivateKey.generate()
        pub = base64.b64encode(other.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )).decode()
        self.assertFalse(self.verify(key=pub)[0])

    def test_tampering_with_signed_content(self):
        self.seal()
        p = pathlib.Path(self.tmp.name, "llm-router.json")
        obj = json.loads(p.read_text())
        pld = json.loads(base64.b64decode(obj["payload_b64"]))
        pld["service"] = "faked"
        obj["payload_b64"] = base64.b64encode(
            json.dumps(pld, sort_keys=True, separators=(",", ":")).encode()
        ).decode()
        p.write_text(json.dumps(obj))
        self.assertFalse(self.verify()[0])

    def test_expired_receipt(self):
        self.seal()
        self.assertEqual(self.verify(now=1101)[1],
                         "STALE_OR_FUTURE_RECOVERY_RECEIPT")

    def test_future_signed_receipt(self):
        self.payload["issued_at"] = 1015.0
        self.seal()
        self.assertEqual(self.verify()[1],
                         "STALE_OR_FUTURE_RECOVERY_RECEIPT")

    def test_cross_service_replay(self):
        self.seal()
        self.assertNotEqual(self.verify(service="otto")[0], True)

    def test_unattested_endpoint(self):
        self.seal()
        rows = [dict(self.rows[0], url="https://attacker.invalid/v1/models"), self.rows[1]]
        self.assertEqual(self.verify(rows=rows)[1], "UNTRUSTED_RECOVERY_OBSERVATION")

    def test_signed_reachability_not_functional(self):
        self.payload["observations"][0]["check"] = "http-status-only"
        self.seal()
        self.assertEqual(self.verify()[1], "UNTRUSTED_RECOVERY_OBSERVATION")

    def test_insufficient_observation_duration(self):
        for r in self.payload["observations"]:
            r["observed_at"] = 969.0
        self.seal()
        self.assertEqual(self.verify()[1], "RECOVERY_NOT_SUSTAINED")

    def test_no_independent_failure_domains(self):
        self.seal()
        rows = [dict(self.rows[0]), dict(self.rows[1], provider="oracle")]
        self.assertFalse(self.verify(rows=rows)[0])

    def test_local_unknown_is_not_signed_alive(self):
        self.seal()
        rows = [dict(self.rows[0], verdict="UNKNOWN"), self.rows[1]]
        self.assertEqual(self.verify(rows=rows)[1], "CURRENT_FUNCTIONAL_READINESS_UNPROVEN")

    def test_short_deployed_sha_is_refused(self):
        self.payload["deployment_sha"] = "da1536c7"
        self.seal()
        self.assertEqual(self.verify()[1], "RECOVERY_IDENTITY_OR_DEPLOYMENT_UNBOUND")

    def test_boolean_timestamp_is_not_valid(self):
        self.payload["issued_at"] = True
        self.seal()
        self.assertEqual(self.verify()[1], "STALE_OR_FUTURE_RECOVERY_RECEIPT")

    def test_duplicate_observation_key_cannot_replace_two_rounds(self):
        self.payload["observations"] = self.payload["observations"][:2]
        self.seal()
        self.assertEqual(self.verify()[1], "INCOMPLETE_RECOVERY_OBSERVATIONS")

    def test_path_traversal_service_id_refused_before_file_access(self):
        self.seal()
        self.assertEqual(self.verify(service="../llm-router")[1], "INVALID_SERVICE_ID")


if __name__ == "__main__":
    unittest.main()
