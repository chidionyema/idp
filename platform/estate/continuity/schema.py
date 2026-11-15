"""SQLite DDL for the mission custody store (ESTATE-P0).

JSON-valued columns store lists/objects; every table is append-only except the
authoritative mission and attempt rows, which move only through the store's
compare-and-swap transitions.
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS missions (
    mission_id TEXT PRIMARY KEY,
    parent_mission_id TEXT,
    instruction_id TEXT NOT NULL,
    mandate_id TEXT NOT NULL,
    mandate_version INTEGER NOT NULL,
    revocation_epoch INTEGER NOT NULL DEFAULT 0,
    goal TEXT NOT NULL,
    acceptance_contract_digest TEXT NOT NULL,
    risk_class TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'P1',
    dependencies TEXT NOT NULL DEFAULT '[]',
    state TEXT NOT NULL,
    authoritative_owner TEXT NOT NULL,
    created_at REAL NOT NULL,
    deadline REAL,
    retry_budget INTEGER NOT NULL DEFAULT 3,
    retry_budget_remaining INTEGER NOT NULL DEFAULT 3,
    cost_budget REAL,
    recovery_policy TEXT NOT NULL DEFAULT 'REASSIGN_ON_STAGNATION',
    current_attempt_id TEXT,
    current_lease_epoch INTEGER NOT NULL DEFAULT 0,
    last_verified_progress_at REAL,
    last_checkpoint_digest TEXT,
    last_observed_outcome TEXT
);

CREATE TABLE IF NOT EXISTS mission_attempts (
    attempt_id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(mission_id),
    agent_adapter TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    execution_host TEXT NOT NULL,
    failure_domain TEXT NOT NULL,
    worktree_id TEXT NOT NULL,
    base_sha TEXT NOT NULL,
    candidate_sha TEXT,
    started_at REAL NOT NULL,
    lease_epoch INTEGER NOT NULL,
    lease_expires_at REAL NOT NULL,
    last_heartbeat_at REAL,
    last_progress_at REAL,
    token_budget_remaining INTEGER,
    quota_observation TEXT,
    checkpoint_digest TEXT,
    state TEXT NOT NULL,
    failure_class TEXT
);

CREATE TABLE IF NOT EXISTS mission_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id TEXT NOT NULL,
    attempt_id TEXT,
    lease_epoch INTEGER,
    from_state TEXT,
    to_state TEXT NOT NULL,
    actor TEXT NOT NULL,
    cause TEXT NOT NULL,
    evidence TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);
"""
