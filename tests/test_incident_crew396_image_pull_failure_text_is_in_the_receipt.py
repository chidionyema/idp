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
