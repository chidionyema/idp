-- Unified Model-Agnostic Agentic Memory Server — schema.sql
-- PostgreSQL 15+ with pgvector enabled.
-- Tenant isolation (RLS), monotonic optimistic concurrency, HNSW vector indexing,
-- Anti-Ouroboros trigger gate, and a distributed PostgreSQL-backed rate limiter.

-- Extensions. gen_random_uuid() is core since PostgreSQL 13; uuid-ossp was never called.
-- The leader runs this file on every boot, so every statement here must be re-runnable.
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
-- CREATE TYPE has no IF NOT EXISTS; without this guard the second boot died on DuplicateObject.
DO $$ BEGIN
    CREATE TYPE trust_tier_enum AS ENUM ('raw_source', 'llm_derived', 'human_confirmed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

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
    -- Valid time: when the fact became true in the world (caller-supplied, defaults to now).
    -- updated_at stays the transaction time: when this server recorded it.
    valid_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_tenant_namespace_key UNIQUE (tenant_id, namespace, key)
);
ALTER TABLE memories ADD COLUMN IF NOT EXISTS valid_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- 3. HNSW Production Index Tuning
-- Invariants: m = 24, ef_construction = 128 (ef_construction >= 2 * m)
CREATE INDEX IF NOT EXISTS idx_memories_hnsw ON memories
USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 128);

CREATE INDEX IF NOT EXISTS idx_memories_filter ON memories(tenant_id, namespace, is_quarantined, is_shared);

-- 4. Row-Level Security (RLS)
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
-- Without FORCE the table owner (the role that ran this file) bypasses every policy.
ALTER TABLE memories FORCE ROW LEVEL SECURITY;

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
    -- Filling in a missing vector (POST /embeddings/backfill) changes nothing about the fact,
    -- so it is not a new version: the bump would leave a version with no memory_versions row,
    -- and /history is the record of what was true when. Any other column changing still bumps.
    IF NEW.embedding IS DISTINCT FROM OLD.embedding
       AND (to_jsonb(NEW) - 'embedding' - 'updated_at') = (to_jsonb(OLD) - 'embedding' - 'updated_at') THEN
        RETURN NEW;
    END IF;
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

-- 8. Bi-temporal history: every version ever written, append-only.
-- A row's valid_to is never stored: it is the valid_from of the next version known at the
-- time asked about. That is what lets a late write (an older fact arriving after a newer
-- one) take its place in the past without rewriting any row that is already there.
CREATE TABLE IF NOT EXISTS memory_versions (
    version_id BIGSERIAL PRIMARY KEY,
    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    trust_tier trust_tier_enum NOT NULL,
    provenance JSONB NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,   -- valid time
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()  -- transaction time
);
CREATE INDEX IF NOT EXISTS idx_memory_versions_lookup
    ON memory_versions(tenant_id, namespace, key, valid_from, recorded_at);

ALTER TABLE memory_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_versions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON memory_versions;
CREATE POLICY tenant_isolation ON memory_versions
    FOR ALL TO PUBLIC
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

-- Every write to memories lands in history here, so no code path can skip it.
CREATE OR REPLACE FUNCTION fn_record_memory_version()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO memory_versions (
        memory_id, tenant_id, namespace, key, content, content_hash,
        trust_tier, provenance, valid_from
    ) VALUES (
        NEW.id, NEW.tenant_id, NEW.namespace, NEW.key, NEW.content, NEW.content_hash,
        NEW.trust_tier, NEW.provenance, NEW.valid_from
    );
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_record_memory_version
AFTER INSERT OR UPDATE OF content, trust_tier, provenance, valid_from ON memories
FOR EACH ROW
EXECUTE FUNCTION fn_record_memory_version();

CREATE OR REPLACE FUNCTION fn_refuse_history_rewrite()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'HISTORY_IS_APPEND_ONLY: memory_versions rows are never updated or deleted'
        USING ERRCODE = '23514';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_refuse_history_rewrite
BEFORE UPDATE OR DELETE ON memory_versions
FOR EACH ROW
EXECUTE FUNCTION fn_refuse_history_rewrite();

-- 9. The role every request runs as. The connecting role owns these tables, and an owner (or
-- a superuser, which bypasses row-level security even when it is FORCEd) is the wrong identity
-- to serve requests as, so the pool drops to this role on every connection. NOLOGIN: it has no
-- password to leak. On estate-db the operator declares it (platform/estate-db/cluster/
-- cluster.yaml) and makes the connecting role `memory` a member, because `memory` has no
-- CREATEROLE; both steps below are then no-ops.
-- Checked before CREATE: a migrating role without CREATEROLE is refused on privilege before
-- PostgreSQL looks for a duplicate, so an exception guard alone fails when the role exists.
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'memory_app') THEN
        CREATE ROLE memory_app NOLOGIN NOSUPERUSER NOBYPASSRLS;
    END IF;
    -- Checked for the same reason: granting a role needs ADMIN OPTION on it, which a member
    -- the operator made does not have, even when the grant would change nothing.
    IF NOT pg_has_role(CURRENT_USER, 'memory_app', 'MEMBER') THEN
        EXECUTE format('GRANT memory_app TO %I', CURRENT_USER);
    END IF;
