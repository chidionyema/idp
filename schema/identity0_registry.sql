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

-- KARMA: agent names are a display-level, once-per-first-eligible-session choice;
-- agent_id (the QUAD identity) never changes and historical names are not erased.
-- Source: founder directive 2026-11-12, IDP #7452.
--
-- IMPORTANT: installing this migration does NOT activate name choice or grant an
-- agent database write access. The existing QUAD identity service must first
-- verify the signed source action and use a separately provisioned least-privilege
-- database role. Founder rename requires a different role. Neither can be
-- inferred from user-supplied "actor" strings or unverified model output.
BEGIN;

ALTER TABLE agents ADD COLUMN IF NOT EXISTS display_name VARCHAR(128);
ALTER TABLE agents ADD COLUMN IF NOT EXISTS first_name_decided_at TIMESTAMP WITH TIME ZONE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_display_name_folded
    ON agents (lower(display_name)) WHERE display_name IS NOT NULL;

CREATE TABLE IF NOT EXISTS quad_name_activation (
    enabled BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (enabled),
    activated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    founder_action_id TEXT NOT NULL UNIQUE,
    verified_action_digest CHAR(64) NOT NULL
);
-- Deliberately no row until the existing founder-authorized QUAD action door
-- has independently authenticated the activation; deploy is not authorization.

