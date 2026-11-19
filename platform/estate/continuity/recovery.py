"""Failure detection and autonomous takeover in the existing mission store."""
from __future__ import annotations

import copy
import hashlib
import math
import time

from .fields import InvalidTransition, LeaseNotAcquired, RecordRejected
from .model import NO_PROGRESS_BOUND_S
from .recovery_policy import RecoveryRefused, plan_recovery

ACTIVE = frozenset({"LEASED", "EXECUTING", "CHECKPOINTING", "VERIFYING", "PROMOTING", "DEPLOY_VERIFY"})


def _reasons(m, attempt, t, bound_s):
    if not math.isfinite(t) or not math.isfinite(bound_s) or bound_s <= 0:
        return []
    if m["state"] not in ACTIVE:
        return []
    if attempt is None:
        return ["active mission has no current attempt"]
    reasons = []
    if attempt["state"] != "RUNNING":
        reasons.append("current attempt is not RUNNING")
    if not math.isfinite(attempt["lease_expires_at"]):
        return []
    if attempt["lease_expires_at"] <= t:
        reasons.append(f"lease expired {t - attempt['lease_expires_at']:.0f}s ago")
    anchor = attempt["last_progress_at"]
    if anchor is None:
        anchor = m["created_at"]
    if not math.isfinite(anchor) or anchor > t:
        return []
    if t - anchor >= bound_s:
        reasons.append(f"no progress for {t - anchor:.0f}s >= bound {bound_s:.0f}s")
    return reasons


