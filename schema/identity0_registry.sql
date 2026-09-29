-- schema/identity0_registry.sql
-- Quad-Layer Sovereign Identity & Execution Substrate (DROS)
-- Layer 2: Persistent Agent Registry
-- Deploy to OCI Autonomous DB (ATP) or PostgreSQL 15+
-- Connection: TLS required. Example: sqlplus admin/Pass@atp_high @identity0_registry.sql

BEGIN;

-- Agents table: the authoritative identity0 registry.
-- The primary key is the agent's URN (e.g., urn:aid:oke:research-agent).
-- The public_key is the raw Ed25519 public key (32 bytes).
CREATE TABLE IF NOT EXISTS agents (
    agent_id          VARCHAR(255) PRIMARY KEY,
    canonical_name    VARCHAR(128) UNIQUE NOT NULL,
    created_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    public_key        BYTEA NOT NULL,
    key_fingerprint   CHAR(64) NOT NULL,
    lineage_parent    VARCHAR(255),
    authority_scope   JSONB NOT NULL,
    operator_id       VARCHAR(255) NOT NULL,
    status            VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    last_heartbeat    TIMESTAMP WITH TIME ZONE,
    migration_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    CONSTRAINT chk_status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'REVOKED')),
    CONSTRAINT chk_pubkey_len CHECK (length(public_key) = 32)
);

-- Sessions table: ephemeral execution contexts tied to a pod's SPIFFE ID.
CREATE TABLE IF NOT EXISTS sessions (
    session_id        VARCHAR(64) PRIMARY KEY,
    agent_id          VARCHAR(255) NOT NULL REFERENCES agents(agent_id) ON DELETE RESTRICT,
    started_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at          TIMESTAMP WITH TIME ZONE,
    host_node         VARCHAR(128) NOT NULL,
    harness           VARCHAR(64) NOT NULL,
    model             VARCHAR(128) NOT NULL,
    spiffe_id         VARCHAR(512) NOT NULL,
    CONSTRAINT chk_session_active CHECK (
        (ended_at IS NULL) OR (ended_at > started_at)
    )
);

-- Agent actions table: every intent executed, signed with Ed25519.
-- The signature covers: intent_name || ':' || args_hash || ':' || session_id || ':' || created_at_unix
CREATE TABLE IF NOT EXISTS agent_actions (
    id                BIGSERIAL PRIMARY KEY,
    agent_id          VARCHAR(255) NOT NULL REFERENCES agents(agent_id),
    session_id        VARCHAR(64) NOT NULL REFERENCES sessions(session_id),
    intent_name       VARCHAR(128) NOT NULL,
    args_hash         CHAR(64) NOT NULL,
    result_hash       CHAR(64) NOT NULL,
    created_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    signature         BYTEA NOT NULL,
    parent_action_id  BIGINT REFERENCES agent_actions(id),
    merkle_root       CHAR(64)
);

-- Merkle anchors table: immutable receipts for action batches (OCI Object Storage).
CREATE TABLE IF NOT EXISTS merkle_anchors (
    root_hash         CHAR(64) PRIMARY KEY,
    leaf_count        BIGINT NOT NULL CHECK (leaf_count > 0),
    anchored_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    oci_object_uri    VARCHAR(1024) NOT NULL
);

-- Indexes for common access patterns.
CREATE INDEX IF NOT EXISTS idx_agents_fingerprint ON agents(key_fingerprint);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status) WHERE status != 'REVOKED';
CREATE INDEX IF NOT EXISTS idx_agents_operator ON agents(operator_id);
CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(agent_id) WHERE ended_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_spiffe ON sessions(spiffe_id);
CREATE INDEX IF NOT EXISTS idx_actions_agent_session ON agent_actions(agent_id, session_id);
CREATE INDEX IF NOT EXISTS idx_actions_signature ON agent_actions(signature);
CREATE INDEX IF NOT EXISTS idx_actions_created ON agent_actions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_actions_parent ON agent_actions(parent_action_id) WHERE parent_action_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_merkle_leaf_count ON merkle_anchors(leaf_count);

COMMIT;

-- Schema verification.
DO $$
BEGIN
    ASSERT (SELECT count(*) > 0 FROM information_schema.columns WHERE table_name = 'agents' AND column_name = 'agent_id');
    ASSERT (SELECT count(*) > 0 FROM information_schema.columns WHERE table_name = 'sessions' AND column_name = 'session_id');
    ASSERT (SELECT count(*) > 0 FROM information_schema.columns WHERE table_name = 'agent_actions' AND column_name = 'signature');
    ASSERT (SELECT count(*) > 0 FROM information_schema.columns WHERE table_name = 'merkle_anchors' AND column_name = 'root_hash');
    RAISE NOTICE 'identity0_registry schema verified successfully';
END $$;
