"""Root-directed control must not confuse a detour with the mission."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "platform" / "estate"))

from continuity import InvalidTransition, MissionStore  # noqa: E402

WORKER = dict.fromkeys(
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


def accept(store, identity, parent=None, dependencies=None, retries=3):
    return store.accept_mission(
        {
            "mission_id": identity,
            "parent_mission_id": parent,
            "instruction_id": identity,
            "mandate_id": "founder",
            "goal": identity,
            "acceptance_contract_digest": identity,
            "risk_class": "LOW",
            "dependencies": dependencies or [],
            "retry_budget": retries,
        }
    )


def test_unwind_thousand_corrections_and_recover_original(tmp_path):
    store = MissionStore(tmp_path / "mission.db")
    try:
        accept(store, "restore-service")
        store.transition("restore-service", "READY", "estate", "admit")
        lease = store.acquire_lease(
            "restore-service", WORKER, now=1000, lease_seconds=3600
        )
        parent = "restore-service"
        for index in range(1000):
            child = f"correction-{index}"
            accept(store, child, parent=parent)
            parent = child
        store.heartbeat(
            "restore-service", lease["attempt_id"], lease["lease_epoch"], now=1599
        )
        decision = store.control_step(parent, now=1600)
        assert decision["root_mission_id"] == "restore-service"
        assert decision["goal"] == "restore-service"
        assert decision["target_mission_id"] == "restore-service"
        assert decision["action"] == "RECOVER"
        store.begin_recovery("restore-service", "STAGNATION", "fixture", now=1600)
        assert store.control_step(parent, now=1600)["action"] == "RESELECT"
        store.transition("restore-service", "REASSIGNING", "recovery", "select")
        new = store.acquire_lease("restore-service", WORKER, now=1601)
        assert new["lease_epoch"] > lease["lease_epoch"]
        assert store.control_step(parent, now=1602)["action"] == "CONTINUE"
    finally:
        store.close()


def test_explicit_dependency_and_cycle(tmp_path):
    store = MissionStore(tmp_path / "mission.db")
    try:
        accept(store, "root", dependencies=["required"])
        accept(store, "required", dependencies=["root"])
        accept(store, "detour", parent="root")
        with pytest.raises(InvalidTransition, match="cyclic objective dependencies"):
            store.control_step("detour")
        # Fixture repairs only the prerequisite graph, not the objective.
        store.db.execute(
            "UPDATE missions SET dependencies='[]' WHERE mission_id='required'"
        )
        result = store.control_step("detour")
        assert result["root_mission_id"] == "root"
        assert result["target_mission_id"] == "required"
        assert result["action"] == "ADMIT"
    finally:
        store.close()


def test_exhausted_retry_budget_preserves_obligation(tmp_path):
    store = MissionStore(tmp_path / "mission.db")
    try:
        accept(store, "root", retries=0)
        store.transition("root", "READY", "estate", "admit")
        store.acquire_lease("root", WORKER, now=1000, lease_seconds=1)
        store.begin_recovery("root", "WORKER_LOST", "fixture", now=1002)
        result = store.control_step("root", now=1002)
        assert result["action"] == "RECONCILE_CAPACITY"
        assert result["goal"] == "root"
        assert store.get_mission("root")["state"] == "RECOVERY_PENDING"
    finally:
        store.close()
