"""The ESTATE-P0 continuity canary worker (attempt A).

Does real work (appends numbered lines to the artifact), checkpoints after
each line, then keeps running until killed. The parent kills it with SIGKILL
mid-task; no graceful shutdown is available.
"""

from __future__ import annotations

import os
import time


def run_attempt_a(store, lease, mission_id: str, work_dir: str, lines: int) -> None:
    artifact = os.path.join(work_dir, "artifact.txt")
    store.transition(
        mission_id,
        "EXECUTING",
        "attempt-a",
        "start",
        attempt_id=lease["attempt_id"],
        lease_epoch=lease["lease_epoch"],
    )
    done = 0
    while done < lines:
        with open(artifact, "a") as fh:
            fh.write(f"line-{done + 1}\n")
        done += 1
        store.write_checkpoint(
            mission_id,
            lease["attempt_id"],
            lease["lease_epoch"],
            {
                "source_revision": "b" * 40,
                "next_admissible_action": "append remaining lines",
                "completed_work": [f"line-{i}" for i in range(1, done + 1)],
                "remaining_work": [f"line-{i}" for i in range(done + 1, lines + 1)],
                "worktree_manifest_digest": "m" * 64,
            },
        )
        store.heartbeat(mission_id, lease["attempt_id"], lease["lease_epoch"])
        time.sleep(0.3)
    time.sleep(60)