CREATE TABLE IF NOT EXISTS agent_name_events (
    event_id BIGSERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(agent_id) ON DELETE RESTRICT,
    source_action_id TEXT NOT NULL UNIQUE,
    source_action_digest CHAR(64) NOT NULL,
    session_id VARCHAR(64),
    event_kind VARCHAR(32) NOT NULL
        CHECK (event_kind IN ('INITIAL_CHOICE','RETAIN','FOUNDER_RENAME')),
    old_display_name VARCHAR(128) NOT NULL,
    new_display_name VARCHAR(128) NOT NULL,
    founder_principal VARCHAR(255),
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT name_event_actor_check CHECK (
        (event_kind = 'FOUNDER_RENAME' AND founder_principal IS NOT NULL)
        OR (event_kind <> 'FOUNDER_RENAME' AND founder_principal IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_agent_name_events_agent_time
    ON agent_name_events(agent_id, recorded_at, event_id);
REVOKE UPDATE, DELETE ON agent_name_events FROM PUBLIC;
REVOKE INSERT ON agent_name_events FROM PUBLIC;

-- Run ONLY as the trusted QUAD identity service after independent source-action
-- validation. A name selection is not a new cryptographic principal.
CREATE OR REPLACE FUNCTION public.quad_initial_name_choice(
    p_agent_id TEXT,
    p_session_id TEXT,
    p_preferred_name TEXT,
    p_quad_action_id TEXT,
    p_action_digest TEXT
) RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public
AS $karma_name_choice$
DECLARE
    a public.agents%ROWTYPE;
    chosen TEXT;
    activated TIMESTAMP WITH TIME ZONE;
    first_session TEXT;
    old_name TEXT;
    previous public.agent_name_events%ROWTYPE;
BEGIN
    IF coalesce(length(p_quad_action_id),0) < 8
        OR p_action_digest !~ '^[0-9a-fA-F]{64}$' THEN
        RAISE EXCEPTION 'KARMA: an authenticated QUAD action receipt is required';
    END IF;
    SELECT * INTO previous FROM public.agent_name_events
      WHERE source_action_id = p_quad_action_id;
    IF FOUND THEN
        IF previous.agent_id = p_agent_id
            AND previous.session_id = p_session_id
            AND previous.source_action_digest = p_action_digest
            AND previous.event_kind IN ('INITIAL_CHOICE','RETAIN') THEN
            RETURN previous.new_display_name; -- idempotent redelivery
        END IF;
        RAISE EXCEPTION 'KARMA: conflicting action replay';
    END IF;
    SELECT activated_at INTO activated FROM public.quad_name_activation
      WHERE enabled = TRUE;
    IF activated IS NULL THEN
        RAISE EXCEPTION 'KARMA: naming not yet activated by founder authority';
    END IF;
    -- Prevent races between two agents choosing the same name (including an
    -- already-known canonical identity that has not chosen a display name).
    PERFORM pg_advisory_xact_lock(hashtext('quad-agent-names'));
    SELECT * INTO a FROM public.agents WHERE agent_id = p_agent_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'KARMA: unknown permanent agent identity';
    END IF;
    SELECT s.session_id INTO first_session FROM public.sessions s
      WHERE s.agent_id = p_agent_id AND s.started_at >= activated
      ORDER BY s.started_at, s.session_id LIMIT 1;
    IF first_session IS NULL OR first_session <> p_session_id THEN
        RAISE EXCEPTION 'KARMA: initial choice is only offered in the first eligible session';
    END IF;
    IF a.first_name_decided_at IS NOT NULL THEN
        RAISE EXCEPTION 'KARMA: this permanent identity has already decided its initial name';
    END IF;
    IF CURRENT_TIMESTAMP > (SELECT started_at + interval '30 minutes'
                            FROM public.sessions WHERE session_id = p_session_id) THEN
        RAISE EXCEPTION 'KARMA: initial naming window has expired';
    END IF;
    old_name := coalesce(a.display_name, a.canonical_name);
    chosen := btrim(coalesce(p_preferred_name,''));
    IF chosen = '' THEN
        chosen := old_name; -- existing name is explicitly retained by default
    ELSIF length(chosen) < 2 OR length(chosen) > 64
        OR chosen !~ '^[[:alnum:]][[:alnum:] ._-]*$'
        OR lower(chosen) IN ('founder','administrator','system','root','estate-agent') THEN
        RAISE EXCEPTION 'KARMA: invalid, reserved or impersonating display name';
    END IF;
    IF EXISTS (
        SELECT 1 FROM public.agents a2
        WHERE a2.agent_id <> p_agent_id
          AND (lower(a2.canonical_name) = lower(chosen)
               OR lower(coalesce(a2.display_name,a2.canonical_name)) = lower(chosen))
    ) THEN
        RAISE EXCEPTION 'KARMA: display name already belongs to another identity';
    END IF;
    UPDATE public.agents SET display_name = chosen,
        first_name_decided_at = CURRENT_TIMESTAMP WHERE agent_id = p_agent_id;
    INSERT INTO public.agent_name_events
      (agent_id, source_action_id, source_action_digest, session_id,
       event_kind, old_display_name, new_display_name)
      VALUES (p_agent_id, p_quad_action_id, p_action_digest, p_session_id,
              CASE WHEN chosen = old_name THEN 'RETAIN' ELSE 'INITIAL_CHOICE' END,
              old_name, chosen);
    RETURN chosen;
END
$karma_name_choice$;

-- A founder-authorized rename has a different database capability. It cannot
-- reset the agent's identity, initial choice, model genealogy or outstanding
-- work. The upstream verified action must carry the founder principal.
CREATE OR REPLACE FUNCTION public.quad_founder_rename_agent(
    p_agent_id TEXT,
    p_new_name TEXT,
    p_founder_principal TEXT,
    p_quad_action_id TEXT,
    p_action_digest TEXT
) RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public
AS $karma_founder_rename$
DECLARE
    a public.agents%ROWTYPE;
    chosen TEXT := btrim(coalesce(p_new_name,''));
    previous public.agent_name_events%ROWTYPE;
BEGIN
    IF coalesce(length(p_founder_principal),0) < 3
       OR coalesce(length(p_quad_action_id),0) < 8
       OR p_action_digest !~ '^[0-9a-fA-F]{64}$' THEN
       RAISE EXCEPTION 'KARMA: independent founder authorization required';
    END IF;
    IF length(chosen) < 2 OR length(chosen) > 64
       OR chosen !~ '^[[:alnum:]][[:alnum:] ._-]*$' THEN
       RAISE EXCEPTION 'KARMA: invalid display name';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtext('quad-agent-names'));
    SELECT * INTO previous FROM public.agent_name_events
      WHERE source_action_id = p_quad_action_id;
    IF FOUND THEN
       IF previous.agent_id = p_agent_id
          AND previous.source_action_digest = p_action_digest
          AND previous.event_kind = 'FOUNDER_RENAME'
          AND previous.new_display_name = chosen
          AND previous.founder_principal = p_founder_principal THEN
          RETURN chosen;
       END IF;
       RAISE EXCEPTION 'KARMA: conflicting founder action replay';
    END IF;
    SELECT * INTO a FROM public.agents WHERE agent_id = p_agent_id FOR UPDATE;
    IF NOT FOUND THEN
       RAISE EXCEPTION 'KARMA: unknown permanent agent identity';
    END IF;
    IF EXISTS (
       SELECT 1 FROM public.agents a2 WHERE a2.agent_id <> p_agent_id
       AND (lower(a2.canonical_name) = lower(chosen)
            OR lower(coalesce(a2.display_name,a2.canonical_name)) = lower(chosen))
    ) THEN
       RAISE EXCEPTION 'KARMA: display name already belongs to another identity';
    END IF;
    INSERT INTO public.agent_name_events
      (agent_id, source_action_id, source_action_digest, event_kind,
       old_display_name, new_display_name, founder_principal)
      VALUES (p_agent_id, p_quad_action_id, p_action_digest, 'FOUNDER_RENAME',
              coalesce(a.display_name, a.canonical_name), chosen, p_founder_principal);
    UPDATE public.agents SET display_name = chosen,
       first_name_decided_at = coalesce(first_name_decided_at, CURRENT_TIMESTAMP)
       WHERE agent_id = p_agent_id;
    RETURN chosen;
END
$karma_founder_rename$;

-- Default Postgres functions are executable by PUBLIC; do not make agent/
-- founder renames publicly callable. Explicit grants happen only when the
-- verified QUAD principal-to-DB-role mapping is operational and tested.
REVOKE EXECUTE ON FUNCTION public.quad_initial_name_choice(
    TEXT,TEXT,TEXT,TEXT,TEXT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.quad_founder_rename_agent(
    TEXT,TEXT,TEXT,TEXT,TEXT) FROM PUBLIC;
COMMIT;
