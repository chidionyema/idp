#!/usr/bin/env python3
"""Offline falsifiers for bin/omniflow-github-relay. No network, secrets or services."""
import importlib.machinery
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

PATH = pathlib.Path(__file__).resolve().parents[1] / "bin" / "omniflow-github-relay"
loader = importlib.machinery.SourceFileLoader("omniflow_relay", str(PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
relay = importlib.util.module_from_spec(spec)
loader.exec_module(relay)


class FakeGitHub:
    repo = "example/repo"
    def __init__(self, comments):
        self.comments = comments
        self.pages = []
    def fetch_page(self, issue, page, per_page=100):
        self.pages.append(page)
        return self.comments[(page - 1) * per_page:page * per_page]


def item(i, event):
    return {"id": i, "body": relay.PREFIX + relay.canonical(event),
            "user": {"login": "attacker-controlled-display"}}


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cursor = relay.Cursor(os.path.join(self.temp.name, "cursor.sqlite"))
        self.event = relay.make_event("mission-1", "agent-a", "ASK", {"text": "hello"})

    def tearDown(self):
        self.cursor.db.close()
        self.temp.cleanup()

    def test_valid_round_trip(self):
        self.assertEqual(relay.parse_comment(relay.PREFIX + relay.canonical(self.event)), self.event)

    def test_rejects_tamper(self):
        forged = dict(self.event)
        forged["payload"] = {"text": "changed"}
        with self.assertRaisesRegex(ValueError, "digest"):
            relay.validate(forged)

    def test_rejects_forged_authority(self):
        forged = dict(self.event)
        forged["tenant_id"] = "victim"
        with self.assertRaisesRegex(ValueError, "unexpected"):
            relay.validate(forged)

    def test_rejects_extra_privilege_field(self):
        forged = dict(self.event)
        forged["approved"] = True
        with self.assertRaises(ValueError):
            relay.validate(forged)

    def test_rejects_oversize(self):
        with self.assertRaises(ValueError):
            relay.make_event("m", "a", "ASK", {"text": "x" * 5000})

    def test_rejects_unsupported_type(self):
        with self.assertRaises(ValueError):
            relay.make_event("m", "a", "EXECUTE", {"text": "do unsafe work"})

    def test_deduplicates_cursor(self):
        github = FakeGitHub([item(1, self.event)])
        seen = []
        self.assertEqual(relay.drain(github, 7, self.cursor, lambda e, m: seen.append(e)), 1)
        self.assertEqual(relay.drain(github, 7, self.cursor, lambda e, m: seen.append(e)), 0)
        self.assertEqual(len(seen), 1)

    def test_handler_failure_keeps_cursor(self):
        github = FakeGitHub([item(10, self.event)])
        with self.assertRaisesRegex(RuntimeError, "handler broke"):
            relay.drain(github, 7, self.cursor,
                        lambda e, m: (_ for _ in ()).throw(RuntimeError("handler broke")))
        self.assertEqual(self.cursor.last(github.repo, 7), 0)
        self.assertEqual(relay.drain(github, 7, self.cursor, lambda e, m: None), 1)

    def test_non_event_comment_skipped(self):
        github = FakeGitHub([{"id": 1, "body": "human conversation"}, item(2, self.event)])
        self.assertEqual(relay.drain(github, 7, self.cursor, lambda e, m: None), 1)
        self.assertEqual(self.cursor.last(github.repo, 7), 2)

    def test_malformed_event_blocks_progress(self):
        github = FakeGitHub([{"id": 1, "body": relay.PREFIX + "{not-json"}, item(2, self.event)])
        with self.assertRaisesRegex(RuntimeError, "quarantined"):
            relay.drain(github, 7, self.cursor, lambda e, m: None)
        self.assertEqual(self.cursor.last(github.repo, 7), 0)

    def test_conflicting_event_id_rejected(self):
        self.cursor.accept("example/repo", 7, 1, self.event)
        other = relay.make_event("mission-1", "agent-a", "ASK", {"text": "different"})
        other["event_id"] = self.event["event_id"]
        with self.assertRaisesRegex(ValueError, "conflicting"):
            self.cursor.accept("example/repo", 7, 2, other)
        self.assertEqual(self.cursor.last("example/repo", 7), 1)

    def test_expired_skipped(self):
        e = dict(self.event)
        e["created_at"] = "2020-01-01T00:00:00+00:00"
        e["expires_at"] = "2020-01-01T00:00:01+00:00"
        self.assertEqual(relay.drain(FakeGitHub([item(1, e)]), 7, self.cursor, lambda e, m: self.fail("expired delivered")), 0)

    def test_100_item_pagination(self):
        events = [item(i, relay.make_event("m", "a", "NOTIFY", {"index": i})) for i in range(1, 102)]
        github = FakeGitHub(events)
        seen = []
        self.assertEqual(relay.drain(github, 7, self.cursor, lambda e, m: seen.append(e)), 101)
        self.assertEqual(github.pages, [1, 2])

    def test_repo_validation(self):
        with self.assertRaises(ValueError):
            relay.GitHub("https://evil/repo", token="test")
        with self.assertRaises(ValueError):
            relay.GitHub("example/repo/extra", token="test")

    def test_author_is_not_identity(self):
        github = FakeGitHub([item(1, self.event)])
        seen = []
        relay.drain(github, 7, self.cursor, lambda e, m: seen.append(m))
        self.assertEqual(seen[0]["github_author"], "attacker-controlled-display")
        self.assertEqual(self.event["actor_label"], "agent-a")
        # Neither field is an authenticated principal or an authorization grant.

if __name__ == "__main__":
    unittest.main()
