"""Durable external-effect intents and receipts (ESTATE-P0 INV-04, WP-06).

record_effect_intent persists the idempotency key BEFORE the operation runs
and refuses a second intent under the same key with different content.
record_receipt stores only what authoritative external state actually
returned. pending_effects lists what a successor must reconcile before
retrying — at-least-once delivery never becomes exactly-once side effects.
"""

from __future__ import annotations

import time
import uuid

from .fence import FenceMixin
from .fields import DuplicateEffect, StaleFenceError
from .util import canonical, digest_of


class EffectsMixin(FenceMixin):
    def record_effect_intent(
        self,
        mission_id: str,
        attempt_id: str,
        lease_epoch: int,
        operation: str,
        target: str,
        idempotency_key: str,
        intent: dict,
        mandate_version: int | None = None,
        now: float | None = None,
    ) -> dict:
        t = time.time() if now is None else now
        intent_digest = digest_of(intent)
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            m = self.assert_fence(mission_id, attempt_id, lease_epoch, now=t, cur=cur)
            if mandate_version is None:
                mandate_version = m["mandate_version"]
            elif mandate_version != m["mandate_version"]:
                cur.execute("ROLLBACK")
                raise StaleFenceError("mandate version mismatch")
            existing = cur.execute(
                "SELECT effect_id, mission_id, operation, target,"
                " intent_digest, state FROM external_effects"
                " WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                # Retry is permitted only for the SAME mission, operation,
                # target, and payload. The key is global, but an identical
                # payload under a different mission is not shared custody.
                if (
                    existing["mission_id"] != mission_id
                    or existing["operation"] != operation
                    or existing["target"] != target
                    or existing["intent_digest"] != intent_digest
                ):
                    raise DuplicateEffect(
                        f"idempotency key {idempotency_key} already bound to"
                        " another mission, operation, target or intent"
                    )
                cur.execute("ROLLBACK")
                return {
                    "effect_id": existing["effect_id"],
                    "state": existing["state"],
                    "duplicate": True,
                }
            effect_id = f"e-{uuid.uuid4()}"
            cur.execute(
                "INSERT INTO external_effects (effect_id, mission_id,"
                " attempt_id, lease_epoch, mandate_version, operation, target,"
                " idempotency_key, intent_digest, state)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    effect_id,
                    mission_id,
                    attempt_id,
                    lease_epoch,
                    mandate_version,
                    operation,
                    target,
                    idempotency_key,
                    intent_digest,
                    "INTENDED",
                ),
            )
            return {
                "effect_id": effect_id,
                "state": "INTENDED",
                "intent_digest": intent_digest,
                "duplicate": False,
            }

    def record_receipt(
        self,
        effect_id: str,
        receipt: dict,
        verified_by: str,
        observed_state: str = "OBSERVED",
        reconciliation_status: str = "RECONCILED",
        now: float | None = None,
    ) -> dict:
        t = time.time() if now is None else now
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            row = cur.execute(
                "SELECT state, reconciliation_status, external_receipt, verified_by"
                " FROM external_effects WHERE effect_id=?",
                (effect_id,),
            ).fetchone()
            if row is None:
                cur.execute("ROLLBACK")
                raise DuplicateEffect(f"unknown effect {effect_id}")
            # Compare the STORED reconciliation state, never the caller's desired
            # state. An OBSERVED/AMBIGUOUS receipt must remain correctable after
            # an independent external reconciliation; otherwise a task can
            # remain permanently stuck despite genuine observed success.
            if (
                row["state"] == "OBSERVED"
                and row["reconciliation_status"] == "RECONCILED"
            ):
                if (
                    observed_state != "OBSERVED"
                    or reconciliation_status != "RECONCILED"
                    or canonical(receipt) != row["external_receipt"]
                    or verified_by != row["verified_by"]
                ):
                    raise DuplicateEffect(
                        f"effect {effect_id} already has an immutable "
                        "reconciled receipt"
                    )
                return {
                    "effect_id": effect_id,
                    "state": row["state"],
                    "duplicate": True,
                }
            cur.execute(
                "UPDATE external_effects SET state=?, external_receipt=?,"
                " observed_at=?, verified_by=?, reconciliation_status=?"
                " WHERE effect_id=?",
                (
                    observed_state,
                    canonical(receipt),
                    t,
                    verified_by,
                    reconciliation_status,
                    effect_id,
                ),
            )
            return {
                "effect_id": effect_id,
                "state": observed_state,
                "observed_at": t,
                "duplicate": False,
            }

    def pending_effects(self, mission_id: str) -> list:
        rows = self.db.execute(
            "SELECT effect_id, operation, target, idempotency_key, state,"
            " reconciliation_status FROM external_effects WHERE mission_id=?"
            " AND reconciliation_status != 'RECONCILED'",
            (mission_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def reconcile_effect(
        self, effect_id: str, external_state: str, outcome: str
    ) -> dict:
        """Reconcile-before-retry from a measured external outcome.

        Once an OBSERVED effect is RECONCILED, all paths, including ambiguous
        retries and NOT_STARTED, must preserve that settled observation.
        """
        if outcome == "COMPLETED":
            return self.record_receipt(
                effect_id,
                {"external": external_state},
                "reconciler",
                "OBSERVED",
                "RECONCILED",
            )
        if outcome not in ("NOT_STARTED", "AMBIGUOUS"):
            raise DuplicateEffect(f"unknown external outcome {outcome}")
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            row = cur.execute(
                "SELECT state, reconciliation_status FROM external_effects"
                " WHERE effect_id=?",
                (effect_id,),
            ).fetchone()
            if row is None:
                raise DuplicateEffect(f"unknown effect {effect_id}")
            if (
                row["state"] == "OBSERVED"
                and row["reconciliation_status"] == "RECONCILED"
            ):
                raise DuplicateEffect(
                    f"effect {effect_id} already has an immutable "
                    "reconciled receipt"
                )
            if outcome == "NOT_STARTED":
                if (
                    row["state"] == "ABANDONED"
                    and row["reconciliation_status"] == "RECONCILED"
                ):
                    return {
                        "effect_id": effect_id,
                        "state": "ABANDONED",
                        "duplicate": True,
                    }
                cur.execute(
                    "UPDATE external_effects SET state='ABANDONED',"
                    " reconciliation_status='RECONCILED' WHERE effect_id=?",
                    (effect_id,),
                )
                return {
                    "effect_id": effect_id,
                    "state": "ABANDONED",
                    "duplicate": False,
                }
            cur.execute(
                "UPDATE external_effects SET reconciliation_status='AMBIGUOUS'"
                " WHERE effect_id=?",
                (effect_id,),
            )
            return {"effect_id": effect_id, "reconciliation_status": "AMBIGUOUS"}
