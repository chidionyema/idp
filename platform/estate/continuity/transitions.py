"""Canonical state-machine transitions (ESTATE-P0 section 5).

No PR, CI run or merge event can skip a stage: only transition() moves a
mission, it validates legality + fence + mandate, and every move leaves an
immutable causally-linked receipt in mission_events.
"""

from __future__ import annotations

import json
import time

from .fence import FenceMixin
from .fields import InvalidTransition, StaleFenceError
from .model import TRANSITIONS

UNFENCED_TRANSITIONS = {
    "ACCEPTED->READY": "estate",
    "RECOVERY_PENDING->REASSIGNING": "recovery",
}


def _require_verified_operational_effect(
    cur, mission_id, attempt_id, lease_epoch, mandate_version, actor, evidence,
    now=None,
):
    """Require a dated, reconciled effect from this exact mission attempt.

    This enforces evidence custody, not the external observer's integrity.
    External verifier authentication must be enforced at receipt admission.
    """
    if (
        not isinstance(evidence, str)
        or not evidence.startswith("effect:")
        or not evidence[7:]
    ):
        raise InvalidTransition(
            "OPERATING requires evidence='effect:<reconciled-effect-id>'"
        )
    effect = cur.execute(
        "SELECT state, reconciliation_status, external_receipt, observed_at,"
        " verified_by"
        " FROM external_effects WHERE effect_id=? AND mission_id=? AND attempt_id=?"
        " AND lease_epoch=? AND mandate_version=?",
        (evidence[7:], mission_id, attempt_id, lease_epoch, mandate_version),
    ).fetchone()
    if (
        effect is None
        or effect["state"] != "OBSERVED"
        or effect["reconciliation_status"] != "RECONCILED"
    ):
        raise InvalidTransition(
            "OPERATING refused: matching reconciled external effect not found"
        )
    if effect["observed_at"] is None or not effect["verified_by"]:
        raise InvalidTransition(
            "OPERATING refused: effect has no dated verifier observation"
        )
    if effect["observed_at"] > (time.time() if now is None else now):
        raise InvalidTransition(
            "OPERATING refused: verifier observation is dated in the future"
        )
    if effect["verified_by"].strip().casefold() == actor.strip().casefold():
        raise InvalidTransition(
            "OPERATING refused: executor cannot attest its own outcome"
        )
    try:
        receipt = json.loads(effect["external_receipt"])
    except (TypeError, ValueError):
        receipt = None
    if not isinstance(receipt, dict) or not receipt:
        raise InvalidTransition("OPERATING refused: effect receipt is missing or empty")


class TransitionMixin(FenceMixin):
    def transition(
        self,
        mission_id: str,
        to_state: str,
        actor: str,
        cause: str,
        evidence: str = "",
        attempt_id: str | None = None,
        lease_epoch: int | None = None,
        mandate_version: int | None = None,
        now: float | None = None,
    ) -> dict:
        t = time.time() if now is None else now
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            m = cur.execute(
                "SELECT state, current_attempt_id, current_lease_epoch,"
                " mandate_version FROM missions WHERE mission_id=?",
                (mission_id,),
            ).fetchone()
            if m is None:
                cur.execute("ROLLBACK")
                raise InvalidTransition(f"unknown mission {mission_id}")
            key = f"{m['state']}->{to_state}"
            if to_state not in TRANSITIONS[m["state"]]:
                if attempt_id is not None and lease_epoch is not None:
                    self.assert_fence(
                        mission_id, attempt_id, lease_epoch, now=t, cur=cur
                    )
                cur.execute("ROLLBACK")
                raise InvalidTransition(f"illegal transition {key}")
            if key in UNFENCED_TRANSITIONS:
                if (
                    mandate_version is not None
                    and mandate_version != m["mandate_version"]
                ):
                    cur.execute("ROLLBACK")
                    raise StaleFenceError("mandate version mismatch")
            else:
                if attempt_id is None or lease_epoch is None:
                    cur.execute("ROLLBACK")
                    raise StaleFenceError(
                        f"transition {key} requires attempt_id and lease_epoch"
                    )
                fenced = self.assert_fence(
                    mission_id, attempt_id, lease_epoch, now=t, cur=cur
                )
                if mandate_version is not None:
                    self.check_mandate(fenced, mandate_version)
            if to_state == "OPERATING":
                _require_verified_operational_effect(
                    cur,
                    mission_id,
                    attempt_id,
                    lease_epoch,
                    m["mandate_version"],
                    actor,
                    evidence,
                    now=t,
                )
            cur.execute(
                "UPDATE missions SET state=? WHERE mission_id=?",
                (to_state, mission_id),
            )
            if to_state == "OPERATING":
                cur.execute(
                    "UPDATE mission_attempts SET state='COMPLETED'"
                    " WHERE attempt_id=? AND state='RUNNING'",
                    (m["current_attempt_id"],),
                )
            self._event(
                mission_id,
                to_state,
                actor,
                cause,
                evidence,
                attempt_id=attempt_id,
                lease_epoch=lease_epoch,
                from_state=m["state"],
                cur=cur,
            )
            return {
                "mission_id": mission_id,
                "state": to_state,
                "transition": key,
                "at": t,
            }
