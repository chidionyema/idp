"""The OTLP door (platform/monitoring/otlp.yaml) can only ship what it can authenticate.

Founder, 2026-09-27: the old telemetry store goes, and every signal leaves through one Alloy pod
to Grafana Cloud. That pod reads three files from Secret human-grafana-cloud. Nothing about that
Secret is typed by hand: the vendor row `grafana_cloud` in platform/vendors/consoles.yaml is
rendered by the vendor chart into the ExternalSecret that makes it. Three names have to agree --
the Secret the pod mounts, the Secret the chart renders, and the three field names on each side
-- and a drift in any one is a pod that starts, exports nothing, and reads green.

The third part grades the one piece of new code the row needed: bin/idp-bootstrap-vendors'
`basic:` verify, run against a local server that accepts one credential. A right pair verifies,
a wrong token is refused with the vendor's status, and the encoded credential never reaches the
line a person reads.
"""

import base64
import functools
import http.server
import pathlib
import re
import shutil
import subprocess
import threading

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
OTLP = ROOT / "platform" / "monitoring" / "otlp.yaml"
CHART = ROOT / "platform" / "vendors"
BOOTSTRAP = ROOT / "bin" / "idp-bootstrap-vendors"
FIELDS = {
    "GRAFANA_CLOUD_OTLP_ENDPOINT",
    "GRAFANA_CLOUD_INSTANCE_ID",
    "GRAFANA_CLOUD_API_TOKEN",
}


def _release():
    return next(
        d
        for d in yaml.safe_load_all(OTLP.read_text())
        if d and d["kind"] == "HelmRelease"
    )


@functools.lru_cache(maxsize=1)
def _bridge():
    helm = shutil.which("helm")
    assert helm, "helm is not on PATH; .github/actions/estate-tools installs it"
    out = subprocess.run(
        [helm, "template", "vendor-bridge", str(CHART)], capture_output=True, text=True
    )
    assert out.returncode == 0, out.stderr[-2000:]
    return [d for d in yaml.safe_load_all(out.stdout) if d]


def test_the_pod_mounts_the_secret_the_vendor_chart_renders() -> None:
    hr = _release()
    mounted = {
        v["secret"]["secretName"]
        for v in hr["spec"]["values"]["controller"]["volumes"]["extra"]
        if "secret" in v
    }
    rendered = {
        (d["metadata"]["namespace"], d["spec"]["target"]["name"]): {
            e["secretKey"] for e in d["spec"]["data"]
        }
        for d in _bridge()
        if d["kind"] == "ExternalSecret"
    }
    assert mounted == {"human-grafana-cloud"}, mounted
    key = (hr["metadata"]["namespace"], "human-grafana-cloud")
    assert key in rendered, (
        f"no ExternalSecret renders {key}; the pod would wait forever"
    )
    assert rendered[key] == FIELDS, rendered[key]


def test_the_config_reads_exactly_the_fields_the_secret_holds() -> None:
    content = _release()["spec"]["values"]["alloy"]["configMap"]["content"]
    read = set(re.findall(r'filename\s*=\s*"/etc/grafana-cloud/([A-Z_]+)"', content))
    assert read == FIELDS, read


def _verify():
    """bin/idp-bootstrap-vendors' own verify(), lifted out of its heredoc and run as written."""
    src = BOOTSTRAP.read_text()
    body = src[src.index("def verify(v, subs):") :]
    body = body[: body.index("\ndef ", 1)]
    ns = {"__builtins__": __builtins__}
    exec(
        "import base64, re, sys, urllib.error, urllib.request\n"
        "def zone(): return ''\n"
        "def say(*a): print(*a)\n" + body,
        ns,
    )
    return ns["verify"]


class _Gateway(http.server.BaseHTTPRequestHandler):
    want = "Basic " + base64.b64encode(b"123456:glc_right").decode()

    def do_POST(self):  # noqa: N802
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        ok = self.headers.get("Authorization") == self.want
        self.send_response(200 if ok else 401)
        self.end_headers()
        # A vendor that echoes the header back: the scrub must catch it.
        self.wfile.write(
            b"{}" if ok else f"bad {self.headers.get('Authorization')}".encode()
        )

    def log_message(self, *a):
        pass


def test_the_basic_verify_accepts_the_pair_and_refuses_a_wrong_token() -> None:
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Gateway)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        row = yaml.safe_load((CHART / "consoles.yaml").read_text())["vendors"][
            "grafana_cloud"
        ]
        verify = _verify()
        endpoint = f"http://127.0.0.1:{srv.server_port}/otlp"
        good = {
            "GRAFANA_CLOUD_OTLP_ENDPOINT": endpoint,
            "GRAFANA_CLOUD_INSTANCE_ID": "123456",
            "GRAFANA_CLOUD_API_TOKEN": "glc_right",
        }
        assert verify(row, good) == ""
        bad = {**good, "GRAFANA_CLOUD_API_TOKEN": "glc_wrong"}
        reason = verify(row, bad)
        assert reason.startswith("HTTP 401"), reason
        leaked = base64.b64encode(b"123456:glc_wrong").decode()
        assert leaked not in reason and "glc_wrong" not in reason, reason
    finally:
        srv.shutdown()
