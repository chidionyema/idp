"""Lease acquisition with compare-and-swap and monotonically increasing
fencing epochs (ESTATE-P0 INV-02, WP-02).

acquire_lease runs under BEGIN IMMEDIATE: of N simultaneous claimants exactly
one inserts the next attempt and advances the epoch; the rest raise
LeaseNotAcquired. A lease may be taken over when the holder's lease expired
or its attempt was fenced by recovery.
"""

from __future__ import annotations

import time
import uuid

from .fields import LeaseNotAcquired

CLAIMABLE_STATES = ("READY", "REASSIGNING")


class LeaseMixin:
    def acquire_lease(
        self,
        mission_id: str,
        worker: dict,
        lease_seconds: float = 300.0,
        now: float | None = None,
    ) -> dict:
        t = time.time() if now is None else now
        for field in (
            "agent_adapter",
            "provider",
            "model",
            "execution_host",
            "failure_domain",
            "worktree_id",
            "base_sha",
        ):
            if not worker.get(field):
                raise LeaseNotAcquired(f"worker record missing {field}")
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            m = cur.execute(
                "SELECT state, current_attempt_id, current_lease_epoch,"
                " retry_budget_remaining FROM missions WHERE mission_id=?",
                (mission_id,),
            ).fetchone()
            if m is None:
                cur.execute("ROLLBACK")
                raise LeaseNotAcquired(f"unknown mission {mission_id}")
            if m["state"] in CLAIMABLE_STATES:
                pass
            elif m["state"] == "LEASED":
                holder = cur.execute(
                    "SELECT lease_expires_at, state FROM mission_attempts"
                    " WHERE attempt_id=?",
                    (m["current_attempt_id"],),
                ).fetchone()
                if (
                    holder is None
                    or holder["state"] != "RUNNING"
                    or holder["lease_expires_at"] > t
                ):
                    cur.execute("ROLLBACK")
                    raise LeaseNotAcquired(f"lease held by {m['current_attempt_id']}")
            else:
                cur.execute("ROLLBACK")
                raise LeaseNotAcquired(
                    f"mission in state {m['state']} is not claimable"
                )
            # No recovery path may mint free retries after the mission's
            # authorised retry budget is exhausted. READY is the initial
            # attempt, not a retry; both expired-LEASED takeover and
            # REASSIGNING consume exactly one retry under this transaction.
            if (
                m["state"] in ("LEASED", "REASSIGNING")
                and m["retry_budget_remaining"] <= 0
            ):
                raise LeaseNotAcquired(
                    f"retry budget exhausted for mission {mission_id}"
                )
            attempt_id = f"a-{uuid.uuid4()}"
            epoch = m["current_lease_epoch"] + 1
            if m["state"] == "REASSIGNING" or m["state"] == "LEASED":
                if m["current_attempt_id"]:
                    cur.execute(
                        "UPDATE mission_attempts SET state='SUPERSEDED'"
                        " WHERE attempt_id=? AND state='RUNNING'",
                        (m["current_attempt_id"],),
                    )
            cur.execute(
                "INSERT INTO mission_attempts (attempt_id, mission_id,"
                " agent_adapter, provider, model, execution_host,"
                " failure_domain, worktree_id, base_sha, started_at,"
                " lease_epoch, lease_expires_at, last_heartbeat_at,"
                " last_progress_at, state)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    attempt_id,
                    mission_id,
                    worker["agent_adapter"],
                    worker["provider"],
                    worker["model"],
                    worker["execution_host"],
                    worker["failure_domain"],
                    worker["worktree_id"],
                    worker["base_sha"],
                    t,
                    epoch,
                    t + lease_seconds,
                    t,
                    t,
                    "RUNNING",
                ),
            )
            cur.execute(
                "UPDATE missions SET state='LEASED', current_attempt_id=?,"
                " current_lease_epoch=?, retry_budget_remaining=?"
                " WHERE mission_id=?",
                (
                    attempt_id,
                    epoch,
                    max(0, m["retry_budget_remaining"] - 1)
                    if m["state"] in ("REASSIGNING", "LEASED")
                    else m["retry_budget_remaining"],
                    mission_id,
                ),
            )
            self._event(
                mission_id,
                "LEASED",
                worker["agent_adapter"],
                "lease acquired",
                f"epoch={epoch} attempt={attempt_id}",
                attempt_id=attempt_id,
                lease_epoch=epoch,
                from_state=m["state"],
                cur=cur,
            )
            return {
                "attempt_id": attempt_id,
                "lease_epoch": epoch,
                "lease_expires_at": t + lease_seconds,
            }
