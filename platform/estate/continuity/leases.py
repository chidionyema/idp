"""Lease acquisition with compare-and-swap and monotonically increasing fencing epochs."""
from __future__ import annotations

import math
import time
import uuid

from .fields import LeaseNotAcquired

CLAIMABLE_STATES = ("READY", "REASSIGNING")


class LeaseMixin:
    def acquire_lease(self, mission_id: str, worker: dict, lease_seconds: float = 300.0, now: float | None = None, *, expected_authority: tuple[int, int, int] | None = None) -> dict:
        t = time.time() if now is None else now
        if not math.isfinite(t) or not math.isfinite(lease_seconds) or lease_seconds <= 0:
            raise LeaseNotAcquired("invalid lease clock or duration")
        for field in ("agent_adapter", "provider", "model", "execution_host", "failure_domain", "worktree_id", "base_sha"):
            if not worker.get(field):
                raise LeaseNotAcquired(f"worker record missing {field}")
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            m = cur.execute("SELECT state, current_attempt_id, current_lease_epoch, retry_budget_remaining, mandate_version, revocation_epoch FROM missions WHERE mission_id=?", (mission_id,)).fetchone()
            if m is None:
                raise LeaseNotAcquired(f"unknown mission {mission_id}")
            if m["state"] not in CLAIMABLE_STATES:
                # Expiry is an observation, not authorization to create a new
                # writer. All takeovers go through the fenced recovery path.
                raise LeaseNotAcquired(f"mission in state {m['state']} is not claimable; reconcile recovery first")
            if expected_authority is not None and expected_authority != (m["mandate_version"], m["revocation_epoch"], m["current_lease_epoch"]):
                raise LeaseNotAcquired("mission authority changed")
            recovering = m["state"] == "REASSIGNING"
            if recovering and m["retry_budget_remaining"] <= 0:
                raise LeaseNotAcquired("retry budget exhausted; obligation remains REASSIGNING")
            if m["current_attempt_id"] is not None:
                raise LeaseNotAcquired("claimable mission still has an active attempt; reconcile custody")
            attempt_id = f"a-{uuid.uuid4()}"
            epoch = m["current_lease_epoch"] + 1
            cur.execute("INSERT INTO mission_attempts (attempt_id, mission_id, agent_adapter, provider, model, execution_host, failure_domain, worktree_id, base_sha, started_at, lease_epoch, lease_expires_at, last_heartbeat_at, last_progress_at, state) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (attempt_id, mission_id, worker["agent_adapter"], worker["provider"], worker["model"], worker["execution_host"], worker["failure_domain"], worker["worktree_id"], worker["base_sha"], t, epoch, t + lease_seconds, t, t, "RUNNING"))
            cur.execute("UPDATE missions SET state='LEASED', current_attempt_id=?, current_lease_epoch=?, retry_budget_remaining=? WHERE mission_id=?", (attempt_id, epoch, m["retry_budget_remaining"] - int(recovering), mission_id))
            self._event(mission_id, "LEASED", worker["agent_adapter"], "lease acquired", f"epoch={epoch} attempt={attempt_id}", attempt_id=attempt_id, lease_epoch=epoch, from_state=m["state"], cur=cur)
            return {"attempt_id": attempt_id, "lease_epoch": epoch, "lease_expires_at": t + lease_seconds}
