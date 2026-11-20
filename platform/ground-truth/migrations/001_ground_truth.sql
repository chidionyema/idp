-- Genesis Real-Time Ground Truth Projection Schema (v0.9.1-SOVEREIGN)
-- Compatible with genesis-kernel v0.8.0+ (/var/lib/genesis/genesis.db)
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;

-- 0. Authoritative Monotonic Fence & Chained Merkle Root (Shared with genesis-kernel)
CREATE TABLE IF NOT EXISTS kernel_fence_state (
    singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
    authoritative_token INTEGER NOT NULL,
    last_merkle_root TEXT NOT NULL
);

-- 1. Append-Only Real-Time Event Ring (Shared with genesis-kernel /api/realtime/ws)
CREATE TABLE IF NOT EXISTS realtime_event_ring (
    seq_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_ns INTEGER NOT NULL,
    fencing_token INTEGER NOT NULL,
    topic TEXT NOT NULL,
    source_node TEXT NOT NULL,
    prev_merkle_root TEXT NOT NULL,
    merkle_root TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_event_ring_ts ON realtime_event_ring(ts_ns);

-- 2. Idempotent Webhook Delivery Log (Gap Detection & Replay Prevention)
CREATE TABLE IF NOT EXISTS gt_webhook_deliveries (
    delivery_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    repo_full_name TEXT NOT NULL,
    received_at_ns INTEGER NOT NULL
);

-- 3. Tracked Repositories (idp, argon, argon-sync, gemini-sync, geaistudio)
CREATE TABLE IF NOT EXISTS gt_repos (
    repo_full_name TEXT PRIMARY KEY,
    default_branch TEXT NOT NULL DEFAULT 'main',
    head_sha TEXT NOT NULL,
    branch_count INTEGER NOT NULL DEFAULT 0,
    stranded_branch_count INTEGER NOT NULL DEFAULT 0,
    unique_blobs_off_main INTEGER NOT NULL DEFAULT 0,
    updated_at_ns INTEGER NOT NULL
);

-- 4. Branch Gravity Ledger (Tracks Stranded Work Off Main)
CREATE TABLE IF NOT EXISTS gt_branches (
    repo_full_name TEXT NOT NULL,
    branch_name TEXT NOT NULL,
    head_sha TEXT NOT NULL,
    code_files_not_on_main INTEGER NOT NULL DEFAULT 0,
    last_author TEXT NOT NULL DEFAULT 'unknown',
    last_commit_at TEXT NOT NULL DEFAULT '',
    updated_at_ns INTEGER NOT NULL,
    PRIMARY KEY (repo_full_name, branch_name)
);
CREATE INDEX IF NOT EXISTS idx_gt_branches_gravity ON gt_branches(repo_full_name, code_files_not_on_main DESC);

-- 5. Workflow Runs & Recurrent CI Failure Taxonomy
CREATE TABLE IF NOT EXISTS gt_workflow_runs (
    run_id INTEGER PRIMARY KEY,
    repo_full_name TEXT NOT NULL,
    workflow_name TEXT NOT NULL,
    head_branch TEXT NOT NULL,
    head_sha TEXT NOT NULL,
    event_name TEXT NOT NULL,
    status TEXT NOT NULL,
    conclusion TEXT NOT NULL,
    failing_step TEXT NOT NULL DEFAULT '',
    failure_class TEXT NOT NULL DEFAULT 'NONE',
    is_main INTEGER NOT NULL CHECK(is_main IN (0, 1)),
    completed_at TEXT NOT NULL,
    updated_at_ns INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_gt_runs_repo_wf ON gt_workflow_runs(repo_full_name, workflow_name, conclusion);
CREATE INDEX IF NOT EXISTS idx_gt_runs_updated ON gt_workflow_runs(updated_at_ns DESC);

-- 6. Open Pull Requests & Live Check Matrix
CREATE TABLE IF NOT EXISTS gt_pull_requests (
    repo_full_name TEXT NOT NULL,
    pr_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    head_branch TEXT NOT NULL,
    head_sha TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('OPEN', 'CLOSED', 'MERGED')),
    checks_verdict TEXT NOT NULL CHECK(checks_verdict IN ('GREEN', 'RED', 'PENDING')),
    failing_checks_json TEXT NOT NULL DEFAULT '[]',
    opened_at TEXT NOT NULL,
    updated_at_ns INTEGER NOT NULL,
    PRIMARY KEY (repo_full_name, pr_number)
);
CREATE INDEX IF NOT EXISTS idx_gt_prs_open ON gt_pull_requests(state, checks_verdict);

-- 7. Open Obligations (Issues)
CREATE TABLE IF NOT EXISTS gt_obligations (
    repo_full_name TEXT NOT NULL,
    issue_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('OPEN', 'CLOSED')),
    labels_json TEXT NOT NULL DEFAULT '[]',
    updated_at_ns INTEGER NOT NULL,
    PRIMARY KEY (repo_full_name, issue_number)
);

