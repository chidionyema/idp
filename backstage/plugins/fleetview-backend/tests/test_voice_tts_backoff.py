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


def _router(status: int) -> tuple[HTTPServer, list[int]]:
    hits: list[int] = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            hits.append(1)
            self.send_response(status)
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
    monkeypatch.setattr(vm, "_tts_router_skip_until", 0.0)


def test_a_refusal_skips_the_router_for_the_next_clauses(monkeypatch):
    srv, hits = _router(500)
    try:
        monkeypatch.setattr(
            vm, "_router", lambda: (f"http://127.0.0.1:{srv.server_port}", {})
        )
        for _ in range(3):
            assert (
                asyncio.run(vm._router_synthesise("a clause", 24000, "diana")) is None
            )
        assert len(hits) == 1
    finally:
        srv.shutdown()


def test_the_router_is_asked_again_once_the_backoff_has_passed(monkeypatch):
    srv, hits = _router(500)
    try:
        monkeypatch.setattr(
            vm, "_router", lambda: (f"http://127.0.0.1:{srv.server_port}", {})
        )
        asyncio.run(vm._router_synthesise("a clause", 24000, "diana"))
        monkeypatch.setattr(vm, "_tts_router_skip_until", 0.0)
        asyncio.run(vm._router_synthesise("a clause", 24000, "diana"))
        assert len(hits) == 2
    finally:
        srv.shutdown()
