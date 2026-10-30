"""Law 0: the founder is not on the MacBook. Inbox reaches a (stand-in) Telegram, acked only on acceptance."""

import json
import os
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SERVER = Path.home() / ".cache/estate-tools/nats-server"
pytestmark = pytest.mark.skipif(not SERVER.exists(), reason="needs nats-server")


@pytest.fixture()
def bus(tmp_path):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    p = subprocess.Popen(
        [str(SERVER), "-js", "-sd", str(tmp_path), "-a", "127.0.0.1", "-p", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)
    yield f"nats://127.0.0.1:{port}"
    p.terminate()


def telegram(status=200):
    seen = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            seen.append(
                (
                    self.path,
                    json.loads(self.rfile.read(int(self.headers["Content-Length"]))),
                )
            )
            self.send_response(status)
            self.end_headers()
            self.wfile.write(json.dumps({"ok": status == 200}).encode())

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, seen


def run(exe, url, agent, *args, api=None, creds=True):
    env = {
        **os.environ,
        "ESTATE_NATS_URL": url,
        "ESTATE_AGENT": agent,
        "ESTATE_FLEET_NO_MEMORY": "1",
    }
    env.pop("TELEGRAM_BOT_TOKEN", None)
    env.pop("TELEGRAM_HOME_CHANNEL", None)
    if creds:
        env.update({"TELEGRAM_BOT_TOKEN": "T0K", "TELEGRAM_HOME_CHANNEL": "42"})
    if api:
        env["TELEGRAM_API_BASE"] = api
    return subprocess.run(
        [str(ROOT / "bin" / exe), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_inbox_reaches_phone_and_is_acked(bus):
    srv, seen = telegram()
    run(
        "estate-fleet",
        bus,
        "founder",
        "send",
        "agent-t",
        "resolved: backup receipt fresh",
    )
    r = run(
        "estate-fleet-telegram",
        bus,
        "agent-t",
        "deliver",
        api=f"http://127.0.0.1:{srv.server_port}",
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert seen[0][0] == "/botT0K/sendMessage" and seen[0][1]["chat_id"] == "42"
    assert "resolved: backup receipt fresh" in seen[0][1]["text"]
    assert "0 pending" in run("estate-fleet", bus, "agent-t", "inbox").stdout


def test_telegram_refusal_leaves_message_unacked(bus):
    srv, _ = telegram(status=500)
    run("estate-fleet", bus, "founder", "send", "agent-u", "keep me")
    r = run(
        "estate-fleet-telegram",
        bus,
        "agent-u",
        "deliver",
        api=f"http://127.0.0.1:{srv.server_port}",
    )
    assert r.returncode != 0
    assert "applied" not in run("estate-fleet", bus, "founder", "status", "1").stdout


def test_no_credentials_is_blind(bus):
    run("estate-fleet", bus, "founder", "send", "agent-v", "x")
    r = run("estate-fleet-telegram", bus, "agent-v", "deliver", creds=False)
    assert r.returncode == 2 and "BLIND" in r.stdout
