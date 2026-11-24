"""The ESTATE-P0 continuity canary (part 1): run attempt A, kill it mid-task.

Exit 0 only with a full receipt; any stage failure exits nonzero. This is
machine evidence, not narration.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from continuity import MissionStore  # noqa: E402
from continuity.canary_stage2 import stage_two  # noqa: E402
from continuity.util import digest_of  # noqa: E402

GOAL = "land the continuity substrate"
LINES = 6


def main() -> int:
    work_dir = tempfile.mkdtemp(prefix="estate-p0-canary-")
    db = os.path.join(work_dir, "custody.sqlite")
    receipt = {"goal": GOAL, "db": db, "work_dir": work_dir}
    signer = Ed25519PrivateKey.generate()
    store = MissionStore(
        db,
        trusted_verifier_keys={
            "canary-artifact-check": signer.public_key().public_bytes_raw()
        },
    )
    acc = store.accept_mission(
        {
            "mission_id": "m-canary",
            "instruction_id": "ESTATE-P0",
            "mandate_id": "SPEC-20261115",
            "goal": GOAL,
            "acceptance_contract_digest": digest_of(GOAL),
            "risk_class": "LOW",
        }
    )
    receipt["acceptance"] = acc["state"]
    store.transition("m-canary", "READY", "estate", "dispatch")
    lease_a = store.acquire_lease(
        "m-canary",
        {
            "agent_adapter": "opencode",
            "provider": "glm",
            "model": "glm-4",
            "execution_host": "mac",
            "failure_domain": "laptop",
            "worktree_id": "wt-canary",
            "base_sha": "a" * 40,
        },
        lease_seconds=8.0,
    )
    receipt["attempt_a"] = {
        "id": lease_a["attempt_id"],
        "epoch": lease_a["lease_epoch"],
    }
    code = (
        "import sys; sys.path.insert(0, %r); "
        "from continuity.canary_worker import run_attempt_a; "
        "from continuity import MissionStore; "
        "run_attempt_a(MissionStore(%r), %r, 'm-canary', %r, %d)"
        % (os.path.dirname(HERE), db, dict(lease_a), work_dir, LINES)
    )
    child = subprocess.Popen([sys.executable, "-c", code])  # noqa: S603 -- fixed argv from local constants, no shell
    deadline = time.time() + 30
    cp = None
    while time.time() < deadline:
        cp = store.latest_checkpoint("m-canary")
        if cp is not None and cp["sequence"] >= LINES // 2:
            break
        time.sleep(0.2)
    child.send_signal(signal.SIGKILL)
    child.wait(timeout=10)
    receipt["kill"] = {
        "returncode": child.returncode,
        "by": "SIGKILL",
        "checkpoints_before_kill": cp["sequence"] if cp else 0,
    }
    if child.returncode != -signal.SIGKILL:
        print(json.dumps(receipt))
        return 2
    return stage_two(store, receipt, work_dir, lease_a, LINES, signer)


if __name__ == "__main__":
    raise SystemExit(main())
