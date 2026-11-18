"""Failure detection and autonomous takeover (ESTATE-P0 WP-04).

Liveness is not progress: heartbeats never reset the stagnation clock.
needs_takeover compares the mission clock against the no-progress bound and
the attempt's lease expiry. begin_recovery fences the old attempt, moves the
mission to RECOVERY_PENDING and records the failure class — no founder
prompt, ownership retained.
"""

from __future__ import annotations

import time

from .fields import InvalidTransition, RecordRejected
from .model import NO_PROGRESS_BOUND_S


class RecoveryMixin:
    def needs_takeover(
        self,
        mission_id: str,
        now: float | None = None,
        bound_s: float = NO_PROGRESS_BOUND_S,
    ) -> dict:
        t = time.time() if now is None else now
        return self._takeover_decision(mission_id, t, bound_s, self.db)

    def _takeover_decision(self, mission_id: str, t: float, bound_s: float, cur) -> dict:
        m = cur.execute("SELECT * FROM missions WHERE mission_id=?", (mission_id,)).fetchone()
        if m is None:
            raise RecordRejected(f"unknown mission {mission_id}")
        attempt = None
        if m["current_attempt_id"]:
            attempt = cur.execute(
                "SELECT * FROM mission_attempts WHERE attempt_id=?",
                (m["current_attempt_id"],),
            ).fetchone()
        reasons = []
        if m["state"] in ("OPERATING", "RECOVERY_PENDING", "REASSIGNING"):
            return {
                "mission_id": mission_id,
                "takeover": False,
                "reasons": [],
                "state": m["state"],
            }
        if m["state"] in (
            "ACCEPTED",
            "READY",
        ):
            return {
                "mission_id": mission_id,
                "takeover": False,
                "reasons": [],
                "state": m["state"],
            }
        # Active stages, including verification and promotion, require a live
        # attempt. A recovery decision is a request to reconcile pending effects,
        # not authorization to replay an external mutation.
        if attempt is None:
            reasons.append("active mission has no current attempt")
        else:
            if attempt["state"] != "RUNNING":
                reasons.append("current attempt is not RUNNING")
            if attempt["lease_expires_at"] <= t:
                reasons.append(
                    f"lease expired {t - attempt['lease_expires_at']:.0f}s ago"
                )
            anchor = attempt["last_progress_at"]
            if anchor is None:
                anchor = m["created_at"]
            if t - anchor >= bound_s:
                reasons.append(
                    f"no progress for {t - anchor:.0f}s >= bound {bound_s:.0f}s"
                )
        return {
            "mission_id": mission_id,
            "takeover": bool(reasons),
            "reasons": reasons,
            "state": m["state"],
        }

    def begin_recovery(
        self,
        mission_id: str,
        failure_class: str,
        fingerprint: str,
        actor: str = "recovery",
        now: float | None = None,
        *,
        recheck_stagnation: bool = False,
        bound_s: float = NO_PROGRESS_BOUND_S,
    ) -> dict:
        t = time.time() if now is None else now
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            # Automatic recovery must make its decision in the same transaction
            # as fencing. A delayed observation is not authority over a new lease.
            if recheck_stagnation:
                decision = self._takeover_decision(mission_id, t, bound_s, cur)
                if not decision["takeover"]:
                    return {"mission_id": mission_id, "state": decision["state"],
                            "transitioned": False, "reasons": []}
            m = cur.execute(
                "SELECT state, current_attempt_id, current_lease_epoch"
                " FROM missions WHERE mission_id=?",
                (mission_id,),
            ).fetchone()
            if m is None:
                cur.execute("ROLLBACK")
                raise RecordRejected(f"unknown mission {mission_id}")
            if m["state"] not in (
                "LEASED",
                "EXECUTING",
                "CHECKPOINTING",
                "VERIFYING",
                "PROMOTING",
                "DEPLOY_VERIFY",
            ):
                cur.execute("ROLLBACK")
                raise InvalidTransition(f"cannot begin recovery from {m['state']}")
            if m["current_attempt_id"]:
                cur.execute(
                    "UPDATE mission_attempts SET state='FAILED',"
                    " failure_class=? WHERE attempt_id=? AND state='RUNNING'",
                    (failure_class, m["current_attempt_id"]),
                )
            cur.execute(
                "UPDATE missions SET state='RECOVERY_PENDING',"
                " current_attempt_id=NULL WHERE mission_id=?",
                (mission_id,),
            )
            cur.execute(
                "INSERT INTO failure_classes (failure_class_id, fingerprint,"
                " first_seen, occurrence_count, owner, status)"
                " VALUES (?,?,?,?,?,?)"
                " ON CONFLICT(fingerprint) DO UPDATE SET"
                " occurrence_count=occurrence_count+1",
                (f"fc-{fingerprint[:24]}", fingerprint, t, 1, actor, "OPEN"),
            )
            self._event(
                mission_id,
                "RECOVERY_PENDING",
                actor,
                f"failure class {failure_class}",
                f"attempt={m['current_attempt_id']} fingerprint={fingerprint}",
                attempt_id=m["current_attempt_id"],
                lease_epoch=m["current_lease_epoch"],
                from_state=m["state"],
                cur=cur,
            )
            return {
                "mission_id": mission_id,
                "state": "RECOVERY_PENDING",
                "fenced_attempt": m["current_attempt_id"],
                "transitioned": True,
                "failure_class": failure_class,
            }

    def recover_stalled(self, mission_id: str, now: float | None = None) -> dict:
        """One supervisor transition, idempotent under replay/concurrent wakeups.

        The caller must be the existing authorized recovery coordinator. This
        fences only genuinely due attempts; it grants no external-effect replay.
        """
        return self.begin_recovery(
            mission_id, "NO_PROGRESS_OR_LEASE_EXPIRED", "continuity-stall-v1",
            actor="recovery", now=now, recheck_stagnation=True,
        )
