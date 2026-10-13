"""A refused router voice is skipped, not paid for on every clause.

2026-10-09: Groq Orpheus's 100-requests-a-day cap was spent, and every /voice/say waited ~5s for
the router's 500 before macOS `say` answered in ~0.8s.
"""

from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

vm = pytest.importorskip("fleetview_backend.voice_media")


_WAV = (
    b"RIFF"
    + (36 + 4).to_bytes(4, "little")
    + b"WAVEfmt "
    + (16).to_bytes(4, "little")
    + (1).to_bytes(2, "little")
    + (1).to_bytes(2, "little")
    + (24000).to_bytes(4, "little")
    + (48000).to_bytes(4, "little")
    + (2).to_bytes(2, "little")
    + (16).to_bytes(2, "little")
    + b"data"
    + (4).to_bytes(4, "little")
    + b"\x00\x10\x00\xf0"
)


def _router(status_by_lane: dict[str, int]) -> tuple[HTTPServer, list[tuple[str, str]]]:
    """A fake router: each lane answers its own status, 200 with a WAV. Records (lane, voice)."""
    hits: list[tuple[str, str]] = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            body = json.loads(
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
            )
            hits.append((body["model"], body["voice"]))
            status = status_by_lane.get(body["model"], 500)
            self.send_response(status)
            if status == 200:
                self.send_header("Content-Type", "audio/wav")
                self.end_headers()
                self.wfile.write(_WAV)
                return
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"error": {"message": "rate limited"}}).encode()
            )

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, hits


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.setattr(vm, "_tts_lane_skip_until", {})


def _serve(monkeypatch, srv):
    monkeypatch.setattr(
        vm, "_router", lambda: (f"http://127.0.0.1:{srv.server_port}", {})
    )


def test_a_refusal_skips_each_router_lane_for_the_next_clauses(monkeypatch):
    srv, hits = _router({})
    try:
        _serve(monkeypatch, srv)
        for _ in range(3):
            assert (
                asyncio.run(vm._router_synthesise("a clause", 24000, "diana")) is None
            )
        assert [lane for lane, _ in hits] == ["voice-tts", "voice-tts-minimax"]
    finally:
        srv.shutdown()


def test_the_router_is_asked_again_once_the_backoff_has_passed(monkeypatch):
    srv, hits = _router({})
    try:
        _serve(monkeypatch, srv)
        asyncio.run(vm._router_synthesise("a clause", 24000, "diana"))
        monkeypatch.setattr(vm, "_tts_lane_skip_until", {})
        asyncio.run(vm._router_synthesise("a clause", 24000, "diana"))
        assert len(hits) == 4
    finally:
        srv.shutdown()


def test_orpheus_refusing_hands_the_clause_to_minimax_in_minimax_s_own_voice(
    monkeypatch,
):
    """2026-10-13: Orpheus refused every call; MiniMax answered with the same key's router."""
    srv, hits = _router({"voice-tts": 400, "voice-tts-minimax": 200})
    try:
        _serve(monkeypatch, srv)
        for _ in range(3):
            assert asyncio.run(vm._router_synthesise("a clause", 24000, "hannah"))
        assert hits == [
            ("voice-tts", "hannah"),
            ("voice-tts-minimax", vm.MINIMAX_VOICE),
            ("voice-tts-minimax", vm.MINIMAX_VOICE),
            ("voice-tts-minimax", vm.MINIMAX_VOICE),
        ]
        assert vm._tts_last_router_voice == f"voice-tts-minimax:{vm.MINIMAX_VOICE}"
    finally:
        srv.shutdown()


def test_orpheus_answering_never_asks_minimax(monkeypatch):
    srv, hits = _router({"voice-tts": 200, "voice-tts-minimax": 200})
    try:
        _serve(monkeypatch, srv)
        assert asyncio.run(vm._router_synthesise("a clause", 24000, "hannah"))
        assert hits == [("voice-tts", "hannah")]
    finally:
        srv.shutdown()
