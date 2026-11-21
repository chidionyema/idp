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
                "SELECT effect_id, intent_digest, state FROM external_effects"
                " WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                if existing["intent_digest"] != intent_digest:
                    cur.execute("ROLLBACK")
                    raise DuplicateEffect(
                        f"idempotency key {idempotency_key} already bound to a"
                        " different intent"
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
                "SELECT state FROM external_effects WHERE effect_id=?",
                (effect_id,),
            ).fetchone()
            if row is None:
                cur.execute("ROLLBACK")
                raise DuplicateEffect(f"unknown effect {effect_id}")
            if row["state"] == "OBSERVED" and reconciliation_status == "RECONCILED":
                cur.execute("ROLLBACK")
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

    def record_yield_proof(
        self,
        mission_id: str,
        attempt_id: str,
        lease_epoch: int,
        effect_id: str,
        metric: str,
        baseline: float,
        observed: float,
        target: float,
        evidence_ref: str,
        verifier: str,
        now: float | None = None,
    ) -> dict:
        """Record a measurable, attributable outcome, never a self-declared status.

        Verifier identity must be authenticated by the caller's admission boundary.
        This store enforces separation of identities and the evidence custody chain.
        """
        import math

        from .fields import InvalidTransition

        t = time.time() if now is None else now
        if not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            for v in (baseline, observed, target)
        ):
            raise InvalidTransition("yield metrics must be finite numbers")
        if not metric.strip() or not evidence_ref.strip() or not verifier.strip():
            raise InvalidTransition(
                "yield requires metric, evidence reference and verifier"
            )
        if observed < target if target >= baseline else observed > target:
            raise InvalidTransition("yield target not met")
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            self.assert_fence(mission_id, attempt_id, lease_epoch, now=t, cur=cur)
            mission = cur.execute(
                "SELECT state FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
            if mission["state"] != "OPERATING":
                raise InvalidTransition("yield cannot precede operational verification")
            effect = cur.execute(
                "SELECT state, reconciliation_status, verified_by FROM external_effects"
                " WHERE effect_id=? AND mission_id=? AND attempt_id=? AND lease_epoch=?",
                (effect_id, mission_id, attempt_id, lease_epoch),
            ).fetchone()
            if (
                effect is None
                or effect["state"] != "OBSERVED"
                or effect["reconciliation_status"] != "RECONCILED"
            ):
                raise InvalidTransition(
                    "yield needs an observed reconciled external effect"
                )
            if verifier.strip().casefold() == effect["verified_by"].strip().casefold():
                raise InvalidTransition("yield verifier cannot be the effect observer")
            proof_id = f"y-{uuid.uuid4()}"
            cur.execute(
                "INSERT INTO mission_yield_proofs"
                " (proof_id, mission_id, attempt_id, lease_epoch, effect_id,"
                " metric, baseline, observed, target, evidence_ref, verifier, verified_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    proof_id,
                    mission_id,
                    attempt_id,
                    lease_epoch,
                    effect_id,
                    metric,
                    baseline,
                    observed,
                    target,
                    evidence_ref,
                    verifier,
                    t,
                ),
            )
            return {"proof_id": proof_id, "state": "RECORDED", "verified_at": t}

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
        """Reconcile-before-retry: classify an ambiguous effect from
        authoritative external state without blind re-execution."""
        if outcome == "COMPLETED":
            return self.record_receipt(
                effect_id,
                {"external": external_state},
                "reconciler",
                "OBSERVED",
                "RECONCILED",
            )
        if outcome == "NOT_STARTED":
            with self.db:
                cur = self.db.execute("BEGIN IMMEDIATE")
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
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            cur.execute(
                "UPDATE external_effects SET reconciliation_status='AMBIGUOUS'"
                " WHERE effect_id=?",
                (effect_id,),
            )
            return {"effect_id": effect_id, "reconciliation_status": "AMBIGUOUS"}
