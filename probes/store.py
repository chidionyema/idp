"""crew#631 CP3: the verdict table. Lives in the Backstage Postgres (the portal is where CP4's
number is shown; no estate-wide Postgres exists and a seventh one would be stitching). Two roles:
`prover` may INSERT, `agent_role` may SELECT; nobody may UPDATE or DELETE (a trigger refuses, and
the grants never include it). Every statement here is built by a pure function so the SQL is
graded in a test; `bin/idp-verdict` runs it through `psql` inside the postgres pod."""

import json

TABLE = "verdicts"
COLUMNS = (
    "verdict_id",
    "check_id",
    "target",
    "commit_sha",
    "artifact_digest",
    "config_revision",
    "outcome",
    "completed_at",
    "prover_id",
    "prover_run_id",
    "evidence_ref",
)

SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
  verdict_id text PRIMARY KEY,
  check_id text NOT NULL,
  target text NOT NULL,
  commit_sha text NOT NULL,
  artifact_digest text,
  config_revision text,
  outcome text NOT NULL CHECK (outcome IN ('PASS','FAIL','BLOCKED','ERROR')),
  completed_at timestamptz NOT NULL,
  prover_id text NOT NULL,
  prover_run_id text NOT NULL,
  evidence_ref text,
  record jsonb NOT NULL,
  stored_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS verdicts_check_completed ON {TABLE} (check_id, completed_at DESC);
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'prover') THEN CREATE ROLE prover NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agent_role') THEN CREATE ROLE agent_role NOLOGIN; END IF;
END $$;
REVOKE ALL ON {TABLE} FROM PUBLIC;
-- PG >= 15: USAGE on schema public is no longer implied. Without it the prover's
-- SET ROLE prover could not resolve unqualified `verdicts` on the estate cluster
-- (relation does not exist) and every backstage verdict was BLIND after the
-- estate-db move (verdict-backstage run 34012387932).
GRANT USAGE ON SCHEMA public TO prover;
GRANT USAGE ON SCHEMA public TO agent_role;
GRANT INSERT, SELECT ON {TABLE} TO prover;
GRANT SELECT ON {TABLE} TO agent_role;
GRANT prover TO CURRENT_USER;
GRANT agent_role TO CURRENT_USER;
CREATE OR REPLACE FUNCTION verdicts_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'verdicts is append-only: % refused', TG_OP; END $$;
DROP TRIGGER IF EXISTS verdicts_append_only ON {TABLE};
CREATE TRIGGER verdicts_append_only BEFORE UPDATE OR DELETE OR TRUNCATE ON {TABLE}
  FOR EACH STATEMENT EXECUTE FUNCTION verdicts_append_only();
"""  # noqa: S608 -- TABLE is this module's own constant, never an input


def _lit(v):
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def insert_sql(v, role="prover"):
    """One INSERT as `role`. Duplicate verdict_id is a no-op, never an update."""
    vals = (
        ", ".join(_lit(v.get(c)) for c in COLUMNS)
        + ", "
        + _lit(json.dumps(v, sort_keys=True))
        + "::jsonb"
    )
    return (
        f"SET ROLE {role};\n"
        f"INSERT INTO {TABLE} ({', '.join(COLUMNS)}, record) VALUES ({vals})\n"
        f"ON CONFLICT (verdict_id) DO NOTHING;\n"
        f"SELECT count(*) FROM {TABLE} WHERE verdict_id = {_lit(v.get('verdict_id'))};\n"
    )


def list_sql(n=20, check_id=None, role="agent_role"):
    where = f"WHERE check_id = {_lit(check_id)} " if check_id else ""
    return (
        f"SET ROLE {role};\n"
        f"SELECT completed_at, outcome, check_id, left(artifact_digest, 24), prover_run_id, verdict_id "
        f"FROM {TABLE} {where}ORDER BY completed_at DESC LIMIT {int(n)};\n"
    )


def refuse_sql():
    """As agent_role, an INSERT must be refused; as prover, an UPDATE must be refused."""
    return (
        "SET ROLE agent_role;\n"
        f"INSERT INTO {TABLE} (verdict_id, check_id, target, commit_sha, outcome, completed_at, prover_id, prover_run_id, record)"
        " VALUES ('refuse-test', 'x', 'x', 'x', 'PASS', now(), 'agent', '0', '{}'::jsonb);\n"
    )


def refuse_update_sql():
    return f"SET ROLE prover;\nUPDATE {TABLE} SET outcome = 'PASS' WHERE outcome = 'FAIL';\n"
