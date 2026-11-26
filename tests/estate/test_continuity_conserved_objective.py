"""Conservation of objective across acceptance, correction and takeover."""

import json
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
