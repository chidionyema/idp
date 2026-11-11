-- The brain-state schema, applied by `bin/idp-edge-cutover --d1` to the `estate-brain` D1
-- database (bound to the estate-lifeboat Worker as DB). Every statement is idempotent, so a
-- second `--all` is a no-op rather than an error.
--
-- Why two tables and not one: `brain_state` is the keyed read model the founder's surface asks
-- for by name (founder_instructions, active_claims, fencing_tokens), and `brain_instructions` is
-- the append-only history behind one of those keys. A single row holding a JSON array would make
-- every instruction append a read-modify-write of the whole history, which is the shape that
-- loses an instruction when two surfaces speak at once. The append is an INSERT; the key is a
-- projection of the tail of the history, kept in step by src/brain.js.

CREATE TABLE IF NOT EXISTS brain_state (
  key         TEXT PRIMARY KEY,
  value       TEXT NOT NULL,
  fencing     INTEGER NOT NULL DEFAULT 0,
  updated_at  TEXT NOT NULL,
  written_by  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS brain_instructions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  at          TEXT NOT NULL,
  surface     TEXT NOT NULL DEFAULT '',
  text        TEXT NOT NULL,
  session_id  TEXT NOT NULL DEFAULT '',
  fencing     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS brain_instructions_at ON brain_instructions (at DESC);

-- The claim read model the founder's surface shows, so a board renders without a GitHub token
-- in a browser. Keyed by issue number because that is the claim of record (AGENTS.md section 5).
CREATE TABLE IF NOT EXISTS brain_claims (
  issue       INTEGER PRIMARY KEY,
  agent       TEXT NOT NULL,
  paths       TEXT NOT NULL DEFAULT '',
  heartbeat   TEXT NOT NULL,
  live        INTEGER NOT NULL DEFAULT 1,
  updated_at  TEXT NOT NULL
);
