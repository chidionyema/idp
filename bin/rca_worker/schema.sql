-- Ledger for the via-negativa engine (docs/specs/2026-09-13-via-negativa-engine.md).
-- Source of truth for admitted negative constraints; bin/rca_worker/worker.py
-- is the only writer (it applies this file to its own Postgres role on every start,
-- run_forever() -- every statement is IF NOT EXISTS, so a rerun is a no-op) and
-- bin/negative-constraints-proxy reads a Redis cache of `signature` (see REDIS_KEY /
-- BANNED_SET_KEY) fed from this table.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rules (
    id BIGSERIAL PRIMARY KEY,
    scope TEXT NOT NULL,
    signature TEXT NOT NULL UNIQUE, -- worker.py upserts on this: ON CONFLICT (signature)
    confidence REAL NOT NULL,
    failure_count INTEGER DEFAULT 0,
    embedding vector(384),
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS rules_signature_idx ON rules (signature);
CREATE INDEX IF NOT EXISTS rules_embedding_idx ON rules USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS failures (
    id BIGSERIAL PRIMARY KEY,
    exit_code INTEGER,
    stdout TEXT,
    stderr TEXT,
    ts TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS failures_ts_idx ON failures (ts);