class RecoveryMixin:
    def needs_takeover(self, mission_id: str, now: float | None = None, bound_s: float = NO_PROGRESS_BOUND_S) -> dict:
        t = time.time() if now is None else now
        m = self._require(mission_id)
        attempt = self.db.execute("SELECT * FROM mission_attempts WHERE attempt_id=?", (m["current_attempt_id"],)).fetchone()
        reasons = _reasons(m, attempt, t, bound_s)
        return {"mission_id": mission_id, "takeover": bool(reasons), "reasons": reasons,
                "state": m["state"], "attempt_id": m["current_attempt_id"],
                "lease_epoch": m.get("current_lease_epoch"),
                "recovery_due": bool(reasons) or m["state"] in ("RECOVERY_PENDING", "REASSIGNING")}

    def begin_recovery(self, mission_id: str, failure_class: str, fingerprint: str,
                       actor: str = "recovery", now: float | None = None, *,
                       expected_epoch: int | None = None, expected_attempt: str | None = None,
                       expected_authority: tuple[int, int] | None = None) -> dict:
        t = time.time() if now is None else now
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            m = cur.execute("SELECT * FROM missions WHERE mission_id=?", (mission_id,)).fetchone()
            if m is None:
                raise RecordRejected(f"unknown mission {mission_id}")
            if m["state"] not in ACTIVE:
                raise InvalidTransition(f"cannot begin recovery from {m['state']}")
            if expected_authority is not None and expected_authority != (m["mandate_version"], m["revocation_epoch"]):
                raise InvalidTransition("stale recovery authority")
            if expected_epoch is not None and (m["current_lease_epoch"] != expected_epoch or m["current_attempt_id"] != expected_attempt):
                raise InvalidTransition("stale takeover observation")
            attempt = cur.execute("SELECT * FROM mission_attempts WHERE attempt_id=?", (m["current_attempt_id"],)).fetchone()
            # The detector and the fence are not separate authorities. A delayed
            # observer must not kill a successor or a worker that progressed.
            if not _reasons(m, attempt, t, NO_PROGRESS_BOUND_S):
                raise InvalidTransition("attempt recovered before fence commit")
            if m["current_attempt_id"]:
                cur.execute("UPDATE mission_attempts SET state='FAILED', failure_class=? WHERE attempt_id=? AND state='RUNNING'", (failure_class, m["current_attempt_id"]))
            cur.execute("UPDATE missions SET state='RECOVERY_PENDING', current_attempt_id=NULL WHERE mission_id=?", (mission_id,))
            cur.execute("INSERT INTO failure_classes (failure_class_id, fingerprint, first_seen, occurrence_count, owner, status) VALUES (?,?,?,?,?,?) ON CONFLICT(fingerprint) DO UPDATE SET occurrence_count=occurrence_count+1", ("fc-" + hashlib.sha256(fingerprint.encode()).hexdigest()[:24], fingerprint, t, 1, actor, "OPEN"))
            self._event(mission_id, "RECOVERY_PENDING", actor, f"failure class {failure_class}", f"attempt={m['current_attempt_id']} fingerprint={fingerprint}", attempt_id=m["current_attempt_id"], lease_epoch=m["current_lease_epoch"], from_state=m["state"], cur=cur)
            return {"mission_id": mission_id, "state": "RECOVERY_PENDING", "fenced_attempt": m["current_attempt_id"], "failure_class": failure_class}

    def reconcile_fault(self, mission_id, snapshot, authenticate, dispatch, verify_dispatch, *, now=None):
        """One Chronos reconciliation tick; existing authorized Legion adapter dispatches.

        A committed lease precedes dispatch. A lost ACK does NOT authorize
        resending; expiry/fence triggers another tick. The successor reconciles
        old effects before doing new work. An ACK is never settlement.
        """
        t = time.time() if now is None else now
        mission = self._require(mission_id)
        if mission["state"] == "OPERATING":
            return {"status": "VERIFY_EXISTING_OPERATING"}
        try:
            # No unapproved expenditure. An external cost authority can extend
            # the offer contract later; this recovery path is zero marginal cost.
            plan = plan_recovery(snapshot, authenticate, now=t, mission_id=mission_id)
        except RecoveryRefused as exc:
            return {"status": "HOLD", "reason": str(exc)}
        try:
            if (mission["mandate_version"], mission["revocation_epoch"], mission["current_lease_epoch"], mission["current_attempt_id"]) != (plan.mandate_version, plan.revocation_epoch, plan.lease_epoch, plan.attempt_id):
                return {"status": "HOLD", "reason": "stale mission authority"}
            observed = self.needs_takeover(mission_id, now=t)
            if (observed["lease_epoch"], observed["attempt_id"]) != (plan.lease_epoch, plan.attempt_id):
                return {"status": "HOLD", "reason": "stale attempt observation"}
            if observed["takeover"]:
                self.begin_recovery(mission_id, plan.kind, plan.key, actor="recovery", now=t,
                                    expected_epoch=observed["lease_epoch"], expected_attempt=observed["attempt_id"],
                                    expected_authority=(plan.mandate_version, plan.revocation_epoch))
            state = self._require(mission_id)["state"]
            if state == "RECOVERY_PENDING":
                self.transition(mission_id, "REASSIGNING", "recovery", "resume durable recovery", now=t)
                state = "REASSIGNING"
            if state not in ("READY", "REASSIGNING"):
                return {"status": "WAIT", "state": state}
            pending = self.pending_effects(mission_id)
            t = time.time() if now is None else now
            remaining = plan.expires_at - t
            if not math.isfinite(remaining) or remaining <= 0:
                return {"status": "HOLD", "reason": "admission expired"}
            lease = self.acquire_lease(mission_id, plan.worker, lease_seconds=min(300.0, remaining), now=t, expected_authority=(plan.mandate_version, plan.revocation_epoch, plan.lease_epoch))
        except (InvalidTransition, LeaseNotAcquired) as exc:
            return {"status": "HOLD", "reason": str(exc)}
        payload = {"mission_id": mission_id, "attempt_id": lease["attempt_id"], "lease_epoch": lease["lease_epoch"],
                   "plan_key": plan.key, "action": plan.action, "target": plan.target, "revision": plan.revision,
                   "executor": plan.executor["principal"], "verifier": plan.verifier["principal"],
                   "mandate_version": plan.mandate_version, "revocation_epoch": plan.revocation_epoch,
                   "expires_at": lease["lease_expires_at"], "reconcile_only": bool(pending), "pending_effects": pending}
        try:
            if now is None and time.time() >= lease["lease_expires_at"]:
                return {"status": "DISPATCH_UNCONFIRMED", "lease": lease, "plan_key": plan.key}
            ack = dispatch(copy.deepcopy(payload))
            valid = (isinstance(ack, dict) and ack.get("accepted") is True
                     and all(k in ack and type(ack[k]) is type(v) and ack[k] == v for k, v in payload.items())
                     and verify_dispatch(copy.deepcopy(ack), copy.deepcopy(payload)) is True)
        except Exception:
            valid = False
        return {"status": "DISPATCH_ACCEPTED" if valid else "DISPATCH_UNCONFIRMED", "lease": lease, "plan_key": plan.key}
