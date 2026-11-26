"""The ESTATE-P0 continuity canary (part 2): takeover, resume, verify, close."""

from __future__ import annotations

import base64
import hashlib
import json
import os

CLOSING = ("EXECUTING", "VERIFYING", "PROMOTING", "DEPLOY_VERIFY", "OPERATING")


def stage_two(store, receipt, work_dir, lease_a, lines, verifier_signer) -> int:
    from continuity import StaleFenceError
    from continuity.util import effect_receipt_subject

    # The parent has already observed SIGKILL and wait() returned. Do not
    # wait for another heartbeat or lease timeout to retain the obligation.
    rec = store.observe_worker_exit(
        "m-canary", lease_a["attempt_id"], lease_a["lease_epoch"],
        returncode=receipt["kill"]["returncode"], observation_ref="canary-process-wait",
    )
    receipt["takeover_detection"] = {
        "needed": rec["action"] == "RECONCILE_AND_REASSIGN",
        "reasons": [rec["failure_class"]],
    }
    receipt["fenced_attempt"] = rec["fenced_attempt"]
    store.transition("m-canary", "REASSIGNING", "recovery", "takeover")
    lease_b = store.acquire_lease(
        "m-canary",
        {
            "agent_adapter": "opencode",
            "provider": "cloud",
            "model": "other",
            "execution_host": "oci",
            "failure_domain": "cloud",
            "worktree_id": "wt-canary-b",
            "base_sha": "b" * 40,
        },
    )
    receipt["attempt_b"] = {
        "id": lease_b["attempt_id"],
        "epoch": lease_b["lease_epoch"],
    }
    try:
        store.heartbeat("m-canary", lease_a["attempt_id"], lease_a["lease_epoch"])
        receipt["zombie_rejected"] = False
        print(json.dumps(receipt))
        return 3
    except StaleFenceError:
        receipt["zombie_rejected"] = True
    artifact_data = store.restore_latest_checkpoint("m-canary")
    receipt["restored_completed_work"] = len(artifact_data["completed_work"])
    artifact = os.path.join(work_dir, "artifact.txt")
    effect = store.record_effect_intent(
        "m-canary",
        lease_b["attempt_id"],
        lease_b["lease_epoch"],
        "verify-canary-artifact",
        artifact,
        "m-canary-artifact-v1",
        {"expected_lines": [f"line-{i}" for i in range(1, lines + 1)]},
    )
    for item in artifact_data["remaining_work"]:
        with open(artifact, "a") as fh:
            fh.write(item + "\n")
    with open(artifact) as fh:
        final = [l.strip() for l in fh if l.strip()]
    want = [f"line-{i}" for i in range(1, lines + 1)]
    receipt["artifact_complete"] = final == want
    receipt["no_duplicate_lines"] = len(final) == len(set(final))
    if not (receipt["artifact_complete"] and receipt["no_duplicate_lines"]):
        print(json.dumps(receipt))
        return 4
    receipt["artifact_sha256"] = hashlib.sha256("\n".join(final).encode()).hexdigest()
    observed = {
        "sha256": receipt["artifact_sha256"],
        "complete": True,
        "no_duplicates": True,
    }
    signature = base64.b64encode(
        verifier_signer.sign(
            effect_receipt_subject(
                effect["effect_id"], observed, "canary-artifact-check"
            )
        )
    ).decode()
    store.record_receipt(
        effect["effect_id"],
        observed,
        verified_by="canary-artifact-check",
        verifier_signature=signature,
    )
    for to in CLOSING:
        store.transition(
            "m-canary",
            to,
            "attempt-b",
            to,
            attempt_id=lease_b["attempt_id"],
            lease_epoch=lease_b["lease_epoch"],
            evidence=f"effect:{effect['effect_id']}" if to == "OPERATING" else "",
        )
    receipt["final_state"] = store.get_mission("m-canary")["state"]
    events = store.db.execute(
        "SELECT COUNT(*) c FROM mission_events WHERE mission_id='m-canary'"
    ).fetchone()["c"]
    receipt["events"] = events
    receipt["operational_verdict"] = (
        "OPERATING" if receipt["final_state"] == "OPERATING" else "FAILED"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["final_state"] == "OPERATING" else 5
