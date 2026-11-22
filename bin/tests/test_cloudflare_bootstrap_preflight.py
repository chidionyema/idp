"""Exercise the real bootstrap preflight without cloud writes or live credentials."""

import os
from pathlib import Path
import shutil
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import secrets
import socket
import subprocess
import tempfile
import threading
import unittest


SOURCE = Path(__file__).resolve().parents[2] / "bin/idp-bootstrap-cloudflare"


class CloudflarePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        shutil.copy2(SOURCE, self.bin / SOURCE.name)
        config = self.root / "clusters/fixture/estate-config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("data:\n  ESTATE_ZONE: meridianlabs.cloud\n")
        (self.bin / "idp-oci-whoami").symlink_to(shutil.which("true"))
        (self.bin / "idp-vault-put").symlink_to(shutil.which("true"))
        home = self.root / "estate/bootstrap-venv/bin"
        home.mkdir(parents=True)
        python = home / "python"
        python.symlink_to(shutil.which("true"))
        self.calls = []
        self.verify_status = "active"
        self.placeholder = secrets.token_urlsafe(24)
        self.console_http = 403
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                fixture.calls.append(self.path)
                if self.path.endswith("/user/tokens/verify"):
                    if fixture.verify_status == "offline":
                        self.connection.shutdown(socket.SHUT_RDWR)
                        self.connection.close()
                        return
                    data = json.dumps(
                        {
                            "success": fixture.verify_status == "active",
                            "result": {"status": fixture.verify_status},
                        }
                    ).encode()
                    self.send_response(200)
                else:
                    data = b"console"
                    self.send_response(fixture.console_http)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        url = f"http://127.0.0.1:{self.server.server_port}"
        self.env = dict(
            os.environ,
            PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
            ESTATE_HOME=str(self.root / "estate"),
            R2_BUCKET="fixture-bucket",
            CLOUDFLARE_API_URL=url + "/api",
            CLOUDFLARE_CONSOLE_URL=url + "/console",
        )
        self.env.pop("CLOUDFLARE_ROOT_TOKEN", None)

    def script(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o700)

    def run_preflight(self, root=True, **env):
        self.verify_status = env.get("FAKE_VERIFY_STATUS", "active")
        self.console_http = int(env.get("FAKE_CONSOLE_HTTP", "403"))
        if env.get("FAKE_VAULT_OK") == "0":
            path = self.bin / "idp-vault-put"
            path.unlink()
            path.symlink_to(shutil.which("false"))
        values = {**self.env, **env}
        if root:
            values["CLOUDFLARE_ROOT_TOKEN"] = self.placeholder
        result = subprocess.run(
            ["bash", str(self.bin / SOURCE.name), "--preflight"],
            env=values,
            text=True,
            capture_output=True,
            timeout=10,  # estate:bound Hermetic preflight probe must fail before the test-runner door; no delivery work is bounded here.
            check=False,
        )
        self.assertNotIn(self.placeholder, result.stdout + result.stderr)
        return result, self.calls

    def test_root_path_uses_api_when_console_is_forbidden(self):
        result, calls = self.run_preflight()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(calls, ["/api/user/tokens/verify"])
        self.assertIn("nothing written", result.stdout)

    def test_invalid_root_is_refused_even_if_console_would_answer(self):
        result, calls = self.run_preflight(
            FAKE_VERIFY_STATUS="disabled", FAKE_CONSOLE_HTTP="200"
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(calls, ["/api/user/tokens/verify"])

    def test_api_network_failure_is_refused(self):
        result, calls = self.run_preflight(FAKE_VERIFY_STATUS="offline")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(calls, ["/api/user/tokens/verify"])

    def test_browser_path_still_checks_console(self):
        result, calls = self.run_preflight(root=False, FAKE_CONSOLE_HTTP="200")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(calls, ["/console"])

    def test_forbidden_console_still_blocks_browser_path(self):
        result, calls = self.run_preflight(root=False)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(calls, ["/console"])

    def test_vault_failure_still_stops_before_provider_probe(self):
        result, calls = self.run_preflight(FAKE_VAULT_OK="0")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
