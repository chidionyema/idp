"""crew#495 / oke-check 33090220723: signoz-0 had restarted 37 times and the receipt's last_log
was 800 characters of cobra stack frames ending at cmd/enterprise/server.go:79. The fatal is one
zap JSON line, "msg" at its head, stacktrace behind it, longer than the tail the collector kept,
so the reason never reached a session and the repair stalled for a day. Rule: each of the last
eight lines keeps its head, and a line longer than 400 characters is marked cut. Rung 4."""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"


def _last_log_src():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    collect = next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]
    return collect.split("def last_log", 1)[1].split("not_ready = [", 1)[0]


def test_a_fatal_line_keeps_its_message_and_a_short_log_is_kept_whole():
    """Both ways: a 3000-char zap fatal keeps "msg" and is marked cut; a short log is verbatim."""
    fatal = json.dumps({"level": "fatal", "msg": "root user: organization already exists",
                        "stacktrace": "github.com/spf13/cobra.(*Command).execute\n" * 60})
    prog = "import urllib.request\n" \
           "class R:\n    def __init__(s, b): s.b = b\n    def __enter__(s): return s\n" \
           "    def __exit__(s, *a): pass\n    def read(s): return s.b\n" \
           "def fake_open(req, context=None, timeout=None):\n" \
           "    if 'container=signoz' in req.full_url: return R(('starting\\n' + FATAL + '\\n').encode())\n" \
           "    return R(b'line1\\nfatal: schema version mismatch\\n')\n" \
           "urllib.request.urlopen = fake_open\ntok = 't'; ctx = None\n" \
           "def last_log" + _last_log_src() + \
           "out = last_log('observability', 'signoz-0', [{'name': 'signoz', 'restartCount': 37}," \
           " {'name': 'short', 'restartCount': 1}])\n" \
           "import json; print(json.dumps(out))\n"
    r = subprocess.run([sys.executable, "-c", "FATAL = " + repr(fatal) + "\n" + prog],
                       capture_output=True, text=True, check=True)
    got = json.loads(r.stdout)
    assert len(fatal) > 800
    assert "organization already exists" in got["signoz"]
    assert got["signoz"].startswith("starting\n") and got["signoz"].endswith(" ...[cut]\n")
    assert len(got["signoz"]) < 500
    assert got["short"] == "line1\nfatal: schema version mismatch\n"
