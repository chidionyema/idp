"""Fail-closed E1-E4 founder transport send-boundary falsifiers (#8478)."""

import unittest
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from lib.founder_admission import (
    AdmissionDenied,
    _canonical,
    admit,
    digest,
    preserve_instruction,
    send_checked,
)

NOW = datetime(2026, 11, 23, 20, 6, 0, tzinfo=timezone.utc)
REV = "a" * 40
EVIDENCE = "TIER_0_RAW_MACHINE_RECEIPT"
RUNTIME = "PLANE_PRODUCTION_RUNTIME"


class FounderAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.keys = {
            role: Ed25519PrivateKey.generate()
            for role in (
                "discovery",
                "execution",
                "effect",
                "independent_verification",
                "certifier",
            )
        }
        self.roots = {
            k: {
                "role": k,
                "control_plane": "isolated-" + k,
                "public_key_hex": v.public_key()
                .public_bytes(
                    serialization.Encoding.Raw, serialization.PublicFormat.Raw
                )
                .hex(),
            }
            for k, v in self.keys.items()
        }
        self.instruction = b"Founder original instruction MUST be byte-preserved."
        self.binding = {
            "instruction_id": "FIR-08",
            "obligation_id": "ob-8478",
            "claim_id": "claim-p1p2p3",
            "actor_id": "agent-mission-12",
            "target": "https://example.org/health",
            "revision": REV,
            "environment": "production",
            "observation_window": {
                "start": "2026-11-23T19:00:00Z",
                "end": "2026-11-23T21:00:00Z",
            },
        }
        self.claim = dict(
            self.binding,
            expected_http_status=200,
            expected_body="verified-runtime",
            original_instruction_bytes=self.instruction,
            original_instruction_sha256=digest(self.instruction),
        )
        self.data = {}
        self.discovery = self.sign(
            "discovery",
            dict(
                self.binding,
                searched_sources=["estate-graph", "production-runtime", "claims"],
                contradictions=[],
                observed_at="2026-11-23T20:05:00Z",
                expires_at="2026-11-23T20:50:00Z",
            ),
        )
        self.proofs = []
        for role in ("execution", "effect", "independent_verification"):
            uri = "https://evidence.example.org/receipts/" + role
            doc = (
                dict(
                    actor_id=self.binding["actor_id"],
                    operation="PATCH authenticated workflow",
                    output_sha256="b" * 64,
                )
                if role == "execution"
                else dict(
                    target=self.binding["target"],
                    revision=REV,
                    status=200,
                    body="verified-runtime exact revision",
                )
            )
            raw = _canonical(doc)
            self.data[uri] = raw
            self.proofs.append(
                self.sign(
                    role,
                    dict(
                        self.binding,
                        capture_authority=role,
                        tier=EVIDENCE,
                        plane="PLANE_CONTROL_AUTH" if role == "execution" else RUNTIME,
                        observed_at="2026-11-23T20:05:00Z",
                        expires_at="2026-11-23T20:50:00Z",
                        evidence_uri=uri,
                        evidence_digest=digest(raw),
                    ),
                )
            )
        self.refresh_certificate()
        self.sent = []
        self.denied = []

    def sign(self, role, payload):
        return dict(
            key_id=role,
            payload=payload,
            signature_hex=self.keys[role].sign(_canonical(payload)).hex(),
        )

    def refresh_certificate(self):
        raw = {
            k: v
            for k, v in self.claim.items()
            if k not in {"certificate", "original_instruction_bytes"}
        }
        certificate = dict(
            self.binding,
            decision="ALLOW",
            observed_at="2026-11-23T20:05:00Z",
            expires_at="2026-11-23T20:50:00Z",
            claim_digest=digest(_canonical(raw)),
            discovery_digest=digest(_canonical(self.discovery["payload"])),
            proof_digests=sorted(digest(_canonical(p["payload"])) for p in self.proofs),
        )
        self.claim["certificate"] = self.sign("certifier", certificate)

    def check(self):
        admit(
            self.claim,
            self.discovery,
            self.proofs,
            now=NOW,
            trust_roots=self.roots,
            read_evidence=lambda uri: self.data[uri],
        )

    def send(self):
        return send_checked(
            self.sent.append,
            b"AUTOMATED status",
            self.claim,
            self.discovery,
            self.proofs,
            now=NOW,
            trust_roots=self.roots,
            read_evidence=lambda uri: self.data[uri],
            conserve_obligation=self.denied.append,
        )

    def test_valid_independently_verified_three_proofs(self):
        self.check()

    def test_valid_actual_transport_send_once(self):
        self.send()
        self.assertEqual(self.sent, [b"AUTOMATED status"])
        self.assertEqual(self.denied, [])

    def test_missing_observer_refuses_even_with_valid_signatures(self):
        with self.assertRaisesRegex(AdmissionDenied, "no-independent-evidence-reader"):
            admit(
                self.claim, self.discovery, self.proofs, now=NOW, trust_roots=self.roots
            )

    def test_missing_obligation_sink_refuses_before_send(self):
        with self.assertRaisesRegex(
            AdmissionDenied, "no-durable-obligation-conservation"
        ):
            send_checked(
                self.sent.append,
                b"status",
                self.claim,
                self.discovery,
                self.proofs,
                now=NOW,
                trust_roots=self.roots,
                read_evidence=lambda uri: self.data[uri],
                conserve_obligation=None,
            )
        self.assertEqual(self.sent, [])

    def test_denied_transport_conserves_original_obligation(self):
        self.proofs.pop()
        with self.assertRaisesRegex(AdmissionDenied, "three-proofs-required"):
            self.send()
        self.assertEqual(self.sent, [])
        self.assertEqual(self.denied[0]["obligation_id"], "ob-8478")
        self.assertEqual(self.denied[0]["verdict"], "DENY")

    def test_agent_verified_flag_cannot_substitute_for_signature(self):
        self.proofs[1]["signature_hex"] = "00" * 64
        self.proofs[1]["verified"] = True
        with self.assertRaisesRegex(AdmissionDenied, "invalid-signature"):
            self.check()

    def test_tier2_laundered_agent_inference_refused(self):
        self.proofs[1] = self.sign(
            "effect", dict(self.proofs[1]["payload"], tier="TIER_2_AGENT_INFERENCE")
        )
        with self.assertRaisesRegex(AdmissionDenied, "epistemic-laundering"):
            self.check()

    def test_same_cryptographic_key_with_distinct_labels_refused(self):
        pub = self.roots["effect"]["public_key_hex"]
        self.roots["independent_verification"]["public_key_hex"] = pub
        self.keys["independent_verification"] = self.keys["effect"]
        self.proofs[2] = self.sign(
            "independent_verification", self.proofs[2]["payload"]
        )
        with self.assertRaisesRegex(AdmissionDenied, "correlated-evidence-custody"):
            self.check()

    def test_same_control_plane_with_separate_keys_refused(self):
        self.roots["independent_verification"]["control_plane"] = self.roots["effect"][
            "control_plane"
        ]
        with self.assertRaisesRegex(AdmissionDenied, "correlated-evidence-custody"):
            self.check()

    def test_source_as_effect_refused(self):
        self.proofs[1] = self.sign(
            "effect", dict(self.proofs[1]["payload"], plane="PLANE_SOURCE_FLOW")
        )
        with self.assertRaisesRegex(AdmissionDenied, "proxy-green-substitution"):
            self.check()

    def test_source_host_as_operational_target_refused(self):
        self.claim["target"] = (
            "https://raw.githubusercontent.com/chidionyema/idp/main/sentinel"
        )
        with self.assertRaisesRegex(AdmissionDenied, "invalid-runtime-target"):
            self.check()

    def test_wrong_live_revision_refused(self):
        uri = self.proofs[2]["payload"]["evidence_uri"]
        self.data[uri] = _canonical(
            dict(
                target=self.binding["target"],
                revision="b" * 40,
                status=200,
                body="verified-runtime",
            )
        )
        p = dict(self.proofs[2]["payload"], evidence_digest=digest(self.data[uri]))
        self.proofs[2] = self.sign("independent_verification", p)
        with self.assertRaisesRegex(AdmissionDenied, "runtime-effect-contradicted"):
            self.check()

    def test_http_525_refused(self):
        uri = self.proofs[1]["payload"]["evidence_uri"]
        self.data[uri] = _canonical(
            dict(
                target=self.binding["target"],
                revision=REV,
                status=525,
                body="handshake failed",
            )
        )
        self.proofs[1] = self.sign(
            "effect",
            dict(self.proofs[1]["payload"], evidence_digest=digest(self.data[uri])),
        )
        with self.assertRaisesRegex(AdmissionDenied, "runtime-effect-contradicted"):
            self.check()

    def test_payload_tampering_refused(self):
        uri = self.proofs[2]["payload"]["evidence_uri"]
        self.data[uri] = b'{"status":200,"tampered":true}'
        with self.assertRaisesRegex(AdmissionDenied, "evidence-digest-mismatch"):
            self.check()

    def test_stale_receipt_refused(self):
        self.proofs[0] = self.sign(
            "execution",
            dict(self.proofs[0]["payload"], expires_at="2026-11-23T19:00:00Z"),
        )
        with self.assertRaisesRegex(AdmissionDenied, "stale-future-or-out-of-window"):
            self.check()

    def test_future_receipt_refused(self):
        self.proofs[0] = self.sign(
            "execution",
            dict(self.proofs[0]["payload"], observed_at="2026-11-23T20:30:00Z"),
        )
        with self.assertRaisesRegex(AdmissionDenied, "stale-future-or-out-of-window"):
            self.check()

    def test_tampered_original_founder_bytes_refused(self):
        self.claim["original_instruction_bytes"] = b"altered founder text"
        with self.assertRaisesRegex(AdmissionDenied, "instruction-integrity"):
            self.check()

    def test_changed_claim_after_certification_refused(self):
        self.claim["expected_body"] = "new expected output"
        with self.assertRaisesRegex(
            AdmissionDenied, "runtime-effect-contradicted|certificate-evidence-mismatch"
        ):
            self.check()

    def test_absent_falsification_hypotheses_refused(self):
        self.claim["diagnosis"] = dict(
            observed_scope="job_env", asserted_scope="estate_global"
        )
        with self.assertRaisesRegex(AdmissionDenied, "no-competing-hypotheses"):
            self.check()

    def test_scope_leaping_global_secret_absence_refused(self):
        self.claim["diagnosis"] = dict(
            observed_scope="job_env",
            asserted_scope="estate_global",
            competing_hypotheses=[
                dict(
                    statement="secret absent",
                    falsified_by="vault presence",
                    discriminating_probe="vault status",
                ),
                dict(
                    statement="secret only in vault",
                    falsified_by="repo secret presence",
                    discriminating_probe="repo status",
                ),
            ],
        )
        with self.assertRaisesRegex(AdmissionDenied, "scope-leaping-negation"):
            self.check()

    def test_mutation_without_discriminator_refused(self):
        self.claim["requests_mutation"] = True
        self.claim["diagnosis"] = dict(
            observed_scope="job_env",
            asserted_scope="job_env",
            competing_hypotheses=[
                dict(
                    statement="lost credential",
                    falsified_by="vault presence",
                    discriminating_probe="vault probe",
                ),
                dict(
                    statement="bad route",
                    falsified_by="edge healthy",
                    discriminating_probe="edge probe",
                ),
            ],
        )
        with self.assertRaisesRegex(AdmissionDenied, "mutation-before-discrimination"):
            self.check()

    def test_duplicate_signed_evidence_uri_refused(self):
        p = dict(
            self.proofs[2]["payload"],
            evidence_uri=self.proofs[1]["payload"]["evidence_uri"],
        )
        self.proofs[2] = self.sign("independent_verification", p)
        with self.assertRaisesRegex(AdmissionDenied, "duplicate-evidence-lineage"):
            self.check()

    def test_missing_certificate_refused(self):
        self.claim.pop("certificate")
        with self.assertRaisesRegex(AdmissionDenied, "missing-signed-envelope"):
            self.check()

    def test_missing_discovery_refused(self):
        self.discovery = {}
        with self.assertRaisesRegex(AdmissionDenied, "malformed-signed-envelope"):
            self.check()

    def test_unknown_root_refused(self):
        self.roots.pop("effect")
        with self.assertRaisesRegex(AdmissionDenied, "untrusted-role"):
            self.check()


if __name__ == "__main__":
    unittest.main()
