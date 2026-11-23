"""Durable external-effect intents and receipts (ESTATE-P0 INV-04, WP-06).

record_effect_intent persists the idempotency key BEFORE the operation runs
and refuses a second intent under the same key with different content.
record_receipt stores only what authoritative external state actually
returned. pending_effects lists what a successor must reconcile before
retrying — at-least-once delivery never becomes exactly-once side effects.
"""

from __future__ import annotations

import json
import time
import uuid

from .fence import FenceMixin
from .fields import DuplicateEffect, RecordRejected, StaleFenceError
from .util import VERIFIER_FIELD, canonical, digest_of, verify_effect_receipt


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
        *,
        verifier_signature: str | None = None,
    ) -> dict:
        """Persist an outcome only when a trusted independent observer signed it.

        A caller-chosen verified_by label is NOT identity. Only an Ed25519
        signature bound to a key configured by the trusted store host can
        certify OBSERVED+RECONCILED. The signed envelope is persisted so
        that terminal transitions re-verify the proof across sessions.
        """
        if not isinstance(verified_by, str) or not verified_by.strip():
            raise RecordRejected("verifier identity must be nonempty")
        t = time.time() if now is None else now
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            row = cur.execute(
                "SELECT state, reconciliation_status, external_receipt, verified_by"
                " FROM external_effects WHERE effect_id=?",
                (effect_id,),
            ).fetchone()
            if row is None:
                raise DuplicateEffect(f"unknown effect {effect_id}")
            if row["reconciliation_status"] == "RECONCILED":
                # Historical optimistic settlements may have no signed
                # witness. They stay unverified until externally reattested.
                try:
                    previous = json.loads(row["external_receipt"])
                    original = verify_effect_receipt(
                        effect_id, previous, row["verified_by"],
                        self._trusted_verifier_keys,
                        observed_state=row["state"],
                    )
                except (ValueError, TypeError):
                    original = None
                if original is not None:
                    if (
                        observed_state != row["state"]
                        or reconciliation_status != "RECONCILED"
                        or canonical(receipt) != canonical(original)
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
                if reconciliation_status != "RECONCILED":
                    # Historical untrusted claims must be reattested, not
                    # overwritten with another unauthenticated claim.
                    raise RecordRejected(
                        "legacy unverified settlement needs signed reattestation"
                    )
            stored_receipt = receipt
            if reconciliation_status == "RECONCILED":
                if observed_state not in ("OBSERVED", "ABANDONED"):
                    raise RecordRejected(
                        "reconciliation needs verified observation or abandonment"
                    )
                if (
                    not isinstance(receipt, dict)
                    or not receipt
                    or VERIFIER_FIELD in receipt
                    or not isinstance(verifier_signature, str)
                    or not verifier_signature
                ):
                    raise RecordRejected(
                        "authenticated independent receipt signature required"
                    )
                stored_receipt = {
                    **receipt,
                    VERIFIER_FIELD: {
                        "key_id": verified_by,
                        "signature": verifier_signature,
                    },
                }
                try:
                    verify_effect_receipt(
                        effect_id, stored_receipt, verified_by,
                        self._trusted_verifier_keys, observed_state=observed_state,
                    )
                except (ValueError, TypeError) as exc:
                    raise RecordRejected(
                        "external observation signature not accepted"
                    ) from exc
            elif isinstance(receipt, dict) and VERIFIER_FIELD in receipt:
                raise RecordRejected("unverified state cannot embed a verifier seal")
            cur.execute(
                "UPDATE external_effects SET state=?, external_receipt=?,"
                " observed_at=?, verified_by=?, reconciliation_status=?"
                " WHERE effect_id=?",
                (
                    observed_state,
                    canonical(stored_receipt),
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
        # Unsigned old rows that claim RECONCILED are still unsettled.
        # The next worker never silently loses obligations during migration.
        rows = self.db.execute(
            "SELECT effect_id, operation, target, idempotency_key, state,"
            " reconciliation_status, external_receipt, verified_by"
            " FROM external_effects WHERE mission_id=?",
            (mission_id,),
        ).fetchall()
        pending = []
        for row in rows:
            item = {
                key: row[key]
                for key in (
                    "effect_id", "operation", "target", "idempotency_key",
                    "state", "reconciliation_status",
                )
            }
            if row["reconciliation_status"] != "RECONCILED":
                pending.append(item)
                continue
            try:
                receipt = json.loads(row["external_receipt"])
                verify_effect_receipt(
                    row["effect_id"], receipt, row["verified_by"],
                    self._trusted_verifier_keys, observed_state=row["state"],
                )
            except (ValueError, TypeError):
                item["reconciliation_status"] = "UNVERIFIED"
                pending.append(item)
        return pending

    def reconcile_effect(
        self, effect_id: str, external_state: str, outcome: str
    ) -> dict:
        """Only independently signed positive/negative receipts settle effects."""
        if outcome in ("COMPLETED", "NOT_STARTED"):
            raise DuplicateEffect(
                f"{outcome} claim requires independent record_receipt admission"
            )
        if outcome != "AMBIGUOUS":
            raise DuplicateEffect(f"unknown external outcome {outcome}")
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            row = cur.execute(
                "SELECT reconciliation_status FROM external_effects"
                " WHERE effect_id=?",
                (effect_id,),
            ).fetchone()
            if row is None:
                raise DuplicateEffect(f"unknown effect {effect_id}")
            if row["reconciliation_status"] == "RECONCILED":
                raise DuplicateEffect(
                    f"effect {effect_id} already claims a reconciled receipt"
                )
            cur.execute(
                "UPDATE external_effects SET reconciliation_status='AMBIGUOUS'"
                " WHERE effect_id=?",
                (effect_id,),
            )
            return {"effect_id": effect_id, "reconciliation_status": "AMBIGUOUS"}
