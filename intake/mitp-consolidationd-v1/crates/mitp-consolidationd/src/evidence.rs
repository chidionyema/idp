//! Staging + promotion gate. Fixes G1/G2:
//!  * G1: this IS the promotion daemon the estate never deployed.
//!  * G2 (E1): default scores are inadmissible. A memory with zero evidence
//!    rows is NEVER promoted, whatever its rho/tau/h — the Python worker's
//!    defaults (1.0/1.0/0.0) would have passed everything.

use crate::config::Config;

/// One piece of positive evidence for a memory: a retrieval that was marked
/// useful, an external receipt, or a human confirmation. `weight` in [0,1].
#[derive(Debug, Clone, PartialEq)]
pub struct EvidenceRow {
    pub memory_id: String,
    /// "retrieval_outcome" | "external_receipt" | "human_confirmation"
    pub kind: String,
    pub weight: f64,
    /// ms since epoch.
    pub observed_at_ms: i64,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct MapleMetrics {
    pub rho: f64,
    pub tau: f64,
    pub harm: f64,
    pub taint: f64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PromotionVerdict {
    Promote,
    Quarantine(&'static str),
    /// Not enough evidence yet; stays private, remains a staging candidate.
    Hold(&'static str),
}

/// Evidence-weighted quality: base metrics discounted toward truth by evidence
/// mass. With zero evidence, effective rho/tau are ZERO — this is the exact
/// inversion of the G2 bug, by construction.
pub fn evidence_adjusted(m: MapleMetrics, evidence: &[EvidenceRow]) -> MapleMetrics {
    if evidence.is_empty() {
        return MapleMetrics { rho: 0.0, tau: 0.0, harm: m.harm.max(1.0), taint: m.taint };
    }
    let w: f64 = evidence.iter().map(|e| e.weight.clamp(0.0, 1.0)).sum();
    let confidence = (w / (w + 1.0)).min(1.0); // saturating: 1 row -> 0.5, 3 rows -> 0.75
    MapleMetrics {
        rho: m.rho.clamp(0.0, 1.0) * confidence,
        tau: m.tau.clamp(0.0, 1.0) * confidence,
        harm: m.harm,
        taint: m.taint,
    }
}

pub fn evaluate(m: MapleMetrics, evidence: &[EvidenceRow], cfg: &Config) -> PromotionVerdict {
    // Quarantine tripwires run on RAW metrics, before any gate: harm and taint
    // are never discounted by evidence (curation_worker.py parity).
    if m.harm > cfg.quarantine_harm {
        return PromotionVerdict::Quarantine("harm tripwire");
    }
    if m.taint > cfg.quarantine_taint {
        return PromotionVerdict::Quarantine("taint tripwire");
    }
    if (evidence.len() as u32) < cfg.min_evidence_rows {
        return PromotionVerdict::Hold("no evidence (E1: defaults inadmissible)");
    }
    let adj = evidence_adjusted(m, evidence);
    if adj.rho >= cfg.theta_rho && adj.tau >= cfg.theta_tau && adj.harm <= cfg.theta_harm {
        PromotionVerdict::Promote
    } else {
        PromotionVerdict::Hold("below evidence-adjusted thresholds")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cfg() -> Config {
        Config::default()
    }
    fn ev(mem: &str, n: usize) -> Vec<EvidenceRow> {
        (0..n)
            .map(|i| EvidenceRow {
                memory_id: mem.into(),
                kind: "retrieval_outcome".into(),
                weight: 1.0,
                observed_at_ms: i64::try_from(1_700_000_000_000i64 + i as i64).unwrap_or(0),
            })
            .collect()
    }

    #[test]
    fn e1_default_scores_never_promote() {
        // The exact G2 scenario: pristine defaults, zero evidence.
        let pristine = MapleMetrics { rho: 1.0, tau: 1.0, harm: 0.0, taint: 0.0 };
        assert_eq!(
            evaluate(pristine, &[], &cfg()),
            PromotionVerdict::Hold("no evidence (E1: defaults inadmissible)")
        );
    }

    #[test]
    fn single_evidence_row_insufficient_confidence() {
        // confidence = 1/2 = 0.5 -> rho_eff = 0.5 < 0.75. One row is not enough.
        let m = MapleMetrics { rho: 1.0, tau: 1.0, harm: 0.0, taint: 0.0 };
        assert!(matches!(evaluate(m, &ev("a", 1), &cfg()), PromotionVerdict::Hold(_)));
    }

    #[test]
    fn strong_evidence_promotes() {
        // 3 rows -> confidence 0.75; rho_eff = 0.75 >= theta_rho, tau_eff = 0.75 < 0.85?
        // 0.75 < 0.85 so still hold; 9 rows -> conf 0.9 -> tau_eff 0.9 >= 0.85. Promote.
        let m = MapleMetrics { rho: 1.0, tau: 1.0, harm: 0.0, taint: 0.0 };
        assert!(matches!(evaluate(m, &ev("a", 3), &cfg()), PromotionVerdict::Hold(_)));
        assert_eq!(evaluate(m, &ev("a", 9), &cfg()), PromotionVerdict::Promote);
    }

    #[test]
    fn harm_tripwire_beats_evidence() {
        let m = MapleMetrics { rho: 1.0, tau: 1.0, harm: 0.5, taint: 0.0 };
        assert_eq!(
            evaluate(m, &ev("a", 100), &cfg()),
            PromotionVerdict::Quarantine("harm tripwire")
        );
    }

    #[test]
    fn taint_tripwire_beats_evidence() {
        let m = MapleMetrics { rho: 1.0, tau: 1.0, harm: 0.0, taint: 0.8 };
        assert_eq!(
            evaluate(m, &ev("a", 100), &cfg()),
            PromotionVerdict::Quarantine("taint tripwire")
        );
    }
}
