"""idp#7490: the voice door, against a real throwaway nats-server and a stand-in FleetView."""

import json
import os
import shutil
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SERVER = Path.home() / ".cache/estate-tools/nats-server"

pytestmark = pytest.mark.skipif(
    not SERVER.exists() or not shutil.which("ffmpeg"),
    reason="needs nats-server and ffmpeg",
)


def _port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture()
def bus(tmp_path):
    port = _port()
    p = subprocess.Popen(
        [str(SERVER), "-js", "-sd", str(tmp_path), "-a", "127.0.0.1", "-p", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)
    yield f"nats://127.0.0.1:{port}"
    p.terminate()


@pytest.fixture()
def fleetview():
    seen = {"say": [], "hear_query": []}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path.startswith("/voice/hear"):
                seen["hear_query"].append(self.path)
                out = json.dumps(
                    {"empty": False, "text": "ship the backup proof"}
                ).encode()
                self.send_response(200)
            else:
                seen["say"].append(json.loads(body)["text"])
                out = b"\x00\x00\x00\x00" * 2400  # 0.1s of silence, float32 24kHz
                self.send_response(200)
            self.end_headers()
            self.wfile.write(out)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}", seen
    srv.shutdown()


def run(exe, url, agent, *args, fv="http://127.0.0.1:1", player="true"):
    env = {
        **os.environ,
        "ESTATE_NATS_URL": url,
        "ESTATE_AGENT": agent,
        "FLEETVIEW_URL": fv,
        "ESTATE_FLEET_VOICE_PLAYER": player,
        "ESTATE_FLEET_NO_MEMORY": "1",
        "ESTATE_FLEET_ACK_WAIT": "1",
    }
    return subprocess.run(
        [str(ROOT / "bin" / exe), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_speech_becomes_a_voice_channel_directive(bus, fleetview, tmp_path):
    fv, seen = fleetview
    wav = tmp_path / "in.wav"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=d=0.2", str(wav)],
        check=True,
    )
    r = run("estate-fleet-voice", bus, "founder", "hear", str(wav), fv=fv)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "author=founder" in seen["hear_query"][0]
    got = run("estate-fleet", bus, "agent-x", "inbox").stdout
    assert "directive" in got and "ship the backup proof" in got


def test_spoken_inbox_acks_only_after_playback(bus, fleetview):
    fv, seen = fleetview
    run("estate-fleet", bus, "founder", "send", "agent-x", "read me first")
    bad = run("estate-fleet-voice", bus, "agent-x", "speak", fv=fv, player="false")
    assert bad.returncode != 0
    time.sleep(1.5)  # un-acked: redelivered after ack_wait
    assert "read me first" in run("estate-fleet", bus, "agent-x", "inbox").stdout
    time.sleep(1.5)
    ok = run("estate-fleet-voice", bus, "agent-x", "speak", fv=fv, player="true")
    assert ok.returncode == 0 and "acked" in ok.stdout
    assert "read me first" in seen["say"][-1]
    assert "0 pending" in run("estate-fleet", bus, "agent-x", "inbox").stdout


def test_voice_engine_down_is_blind_not_silence(bus):
    r = run("estate-fleet-voice", bus, "agent-x", "speak", "hello")
    assert r.returncode == 2 and "BLIND" in r.stdout
