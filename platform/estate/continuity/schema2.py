"""Checkpoint, external-effect and failure-class tables (ESTATE-P0)."""

SCHEMA_2 = """
CREATE TABLE IF NOT EXISTS mission_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(mission_id),
    attempt_id TEXT,
    sequence INTEGER NOT NULL,
    schema_version INTEGER NOT NULL,
    source_revision TEXT NOT NULL,
    worktree_manifest_digest TEXT NOT NULL,
    goal_digest TEXT NOT NULL,
    remaining_work TEXT NOT NULL DEFAULT '[]',
    completed_work TEXT NOT NULL DEFAULT '[]',
    verified_facts TEXT NOT NULL DEFAULT '[]',
    evidence_refs TEXT NOT NULL DEFAULT '[]',
    failed_operations TEXT NOT NULL DEFAULT '[]',
    pending_external_effects TEXT NOT NULL DEFAULT '[]',
    next_admissible_action TEXT NOT NULL,
    mandate_version INTEGER NOT NULL,
    created_at REAL NOT NULL,
    content_digest TEXT NOT NULL,
    artifact_json TEXT NOT NULL,
    UNIQUE (mission_id, sequence)
);

CREATE TABLE IF NOT EXISTS external_effects (
    effect_id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(mission_id),
    attempt_id TEXT NOT NULL,
    lease_epoch INTEGER NOT NULL,
    mandate_version INTEGER NOT NULL,
    operation TEXT NOT NULL,
    target TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    intent_digest TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'INTENDED',
    external_transaction_ref TEXT,
    external_receipt TEXT,
    observed_at REAL,
    verified_by TEXT,
    reconciliation_status TEXT NOT NULL DEFAULT 'PENDING'
);

CREATE TABLE IF NOT EXISTS failure_classes (
    failure_class_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL UNIQUE,
    first_seen REAL NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    affected_nodes TEXT NOT NULL DEFAULT '[]',
    root_cause TEXT,
    corrective_change_ref TEXT,
    regression_test_ref TEXT,
    recurrence_measurement TEXT,
    owner TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN'
);

CREATE INDEX IF NOT EXISTS idx_attempts_mission
    ON mission_attempts (mission_id, lease_epoch);
CREATE INDEX IF NOT EXISTS idx_effects_mission
    ON external_effects (mission_id, reconciliation_status);
CREATE INDEX IF NOT EXISTS idx_checkpoints_mission
    ON mission_checkpoints (mission_id, sequence);
"""
