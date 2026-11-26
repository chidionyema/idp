"""Conservation of objective across acceptance, correction and takeover."""

import pytest

from platform.estate.continuity.fields import CheckpointRejected
from platform.estate.continuity.store import MissionStore
from platform.estate.continuity.util import digest_of


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
        assert store.get_mission("root")["goal"] == record["goal"]
    finally:
        store.close()
