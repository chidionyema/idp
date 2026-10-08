import http.server
import json
import os
import secrets
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]

SIGN_IN_HTML = (
    "<h1>Sign in</h1>"
    "<script>setInterval(async()=>{"
    "const r=await fetch('/session');"
    "if(r.status===200)location.reload()"
    "},250)</script>"
)
CONSOLE_HTML = "<button onclick=\"location='/new'\">Create token</button>"
NEW_HTML = (
    '<form action="/create" method="post">'
    '<label for="n">Token name</label>'
    '<input id="n" name="name">'
    '<button type="submit">Create</button>'
    "</form>"
)


@pytest.fixture
def vendor():
    state = {"signed_in": False, "name": None}
    token = "tok_" + secrets.token_hex(16)

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == "/console":
                cookie = self.headers.get("Cookie", "")
                html = CONSOLE_HTML if "session=ok" in cookie else SIGN_IN_HTML
                body = html.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/session":
                if state["signed_in"]:
                    self.send_response(200)
                    self.send_header("Set-Cookie", "session=ok; Path=/")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                else:
                    self.send_response(204)
                    self.end_headers()
            elif self.path == "/human-signs-in":
                state["signed_in"] = True
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()
            elif self.path == "/new":
                body = NEW_HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/echo-refuse":
                # The vendor refuses the new key and echoes it back in the body.
                body = f"refused {self.headers.get('Authorization', '')}".encode()
                self.send_response(401)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/verify":
                ok = self.headers.get("Authorization") == f"Bearer {token}"
                body = json.dumps({"ok": True}).encode()
                self.send_response(200 if ok else 401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if ok:
                    self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            if self.path == "/create":
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length).decode()
                parsed = urllib.parse.parse_qs(raw)
                state["name"] = parsed.get("name", [None])[0]
                body = f"<p>Your new token: <code>{token}</code></p>".encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield {"base": base, "state": state, "token": token, "server": server}
    finally:
        server.shutdown()
        server.server_close()


def _human(base):
    import time

    time.sleep(1.5)
    urllib.request.urlopen(base + "/human-signs-in")  # noqa: S310


def _run(
    tmp_path,
    v,
    *,
    regex="tok_[0-9a-f]{32}",
    wait_step_s=20,
    wait_s=10,
    human=True,
    verify_path="/verify",
):
    base = v["base"]
    wait_spec = {"role": "button", "name": "(?i)create token", "why": "sign in"}
    if wait_step_s:
        wait_spec["wait_s"] = wait_step_s
    row = {
        "kind": "secret",
        "page": base + "/console",
        "shape": "tok_[0-9a-f]{32}",
        "store_default": "estate-vault",
        "verify": {
            "method": "GET",
            "url": base + verify_path,
            "headers": {"Authorization": "Bearer {key}"},
        },
        "targets": [{"ns": "llm", "field": "FAKE_API_KEY"}],
        "setup": {
            "road": "browser",
            "entry": "fake-vendor-env",
            "steps": [
                {"goto": base + "/console"},
                {"wait": wait_spec},
                {"click": {"role": "button", "name": "(?i)create token"}},
                {
                    "fill": {
                        "label": "(?i)token name",
                        "value": "estate-{vendor}-{date}",
                    }
                },
                {"click": {"role": "button", "name": "(?i)^create$"}},
                {"capture": {"field": "FAKE_API_KEY", "regex": regex}},
            ],
        },
    }
    consoles = tmp_path / "consoles.yaml"
    consoles.write_text(yaml.safe_dump({"vendors": {"fakevendor": row}}))

    script = tmp_path / "fake-vault-put"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "env_file = os.environ['ESTATE_ENV_FILE']\n"
        "lines = open(env_file).read().splitlines()\n"
        "record = {\n"
        "    'argv': sys.argv[1:],\n"
        "    'env_file': env_file,\n"
        "    'keys': [line.split('=', 1)[0] for line in lines],\n"
        "    'values': dict(line.split('=', 1) for line in lines),\n"
        "}\n"
        "with open(os.environ['FAKE_VAULT_RECORD'], 'w') as f:\n"
        "    f.write(json.dumps(record))\n"
        "sys.exit(0)\n"
    )
    script.chmod(0o755)
    record_path = tmp_path / "record.json"

    if human:
        threading.Thread(target=_human, args=(base,), daemon=True).start()

    proc = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(ROOT / "bin/idp-vendor-setup"),
            "fakevendor",
            "--headless",
            "--wait-s",
            str(wait_s),
        ],
        env={
            **os.environ,
            "IDP_VENDOR_CONSOLES": str(consoles),
            "ESTATE_HOME": str(tmp_path / "estate"),
            "IDP_VAULT_PUT": str(script),
            "FAKE_VAULT_RECORD": str(record_path),
            "IDP_VENDOR_SETUP_REEXEC": "1",
        },
        capture_output=True,
        text=True,
        timeout=180,
    )
    return proc, record_path


def test_the_estate_makes_the_key_end_to_end(tmp_path, vendor):
    proc, record_path = _run(tmp_path, vendor)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "fake-vendor-env" in proc.stdout

    record = json.loads(record_path.read_text())
    assert record["values"]["V_FAKE_API_KEY"] == vendor["token"]
    assert record["argv"] == [
        "--merge",
        "fake-vendor-env",
        "FAKE_API_KEY=V_FAKE_API_KEY",
    ]

    assert vendor["token"] not in proc.stdout + proc.stderr
    assert not os.path.exists(record["env_file"])
    assert vendor["state"]["name"].startswith("estate-fakevendor-2")
    assert (tmp_path / "estate" / "vendor-browser" / "fakevendor").is_dir()


def test_a_wrong_capture_regex_fails_naming_the_field(tmp_path, vendor):
    proc, record_path = _run(tmp_path, vendor, regex="tok_[0-9a-f]{99}", wait_s=5)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "FAKE_API_KEY" in proc.stdout
    assert vendor["token"] not in proc.stdout + proc.stderr
    assert not record_path.exists()


def test_a_wait_that_never_resolves_says_what_it_waits_for(tmp_path, vendor):
    proc, record_path = _run(tmp_path, vendor, human=False, wait_step_s=0, wait_s=3)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "waiting for sign in" in proc.stdout
    assert not record_path.exists()


def test_a_key_the_vendor_refuses_is_not_written_and_its_echo_is_scrubbed(
    tmp_path, vendor
):
    proc, record_path = _run(tmp_path, vendor, verify_path="/echo-refuse")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "HTTP 401" in proc.stdout
    assert vendor["token"] not in proc.stdout + proc.stderr
    assert not record_path.exists()
