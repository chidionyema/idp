"""The web door refuses an unbound client at the network boundary, not in the app.

A stub upstream answers 200 to everything; every refusal below therefore came from the door.
"""

from __future__ import annotations

import http.server
import json
import pathlib
import socket
import sys
import threading
import urllib.error
import urllib.request

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "platform" / "estate" / "web"))
import door  # noqa: E402
import net_bind  # noqa: E402


class Upstream(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_a):
        return

    def do_GET(self):  # noqa: N802
        body = b"app"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture()
def stack(tmp_path, monkeypatch):
    monkeypatch.setattr(net_bind, "SESSION_DIR", tmp_path / "sessions")
    up_port, door_port = free_port(), free_port()
    up = http.server.ThreadingHTTPServer(("127.0.0.1", up_port), Upstream)
    threading.Thread(target=up.serve_forever, daemon=True).start()

    class D(door.Door):
        pass

    D.upstream = f"127.0.0.1:{up_port}"
    d = http.server.ThreadingHTTPServer(("127.0.0.1", door_port), D)
    threading.Thread(target=d.serve_forever, daemon=True).start()
    yield door_port, up_port
    d.shutdown()
    up.shutdown()


def call(port, path="/app", headers=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", headers=headers or {}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:  # noqa: S310
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_no_session_is_refused_before_the_app(stack):
    door_port, _ = stack
    code, body = call(door_port)
    assert code == 401 and json.loads(body)["refused"] == "NO_SESSION"


def test_expired_session_is_refused(stack):
    door_port, _ = stack
    tok = net_bind.open_session("I-1", ttl_s=-1)
    code, body = call(door_port, headers={"Authorization": f"Bearer {tok}"})
    assert code == 403 and json.loads(body)["refused"] == "EXPIRED_SESSION"


def test_wrong_ticket_is_refused(stack):
    door_port, _ = stack
    tok = net_bind.open_session("I-1")
    code, body = call(
        door_port, headers={"Authorization": f"Bearer {tok}", "X-Estate-Ticket": "I-2"}
    )
    assert code == 403 and json.loads(body)["refused"] == "WRONG_TICKET"


def test_replayed_nonce_is_refused(stack):
    door_port, _ = stack
    tok = net_bind.open_session("I-1")
    h = {
        "Authorization": f"Bearer {tok}",
        "X-Estate-Ticket": "I-1",
        "X-Estate-Nonce": "n1",
    }
    assert call(door_port, headers=h)[0] == 200
    code, body = call(door_port, headers=h)
    assert code == 409 and json.loads(body)["refused"] == "REPLAY"


def test_a_bound_client_reaches_the_app(stack):
    door_port, _ = stack
    tok = net_bind.open_session("I-1")
    code, body = call(
        door_port, headers={"Authorization": f"Bearer {tok}", "X-Estate-Nonce": "n2"}
    )
    assert code == 200 and body == b"app"


def test_the_door_answers_its_own_health(stack):
    door_port, _ = stack
    code, body = call(door_port, path="/health")
    assert code == 200 and b"afloat" in body
