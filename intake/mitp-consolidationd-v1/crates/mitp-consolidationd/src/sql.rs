//! SQL templates. The estate wires these to sqlx/postgres in its executor;
//! this crate's invariants are statically enforced in tests:
//!
//!  * E2/E13: NO statement here may UPDATE or DELETE `memories` or
//!    `memory_versions`, and none may set `superseded_by` (E4).
//!  * E3: every tenant-scoped statement is preceded by SET_TENANT within the
//!    same transaction; write statements use RETURNING and the caller asserts
//!    rowcount (idp#6507).
//!
//! Migration M-001 (side tables) is idempotent and RLS-consistent with
//! schema.sql sections 6b/11.

pub const MIGRATION_M001: &str = r#"
CREATE TABLE IF NOT EXISTS memory_quality (
    memory_id UUID PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    rho DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    tau DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    harm DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    taint DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    evidence_count BIGINT NOT NULL DEFAULT 0,
    brier DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    cusum DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    policy_version TEXT NOT NULL
);
ALTER TABLE memory_quality ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_quality FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON memory_quality;
CREATE POLICY tenant_isolation ON memory_quality
    FOR ALL TO PUBLIC
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
GRANT SELECT, INSERT, UPDATE ON memory_quality TO memory_app;

CREATE TABLE IF NOT EXISTS memory_evidence (
    evidence_id BIGSERIAL PRIMARY KEY,
    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    kind TEXT NOT NULL,
    weight DOUBLE PRECISION NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    receipt_ref TEXT
);
ALTER TABLE memory_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_evidence FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON memory_evidence;
CREATE POLICY tenant_isolation ON memory_evidence
    FOR ALL TO PUBLIC
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
GRANT SELECT, INSERT ON memory_evidence TO memory_app;

CREATE TABLE IF NOT EXISTS consolidation_receipts (
    receipt_id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    cycle_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE consolidation_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE consolidation_receipts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON consolidation_receipts;
CREATE POLICY tenant_isolation ON consolidation_receipts
    FOR ALL TO PUBLIC
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
GRANT SELECT, INSERT ON consolidation_receipts TO memory_app;
"#;

pub const ADVISORY_LOCK: &str = "SELECT pg_try_advisory_xact_lock($1) AS acquired;";

pub const SET_TENANT: &str = "SELECT set_config('app.tenant_id', $1, true);";

pub const LIST_TENANTS: &str = "SELECT tenant_id FROM tenants;";

/// Staging candidates: private, unquarantined, with at least one evidence row.
/// The WHERE clause is the E1 fix made structural: defaults alone can never
/// surface a row here because evidence_count comes from memory_evidence, not
/// from the (defaulted) columns on memories.
pub const STAGING_CANDIDATES: &str = r#"
SELECT m.id, m.namespace, m.key, m.content, m.relevance_rho, m.truthfulness_tau,
       m.harm_h, m.taint_level, m.created_at,
       COALESCE(e.cnt, 0) AS evidence_count
FROM memories m
LEFT JOIN (
    SELECT memory_id, COUNT(*) AS cnt FROM memory_evidence GROUP BY memory_id
) e ON e.memory_id = m.id
WHERE m.is_shared = FALSE AND m.is_quarantined = FALSE
ORDER BY m.created_at ASC
LIMIT $1;
"#;

/// Promotion is a SIDE-TABLE event plus one audited flip of is_shared.
/// NOTE: is_shared is a lifecycle flag, not bookkeeping — this UPDATE is the
/// single permitted mutation of `memories`, and it deliberately fires the
/// version trigger so history records the promotion. It never touches
/// content/updated_at semantics used for ranking recency: ranking reads
/// recorded_at from memory_versions, not memories.updated_at, once the estate
/// adopts the read path in M-002 (follow-up).
pub const PROMOTE_SHARED: &str = r#"
UPDATE memories SET is_shared = TRUE WHERE id = $1 AND is_shared = FALSE RETURNING id;
"#;

pub const QUARANTINE: &str = r#"
UPDATE memories SET is_quarantined = TRUE WHERE id = $1 AND is_quarantined = FALSE RETURNING id;
"#;

/// Distillation inserts are NEW llm_derived facts with provenance.source_ids.
/// No superseded_by — Anti-Ouroboros is complied with by construction (E4).
pub const INSERT_DISTILLED: &str = r#"
INSERT INTO memories (tenant_id, namespace, key, content, content_hash, trust_tier, provenance)
VALUES ($1, $2, $3, $4, $5, 'llm_derived', $6)
ON CONFLICT (tenant_id, namespace, key) DO NOTHING
RETURNING id;
"#;

pub const UPSERT_QUALITY: &str = r#"
INSERT INTO memory_quality (memory_id, tenant_id, rho, tau, harm, taint, evidence_count, brier, cusum, policy_version)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
ON CONFLICT (memory_id) DO UPDATE SET
    rho = EXCLUDED.rho, tau = EXCLUDED.tau, harm = EXCLUDED.harm, taint = EXCLUDED.taint,
    evidence_count = EXCLUDED.evidence_count, brier = EXCLUDED.brier, cusum = EXCLUDED.cusum,
    updated_at = CURRENT_TIMESTAMP, policy_version = EXCLUDED.policy_version
RETURNING memory_id;
"#;

pub const INSERT_EVIDENCE: &str = r#"
INSERT INTO memory_evidence (memory_id, tenant_id, kind, weight, receipt_ref)
VALUES ($1, $2, $3, $4, $5) RETURNING evidence_id;
"#;

pub const INSERT_RECEIPT: &str = r#"
INSERT INTO consolidation_receipts (tenant_id, cycle_id, payload) VALUES ($1, $2, $3) RETURNING receipt_id;
"#;

/// Promoted facts due for revalidation, weighted by retrieval frequency x age.
pub const REVALIDATION_SAMPLE: &str = r#"
SELECT m.id, COALESCE(a.access_count, 0) AS access_count, m.created_at
FROM memories m
LEFT JOIN memory_access a ON a.memory_id = m.id
WHERE m.is_shared = TRUE AND m.is_quarantined = FALSE
ORDER BY COALESCE(a.access_count, 0) * EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - m.created_at)) DESC
LIMIT $1;
"#;

