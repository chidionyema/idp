"""Canonical state-machine transitions (ESTATE-P0 section 5).

No PR, CI run or merge event can skip a stage: only transition() moves a
mission, it validates legality + fence + mandate, and every move leaves an
immutable causally-linked receipt in mission_events.
"""

from __future__ import annotations

import time

from .fence import FenceMixin
from .fields import InvalidTransition, StaleFenceError
from .model import TRANSITIONS

UNFENCED_TRANSITIONS = {
    "ACCEPTED->READY": "estate",
    "RECOVERY_PENDING->REASSIGNING": "recovery",
}


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
