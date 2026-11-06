"""Prove GitHub receipt reporting cannot turn untrusted metadata into execution."""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "bin" / "genesis_drive_receipt_issue.py"
spec = importlib.util.spec_from_file_location("genesis_drive_receipt_issue", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def receipt():
    return {"status": "QUARANTINED_AUTHENTICATED_REVIEW_ONLY",
            "target_repo": "chidionyema/idp", "event_id": "gemini-123456789abc",
            "source_sha256": "a" * 64, "document_ref_sha256": "b" * 64,
            "envelope_sha256": "c" * 64}


class StubApi:
    def __init__(self, comments=None):
        self.comments = list(comments or [])
        self.posts = []
    def __call__(self, method, path, payload, token):
        assert token == "dummy-test-token"
        if method == "GET":
            return list(self.comments) if "page=1" in path else []
        assert method == "POST" and "/comments" in path
        self.posts.append(payload["body"])
        return {"id": 112233}


class ReceiptTests(unittest.TestCase):
    def test_posts_fixed_bound_review_only_fields(self):
        api = StubApi()
        result = mod.publish(receipt(), 12345, "dummy-test-token", api)
        self.assertEqual(result["status"], "RECORDED_QUARANTINED")
        self.assertEqual(len(api.posts), 1)
        self.assertNotIn("document_id", api.posts[0])
        self.assertIn("QUARANTINED", api.posts[0])

    def test_duplicate_authenticated_bot_comment_is_idempotent(self):
        clean = mod.checked_receipt(receipt())
        api = StubApi([{"id": 42, "user": {"login": "github-actions[bot]"},
                        "body": mod.make_body(clean, 9876)}])
        result = mod.publish(receipt(), 12345, "dummy-test-token", api)
        self.assertEqual(result["status"], "ALREADY_RECORDED")
        self.assertEqual(api.posts, [])

    def test_external_comment_cannot_spoof_ack(self):
        clean = mod.checked_receipt(receipt())
        api = StubApi([{"id": 42, "user": {"login": "attacker"},
                        "body": mod.make_body(clean, 9876)}])
        self.assertEqual(mod.publish(receipt(), 12345, "dummy-test-token", api)["status"],
                         "RECORDED_QUARANTINED")

    def test_conflicting_signed_event_is_rejected(self):
        clean = mod.checked_receipt(receipt())
        modified = receipt()
        modified["source_sha256"] = "f" * 64
        api = StubApi([{"user": {"login": "github-actions[bot]"},
                        "body": mod.make_body(mod.checked_receipt(modified), 9876)}])
        with self.assertRaisesRegex(RuntimeError, "conflict"):
            mod.publish(receipt(), 12345, "dummy-test-token", api)

    def test_absent_gh_token_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "token"):
            mod.publish(receipt(), 12345, "", StubApi())

    def test_invalid_receipt_cannot_publish(self):
        for mutation in ({"status": "APPROVED"}, {"event_id": "unsafe\nline"},
                         {"source_sha256": "invalid"},
                         {"target_repo": "attacker/repo"},
                         {"document_ref_sha256": ""}):
            wrong = receipt()
            wrong.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                mod.publish(wrong, 12345, "dummy-test-token", StubApi())

    def test_pagination_overflow_fails_closed(self):
        class FullPages(StubApi):
            def __call__(self, method, path, payload, token):
                if method == "GET":
                    return [{"user": {"login": "other"}, "body": "unrelated"}] * 100
                return super().__call__(method, path, payload, token)
        with self.assertRaisesRegex(RuntimeError, "pagination"):
            mod.publish(receipt(), 12345, "dummy-test-token", FullPages())


if __name__ == "__main__":
    unittest.main()