-- 8. AI Studio / Gemini Source Custody Ledger
CREATE TABLE IF NOT EXISTS gt_custody_ledger (
    artifact_id TEXT PRIMARY KEY,
    surface TEXT NOT NULL,
    artifact_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('IN_MAIN', 'ON_BRANCH', 'PARTIAL', 'EMPTY', 'UNDELIVERED')),
    location TEXT NOT NULL,
    evidence TEXT NOT NULL,
    updated_at_ns INTEGER NOT NULL
);

-- 9. Live Counterexamples (Deterministic AST/Config Assertions on Main)
CREATE TABLE IF NOT EXISTS gt_counterexamples (
    check_id TEXT PRIMARY KEY,
    claim TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK(verdict IN ('CONFIRMED_DEFECT', 'CLEARED', 'UNKNOWN')),
    repo_full_name TEXT NOT NULL,
    head_sha TEXT NOT NULL,
    evidence TEXT NOT NULL,
    checked_at_ns INTEGER NOT NULL
);

-- 10. Real-Time Provider Capacity & Circuit-Breaker State (sovereign-router / pennyd)
CREATE TABLE IF NOT EXISTS gt_provider_health (
    provider_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK(status IN ('HEALTHY', 'DEGRADED_429', 'DOWN_5XX')),
    last_http_status INTEGER NOT NULL DEFAULT 200,
    circuit_open_until_ns INTEGER NOT NULL DEFAULT 0,
    detail TEXT NOT NULL DEFAULT '',
    updated_at_ns INTEGER NOT NULL
);

-- 11. Real-Time Founder-Signed Role-to-Model Allocations (LAW_DYNAMIC_ROLE_MODEL_ALLOCATION)
CREATE TABLE IF NOT EXISTS gt_role_allocations (
    role_id TEXT PRIMARY KEY,
    ordered_pool_json TEXT NOT NULL,
    weights_json TEXT NOT NULL DEFAULT '{}',
    budget_cap_usd REAL NOT NULL,
    max_tokens_cap INTEGER NOT NULL,
    circuit_breaker_policy TEXT NOT NULL DEFAULT 'trip_on_429_5xx_60s',
    config_version INTEGER NOT NULL,
    founder_sig TEXT NOT NULL,
    updated_at_ns INTEGER NOT NULL
);

-- 12. Mandatory Pre-Inference Agent Leases (Bound to Fencing Token + Scope SHA-256)
CREATE TABLE IF NOT EXISTS gt_agent_leases (
    lease_id TEXT PRIMARY KEY,
    agent_surface TEXT NOT NULL,
    role_id TEXT NOT NULL,
    repo_full_name TEXT NOT NULL,
    bound_seq_id INTEGER NOT NULL,
    bound_fencing_token INTEGER NOT NULL,
    admitted_paths_json TEXT NOT NULL,
    scope_sha256 TEXT NOT NULL,
    expires_at_sec INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'SUBMITTED', 'REVOKED', 'EXPIRED')),
    created_at_ns INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_gt_leases_token ON gt_agent_leases(bound_fencing_token, status);
CREATE TABLE IF NOT EXISTS gt_ingress_nonces (
 nonce TEXT PRIMARY KEY,
 session_id TEXT NOT NULL,
 ticket_sha256 TEXT NOT NULL,
 fencing_token INTEGER NOT NULL,
 consumed_at_ns INTEGER NOT NULL);
