"""The catalogue leg of the voice battery fails on the failure that actually happened.

2026-10-24: `GET /api/proxy/fleetview/voice/intents` answered non-200 in production, so the
Face's command deck went empty while every other leg of `bin/idp-verify-surfaces --post` stayed
green -- /healthz answered, a real conversation still ran, voice still sounded fine. The battery
graded everything except the one list the whole deck is built from, and nothing noticed for a day.

These tests exist because a leg that cannot go red is not a leg. Each one pins a way the
catalogue can be wrong while the HTTP status is still 200 -- an empty deck, a flag the ladder
reads that is missing, a ladder that has inverted to all-read or collapsed to all-mutate -- and
proves the leg says FAIL, and that `main` turns that FAIL into a non-zero exit the battery sees.
"""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from probes import voice  # noqa: E402


class _Stub(BaseHTTPRequestHandler):
    """A backend that answers healthz 200 and whatever the test wants /voice/intents to be."""

    catalogue_status = 200
    catalogue_body = b""
    seen: list[str] = []

    def do_GET(self):  # noqa: N802
        type(self).seen.append(self.path)
        if self.path == "/healthz":
            self._send(200, b'{"ok":true}')
            return
        if self.path == voice.CATALOGUE_PATH:
            self._send(self.catalogue_status, self.catalogue_body)
            return
        self._send(404, b"{}")

    def do_POST(self):  # noqa: N802
        self._send(500, b"{}")

    def _send(self, status: int, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # silence
        pass


def _serve(status=200, body=b"", monkeypatch=None):
    _Stub.catalogue_status = status
    _Stub.catalogue_body = body
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _deck(*flags: bool) -> bytes:
    return json.dumps(
        {
            "intents": [
                {"name": f"intent-{i}", "read_only": f, "description": "", "args": []}
                for i, f in enumerate(flags)
            ]
        }
    ).encode()


def test_a_real_catalogue_passes(tmp_path):
    srv, base = _serve(200, _deck(True, False, True))
    try:
        leg = voice.catalogue_leg(base)
    finally:
        srv.shutdown()
    assert leg["ok"] is True, leg
    assert "3 intents" in leg["actual"]
    assert "2 read / 1 confirm" in leg["actual"]


def test_a_500_is_a_failed_leg_not_a_silent_skip():
    srv, base = _serve(500, b'{"detail":"boom"}')
    try:
        leg = voice.catalogue_leg(base)
    finally:
        srv.shutdown()
    assert leg["ok"] is False
    assert "HTTP 500" in leg["actual"]


def test_an_empty_deck_is_red_even_though_the_status_is_200():
    # The exact production shape: route mounted, 200 returned, nothing in it.
    srv, base = _serve(200, json.dumps({"intents": []}).encode())
    try:
        leg = voice.catalogue_leg(base)
    finally:
        srv.shutdown()
    assert leg["ok"] is False
    assert "0 intents" in leg["actual"]


def test_a_ladder_that_inverted_to_all_read_is_red():
    # Every intent running on the first utterance means the confirmation gate vanished.
    srv, base = _serve(200, _deck(True, True, True))
    try:
        leg = voice.catalogue_leg(base)
    finally:
        srv.shutdown()
    assert leg["ok"] is False
    assert "0 confirm" in leg["actual"]


def test_a_ladder_that_collapsed_to_all_mutate_is_red():
    # Every read intent demanding a spoken yes is the same defect the other way up.
    srv, base = _serve(200, _deck(False, False))
    try:
        leg = voice.catalogue_leg(base)
    finally:
        srv.shutdown()
    assert leg["ok"] is False
    assert "0 read" in leg["actual"]


def test_an_item_with_no_read_only_flag_is_named():
    body = json.dumps(
        {"intents": [{"name": "a"}, {"name": "b", "read_only": True}]}
    ).encode()
    srv, base = _serve(200, body)
    try:
        leg = voice.catalogue_leg(base)
    finally:
        srv.shutdown()
    assert leg["ok"] is False
    assert "1 with no read_only flag" in leg["actual"]


def test_a_non_json_body_is_graded_not_crashed():
    srv, base = _serve(200, b"<!DOCTYPE html><html>login</html>")
    try:
        leg = voice.catalogue_leg(base)
    finally:
        srv.shutdown()
    assert leg["ok"] is False
    assert "not JSON" in leg["actual"]


def test_unreachable_is_red_and_says_so():
    # Nothing listening: a probe that cannot connect must not read as PASS.
    leg = voice.catalogue_leg("http://127.0.0.1:1")
    assert leg["ok"] is False
    assert "unreachable" in leg["actual"]


def test_main_returns_non_zero_when_only_the_catalogue_is_wrong(monkeypatch):
    """The exit status is the whole contract: `bin/idp-verify-surfaces` grades `_run` on it."""
    monkeypatch.setattr(voice, "conversation", lambda *a, **k: [])
    srv, base = _serve(200, json.dumps({"intents": []}).encode())
    try:
        rc = voice.main(["probes.voice", base, "--all"])
    finally:
        srv.shutdown()
    assert rc == 1, "an empty catalogue left the battery green"


def test_main_returns_zero_when_the_catalogue_is_healthy(monkeypatch):
    monkeypatch.setattr(voice, "conversation", lambda *a, **k: [])
    srv, base = _serve(200, _deck(True, False))
    try:
        rc = voice.main(["probes.voice", base, "--all"])
    finally:
        srv.shutdown()
    assert rc == 0


def test_the_catalogue_is_read_through_the_door_the_face_uses(monkeypatch):
    """Same path, same host as the Face: /voice/intents on the backend the battery is given."""
    monkeypatch.setattr(voice, "conversation", lambda *a, **k: [])
    srv, base = _serve(200, _deck(True, False))
    _Stub.seen = []
    try:
        voice.main(["probes.voice", base, "--all"])
    finally:
        srv.shutdown()
    assert voice.CATALOGUE_PATH in _Stub.seen
