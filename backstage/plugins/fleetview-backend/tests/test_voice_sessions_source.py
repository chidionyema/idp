"""The voice answers from the fleet the board draws, not the sidecar's empty store.

2026-10-08 on OKE: the board (proxied to the founder's Mac) drew 431 agents, while /voice/stream
read the sidecar's CI-built estate.db (no session rows) and said "zero agents are running".
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

serve = pytest.importorskip("fleetview_backend.serve")


@pytest.fixture(autouse=True)
def _no_snapshot(monkeypatch):
    monkeypatch.setattr(serve, "_sessions_snapshot", {"rows": None, "at": 0.0})


def _upstream(payload: dict, delay: float = 0.0) -> tuple[HTTPServer, str]:
    body = json.dumps(payload).encode()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            time.sleep(delay)
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


def test_a_turn_answers_from_the_snapshot_not_the_slow_relay(monkeypatch):
    """2026-10-09: the Mac's board took 8-30s over the Tailscale relay and every turn waited."""
    _empty_local(monkeypatch)
    fresh = [{"session_id": "fresh", "activity": "working"}]
    srv, url = _upstream({"sessions": fresh}, delay=2.0)
    try:
        monkeypatch.setenv("FLEETVIEW_SESSIONS_URL", url)
        snap = [{"session_id": "snap", "activity": "finished"}]
        serve._sessions_snapshot.update(rows=snap, at=time.time() - 60)
        t = time.time()
        assert serve._voice_sessions() == snap
        assert time.time() - t < 0.5, "the turn waited on the upstream"
        # The stale snapshot started a refresh behind the turn; the next turn sees its result.
        deadline = time.time() + 5
        while serve._sessions_snapshot["rows"] != fresh and time.time() < deadline:
            time.sleep(0.05)
        assert serve._voice_sessions() == fresh
    finally:
        srv.shutdown()
