"""crew#586 / LAW 50: the conscience receipt is one OTLP log record with science.source=conscience,
posted with the edge's basic-auth pair; a 2xx is ok, anything else FAIL, no config BLIND."""
import base64
import http.server
import json
import os
import pathlib
import subprocess
import sys
import threading

IDP = pathlib.Path(__file__).resolve().parents[1]
EMIT = IDP / "bin" / "lib" / "conscience_emit.py"
RECEIPT = {"measured_at": "2026-08-28T07:23:00+00:00", "host": "runner", "score": {"green": 6, "total": 7}, "blind": False,
           "tenets": [{"name": "secure", "ok": False}, {"name": "portable", "ok": True}]}


class _Collector(http.server.BaseHTTPRequestHandler):
    seen = []
    status = 200

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        _Collector.seen.append((self.path, self.headers.get("Authorization"), json.loads(body)))
        self.send_response(_Collector.status); self.end_headers()

    def log_message(self, *a):  # quiet
        pass


def _serve():
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Collector)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _run(tmp_path, env):
    rep = tmp_path / "r.json"; rep.write_text(json.dumps(RECEIPT))
    return subprocess.run([sys.executable, str(EMIT), str(rep)], env={**os.environ, **env}, capture_output=True, text=True)


def test_the_receipt_lands_as_one_record_with_the_source_attribute_and_the_auth_pair(tmp_path):
    srv = _serve(); _Collector.seen.clear(); _Collector.status = 200
    p = _run(tmp_path, {"OTEL_EXPORTER_OTLP_ENDPOINT": f"http://127.0.0.1:{srv.server_port}", "OTLP_INGEST_USER": "science", "OTLP_INGEST_PASSWORD": "pw"})
    assert p.returncode == 0 and "ok   conscience emit" in p.stdout and "HTTP 200" in p.stdout, p.stdout + p.stderr
    path, auth, body = _Collector.seen[0]
    assert path == "/v1/logs" and auth == "Basic " + base64.b64encode(b"science:pw").decode()
    rec = body["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]
    attrs = {a["key"]: list(a["value"].values())[0] for a in rec["attributes"]}
    assert attrs == {"science.source": "conscience", "conscience.green": "6", "conscience.total": "7", "conscience.red": "secure"}
    assert json.loads(rec["body"]["stringValue"])["score"] == {"green": 6, "total": 7}
    assert "pw" not in p.stdout


def test_a_refused_post_is_fail_not_ok(tmp_path):
    srv = _serve(); _Collector.status = 401
    p = _run(tmp_path, {"OTEL_EXPORTER_OTLP_ENDPOINT": f"http://127.0.0.1:{srv.server_port}", "OTLP_INGEST_USER": "science", "OTLP_INGEST_PASSWORD": "pw"})
    assert p.returncode == 1 and "FAIL conscience emit" in p.stdout and "HTTP 401" in p.stdout


def test_no_endpoint_is_blind(tmp_path):
    p = _run(tmp_path, {"OTEL_EXPORTER_OTLP_ENDPOINT": "", "OTLP_INGEST_USER": "", "OTLP_INGEST_PASSWORD": ""})
    assert p.returncode == 2 and "BLIND" in p.stdout
