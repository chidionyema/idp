"""crew#396 / oke-check 33036925574: after the image fix landed, temporal-frontend, -history and
-matching restarted six times each and the receipt said only "Back-off restarting failed
container". The receipt is the only kube path a session has, so the exit reason was unreadable
and the repair stalled. Rule: every not-ready pod row carries the last lines of the previous run
of each container that restarted, and the role can read pod logs. Rung 4, incident test."""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"


def _docs():
    return [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]


def test_collector_reads_the_previous_log_of_a_restarted_container_and_the_role_allows_it():
    docs = _docs()
    collect = next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]
    compile(collect, "collect.py", "exec")
    assert "previous=true" in collect and '"last_log"' in collect
    role = next(d for d in docs if d["kind"] == "ClusterRole")
    granted = {(g, r) for rule in role["rules"] for g in rule["apiGroups"] for r in rule["resources"]
               if {"get", "list"} <= set(rule["verbs"])}
    assert ("", "pods/log") in granted


def test_last_log_is_read_only_for_restarted_containers_and_a_failed_read_is_recorded():
    """Both ways in one run: the collector's last_log() against a fake API server that answers
    the log path for one container and refuses it for another; a container with no restarts is
    never asked for."""
    collect = next(d for d in _docs() if d["kind"] == "ConfigMap")["data"]["collect.py"]
    src = collect.split("def last_log", 1)[1].split("not_ready = [", 1)[0]
    prog = "import urllib.request\nasked = []\n" \
           "class R:\n    def __init__(s, b): s.b = b\n    def __enter__(s): return s\n" \
           "    def __exit__(s, *a): pass\n    def read(s): return s.b\n" \
           "def fake_open(req, context=None, timeout=None):\n    asked.append(req.full_url)\n" \
           "    if 'container=good' in req.full_url: return R(b'line1\\nfatal: schema version mismatch\\n')\n" \
           "    raise OSError('403 Forbidden')\n" \
           "urllib.request.urlopen = fake_open\ntok = 't'; ctx = None\n" \
           "def last_log" + src + \
           "out = last_log('temporal', 'temporal-frontend-1', [{'name': 'good', 'restartCount': 6}," \
           " {'name': 'bad', 'restartCount': 1}, {'name': 'quiet', 'restartCount': 0}])\n" \
           "import json; print(json.dumps({'out': out, 'asked': asked}))\n"
    r = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, check=True)
    got = json.loads(r.stdout)
    assert got["out"]["good"].endswith("fatal: schema version mismatch\n")
    assert got["out"]["bad"].startswith("log read failed: 403")
    assert "quiet" not in got["out"] and len(got["asked"]) == 2
    assert all("previous=true" in u and "tailLines=8" in u for u in got["asked"])
