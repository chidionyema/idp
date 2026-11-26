"""Checkpoint write and validated reconstruction (ESTATE-P0 WP-03).

Checkpoints are stored in the custody database — outside the worker process
failure domain — with a sha256 content digest. restore_latest_checkpoint
validates schema version, mandate version, artifact integrity and digest
match before a successor may act; anything malformed is an explicit
CheckpointRejected, never fabricated continuity.
"""

from __future__ import annotations

import json
import time
import uuid

from .fields import CheckpointRejected, StaleFenceError
from .records import CHECKPOINT_FIELDS
from .util import canonical, digest_of

INPUT_FIELDS = tuple(
    f
    for f in CHECKPOINT_FIELDS
    if f
    not in (
        "checkpoint_id",
        "mission_id",
        "attempt_id",
        "sequence",
        "created_at",
        "content_digest",
    )
)


class CheckpointMixin:
    def write_checkpoint(
        self,
        mission_id: str,
        attempt_id: str,
        lease_epoch: int,
        payload: dict,
        mandate_version: int | None = None,
        now: float | None = None,
    ) -> dict:
        t = time.time() if now is None else now
        unknown = set(payload) - set(INPUT_FIELDS)
        if unknown:
            raise CheckpointRejected(f"unknown fields: {sorted(unknown)}")
        missing = [
            f
            for f in ("source_revision", "next_admissible_action")
            if not payload.get(f)
        ]
        if missing:
            raise CheckpointRejected(f"missing fields: {missing}")
        body = dict(payload)
        body["mandate_version"] = (
            mandate_version
            if mandate_version is not None
            else payload.get("mandate_version", 1)
        )
        with self.db:
            cur = self.db.execute("BEGIN IMMEDIATE")
            m = self.assert_fence(mission_id, attempt_id, lease_epoch, now=t, cur=cur)
            if body["mandate_version"] != m["mandate_version"]:
                cur.execute("ROLLBACK")
                raise StaleFenceError("checkpoint mandate_version is stale")
            goal_digest = digest_of(m["goal"])
            if "goal_digest" in body and body["goal_digest"] != goal_digest:
                cur.execute("ROLLBACK")
                raise CheckpointRejected("checkpoint cannot replace accepted objective")
            body["goal_digest"] = goal_digest
            seq_row = cur.execute(
                "SELECT COALESCE(MAX(sequence), -1) + 1 FROM"
                " mission_checkpoints WHERE mission_id=?",
                (mission_id,),
            ).fetchone()
            sequence = seq_row[0]
            checkpoint_id = f"cp-{uuid.uuid4()}"
            content = {k: v for k, v in body.items()}
            content["mission_id"] = mission_id
            content["attempt_id"] = attempt_id
            content["sequence"] = sequence
            content_digest = digest_of(content)
            artifact = dict(content)
            artifact["created_at"] = t
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
                    attempt_id,
                    sequence,
                    int(body.get("schema_version", 1)),
                    body["source_revision"],
                    body.get("worktree_manifest_digest", ""),
                    body.get("goal_digest", ""),
                    canonical(body.get("remaining_work", [])),
                    canonical(body.get("completed_work", [])),
                    canonical(body.get("verified_facts", [])),
                    canonical(body.get("evidence_refs", [])),
                    canonical(body.get("failed_operations", [])),
                    canonical(body.get("pending_external_effects", [])),
                    body["next_admissible_action"],
                    body["mandate_version"],
                    t,
                    content_digest,
                    canonical(artifact),
                ),
            )
            cur.execute(
                "UPDATE missions SET last_checkpoint_digest=? WHERE mission_id=?",
                (content_digest, mission_id),
            )
            # Custody is not independent evidence of progress. In particular,
            # a worker must not extend its own lease stagnation clock by
            # repeatedly writing a new checkpoint containing more narration.
            cur.execute(
                "UPDATE mission_attempts SET checkpoint_digest=? WHERE attempt_id=?",
                (content_digest, attempt_id),
            )
            return {
                "checkpoint_id": checkpoint_id,
                "sequence": sequence,
                "content_digest": content_digest,
            }

    def latest_checkpoint(self, mission_id: str) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM mission_checkpoints WHERE mission_id=?"
            " ORDER BY sequence DESC LIMIT 1",
            (mission_id,),
        ).fetchone()
        if row is None:
            return None
        out = dict(row)
        out["artifact"] = row["artifact_json"]
        return out

    def restore_latest_checkpoint(
        self,
        mission_id: str,
        expect_mandate_version: int | None = None,
        required_artifact_digests: dict | None = None,
        schema_floor: int = 1,
    ) -> dict:
        cp = self.latest_checkpoint(mission_id)
        if cp is None:
            raise CheckpointRejected(f"mission {mission_id} has no checkpoint")
        if cp["schema_version"] < schema_floor:
            raise CheckpointRejected(
                f"checkpoint schema {cp['schema_version']} below floor {schema_floor}"
            )
        try:
            artifact = json.loads(cp["artifact_json"])
        except json.JSONDecodeError as exc:
            raise CheckpointRejected(f"checkpoint artifact unparsable: {exc}") from exc
        if not isinstance(artifact, dict):
            raise CheckpointRejected("checkpoint artifact is not an object")
        content = {k: v for k, v in artifact.items() if k != "created_at"}
        if (
            artifact.get("mission_id") != mission_id
            or artifact.get("attempt_id") != cp["attempt_id"]
            or artifact.get("sequence") != cp["sequence"]
        ):
            raise CheckpointRejected("checkpoint identity mismatch")
        # Older sequence-zero records omitted sequence from the signed digest.
        # Accept that exact legacy format only for the initial checkpoint.
        legacy = {k: v for k, v in content.items() if k != "sequence"}
        if digest_of(content) != cp["content_digest"] and not (
            cp["sequence"] == 0
            and cp["attempt_id"] is None
            and digest_of(legacy) == cp["content_digest"]
        ):
            raise CheckpointRejected("checkpoint digest mismatch")
        if (
            expect_mandate_version is not None
            and artifact["mandate_version"] != expect_mandate_version
        ):
            raise CheckpointRejected(
                f"checkpoint mandate {artifact['mandate_version']} != expected"
                f" {expect_mandate_version}"
            )
        mission = self.get_mission(mission_id)
        if mission is None:
            raise CheckpointRejected(f"mission {mission_id} vanished")
        if artifact.get("goal_digest") != digest_of(mission["goal"]):
            raise CheckpointRejected("checkpoint objective does not match accepted goal")
        if artifact["mandate_version"] != mission["mandate_version"]:
            raise CheckpointRejected("checkpoint mandate is revoked or superseded")
        if mission["revocation_epoch"] > 0:
            raise CheckpointRejected("mission mandate revoked")
        if required_artifact_digests:
            for ref, want in required_artifact_digests.items():
                got = artifact.get(ref)
                if isinstance(got, str) and got != want:
                    raise CheckpointRejected(
                        f"artifact {ref} digest mismatch: {got} != {want}"
                    )
        return artifact
