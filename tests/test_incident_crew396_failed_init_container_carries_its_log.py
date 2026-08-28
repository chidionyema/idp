"""crew#396 / oke-check 33044644964 (06:00Z): six kini-state Job pods were phase Failed with
`failed` {"receipt": "Error exit=1: "} and `last_log` {}. The `receipt` container is an init
container (platform/temporal/kini-state.yaml) and last_log() was handed containerStatuses only,
so the one container that exited was the one never asked for its log. Rule: every not-ready pod
row reads the log of every exited container, init containers included. Rung 4, incident test."""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"


def _collect():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    return next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]


def test_the_pod_row_hands_init_container_statuses_to_last_log():
    collect = _collect()
    compile(collect, "collect.py", "exec")
    call = collect.split('"last_log": last_log(', 1)[1].split("}\n", 1)[0]
    assert 'initContainerStatuses' in call and 'containerStatuses' in call


def test_an_exited_init_container_is_asked_for_its_current_log_and_a_quiet_one_is_not():
    """Both ways in one run: a terminated exit=1 container with no restarts (the kini-state
    receipt shape) is read with previous=false; a container that never exited is never asked."""
    src = _collect().split("def last_log", 1)[1].split("not_ready = [", 1)[0]
    prog = "import urllib.request\nasked = []\n" \
           "class R:\n    def __init__(s, b): s.b = b\n    def __enter__(s): return s\n" \
           "    def __exit__(s, *a): pass\n    def read(s): return s.b\n" \
           "def fake_open(req, context=None, timeout=None):\n    asked.append(req.full_url)\n" \
           "    return R(b'receipt: no rows for 29796750\\n')\n" \
           "urllib.request.urlopen = fake_open\ntok = 't'; ctx = None\n" \
           "def last_log" + src + \
           "out = last_log('temporal', 'kini-state-29796750-9ml56', [" \
           "{'name': 'receipt', 'restartCount': 0, 'state': {'terminated': {'exitCode': 1, 'reason': 'Error'}}}," \
           "{'name': 'publish', 'restartCount': 0, 'state': {'waiting': {'reason': 'PodInitializing'}}}])\n" \
           "import json; print(json.dumps({'out': out, 'asked': asked}))\n"
    r = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, check=True)
    got = json.loads(r.stdout)
    assert got["out"] == {"receipt": "receipt: no rows for 29796750\n"}
    assert len(got["asked"]) == 1 and "previous=false" in got["asked"][0] and "container=receipt" in got["asked"][0]
