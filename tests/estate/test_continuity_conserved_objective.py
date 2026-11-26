"""Conservation of objective across acceptance, correction and takeover."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "platform" / "estate"))

from continuity.fields import CheckpointRejected  # noqa: E402
from continuity.store import MissionStore  # noqa: E402
from continuity.util import digest_of  # noqa: E402


def test_correction_cannot_replace_accepted_objective(tmp_path):
    store = MissionStore(tmp_path / "custody.db")
    record = {
        "mission_id": "root",
        "instruction_id": "instruction",
        "mandate_id": "mandate",
        "goal": "restore authenticated remote inference",
        "acceptance_contract_digest": "contract",
        "risk_class": "R",
    }
    try:
        with pytest.raises(ValueError):
            store.accept_mission(record, {"goal_digest": digest_of("explain")})
        store.accept_mission(record)
        assert store.restore_latest_checkpoint("root")["goal_digest"] == digest_of(
            record["goal"]
        )
        with pytest.raises(ValueError):
            store.accept_mission({**record, "goal": "explain"})
        assert store.accept_mission(record)["duplicate"]
        store.transition("root", "READY", "estate", "admit")
        worker = dict.fromkeys(
            (
                "agent_adapter",
                "provider",
                "model",
                "execution_host",
                "failure_domain",
                "worktree_id",
                "base_sha",
            ),
            "fixture",
        )
        lease = store.acquire_lease("root", worker, lease_seconds=3600, now=1000)
        payload = {
            "source_revision": "fixture",
            "next_admissible_action": "resume original work",
        }
        for index in range(1000):
            with pytest.raises(CheckpointRejected):
                store.write_checkpoint(
                    "root",
                    lease["attempt_id"],
                    lease["lease_epoch"],
                    {**payload, "goal_digest": digest_of(f"correction {index}")},
                    now=1001,
                )
        store.write_checkpoint(
            "root", lease["attempt_id"], lease["lease_epoch"], payload, now=1001
        )
        assert store.restore_latest_checkpoint("root")["goal_digest"] == digest_of(
            record["goal"]
        )
        store.begin_recovery("root", "WORKER_LOST", "fixture-failure", now=1002)
        store.transition("root", "REASSIGNING", "recovery", "takeover", now=1002)
        successor = store.acquire_lease("root", worker, now=1003)
        assert successor["lease_epoch"] == lease["lease_epoch"] + 1
        store.close()
        store = MissionStore(tmp_path / "custody.db")
        restored = store.restore_latest_checkpoint("root")
        assert restored["goal_digest"] == digest_of(record["goal"])
        assert restored["next_admissible_action"] == "resume original work"
        assert store.get_mission("root")["goal"] == record["goal"]
    finally:
        store.close()


def test_legacy_checkpoint_uses_custody_goal(tmp_path):
    store = MissionStore(tmp_path / "legacy.db")
    try:
        store.accept_mission(
            {
                "mission_id": "legacy",
                "instruction_id": "instruction",
                "mandate_id": "mandate",
                "goal": "original",
                "acceptance_contract_digest": "contract",
                "risk_class": "LOW",
            }
        )
        store.transition("legacy", "READY", "estate", "admit")
        worker = dict.fromkeys(
            (
                "agent_adapter",
                "provider",
                "model",
                "execution_host",
                "failure_domain",
                "worktree_id",
                "base_sha",
            ),
            "fixture",
        )
        lease = store.acquire_lease("legacy", worker, now=1000)
        store.write_checkpoint(
            "legacy",
            lease["attempt_id"],
            lease["lease_epoch"],
            {"source_revision": "fixture", "next_admissible_action": "resume"},
            now=1001,
        )
        checkpoint = store.latest_checkpoint("legacy")
        artifact = json.loads(checkpoint["artifact_json"])
        del artifact["goal_digest"]
        digest = digest_of({k: v for k, v in artifact.items() if k != "created_at"})
        # Construct the exact pre-invariant checkpoint shape.
        store.db.execute(
            "UPDATE mission_checkpoints SET artifact_json=?, goal_digest='',"
            " content_digest=? WHERE checkpoint_id=?",
            (json.dumps(artifact), digest, checkpoint["checkpoint_id"]),
        )
        assert store.restore_latest_checkpoint("legacy")["goal_digest"] == digest_of(
            "original"
        )
    finally:
        store.close()


def test_zero_exit_is_not_yield_and_successor_is_fenced(tmp_path):
    from continuity.fields import StaleFenceError

    path = tmp_path / "exit-custody.db"
    store = MissionStore(path)
    record = {
        "mission_id": "root",
        "instruction_id": "one-instruction",
        "mandate_id": "founder",
        "goal": "produce verified artifact",
        "acceptance_contract_digest": "contract",
        "risk_class": "LOW",
        "retry_budget": 1,
    }
    worker = dict.fromkeys(
        (
            "agent_adapter",
            "provider",
            "model",
            "execution_host",
            "failure_domain",
            "worktree_id",
            "base_sha",
        ),
        "fixture",
    )
    store.accept_mission(record)
    store.transition("root", "READY", "estate", "admit")
    first = store.acquire_lease("root", worker, now=1000, lease_seconds=100)
    store.transition(
        "root",
        "EXECUTING",
        "worker",
        "start",
        attempt_id=first["attempt_id"],
        lease_epoch=1,
        now=1001,
    )
    child = subprocess.run(  # noqa: S603 - fixed fixture process
        [sys.executable, "-c", "print('All done. Everything is green.')"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert child.returncode == 0
    result = store.observe_worker_exit(
        "root",
        first["attempt_id"],
        1,
        returncode=child.returncode,
        observation_ref="trusted-process-wait",
        now=1002,
    )
    assert result["action"] == "RECONCILE_AND_REASSIGN"
    assert result["settled"] is False
    assert store.get_mission("root")["state"] == "RECOVERY_PENDING"
    assert store.get_mission("root")["goal"] == record["goal"]
    assert store.get_mission("root")["retry_budget_remaining"] == 1
    with pytest.raises(StaleFenceError):
        store.heartbeat("root", first["attempt_id"], 1, now=1003)
    store.close()
    store = MissionStore(path)
    assert store.restore_latest_checkpoint("root")["goal_digest"] == digest_of(
        record["goal"]
    )
    store.transition("root", "REASSIGNING", "recovery", "takeover", now=1003)
    second = store.acquire_lease(
        "root", {**worker, "provider": "alternative"}, now=1004
    )
    assert second["lease_epoch"] == 2
    stale = store.observe_worker_exit(
        "root",
        first["attempt_id"],
        1,
        returncode=0,
        observation_ref="trusted-process-wait",
        now=1005,
    )
    assert stale["action"] == "IGNORE_STALE_EXIT"
    assert store.get_mission("root")["current_attempt_id"] == second["attempt_id"]
    assert store.get_mission("root")["retry_budget_remaining"] == 0
    assert store.db.execute("SELECT COUNT(*) FROM failure_classes").fetchone()[0] == 1
    store.close()
