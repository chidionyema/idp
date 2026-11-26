"""The acceptance transaction, split from accept.py for review (ESTATE-P0)."""

from __future__ import annotations

import uuid

from .util import canonical, digest_of

MISSION_COLUMNS = (
    "mission_id,parent_mission_id,instruction_id,mandate_id,mandate_version,"
    "revocation_epoch,goal,acceptance_contract_digest,risk_class,priority,"
    "dependencies,state,authoritative_owner,created_at,deadline,retry_budget,"
    "retry_budget_remaining,cost_budget,recovery_policy,current_attempt_id,"
    "current_lease_epoch,last_verified_progress_at,last_checkpoint_digest,"
    "last_observed_outcome"
)


class AcceptTxnMixin:
    def _insert_accepted(self, row, initial, mission_id):
        if (
            initial["mission_id"] != mission_id
            or initial["attempt_id"] is not None
            or initial["sequence"] != 0
            or initial["goal_digest"] != digest_of(row[6])
            or initial["mandate_version"] != row[4]
        ):
            raise ValueError("initial checkpoint cannot change accepted objective")
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            existing = cur.execute(
                "SELECT acceptance_contract_digest, state, goal, instruction_id,"
                " parent_mission_id, mandate_id, mandate_version, revocation_epoch"
                " FROM missions"
                " WHERE mission_id=?",
                (mission_id,),
            ).fetchone()
            if existing is not None:
                if any(
                    existing[field] != row[index]
                    for field, index in (
                        ("parent_mission_id", 1),
                        ("instruction_id", 2),
                        ("mandate_id", 3),
                        ("mandate_version", 4),
                        ("revocation_epoch", 5),
                        ("goal", 6),
                        ("acceptance_contract_digest", 7),
                    )
                ):
                    cur.execute("ROLLBACK")
                    raise ValueError(
                        f"mission {mission_id} already accepted with a different contract"
                    )
                cur.execute("ROLLBACK")
                return {
                    "mission_id": mission_id,
                    "state": existing["state"],
                    "duplicate": True,
                }
            insert_sql = (
                f"INSERT INTO missions ({MISSION_COLUMNS})"  # noqa: S608 -- constant column list
                f" VALUES ({','.join('?' * 24)})"
            )
            cur.execute(insert_sql, row)
            checkpoint_id = f"cp-{uuid.uuid4()}"
            content = {
                k: initial[k] for k in initial if k != "created_at"
            }
            content_digest = digest_of(content)
            cur.execute(
                "INSERT INTO mission_checkpoints (checkpoint_id, mission_id,"
                " attempt_id, sequence, schema_version, source_revision,"
                " worktree_manifest_digest, goal_digest, remaining_work,"
                " completed_work, verified_facts, evidence_refs,"
                " failed_operations, pending_external_effects,"
                " next_admissible_action, mandate_version, created_at,"
                " content_digest, artifact_json)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    checkpoint_id,
                    mission_id,
                    None,
                    0,
                    initial["schema_version"],
                    initial["source_revision"],
                    initial["worktree_manifest_digest"],
                    initial["goal_digest"],
                    canonical(initial["remaining_work"]),
                    canonical(initial["completed_work"]),
                    canonical(initial["verified_facts"]),
                    canonical(initial["evidence_refs"]),
                    canonical(initial["failed_operations"]),
                    canonical(initial["pending_external_effects"]),
                    initial["next_admissible_action"],
                    initial["mandate_version"],
                    initial["created_at"],
                    content_digest,
                    canonical(initial),
                ),
            )
            cur.execute(
                "UPDATE missions SET last_checkpoint_digest=? WHERE mission_id=?",
                (content_digest, mission_id),
            )
            self._event(
                mission_id,
                "ACCEPTED",
                "estate",
                "durable acceptance",
                content_digest,
                from_state=None,
                cur=cur,
            )
            return {
                "mission_id": mission_id,
                "state": "ACCEPTED",
                "initial_checkpoint": checkpoint_id,
                "content_digest": content_digest,
                "duplicate": False,
            }