END $$;
GRANT USAGE ON SCHEMA public TO memory_app;
GRANT SELECT ON tenants, surface_tokens TO memory_app;
GRANT SELECT, INSERT, UPDATE ON memories TO memory_app;
GRANT SELECT, INSERT ON memory_versions TO memory_app;
GRANT USAGE ON SEQUENCE memory_versions_version_id_seq TO memory_app;
GRANT SELECT, INSERT, UPDATE ON rate_limits TO memory_app;
GRANT EXECUTE ON FUNCTION fn_hit_rate_limit(TEXT, BIGINT, INT) TO memory_app;

-- 10. Test leftovers deleted, history included. A live BDD run from an unmerged branch
-- (2026-10-01, test_unified_memory_spec_bdd.py) and the memory gate's old probe wrote these
-- into the namespaces real recall ranks against; on 2026-10-13 they were 34 of 47 facts and
-- outranked every real one. The founder chose deletion over quarantine (2026-10-13, "delete
-- them", then "Delete anyway" when told it means lifting the append-only guard). Named key by
-- key, so no real fact can match. The guard is lifted only when one of them still exists, and
-- inside the boot transaction: a failure rolls the lift back with the delete, and once they
-- are gone every later boot is a no-op that never touches the guard. FORCE ROW LEVEL SECURITY
-- holds the migrating owner too, so each tenant is set in turn, and the setting cleared after.
DO $$
DECLARE
    t UUID;
    doomed UUID[];
BEGIN
    FOR t IN SELECT tenant_id FROM tenants LOOP
        PERFORM set_config('app.tenant_id', t::text, true);
        SELECT array_agg(id) INTO doomed FROM memories WHERE (namespace, key) IN (VALUES
            ('estate', 'bdd.promote.bdd9bda212daa62'), ('estate', 'bdd.promote.bdd7d7bb87200cc'),
            ('estate', 'bdd.llm1.bdd1de600f4c276'), ('estate', 'bdd.llm1.bdd8b2c6ab53076'),
            ('estate', 'bdd.llm2.bdd1de600f4c276'), ('estate', 'bdd.llm2.bdd8b2c6ab53076'),
            ('estate', 'bdd.harm.bdd480995f6cc81'), ('estate', 'bdd.harm.bddd41fbc72c129'),
            ('estate', 'bdd.guard.bdd9eaf02d7bc62'), ('estate', 'bdd.guard.bddc64f1121f5b8'),
            ('estate', 'bdd.new.bdd777abff0e0d1'), ('estate', 'bdd.old.bdd777abff0e0d1'),
            ('estate', 'bdd.new.bddcc1677b49fbd'), ('estate', 'bdd.old.bddcc1677b49fbd'),
            ('estate', 'bdd.sem.bddd61b518941b6'), ('estate', 'bdd.sem.bdd5fb3ac115425'),
            ('estate', 'bdd.bddae0bfe20b40f'), ('estate', 'bdd.bddce01492d5888'),
            ('estate', 'estate.history.bddd8683f095075'),
            ('estate', 'estate.history.bdd045829124f63'),
            ('founder', 'estate.expiring.bdd77690fd82a88'),
            ('founder', 'estate.expiring.bdd7c332e2da604'),
            ('founder', 'estate.test.bddb939df044952'), ('founder', 'estate.test.bdd43467d69802b'),
            ('founder', 'estate.forget.bdd7cab29ea9d79'),
            ('founder', 'estate.forget.bdd21c63d763c83'),
            ('estate', 'gate-smoke'),
            ('estate', 'measurement.memory-gate.c736d73e5d9bf801'),
            ('estate', 'measurement.memory-gate.a3793b5c8c5a6768'),
            ('estate', 'measurement.memory-gate.2827f97c14b0c6d3'),
            ('estate', 'measurement.memory-gate.614deee11be97dd1'),
            ('estate', 'measurement.memory-gate.10942472c1eda1d9'),
            ('estate', 'measurement.memory-gate.51562056a8038935'),
            ('estate', 'measurement.crew-990-proof.979e5e072dcdc9d3'));
        IF doomed IS NOT NULL THEN
            ALTER TABLE memory_versions DISABLE TRIGGER trg_refuse_history_rewrite;
            DELETE FROM memories WHERE id = ANY(doomed);
            ALTER TABLE memory_versions ENABLE TRIGGER trg_refuse_history_rewrite;
        END IF;
    END LOOP;
    PERFORM set_config('app.tenant_id', '', true);
END $$;
