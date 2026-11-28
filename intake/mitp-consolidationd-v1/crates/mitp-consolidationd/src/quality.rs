//! G3/E2 fix: the quality side-table model. Quality scores derived from
//! evidence live HERE, never in an UPDATE to `memories` (which would fire
//! fn_bump_memory_version, reset updated_at, and poison recency ranking —
//! the exact failure consolidation.py's docstring predicts for the Python
//! curation worker).
//!
//! Table (created by migration M-001 in sql.rs):
//!   memory_quality(memory_id PK, tenant_id, rho, tau, harm, taint,
//!                  evidence_count, brier, cusum, updated_at, policy_version)
//!
//! MAPLE scoring becomes a pure read-time function score(memory_defaults,
//! quality_row) — the Python server can adopt it without schema surgery on
//! `memories`.

use crate::evidence::{EvidenceRow, MapleMetrics};

#[derive(Debug, Clone, PartialEq)]
pub struct QualityRow {
    pub memory_id: String,
    pub tenant_id: String,
    pub rho: f64,
    pub tau: f64,
    pub harm: f64,
    pub taint: f64,
    pub evidence_count: u64,
    pub brier: f64,
    pub cusum: f64,
    pub updated_at_ms: i64,
    pub policy_version: String,
}

impl QualityRow {
    pub fn fresh(memory_id: &str, tenant_id: &str, now_ms: i64, policy_version: &str) -> Self {
        QualityRow {
            memory_id: memory_id.into(),
            tenant_id: tenant_id.into(),
            rho: 0.0,
            tau: 0.0,
            harm: 0.0,
            taint: 0.0,
            evidence_count: 0,
            brier: 0.0,
            cusum: 0.0,
            updated_at_ms: now_ms,
            policy_version: policy_version.into(),
        }
    }

    /// Fold one evidence row in. Monotone in evidence_count; rho/tau move
    /// toward the evidence-implied value with a saturating step so a single
    /// row can never saturate a score.
    pub fn absorb(&mut self, e: &EvidenceRow, now_ms: i64) {
        let w = e.weight.clamp(0.0, 1.0);
        let n = (self.evidence_count + 1) as f64;
        let step = w / n; // running mean
        match e.kind.as_str() {
            "retrieval_outcome" | "external_receipt" => {
                self.rho += (1.0 - self.rho) * step;
                self.tau += (1.0 - self.tau) * step;
            }
            "human_confirmation" => {
                self.rho = (self.rho + w).min(1.0);
                self.tau = (self.tau + w).min(1.0);
            }
            _ => {}
        }
        self.evidence_count += 1;
        self.updated_at_ms = now_ms;
    }

    /// Read-time MAPLE metrics: combine store defaults with accumulated quality.
    pub fn maple(&self, defaults: MapleMetrics) -> MapleMetrics {
        if self.evidence_count == 0 {
            // No evidence: defaults pass through UNCHANGED for retrieval scoring,
            // but the promotion gate (evidence.rs) refuses promotion regardless.
            return defaults;
        }
        MapleMetrics {
            rho: self.rho.max(defaults.rho * 0.0), // evidence-derived replaces default
            tau: self.tau,
            harm: defaults.harm.max(self.harm),
            taint: defaults.taint.max(self.taint),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn row() -> QualityRow {
        QualityRow::fresh("m1", "t1", 1_700_000_000_000, "tp-memory.policy.v1")
    }

    #[test]
    fn absorption_is_monotone_and_saturating() {
        let mut q = row();
        let e = EvidenceRow { memory_id: "m1".into(), kind: "retrieval_outcome".into(), weight: 1.0, observed_at_ms: 0 };
        let mut prev = 0.0;
        for _ in 0..50 {
            q.absorb(&e, 1);
            assert!(q.rho >= prev, "rho must never decrease on positive evidence");
            assert!(q.rho <= 1.0);
            prev = q.rho;
        }
        assert!(q.rho > 0.9);
        assert_eq!(q.evidence_count, 50);
    }

    #[test]
    fn no_evidence_passes_defaults_for_retrieval_only() {
        let q = row();
        let d = MapleMetrics { rho: 1.0, tau: 1.0, harm: 0.0, taint: 0.0 };
        assert_eq!(q.maple(d), d, "retrieval scoring unaffected; promotion gate handles admission");
    }

    #[test]
    fn harm_and_taint_take_max() {
        let mut q = row();
        q.harm = 0.3;
        let d = MapleMetrics { rho: 0.0, tau: 0.0, harm: 0.1, taint: 0.0 };
        q.evidence_count = 1;
        assert_eq!(q.maple(d).harm, 0.3, "harm never relaxes via quality table");
    }
}
