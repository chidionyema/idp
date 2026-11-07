"""Negative tests for the existing memory/topology ACK trust boundary.

Uses ephemeral Ed25519 keys and deterministic timestamps; never represents
live agent, estate-graph or cloud admission certification.
"""
from __future__ import annotations

import base64
import importlib.util
import json
import pathlib
import sys
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

SOURCE = (
    pathlib.Path(__file__).resolve().parents[1] /
    "platform/estate/memory/context_admission.py"
)
spec = importlib.util.spec_from_file_location("context_admission_under_test", SOURCE)
ctx = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ctx
spec.loader.exec_module(ctx)


class ContextAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.issuer = Ed25519PrivateKey.generate()
        self.public = self.issuer.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.now = 5000
        self.data = {
            "schema": ctx.SCHEMA,
            "source": "estate-graph",
            "actor": "agent-kimi",
            "mission": "idp-6156",
            "session": "sess-1",
            "lease_epoch": 3,
            "sequence": 8,
            "memory_sha256": "a" * 64,
            "topology_sha256": "b" * 64,
            "source_commit": "c" * 40,
            "source_observed_at": 4970,
            "issued_at": 4975,
            "acknowledged_at": 4980,
            "expires_at": 5060,
            "readiness": "STRICT_READY",
        }
        self.expected = {
            "public_key": self.public,
            "actor": "agent-kimi",
            "mission": "idp-6156",
            "session": "sess-1",
            "epoch": 3,
            "min_sequence": 8,
            "memory_sha256": "a" * 64,
            "topology_sha256": "b" * 64,
            "source_commit": "c" * 40,
            "now": self.now,
        }

    def signed(self, *, signer=None, payload=None):
        raw = ctx.canonical(self.data if payload is None else payload)
        signature = (signer or self.issuer).sign(raw)
        return json.dumps({
            "format": "genesis.context.ed25519.v1",
            "payload_b64": base64.b64encode(raw).decode(),
            "signature_b64": base64.b64encode(signature).decode(),
        }).encode()

    def check(self, payload=None, **expected):
        data = dict(self.expected, **expected)
        return ctx.verify(self.signed(payload=payload), **data)

    def test_fresh_exact_context_ack_is_accepted(self):
        result = self.check()
        self.assertTrue(result.admitted)
        self.assertEqual(result.reason, "CONTEXT_ACK_VERIFIED")
        self.assertEqual(len(result.receipt_digest), 64)

    def test_missing_ack_is_refused(self):
        self.assertFalse(ctx.verify(b"", **self.expected).admitted)

    def test_empty_certifier_root_is_refused(self):
        self.assertEqual(self.check(public_key=b"").reason,
                         "CONTEXT_CERTIFIER_UNAVAILABLE")

    def test_forged_signature_does_not_work(self):
        foreign = Ed25519PrivateKey.generate()
        result = ctx.verify(self.signed(signer=foreign), **self.expected)
        self.assertEqual(result.reason, "CONTEXT_SIGNATURE_UNVERIFIED")

    def test_wrong_actor_is_refused(self):
        self.assertEqual(self.check(actor="agent-gemini").reason,
                         "CONTEXT_ACK_WRONG_AGENT_OR_MISSION")

    def test_wrong_mission_is_refused(self):
        self.assertEqual(self.check(mission="idp-7790").reason,
                         "CONTEXT_ACK_WRONG_AGENT_OR_MISSION")

    def test_session_replay_is_refused(self):
        self.assertEqual(self.check(session="other-session").reason,
                         "CONTEXT_ACK_WRONG_AGENT_OR_MISSION")

    def test_expired_worker_lease_is_refused(self):
        self.assertEqual(self.check(epoch=4).reason, "CONTEXT_LEASE_STALE")

    def test_topology_drift_is_refused(self):
        self.assertEqual(self.check(topology_sha256="d"*64).reason,
                         "CONTEXT_CHANGED_SINCE_ACK")

    def test_memory_drift_is_refused(self):
        self.assertEqual(self.check(memory_sha256="d"*64).reason,
                         "CONTEXT_CHANGED_SINCE_ACK")

    def test_source_head_drift_is_refused(self):
        self.assertEqual(self.check(source_commit="d"*40).reason,
                         "CONTEXT_CHANGED_SINCE_ACK")

    def test_downgraded_delivery_sequence_is_refused(self):
        self.assertEqual(self.check(min_sequence=9).reason, "CONTEXT_ACK_REPLAY")

    def test_stale_memory_is_refused_even_with_valid_signature(self):
        self.assertEqual(self.check(now=5121).reason,
                         "CONTEXT_STALE_OR_OUT_OF_ORDER")

    def test_expired_receipt_is_refused_even_with_fresh_source(self):
        self.assertEqual(self.check(now=5060).reason, "CONTEXT_ACK_EXPIRED")

    def test_clock_regression_or_future_timestamp_refused(self):
        self.assertEqual(self.check(now=4960).reason,
                         "CONTEXT_RECEIPT_FROM_FUTURE")

    def test_unready_graph_is_refused(self):
        p = dict(self.data, readiness="WARN")
        self.assertEqual(self.check(payload=p).reason, "ESTATE_GRAPH_NOT_READY")

    def test_untrusted_authority_is_refused(self):
        p = dict(self.data, source="browser-self-assertion")
        self.assertEqual(self.check(payload=p).reason, "WRONG_CONTEXT_AUTHORITY")

    def test_boolean_lease_epoch_is_not_accepted(self):
        p = dict(self.data, lease_epoch=True)
        self.assertEqual(self.check(payload=p).reason, "CONTEXT_LEASE_STALE")

    def test_boolean_timestamp_is_not_accepted(self):
        p = dict(self.data, issued_at=True)
        self.assertEqual(self.check(payload=p).reason,
                         "INVALID_DELIVERY_SEQUENCE_OR_TIME")

    def test_self_extended_expiry_is_refused(self):
        p = dict(self.data, expires_at=9999)
        self.assertEqual(self.check(payload=p).reason, "CONTEXT_ACK_EXPIRED")

    def test_signature_is_bound_to_exact_payload(self):
        raw = json.loads(self.signed())
        obj = json.loads(base64.b64decode(raw["payload_b64"]))
        obj["topology_sha256"] = "f" * 64
        raw["payload_b64"] = base64.b64encode(ctx.canonical(obj)).decode()
        got = ctx.verify(json.dumps(raw).encode(), **self.expected)
        self.assertEqual(got.reason, "CONTEXT_SIGNATURE_UNVERIFIED")

    def test_unexpected_fields_refused_even_when_signed(self):
        p = dict(self.data, ignore_previous_instructions=True)
        self.assertEqual(self.check(payload=p).reason, "NONCANONICAL_CONTEXT")

    def test_invalid_relay_envelope_refused(self):
        self.assertEqual(ctx.verify(b'{"source":"gemini"}', **self.expected).reason,
                         "MALFORMED_CONTEXT_ENVELOPE")


if __name__ == "__main__":
    unittest.main()
