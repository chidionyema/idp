"""Retry budgets are enforced by the durable lease transaction, not by narration."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform" / "estate"))
from continuity import LeaseNotAcquired, MissionStore  # noqa: E402


WORKER = {
    "agent_adapter": "legion",
    "provider": "test",
    "model": "test",
    "execution_host": "cloud",
    "failure_domain": "runner",
    "worktree_id": "worktree-a",
    "base_sha": "a" * 40,
}


def mission(tmp_path, budget):
    store = MissionStore(tmp_path / "retry-budget.sqlite")
    store.accept_mission(
        {
            "mission_id": "m-budget",
            "instruction_id": "idp#7443",
            "mandate_id": "founder",
            "goal": "settle verified external effect",
            "acceptance_contract_digest": "a" * 64,
            "risk_class": "HIGH",
            "retry_budget": budget,
        }
    )
    store.transition("m-budget", "READY", "estate", "dispatch")
    return store


def test_zero_retry_budget_still_permits_one_initial_execution(tmp_path):
    store = mission(tmp_path, budget=0)
    at = time.time()
    first = store.acquire_lease("m-budget", WORKER, now=at, lease_seconds=1)
    assert first["lease_epoch"] == 1
    assert store.get_mission("m-budget")["retry_budget_remaining"] == 0
    store.begin_recovery("m-budget", "WORKER_LOST", "zero-retry")
    store.transition("m-budget", "REASSIGNING", "recovery", "takeover")
    with pytest.raises(LeaseNotAcquired, match="retry budget exhausted"):
        store.acquire_lease("m-budget", WORKER, now=at + 2)
    assert store.get_mission("m-budget")["state"] == "REASSIGNING"
    assert store.get_mission("m-budget")["current_lease_epoch"] == 1
    store.close()


def test_expired_lease_takeover_consumes_budget_exactly_once(tmp_path):
    store = mission(tmp_path, budget=1)
    at = time.time()
    first = store.acquire_lease("m-budget", WORKER, now=at, lease_seconds=1)
    with pytest.raises(LeaseNotAcquired, match="lease held"):
        store.acquire_lease("m-budget", WORKER, now=at + 0.5)
    assert store.get_mission("m-budget")["retry_budget_remaining"] == 1
    second = store.acquire_lease("m-budget", WORKER, now=at + 2, lease_seconds=1)
    assert second["lease_epoch"] == 2
    assert second["attempt_id"] != first["attempt_id"]
    assert store.get_mission("m-budget")["retry_budget_remaining"] == 0
    with pytest.raises(LeaseNotAcquired, match="retry budget exhausted"):
        store.acquire_lease("m-budget", WORKER, now=at + 4, lease_seconds=1)
    assert store.get_mission("m-budget")["current_lease_epoch"] == 2
    store.close()


def test_recovery_reassignment_consumes_budget_and_stays_fenced(tmp_path):
    store = mission(tmp_path, budget=1)
    at = time.time()
    first = store.acquire_lease("m-budget", WORKER, now=at, lease_seconds=50)
    store.begin_recovery("m-budget", "WORKER_LOST", "first-recovery")
    store.transition("m-budget", "REASSIGNING", "recovery", "takeover")
    second = store.acquire_lease("m-budget", WORKER, now=at + 1, lease_seconds=50)
    assert second["lease_epoch"] == first["lease_epoch"] + 1
    assert store.get_mission("m-budget")["retry_budget_remaining"] == 0
    store.begin_recovery("m-budget", "WORKER_LOST", "second-recovery")
    store.transition("m-budget", "REASSIGNING", "recovery", "takeover")
    with pytest.raises(LeaseNotAcquired, match="retry budget exhausted"):
        store.acquire_lease("m-budget", WORKER, now=at + 2)
    assert store.get_mission("m-budget")["current_lease_epoch"] == 2
    store.close()
