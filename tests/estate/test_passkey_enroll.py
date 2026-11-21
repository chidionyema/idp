"""Falsifiers for the enrolment client — the one step the founder performs once.

A keyring is a public key plus the commit it was enrolled under. The two ways this becomes a
lie: a keyring written from nothing (no registration ever posted), and a keyring whose origin
or RP ID does not match the host the passkey was created for, which would make every later
assertion verify against the wrong relying party.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "bin" / "idp-passkey-enroll"


def _serve(payload: dict | None, status: int = 200):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if payload is None:
                self.send_response(404)
                self.end_headers()
                return
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            return

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _run(host: str, out: Path, timeout: int = 2) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--host",
            host,
            "--out",
            str(out),
            "--timeout",
            str(timeout),
            "--poll",
            "1",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_a_registration_writes_the_keyring_shape_the_verifier_reads(
    tmp_path: Path,
) -> None:
    srv = _serve({"credentialId": "A" * 32, "publicKeySpki": "B" * 64})
    host = f"http://127.0.0.1:{srv.server_port}"
    out = tmp_path / "founder-passkey.json"
    r = _run(host, out)
    srv.shutdown()
    assert r.returncode == 0, r.stderr
    ring = json.loads(out.read_text())
    assert set(ring) == {
        "credentialId",
        "publicKeySpki",
        "rpId",
        "origin",
        "enrollmentCommit",
    }
    assert ring["rpId"] == host.removeprefix("http://")
    assert len(ring["enrollmentCommit"]) == 40


def test_no_registration_writes_no_keyring(tmp_path: Path) -> None:
    srv = _serve(None)
    out = tmp_path / "founder-passkey.json"
    r = _run(f"http://127.0.0.1:{srv.server_port}", out)
    srv.shutdown()
    assert r.returncode == 1, r.stdout
    assert not out.exists(), "a keyring must never exist without a registration"


def test_a_registration_without_key_material_is_refused(tmp_path: Path) -> None:
    srv = _serve({"credentialId": "A" * 32})
    out = tmp_path / "founder-passkey.json"
    r = _run(f"http://127.0.0.1:{srv.server_port}", out)
    srv.shutdown()
    assert r.returncode == 1
    assert not out.exists()