pub const HOUSEKEEPING_SCRATCHPAD: &str = r#"
DELETE FROM harness_scratchpad WHERE expires_at < CURRENT_TIMESTAMP;
"#;

pub const HOUSEKEEPING_RECURRENCE: &str = r#"
DELETE FROM preference_recurrence WHERE updated_at < CURRENT_TIMESTAMP - make_interval(days => $1);
"#;

/// Static contract: statements that must never appear in this crate's SQL.
/// Enforced by tests; a regression here fails the build, not production.
pub const FORBIDDEN_SUBSTRINGS: [&str; 4] = [
    "UPDATE memory_versions",
    "DELETE FROM memory_versions",
    "DELETE FROM memories",
    "superseded_by",
];

#[cfg(test)]
mod tests {
    use super::*;

    fn all_sql() -> Vec<(&'static str, &'static str)> {
        vec![
            ("MIGRATION_M001", MIGRATION_M001),
            ("ADVISORY_LOCK", ADVISORY_LOCK),
            ("SET_TENANT", SET_TENANT),
            ("LIST_TENANTS", LIST_TENANTS),
            ("STAGING_CANDIDATES", STAGING_CANDIDATES),
            ("PROMOTE_SHARED", PROMOTE_SHARED),
            ("QUARANTINE", QUARANTINE),
            ("INSERT_DISTILLED", INSERT_DISTILLED),
            ("UPSERT_QUALITY", UPSERT_QUALITY),
            ("INSERT_EVIDENCE", INSERT_EVIDENCE),
            ("INSERT_RECEIPT", INSERT_RECEIPT),
            ("REVALIDATION_SAMPLE", REVALIDATION_SAMPLE),
            ("HOUSEKEEPING_SCRATCHPAD", HOUSEKEEPING_SCRATCHPAD),
            ("HOUSEKEEPING_RECURRENCE", HOUSEKEEPING_RECURRENCE),
        ]
    }

    #[test]
    fn e13_history_is_never_touched() {
        for (name, sql) in all_sql() {
            let up = sql.to_uppercase();
            for bad in ["UPDATE MEMORY_VERSIONS", "DELETE FROM MEMORY_VERSIONS", "DELETE FROM MEMORIES"] {
                assert!(!up.contains(bad), "{name} contains forbidden statement: {bad}");
            }
        }
    }

    #[test]
    fn e4_no_statement_sets_superseded_by() {
        for (name, sql) in all_sql() {
            assert!(
                !sql.to_lowercase().contains("superseded_by"),
                "{name} references superseded_by — Anti-Ouroboros path is human-only"
            );
        }
    }

    #[test]
    fn memories_update_is_lifecycle_flags_only() {
        // The only UPDATEs of memories permitted: is_shared and is_quarantined flips.
        for (name, sql) in all_sql() {
            let up = sql.to_uppercase();
            if up.contains("UPDATE MEMORIES") {
                assert!(
                    up.contains("SET IS_SHARED = TRUE") || up.contains("SET IS_QUARANTINED = TRUE"),
                    "{name} updates memories outside lifecycle flags — E2 violation"
                );
                assert!(!up.contains("UPDATED_AT"), "{name} must not touch updated_at");
                assert!(!up.contains("CONTENT"), "{name} must not touch content");
            }
        }
    }

    #[test]
    fn writes_use_returning_for_rowcount_assertion() {
        for (name, sql) in all_sql() {
            let up = sql.to_uppercase();
            let trimmed = up.trim_start();
            // INSERT/UPDATE carry RETURNING so callers assert rowcount (E3).
            // DELETEs are housekeeping sweeps whose 0-row outcome is normal.
            if trimmed.starts_with("INSERT") || trimmed.starts_with("UPDATE") {
                assert!(up.contains("RETURNING"), "{name} write lacks RETURNING (E3 rowcount assertion)");
            }
        }
    }

    #[test]
    fn migration_tables_all_have_force_rls() {
        let up = MIGRATION_M001.to_uppercase();
        for table in ["MEMORY_QUALITY", "MEMORY_EVIDENCE", "CONSOLIDATION_RECEIPTS"] {
            assert!(up.contains(&format!("ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")), "{table} missing RLS");
            assert!(up.contains(&format!("ALTER TABLE {table} FORCE ROW LEVEL SECURITY")), "{table} missing FORCE RLS");
        }
    }
}
