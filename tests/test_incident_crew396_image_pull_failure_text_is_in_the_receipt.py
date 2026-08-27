"""crew#396, second fault, oke-check 33039951589: sovereign-worker-68f5b47785-rwgd7 and
kini-finish-0-6dlx5 sat in ImagePullBackOff for hours and the receipt row said only
phase=Pending, restarts=0. The pull error lives in containerStatuses[].state.waiting, and the
events list keeps the 20 newest, so the text never reached a session. Rule: every not-ready pod
row carries the waiting reason and message of each container that is waiting on something other
than normal startup, init containers included. Rung 4, incident test, proved both ways."""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"


def _collect() -> str:
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    return next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]


def test_a_waiting_container_names_its_reason_and_a_starting_one_is_silent():
    collect = _collect()
    compile(collect, "collect.py", "exec")
    assert '"waiting": waiting(p["status"])' in collect
    src = collect.split("def waiting", 1)[1].split("not_ready = [", 1)[0]
    status = {
        "phase": "Pending",
        "initContainerStatuses": [{"name": "init", "state": {"waiting": {"reason": "ImagePullBackOff",
                                   "message": 'Back-off pulling image "ghcr.io/x/y:main-727"'}}}],
        "containerStatuses": [
            {"name": "worker", "state": {"waiting": {"reason": "ErrImagePull", "message": "manifest unknown"}}},
            {"name": "sidecar", "state": {"waiting": {"reason": "ContainerCreating"}}},
            {"name": "ok", "state": {"running": {"startedAt": "2026-08-27T00:00:00Z"}}},
        ],
    }
    prog = "def waiting" + src + f"\nimport json; print(json.dumps(waiting({status!r})))\n"
    r = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, check=True)
    got = json.loads(r.stdout)
    assert got == {"init": 'ImagePullBackOff: Back-off pulling image "ghcr.io/x/y:main-727"',
                   "worker": "ErrImagePull: manifest unknown"}
    empty = "def waiting" + src + "\nimport json; print(json.dumps(waiting({'phase': 'Running', 'containerStatuses': [{'name': 'a', 'state': {'running': {}}}]})))\n"
    r = subprocess.run([sys.executable, "-c", empty], capture_output=True, text=True, check=True)
    assert json.loads(r.stdout) == {}


def test_a_failed_job_pod_that_never_restarted_carries_its_current_log():
    """Second receipt (05:00Z): kini-state Job pods were phase Failed, restarts 0, last_log {}.
    Both ways: exit 1 with no restart is read (current log), exit 0 is not, a restarted one is
    still read as before (previous log)."""
    collect = _collect()
    src = collect.split("def last_log", 1)[1].split("not_ready = [", 1)[0]
    prog = "import urllib.request\nasked = []\n" \
           "class R:\n    def __init__(s, b): s.b = b\n    def __enter__(s): return s\n" \
           "    def __exit__(s, *a): pass\n    def read(s): return s.b\n" \
           "def fake_open(req, context=None, timeout=None):\n    asked.append(req.full_url); return R(b'Traceback: boom\\n')\n" \
           "urllib.request.urlopen = fake_open\ntok = 't'; ctx = None\n" \
           "def last_log" + src + \
           "out = last_log('temporal', 'kini-state-1-abc', [{'name': 'step', 'restartCount': 0, 'state': {'terminated': {'exitCode': 1}}}," \
           " {'name': 'done', 'restartCount': 0, 'state': {'terminated': {'exitCode': 0}}}," \
           " {'name': 'looping', 'restartCount': 3, 'state': {'waiting': {'reason': 'CrashLoopBackOff'}}}])\n" \
           "import json; print(json.dumps({'out': out, 'asked': asked}))\n"
    r = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, check=True)
    got = json.loads(r.stdout)
    assert set(got["out"]) == {"step", "looping"} and got["out"]["step"] == "Traceback: boom\n"
    assert [u.split("container=")[1] for u in got["asked"]] == ["step&previous=false&tailLines=8", "looping&previous=true&tailLines=8"]


def test_third_receipt_a_killed_job_pod_names_its_pod_reason_and_terminated_reason():
    """Third receipt (05:33Z, oke-check 33042332456): six kini-state pods were phase Failed, restarts 0,
    waiting {} and last_log {}. Both ways in one run: failed() names the pod-level reason and a
    container's terminated reason and exit code; a pod with no reason and a running container is {}."""
    collect = _collect()
    assert '"failed": failed(p["status"])' in collect
    src = collect.split("def failed", 1)[1].split("not_ready = [", 1)[0]
    killed = {"phase": "Failed", "reason": "DeadlineExceeded", "message": "Pod was active longer than the specified deadline",
              "containerStatuses": [{"name": "step", "restartCount": 0,
                                     "state": {"terminated": {"reason": "Error", "exitCode": 137}}}]}
    quiet = {"phase": "Running", "containerStatuses": [{"name": "web", "restartCount": 0, "state": {"running": {}}}]}
    prog = "def failed" + src + f"\nimport json; print(json.dumps(failed({killed!r}))); print(json.dumps(failed({quiet!r})))"
    out = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, check=True).stdout.splitlines()
    got = json.loads(out[0])
    assert got["pod"].startswith("DeadlineExceeded: Pod was active longer")
    assert got["step"] == "Error exit=137: "
    assert json.loads(out[1]) == {}
