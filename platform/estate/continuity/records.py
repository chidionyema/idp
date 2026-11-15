"""Attempt, checkpoint, effect and failure-class field sets (ESTATE-P0)."""

from __future__ import annotations

ATTEMPT_FIELDS = (
    "attempt_id",
    "mission_id",
    "agent_adapter",
    "provider",
    "model",
    "execution_host",
    "failure_domain",
    "worktree_id",
    "base_sha",
    "candidate_sha",
    "started_at",
    "lease_epoch",
    "lease_expires_at",
    "last_heartbeat_at",
    "last_progress_at",
    "token_budget_remaining",
    "quota_observation",
    "checkpoint_digest",
    "state",
    "failure_class",
)

ACTIVE_ATTEMPT_STATES = ("RUNNING", "FENCED")
STALE_ATTEMPT_STATES = ("SUPERSEDED", "FAILED", "COMPLETED")

CHECKPOINT_FIELDS = (
    "checkpoint_id",
    "mission_id",
    "attempt_id",
    "sequence",
    "schema_version",
    "source_revision",
    "worktree_manifest_digest",
    "goal_digest",
    "remaining_work",
    "completed_work",
    "verified_facts",
    "evidence_refs",
    "failed_operations",
    "pending_external_effects",
    "next_admissible_action",
    "mandate_version",
    "created_at",
    "content_digest",
)

EFFECT_FIELDS = (
    "effect_id",
    "mission_id",
    "attempt_id",
    "lease_epoch",
    "mandate_version",
    "operation",
    "target",
    "idempotency_key",
    "intent_digest",
    "state",
    "external_transaction_ref",
    "external_receipt",
    "observed_at",
    "verified_by",
    "reconciliation_status",
)

FAILURE_CLASS_FIELDS = (
    "failure_class_id",
    "fingerprint",
    "first_seen",
    "occurrence_count",
    "affected_nodes",
    "root_cause",
    "corrective_change_ref",
    "regression_test_ref",
    "recurrence_measurement",
    "owner",
    "status",
)
