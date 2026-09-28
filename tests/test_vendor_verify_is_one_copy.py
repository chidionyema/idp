import http.server
import pathlib
import sys
import threading

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin/lib"))
import vendor_verify  # noqa: E402


def _heredoc():
    text = (ROOT / "bin/idp-bootstrap-vendors").read_text()
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.endswith("<<'PY'"))
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == "PY")
    return "\n".join(lines[start + 1 : end])


def test_the_heredoc_compiles_and_holds_no_second_verify():
    src = _heredoc()
    compile(src, "idp-bootstrap-vendors", "exec")
    assert "def zone(" not in src
    assert "urllib.request.urlopen" not in src
    assert "from vendor_verify import verify" in src


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/ok"):
            auth = self.headers.get("Authorization", "")
            if auth == "Bearer good-key-123":
                body = b'{"ok":true}'
                self.send_response(200)
            else:
                body = f"bad key {auth}".encode()
                self.send_response(401)
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/echo":
            # A vendor that refuses and echoes the credential back, as some do.
            body = f"bad credential {self.headers.get('Authorization', '')}".encode()
            self.send_response(401)
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/refuse":
            auth = self.headers.get("Authorization", "")
            body = (
                b"invalid_client"
                if auth == "Bearer unknown"
                else b"unauthorized_client"
            )
            self.send_response(400)
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{srv.server_port}"
    finally:
        srv.shutdown()


def test_a_key_the_vendor_accepts_verifies(server):
    v = {
        "verify": {
            "method": "GET",
            "url": server + "/ok",
            "headers": {"Authorization": "Bearer {key}"},
        }
    }
    assert vendor_verify.verify(v, {"key": "good-key-123"}, str(ROOT)) == ""


def test_a_refused_key_names_the_status_and_never_the_value(server):
    v = {
        "verify": {
            "method": "GET",
            "url": server + "/ok",
            "headers": {"Authorization": "Bearer {key}"},
        }
    }
    reason = vendor_verify.verify(v, {"key": "sk-secret-value-999"}, str(ROOT))
    assert reason.startswith("HTTP 401")
    assert "***" in reason
    assert "sk-secret-value-999" not in reason


def test_refuse_when_reads_the_4xx_body(server):
    v = {
        "verify": {
            "method": "GET",
            "url": server + "/refuse",
            "headers": {"Authorization": "Bearer {key}"},
            "refuse_when": "invalid_client",
        }
    }
    reason = vendor_verify.verify(v, {"key": "unknown"}, str(ROOT))
    assert reason
    assert reason.startswith("HTTP 400")
    assert vendor_verify.verify(v, {"key": "known"}, str(ROOT)) == ""


def test_an_unresolved_placeholder_is_a_fail_not_a_probe(server):
    v = {
        "verify": {
            "method": "GET",
            "url": server + "/ok?x=${NOPE}",
            "headers": {"Authorization": "Bearer {key}"},
        }
    }
    with pytest.raises(SystemExit) as exc:
        vendor_verify.verify(v, {"key": "good-key-123"}, str(ROOT))
    assert exc.value.code == 1


def test_basic_auth_is_encoded_here_and_its_echo_is_scrubbed(server):
    # idp#4591: Grafana Cloud's OTLP gateway takes basic auth over two fields. The base64 of
    # "user:password" is a secret too; a vendor echoing the header must not reach the log.
    v = {"verify": {"method": "GET", "url": server + "/echo", "basic": "{ID}:{TOKEN}"}}
    reason = vendor_verify.verify(
        v, {"ID": "123", "TOKEN": "glc-secret-value"}, str(ROOT)
    )
    assert reason.startswith("HTTP 401")
    assert "Basic ***" in reason
    assert "MTIzOmdsYy1zZWNyZXQtdmFsdWU" not in reason
