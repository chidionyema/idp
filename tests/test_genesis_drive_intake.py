"""Security regression tests: Gemini Web Drive is a signed data lane, never an actuator."""
import hashlib
import hmac
import importlib.util
import json
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "bin" / "genesis_drive_intake.py"
spec = importlib.util.spec_from_file_location("genesis_drive_intake", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
KEY = "testing-gemini-web-drive-verification-key-32bytes"


def valid():
    obj = {
        "schema_version": 1, "event_id": "gemini-123456789abcd",
        "source": "gemini-web-drive", "source_sha256": "a" * 64,
        "document_id": "document-1234", "target_repo": "chidionyema/idp",
        "intent": "review-only", "issued_at": 1_000_000,
    }
    return sign(obj)


def sign(obj, key=KEY):
    o = dict(obj)
    o.pop("signature", None)
    o["signature"] = hmac.new(key.encode(), mod.signing_bytes(o), hashlib.sha256).hexdigest()
    return o


def evaluate(obj, key=KEY, now=1_000_000):
    return mod.validate(json.dumps(obj).encode(), key=key, now=now)


class IntakeTests(unittest.TestCase):
    def test_accepts_authenticated_quarantined_review_only(self):
        self.assertEqual(evaluate(valid())["status"], "QUARANTINED_AUTHENTICATED_REVIEW_ONLY")

    def test_rejects_privileged_intents_even_if_signed(self):
        for intent in ("merge", "rotate-secret", "workflow_dispatch", "shell", "approve"):
            obj = valid()
            obj["intent"] = intent
            with self.subTest(intent=intent), self.assertRaises(ValueError):
                evaluate(sign(obj))

    def test_rejects_unknown_fields(self):
        obj = valid()
        obj["command"] = "echo unsafe"
        with self.assertRaisesRegex(ValueError, "fields"):
            evaluate(obj)

    def test_rejects_oversize(self):
        with self.assertRaisesRegex(ValueError, "large"):
            mod.validate(b"x" * (mod.MAX_BYTES + 1), key=KEY, now=1_000_000)

    def test_rejects_bad_digests(self):
        obj = valid()
        obj["source_sha256"] = "not-a-digest"
        with self.assertRaises(ValueError):
            evaluate(obj)

    def test_rejects_untrusted_repos(self):
        obj = valid()
        obj["target_repo"] = "attacker/other"
        with self.assertRaises(ValueError):
            evaluate(sign(obj))

    def test_deterministic_envelope_receipt(self):
        obj = valid()
        a = mod.validate(json.dumps(obj).encode(), key=KEY, now=1_000_000)
        b = mod.validate(json.dumps(obj, sort_keys=True).encode(), key=KEY, now=1_000_000)
        self.assertEqual(a["envelope_sha256"], b["envelope_sha256"])

    def test_rejects_duplicate_json_members(self):
        obj = valid()
        raw = json.dumps(obj).replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1', 1)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            mod.validate(raw.encode(), key=KEY, now=1_000_000)

    def test_receipt_binds_exact_drive_document(self):
        obj = valid()
        receipt = evaluate(obj)
        self.assertNotIn("document_id", receipt)  # Private Drive ID must not leak to public CI logs.
        self.assertEqual(receipt["source_sha256"], obj["source_sha256"])
        modified = dict(obj)
        modified["document_id"] = "different-private-file-id"
        with self.assertRaisesRegex(ValueError, "signature"):
            evaluate(modified)

    def test_rejects_array(self):
        with self.assertRaises(ValueError):
            mod.validate(b"[]", key=KEY, now=1_000_000)

    def test_wrong_signer(self):
        with self.assertRaisesRegex(ValueError, "signature"):
            evaluate(valid(), key="different-signer-key-long-enough-for-testing")

    def test_tampering_after_signature(self):
        obj = valid()
        obj["source_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "signature"):
            evaluate(obj)

    def test_rejects_timestamp_backdating_and_future(self):
        for instant in (1_000_901, 999_099):
            with self.subTest(instant=instant), self.assertRaisesRegex(ValueError, "timestamp"):
                evaluate(valid(), now=instant)

    def test_rejects_boolean_timestamp(self):
        obj = valid()
        obj["issued_at"] = True
        with self.assertRaisesRegex(ValueError, "timestamp"):
            evaluate(obj)

    def test_rejects_missing_or_weak_key(self):
        for key in ("", "short"):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "key"):
                evaluate(valid(), key=key)

    def test_rejects_signature_with_wrong_shape(self):
        obj = valid()
        obj["signature"] = "bad"
        with self.assertRaises(ValueError):
            evaluate(obj)

    def test_does_not_accept_an_automatic_deploy_request(self):
        obj = valid()
        obj["intent"] = "deploy"
        with self.assertRaisesRegex(ValueError, "privileged"):
            evaluate(sign(obj))


if __name__ == "__main__":
    unittest.main()
