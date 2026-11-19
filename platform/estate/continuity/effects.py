"""Durable external-effect intents, mutually fenced across attempts."""
from __future__ import annotations

import time
import uuid

from .fence import FenceMixin
from .fields import DuplicateEffect, StaleFenceError
from .util import canonical, digest_of


class EffectsMixin(FenceMixin):
    def record_effect_intent(self, mission_id: str, attempt_id: str, lease_epoch: int, operation: str,
                             target: str, idempotency_key: str, intent: dict,
                             mandate_version: int | None = None, now: float | None = None) -> dict:
        t = time.time() if now is None else now
        intent_digest = digest_of(intent)
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            m = self.assert_fence(mission_id, attempt_id, lease_epoch, now=t, cur=cur)
            if mandate_version is None:
                mandate_version = m["mandate_version"]
            elif mandate_version != m["mandate_version"]:
                raise StaleFenceError("mandate version mismatch")
            existing = cur.execute("SELECT * FROM external_effects WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing is not None:
                if (existing["mission_id"], existing["operation"], existing["target"], existing["mandate_version"], existing["intent_digest"]) != (mission_id, operation, target, mandate_version, intent_digest):
                    raise DuplicateEffect("idempotency key bound to different mission, mandate, target, operation or intent")
                # Duplicate means RECONCILE, never authorization to replay.
                return {"effect_id": existing["effect_id"], "state": existing["state"], "duplicate": True}
            previous = cur.execute("SELECT effect_id FROM external_effects WHERE mission_id=? AND attempt_id!=? AND reconciliation_status!='RECONCILED' LIMIT 1", (mission_id, attempt_id)).fetchone()
            if previous is not None:
                raise DuplicateEffect("unreconciled predecessor effect; new effect refused")
            effect_id = f"e-{uuid.uuid4()}"
            cur.execute("INSERT INTO external_effects (effect_id, mission_id, attempt_id, lease_epoch, mandate_version, operation, target, idempotency_key, intent_digest, state) VALUES (?,?,?,?,?,?,?,?,?,?)", (effect_id, mission_id, attempt_id, lease_epoch, mandate_version, operation, target, idempotency_key, intent_digest, "INTENDED"))
            return {"effect_id": effect_id, "state": "INTENDED", "intent_digest": intent_digest, "duplicate": False}

    def record_receipt(self, effect_id: str, receipt: dict, verified_by: str, observed_state: str = "OBSERVED",
                       reconciliation_status: str = "RECONCILED", now: float | None = None) -> dict:
        t = time.time() if now is None else now
        if observed_state not in ("OBSERVED", "INTENDED", "ABANDONED") or reconciliation_status not in ("RECONCILED", "PENDING", "AMBIGUOUS"):
            raise DuplicateEffect("invalid receipt state")
        if reconciliation_status == "RECONCILED" and (observed_state == "INTENDED" or not isinstance(receipt, dict) or not receipt or not verified_by):
            raise DuplicateEffect("reconciled receipt is missing terminal evidence")
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            row = cur.execute("SELECT state,reconciliation_status FROM external_effects WHERE effect_id=?", (effect_id,)).fetchone()
            if row is None:
                raise DuplicateEffect(f"unknown effect {effect_id}")
            if row["reconciliation_status"] == "RECONCILED":
                if row["state"] != observed_state or reconciliation_status != "RECONCILED":
                    raise DuplicateEffect("cannot regress a reconciled receipt")
                return {"effect_id": effect_id, "state": row["state"], "duplicate": True}
            cur.execute("UPDATE external_effects SET state=?, external_receipt=?, observed_at=?, verified_by=?, reconciliation_status=? WHERE effect_id=?", (observed_state, canonical(receipt), t, verified_by, reconciliation_status, effect_id))
            return {"effect_id": effect_id, "state": observed_state, "observed_at": t, "duplicate": False}

    def pending_effects(self, mission_id: str) -> list:
        rows = self.db.execute("SELECT effect_id, operation, target, idempotency_key, state, reconciliation_status FROM external_effects WHERE mission_id=? AND reconciliation_status != 'RECONCILED'", (mission_id,)).fetchall()
        return [dict(r) for r in rows]

    def reconcile_effect(self, effect_id: str, external_state: str, outcome: str) -> dict:
        """Existing reconciler must authenticate the external observation upstream."""
        if outcome == "COMPLETED":
            return self.record_receipt(effect_id, {"external": external_state}, "reconciler", "OBSERVED", "RECONCILED")
        if outcome == "NOT_STARTED":
            return self.record_receipt(effect_id, {"external": external_state}, "reconciler", "ABANDONED", "RECONCILED")
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            row = cur.execute("SELECT reconciliation_status FROM external_effects WHERE effect_id=?", (effect_id,)).fetchone()
            if row is None or row["reconciliation_status"] == "RECONCILED":
                raise DuplicateEffect("unknown or already reconciled effect")
            cur.execute("UPDATE external_effects SET reconciliation_status='AMBIGUOUS' WHERE effect_id=?", (effect_id,))
            return {"effect_id": effect_id, "reconciliation_status": "AMBIGUOUS"}
