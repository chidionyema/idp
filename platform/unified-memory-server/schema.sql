-- Unified Model-Agnostic Agentic Memory Server — schema.sql
-- PostgreSQL 15+ with pgvector enabled.
-- Tenant isolation (RLS), monotonic optimistic concurrency, HNSW vector indexing,
-- Anti-Ouroboros trigger gate, and a distributed PostgreSQL-backed rate limiter.

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Tenants & Surface Authentication Tokens
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS surface_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    surface_name TEXT NOT NULL, -- 'earpiece', 'cursor', 'desktop', 'claude_web'
    token_hash TEXT NOT NULL UNIQUE, -- SHA-256 hashed token
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_surface_tokens_lookup ON surface_tokens(token_hash) WHERE revoked_at IS NULL;

-- 2. Core Memories Store with Optimistic Concurrency
CREATE TYPE trust_tier_enum AS ENUM ('raw_source', 'llm_derived', 'human_confirmed');

CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    namespace TEXT NOT NULL DEFAULT 'default',
    key TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL, -- BLAKE3 or SHA-256 formatted hex
    embedding vector(1536), -- Tuned for text-embedding-3-small or equivalent
    version BIGINT NOT NULL DEFAULT 1,
    trust_tier trust_tier_enum NOT NULL DEFAULT 'raw_source',
    provenance JSONB NOT NULL DEFAULT '{}'::jsonb, -- Includes source metadata, TrustProof

    -- MAPLE-Guard Lifecycle Metrics
    relevance_rho DOUBLE PRECISION NOT NULL DEFAULT 1.0,   -- ρ
    truthfulness_tau DOUBLE PRECISION NOT NULL DEFAULT 1.0, -- τ
    harm_h DOUBLE PRECISION NOT NULL DEFAULT 0.0,           -- h
    taint_level DOUBLE PRECISION NOT NULL DEFAULT 0.0,      -- taint(m)
    scope_risk DOUBLE PRECISION NOT NULL DEFAULT 0.0,       -- scope(m)
    is_shared BOOLEAN NOT NULL DEFAULT FALSE,
    is_quarantined BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    superseded_by UUID REFERENCES memories(id),

    CONSTRAINT uq_tenant_namespace_key UNIQUE (tenant_id, namespace, key)
);

-- 3. HNSW Production Index Tuning
-- Invariants: m = 24, ef_construction = 128 (ef_construction >= 2 * m)
CREATE INDEX IF NOT EXISTS idx_memories_hnsw ON memories
USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 128);

CREATE INDEX IF NOT EXISTS idx_memories_filter ON memories(tenant_id, namespace, is_quarantined, is_shared);

-- 4. Row-Level Security (RLS)
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON memories;
CREATE POLICY tenant_isolation ON memories
    FOR ALL TO PUBLIC
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

-- Security hardening: Strip dangerous operations from non-admin roles
REVOKE TRUNCATE, REFERENCES ON memories FROM PUBLIC;

-- 5. Monotonic Version Bump Trigger
CREATE OR REPLACE FUNCTION fn_bump_memory_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_bump_memory_version
BEFORE UPDATE ON memories
FOR EACH ROW
EXECUTE FUNCTION fn_bump_memory_version();

-- 6. Anti-Ouroboros Protocol Enforcement (ACA Protocol)
-- Invariant: llm_derived memories MUST NOT supersede another llm_derived memory without human intervention.
CREATE OR REPLACE FUNCTION fn_enforce_anti_ouroboros()
RETURNS TRIGGER AS $$
DECLARE
    target_trust trust_tier_enum;
BEGIN
    IF NEW.superseded_by IS NOT NULL THEN
        SELECT trust_tier INTO target_trust FROM memories WHERE id = NEW.superseded_by;

        IF OLD.trust_tier = 'llm_derived' AND target_trust = 'llm_derived' THEN
            RAISE EXCEPTION 'ANTI_OUROBOROS_VIOLATION: An llm_derived memory cannot supersede another llm_derived memory without human_confirmed promotion'
                USING ERRCODE = '23514'; -- check_violation
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_enforce_anti_ouroboros
BEFORE UPDATE OF superseded_by ON memories
FOR EACH ROW
EXECUTE FUNCTION fn_enforce_anti_ouroboros();

-- 7. Distributed Rate Limiting (Single Upsert per Hit)
CREATE TABLE IF NOT EXISTS rate_limits (
    surface_id TEXT NOT NULL,
    window_bucket BIGINT NOT NULL,
    request_count INT NOT NULL DEFAULT 1,
    PRIMARY KEY (surface_id, window_bucket)
);

CREATE OR REPLACE FUNCTION fn_hit_rate_limit(p_surface_id TEXT, p_window_bucket BIGINT, p_limit INT)
RETURNS BOOLEAN AS $$
DECLARE
    current_reqs INT;
BEGIN
    INSERT INTO rate_limits (surface_id, window_bucket, request_count)
    VALUES (p_surface_id, p_window_bucket, 1)
    ON CONFLICT (surface_id, window_bucket)
    DO UPDATE SET request_count = rate_limits.request_count + 1
    RETURNING request_count INTO current_reqs;

    RETURN current_reqs <= p_limit;
END;
$$ LANGUAGE plpgsql;
