"""Fence checks and fenced mutations (ESTATE-P0 INV-03).

Every mediated write names (mission_id, attempt_id, lease_epoch); the store
refuses it unless that triple is the current authoritative owner. An expired
or superseded worker reconnecting later is refused, and so is a worker whose
mandate version is behind the mission's.
"""

from __future__ import annotations

import time

from .fields import StaleFenceError


class FenceMixin:
    def assert_fence(
        self,
        mission_id: str,
        attempt_id: str | None,
        lease_epoch: int | None,
        now: float | None = None,
        cur=None,
    ) -> dict:
        """Raise StaleFenceError unless (attempt_id, lease_epoch) owns the mission.

        Returns the mission row for the caller's transaction.
        """
        execute = (cur or self.db).execute
        m = execute(
            "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
        ).fetchone()
        if m is None:
            raise StaleFenceError(f"unknown mission {mission_id}")
        if m["current_attempt_id"] != attempt_id:
            raise StaleFenceError(
                f"attempt {attempt_id} is not current"
                f" (current={m['current_attempt_id']})"
            )
        if m["current_lease_epoch"] != lease_epoch:
            raise StaleFenceError(
                f"epoch {lease_epoch} is stale (current={m['current_lease_epoch']})"
            )
        attempt = execute(
            "SELECT lease_expires_at, state FROM mission_attempts WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()
        if attempt is None or attempt["state"] != "RUNNING":
            raise StaleFenceError(f"attempt {attempt_id} is not RUNNING")
        t = time.time() if now is None else now
        if attempt["lease_expires_at"] <= t:
            raise StaleFenceError(
                f"lease for {attempt_id} expired at {attempt['lease_expires_at']}"
            )
        return m

    def check_mandate(self, mission_row, mandate_version: int) -> None:
        if mandate_version != mission_row["mandate_version"]:
            raise StaleFenceError(
                f"mandate_version {mandate_version} != current"
                f" {mission_row['mandate_version']}"
            )

    def heartbeat(
        self,
        mission_id: str,
        attempt_id: str,
        lease_epoch: int,
        now: float | None = None,
    ) -> dict:
        t = time.time() if now is None else now
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            self.assert_fence(mission_id, attempt_id, lease_epoch, now=t, cur=cur)
            cur.execute(
                "UPDATE mission_attempts SET last_heartbeat_at=? WHERE attempt_id=?",
                (t, attempt_id),
            )
            return {
                "heartbeat_at": t,
                "note": "heartbeat does not reset progress clock",
            }

    def report_progress(
        self,
        mission_id: str,
        attempt_id: str,
        lease_epoch: int,
        evidence: str,
        now: float | None = None,
    ) -> dict:
        t = time.time() if now is None else now
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            self.assert_fence(mission_id, attempt_id, lease_epoch, now=t, cur=cur)
            cur.execute(
                "UPDATE mission_attempts SET last_progress_at=?,"
                " last_heartbeat_at=? WHERE attempt_id=?",
                (t, t, attempt_id),
            )
            cur.execute(
                "UPDATE missions SET last_verified_progress_at=? WHERE mission_id=?",
                (t, mission_id),
            )
            return {"progress_at": t, "evidence": evidence}
