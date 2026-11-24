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
from .util import verify_effect_receipt

UNFENCED_TRANSITIONS = {
    "ACCEPTED->READY": "estate",
    "RECOVERY_PENDING->REASSIGNING": "recovery",
}


def _require_verified_operational_effect(
    cur,
    mission_id,
    attempt_id,
    lease_epoch,
    mandate_version,
    actor,
    evidence,
    now=None,
    trusted_keys=None,
):
    """Require an independent effect from this mission and mandate.

    A successor may inherit a verified effect from a fenced predecessor,
    but never acquire the previous worker's authority. The CURRENT lease
    is checked by the transition caller; the effect's source custody,
    mandate, signature and non-executor observer remain independently bound.
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
        "SELECT e.state, e.reconciliation_status, e.external_receipt,"
        " e.observed_at, e.verified_by, e.attempt_id AS source_attempt,"
        " e.lease_epoch AS source_epoch, src.agent_adapter AS source_adapter"
        " FROM external_effects e JOIN mission_attempts src"
        " ON src.attempt_id=e.attempt_id AND src.mission_id=e.mission_id"
        " AND src.lease_epoch=e.lease_epoch"
        " WHERE e.effect_id=? AND e.mission_id=? AND e.mandate_version=?"
        " AND e.lease_epoch<=?",
        (evidence[7:], mission_id, mandate_version, lease_epoch),
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
    # The transition actor is a caller-supplied label. Compare the verifier
    # with the actual leased harness identity too, or an agent can pass a
    # different actor label and count its own observation as independent.
    holder = cur.execute(
        "SELECT agent_adapter FROM mission_attempts WHERE attempt_id=?"
        " AND mission_id=? AND lease_epoch=?",
        (attempt_id, mission_id, lease_epoch),
    ).fetchone()
    if holder is None or (
        effect["verified_by"].strip().casefold()
        == holder["agent_adapter"].strip().casefold()
    ):
        raise InvalidTransition(
            "OPERATING refused: leased executor cannot attest its own outcome"
        )
    # A former worker cannot be promoted into its own verifier by fencing
    # that worker and assigning a different executor. Independence is judged
    # against BOTH historical and current execution identities.
    source_actors = cur.execute(
        "SELECT actor FROM mission_events WHERE mission_id=?"
        " AND attempt_id=? AND to_state IN ('EXECUTING',"
        " 'CHECKPOINTING', 'VERIFYING', 'PROMOTING', 'DEPLOY_VERIFY')",
        (mission_id, effect["source_attempt"]),
    ).fetchall()
    source_identities = {
        item["actor"].strip().casefold() for item in source_actors if item["actor"]
    }
    source_identities.add(effect["source_adapter"].strip().casefold())
    if effect["verified_by"].strip().casefold() in source_identities:
        raise InvalidTransition(
            "OPERATING refused: predecessor executor cannot self-certify"
        )
    try:
        receipt = json.loads(effect["external_receipt"])
    except (TypeError, ValueError):
        receipt = None
    if not isinstance(receipt, dict) or not receipt:
        raise InvalidTransition("OPERATING refused: effect receipt is missing or empty")
    try:
        verify_effect_receipt(
            evidence[7:],
            receipt,
            effect["verified_by"],
            trusted_keys or {},
        )
    except (ValueError, TypeError) as exc:
        raise InvalidTransition(
            "OPERATING refused: external receipt has no trusted observer seal"
        ) from exc


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
                    trusted_keys=self._trusted_verifier_keys,
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
