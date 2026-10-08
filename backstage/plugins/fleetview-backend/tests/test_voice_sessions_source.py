"""The voice answers from the fleet the board draws, not the sidecar's empty store.

2026-10-08 on OKE: the board (proxied to the founder's Mac) drew 431 agents, while /voice/stream
read the sidecar's CI-built estate.db (no session rows) and said "zero agents are running".
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

serve = pytest.importorskip("fleetview_backend.serve")


def _upstream(payload: dict) -> tuple[HTTPServer, str]:
    body = json.dumps(payload).encode()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}/sessions"


def _empty_local(monkeypatch):
    monkeypatch.setattr(
        serve.routes, "sessions_envelope", lambda: ({"sessions": []}, 200)
    )


def test_voice_reads_the_boards_fleet_when_configured(monkeypatch):
    _empty_local(monkeypatch)
    rows = [{"session_id": f"s{i}", "activity": "finished"} for i in range(3)]
    srv, url = _upstream({"sessions": rows})
    try:
        monkeypatch.setenv("FLEETVIEW_SESSIONS_URL", url)
        assert serve._voice_sessions() == rows
    finally:
        srv.shutdown()


def test_unreachable_upstream_falls_back_to_the_local_store(monkeypatch):
    local = [{"session_id": "local", "activity": "stuck"}]
    monkeypatch.setattr(
        serve.routes, "sessions_envelope", lambda: ({"sessions": local}, 200)
    )
    monkeypatch.setenv("FLEETVIEW_SESSIONS_URL", "http://127.0.0.1:9/sessions")
    assert serve._voice_sessions() == local


def test_unset_uses_the_local_store(monkeypatch):
    _empty_local(monkeypatch)
    monkeypatch.delenv("FLEETVIEW_SESSIONS_URL", raising=False)
    assert serve._voice_sessions() == []
