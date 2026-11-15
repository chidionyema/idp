"""Atomic mission acceptance (ESTATE-P0 INV-01).

accept_mission writes the mission row AND its initial checkpoint in one
BEGIN IMMEDIATE transaction, so custody exists before any worker starts.
Idempotent on mission_id with an identical contract; a different contract
under the same id is refused.
"""

from __future__ import annotations

import time
import uuid

from .fields import MISSION_FIELDS, UnknownField
from .util import canonical, digest_of

ACCEPT_REQUIRED = (
    "instruction_id",
    "mandate_id",
    "goal",
    "acceptance_contract_digest",
    "risk_class",
)


def _validate_accept(record: dict) -> str:
    unknown = set(record) - set(MISSION_FIELDS)
    if unknown:
        raise UnknownField(f"unknown fields: {sorted(unknown)}")
    missing = [f for f in ACCEPT_REQUIRED if not record.get(f)]
    if missing:
        raise UnknownField(f"missing fields: {missing}")
    return record.get("mission_id") or f"m-{uuid.uuid4()}"


class AcceptMixin:
    def accept_mission(self, record: dict, extra_initial: dict | None = None) -> dict:
        mission_id = _validate_accept(record)
        now = time.time()
        mandate_version = int(record.get("mandate_version", 1))
        retry_budget = int(record.get("retry_budget", 3))
        row = (
            mission_id,
            record.get("parent_mission_id"),
            record["instruction_id"],
            record["mandate_id"],
            mandate_version,
            int(record.get("revocation_epoch", 0)),
            record["goal"],
            record["acceptance_contract_digest"],
            record["risk_class"],
            record.get("priority", "P1"),
            canonical(record.get("dependencies", [])),
            "ACCEPTED",
            record.get("authoritative_owner", "estate"),
            now,
            record.get("deadline"),
            retry_budget,
            retry_budget,
            record.get("cost_budget"),
            record.get("recovery_policy", "REASSIGN_ON_STAGNATION"),
            None,
            0,
            None,
            None,
            None,
        )
        initial = {
            "mission_id": mission_id,
            "attempt_id": None,
            "sequence": 0,
            "schema_version": 1,
            "source_revision": record.get("source_revision", ""),
            "worktree_manifest_digest": record.get("worktree_manifest_digest", ""),
            "goal_digest": digest_of(record["goal"]),
            "remaining_work": [record["goal"]],
            "completed_work": [],
            "verified_facts": [],
            "evidence_refs": [],
            "failed_operations": [],
            "pending_external_effects": list(
                record.get("pending_external_effects", [])
            ),
            "next_admissible_action": "transition READY",
            "mandate_version": mandate_version,
            "created_at": now,
        }
        if extra_initial:
            initial.update(extra_initial)
        return self._insert_accepted(row, initial, mission_id)
