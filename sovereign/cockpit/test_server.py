"""Unit tests for sovereign.cockpit.server, run against a real socket on an
ephemeral loopback port. A does not need to have landed sovereign/engine/client.py
for this file to run: a fake client module is injected into sys.modules (and
set as the sovereign.engine.client attribute) before sovereign.cockpit.server is
imported, per CONTRACT.md's instruction to builder C. If sovereign/engine/client.py
is later on disk, THIS process still uses the fake, because sys.modules is a cache
keyed by name -- only a fresh interpreter would pick up the real one.

Run:  sovereign/.venv/bin/python -m unittest sovereign.cockpit.test_server -v
"""
from __future__ import annotations

import http.client
import json
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

# --- inject a fake sovereign.engine.client before importing the server -----
_SESSIONS = {
    "sb-aaaa1111": {
        "session_id": "sb-aaaa1111",
        "repo": "idp",
        "task": "sleep 60",
        "step": 2,
        "status": "running",
        "runner": "sleep",
        "asking": None,
        "started_at": "2026-08-25T00:00:00Z",
        "updated_at": "2026-08-25T00:00:01Z",
        "last_output": "",
        "line_message_id": None,
    },
    "sb-bbbb2222": {
        "session_id": "sb-bbbb2222",
        "repo": "idp",
        "task": "needs: approval",
        "step": 1,
        "status": "waiting",
        "runner": "ask",
        "asking": "approval",
        "started_at": "2026-08-25T00:00:00Z",
        "updated_at": "2026-08-25T00:00:01Z",
        "last_output": "",
        "line_message_id": None,
    },
}

_signals_received: list[tuple] = []


async def _fake_list_sessions():
    return list(_SESSIONS.values())


async def _fake_show(session_id):
    if session_id not in _SESSIONS:
        raise KeyError(f"no such session: {session_id}")
    return dict(_SESSIONS[session_id], stopped_by=None, reason=None, steps=[])


async def _fake_signal(session_id, kind, by, text=""):
    if session_id not in _SESSIONS:
        raise KeyError(f"no such session: {session_id}")
    _signals_received.append((session_id, kind, by, text))
    if kind == "stop":
        _SESSIONS[session_id]["status"] = "stopped"
    elif kind == "approve":
        _SESSIONS[session_id]["status"] = "done"
    elif kind == "deny":
        _SESSIONS[session_id]["status"] = "denied"
    return {"ok": True}


_fake_engine_client = types.ModuleType("sovereign.engine.client")
_fake_engine_client.list_sessions = _fake_list_sessions
_fake_engine_client.show = _fake_show
_fake_engine_client.signal = _fake_signal

sys.modules["sovereign.engine.client"] = _fake_engine_client
try:
    import sovereign.engine as _engine_pkg

    _engine_pkg.client = _fake_engine_client
except Exception:
    pass

from sovereign.cockpit import server  # noqa: E402  (must follow the injection above)

# Belt and braces: patch the name the module actually calls, in case this
# process had already imported a real (or no) sovereign.engine.client earlier.
server.engine_client = _fake_engine_client


class CockpitServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.inbox_path = Path(cls.tmpdir.name) / "inbox.jsonl"
        cls.inbox_path.write_text(
            '{"source": "healthchecks", "text": "prospector down"}\n'
            '{"source": "estate_alert", "text": "disk 91%"}\n'
        )
        cls._inbox_patch = mock.patch.object(server, "_inbox_path", lambda: cls.inbox_path)
        cls._inbox_patch.start()

        cls.httpd = server.build_server(port=0, bind="127.0.0.1")
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)
        cls._inbox_patch.stop()
        cls.tmpdir.cleanup()

    def _conn(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        self.addCleanup(conn.close)
        return conn

    def test_healthz(self):
        conn = self._conn()
        conn.request("GET", "/healthz")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.read(), b"ok")

    def test_index_served_at_root(self):
        conn = self._conn()
        conn.request("GET", "/")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        body = resp.read()
        self.assertIn(b"Otto", body)

    def test_session_page_serves_shell(self):
        conn = self._conn()
        conn.request("GET", "/s/sb-aaaa1111")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)

    def test_api_sessions_matches_fake_client(self):
        conn = self._conn()
        conn.request("GET", "/api/sessions")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        got = json.loads(resp.read())
        self.assertEqual({s["session_id"] for s in got}, set(_SESSIONS.keys()))

    def test_api_session_show(self):
        conn = self._conn()
        conn.request("GET", "/api/sessions/sb-aaaa1111")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        got = json.loads(resp.read())
        self.assertEqual(got["session_id"], "sb-aaaa1111")

    def test_api_session_show_unknown_is_404(self):
        conn = self._conn()
        conn.request("GET", "/api/sessions/sb-doesnotexist")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 404)

    def test_post_stop_signals_and_changes_status(self):
        conn = self._conn()
        body = json.dumps({"by": "founder"})
        conn.request("POST", "/api/sessions/sb-aaaa1111/stop", body=body)
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertIn(("sb-aaaa1111", "stop", "founder", ""), _signals_received)

        conn2 = self._conn()
        conn2.request("GET", "/api/sessions/sb-aaaa1111")
        got = json.loads(conn2.getresponse().read())
        self.assertEqual(got["status"], "stopped")

    def test_post_approve_decision(self):
        conn = self._conn()
        body = json.dumps({"by": "founder"})
        conn.request("POST", "/api/sessions/sb-bbbb2222/approve", body=body)
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertIn(("sb-bbbb2222", "approve", "founder", ""), _signals_received)

    def test_api_inbox_returns_lines_newest_first(self):
        conn = self._conn()
        conn.request("GET", "/api/inbox")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        got = json.loads(resp.read())
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0]["text"], "disk 91%")  # newest line first

    def test_bad_init_data_from_loopback_is_401(self):
        conn = self._conn()
        conn.request(
            "GET", "/api/sessions",
            headers={"X-Telegram-Init-Data": "user=x&hash=not-a-real-signature"},
        )
        resp = conn.getresponse()
        self.assertEqual(resp.status, 401)
        resp.read()

    def test_no_init_data_from_loopback_is_allowed(self):
        conn = self._conn()
        conn.request("GET", "/api/sessions")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        resp.read()

    def test_unknown_route_is_404(self):
        conn = self._conn()
        conn.request("GET", "/api/nope")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 404)
        resp.read()

    def test_api_config_returns_cockpit_keys(self):
        # cp22: the page's poll interval and labels come from this endpoint,
        # not a literal in index.html.
        conn = self._conn()
        conn.request("GET", "/api/config")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        got = json.loads(resp.read())
        self.assertEqual(got["cockpit.poll_s"], 3)
        self.assertEqual(got["cockpit.inbox_tail"], 200)
        self.assertIn("telegram.api_base", got)
        for key in got:
            self.assertFalse(key.upper().endswith(("TOKEN", "KEY", "SECRET")))


if __name__ == "__main__":
    unittest.main()
