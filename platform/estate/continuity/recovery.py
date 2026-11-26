"""Failure detection and autonomous takeover (ESTATE-P0 WP-04).

Liveness is not progress: heartbeats never reset the stagnation clock.
needs_takeover compares the mission clock against the no-progress bound and
the attempt's lease expiry. begin_recovery fences the old attempt, moves the
mission to RECOVERY_PENDING and records the failure class — no founder
prompt, ownership retained.
"""

from __future__ import annotations

import time

from .util import digest_of

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
        m = self._require(mission_id)
        attempt = None
        if m["current_attempt_id"]:
            attempt = self.db.execute(
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

    def observe_worker_exit(
        self,
        mission_id: str,
        attempt_id: str,
        lease_epoch: int,
        *,
        returncode: int,
        observation_ref: str,
        now: float | None = None,
    ) -> dict:
        """Trusted supervisor's process-exit boundary, never an agent verdict.

        Exit zero, natural stop, token exhaustion and crash are all attempt
        outcomes, not settlement. Only the existing verified OPERATING state
        permits normal completion. Record the failed attempt and fence it
        atomically, even if its lease expired. Reconcile uncertain external
        effects before any replay. A late exit cannot fence a successor.
        """
        if type(returncode) is not int or not isinstance(observation_ref, str):
            raise RecordRejected("invalid supervisor exit observation")
        if not observation_ref.strip() or len(observation_ref) > 512:
            raise RecordRejected("exit observation needs a bounded evidence reference")
        t = time.time() if now is None else now
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            m = cur.execute(
                "SELECT state, current_attempt_id, current_lease_epoch"
                " FROM missions WHERE mission_id=?",
                (mission_id,),
            ).fetchone()
            if m is None:
                raise RecordRejected(f"unknown mission {mission_id}")
            if (
                m["current_attempt_id"] != attempt_id
                or m["current_lease_epoch"] != lease_epoch
            ):
                return {"state": m["state"], "action": "IGNORE_STALE_EXIT"}
            if m["state"] == "OPERATING":
                return {"state": "OPERATING", "action": "SETTLED"}
            attempt = cur.execute(
                "SELECT state, agent_adapter FROM mission_attempts"
                " WHERE mission_id=? AND attempt_id=? AND lease_epoch=?",
                (mission_id, attempt_id, lease_epoch),
            ).fetchone()
            if attempt is None or attempt["state"] != "RUNNING":
                raise RecordRejected("exit observation has no active attempt")
            if m["state"] not in (
                "LEASED", "EXECUTING", "CHECKPOINTING", "VERIFYING",
                "PROMOTING", "DEPLOY_VERIFY",
            ):
                raise InvalidTransition("exit observation outside active mission")
            failure_class = (
                "UNSETTLED_WORKER_EXIT" if returncode == 0 else "WORKER_EXIT_FAILURE"
            )
            fingerprint = digest_of({
                "class": failure_class,
                "adapter": attempt["agent_adapter"],
                "returncode": returncode,
            })
            result = self._recover_in_transaction(
                cur, m, mission_id, failure_class, fingerprint, "recovery", t,
                evidence_suffix=f" exit={returncode} observation={digest_of(observation_ref)}",
            )
            return {
                **result,
                "action": "RECONCILE_AND_REASSIGN",
                "settled": False,
            }

    def begin_recovery(
        self,
        mission_id: str,
        failure_class: str,
        fingerprint: str,
        actor: str = "recovery",
        now: float | None = None,
    ) -> dict:
        t = time.time() if now is None else now
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
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
            return self._recover_in_transaction(
                cur, m, mission_id, failure_class, fingerprint, actor, t
            )

    def _recover_in_transaction(
        self, cur, m, mission_id, failure_class, fingerprint, actor, t,
        evidence_suffix="",
    ) -> dict:
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
            f"attempt={m['current_attempt_id']} fingerprint={fingerprint}" + evidence_suffix,
            attempt_id=m["current_attempt_id"],
            lease_epoch=m["current_lease_epoch"],
            from_state=m["state"],
            cur=cur,
        )
        return {
            "mission_id": mission_id,
            "state": "RECOVERY_PENDING",
            "fenced_attempt": m["current_attempt_id"],
            "failure_class": failure_class,
        }
