"""Gemini Drive intake is a quarantine boundary, not an actuator."""
import importlib.util
import json
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "bin" / "genesis_drive_intake.py"
spec = importlib.util.spec_from_file_location("genesis_drive_intake", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def valid():
    return {"schema_version": 1, "event_id": "event-12345",
            "source": "gemini-web-drive", "source_sha256": "a" * 64,
            "document_id": "document-1234", "target_repo": "chidionyema/idp",
            "intent": "review-only"}

class IntakeTests(unittest.TestCase):
    def test_accepts_only_quarantined_review(self):
        self.assertEqual(mod.validate(json.dumps(valid()).encode())["status"],
                         "QUARANTINED_REVIEW_ONLY")

    def test_rejects_privileged_intents(self):
        for intent in ("merge", "rotate-secret", "workflow_dispatch", "shell", "approve"):
            obj = valid()
            obj["intent"] = intent
            with self.subTest(intent=intent), self.assertRaises(ValueError):
                mod.validate(json.dumps(obj).encode())

    def test_rejects_unknown_fields(self):
        obj = valid()
        obj["command"] = "echo unsafe"
        with self.assertRaises(ValueError):
            mod.validate(json.dumps(obj).encode())

    def test_rejects_oversize(self):
        with self.assertRaises(ValueError):
            mod.validate(b"x" * (mod.MAX_BYTES + 1))

    def test_rejects_bad_digests(self):
        obj = valid()
        obj["source_sha256"] = "not-a-digest"
        with self.assertRaises(ValueError):
            mod.validate(json.dumps(obj).encode())

    def test_rejects_untrusted_repos(self):
        obj = valid()
        obj["target_repo"] = "attacker/other"
        with self.assertRaises(ValueError):
            mod.validate(json.dumps(obj).encode())

    def test_deterministic_receipt(self):
        obj = valid()
        a = mod.validate(json.dumps(obj).encode())
        b = mod.validate(json.dumps(obj, sort_keys=True).encode())
        self.assertEqual(a["envelope_sha256"], b["envelope_sha256"])

    def test_rejects_array(self):
        with self.assertRaises(ValueError):
            mod.validate(b"[]")

if __name__ == "__main__":
    unittest.main()
