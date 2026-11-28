//! Daemon configuration: env-driven, fail-closed, every value provenance-stamped.
//!
//! Defaults are the SAFE end of every knob:
//!  * shadow mode ON  (distill + score, never promote — D3 default pending founder)
//!  * distiller budget ZERO (D2 default pending founder: no signed budget, no model call)
//!  * promotion evidence threshold 1 (E1)

/// Micro-units (1e-6 of the estate's internal currency unit), matching pennyd's
/// single-writer ledger convention.
pub type Micro = u64;

#[derive(Debug, Clone, PartialEq)]
pub struct Config {
    /// Advisory lock id; reuses the Python curation worker's 883921 so a
    /// deployed legacy worker and this daemon can never run simultaneously.
    pub advisory_lock_id: i64,
    /// E1: minimum positive evidence rows required before promotion is even evaluated.
    pub min_evidence_rows: u32,
    /// MAPLE promotion thresholds (from security_core.py; now versioned via policy).
    pub theta_rho: f64,
    pub theta_tau: f64,
    pub theta_harm: f64,
    /// Quarantine tripwires (curation_worker.py parity).
    pub quarantine_harm: f64,
    pub quarantine_taint: f64,
    /// E8: hard per-cycle distiller budget in micro-units. Default 0 = no model calls.
    pub distill_budget_micro: Micro,
    /// D3 default: when true, distillation proposals are scored and receipted
    /// but never written to the store.
    pub shadow_mode: bool,
    /// Revalidation sampling: max promoted facts re-checked per cycle.
    pub revalidate_batch: u32,
    /// CUSUM alarm threshold on per-fact Brier drift (revalidate.rs).
    pub cusum_alarm_h: f64,
    /// Brier level above which a promoted fact is demoted outright.
    pub demote_brier: f64,
    /// Policy version stamped on every score and receipt (E10).
    pub policy_version: String,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            advisory_lock_id: 883_921,
            min_evidence_rows: 1,
            theta_rho: 0.75,
            theta_tau: 0.85,
            theta_harm: 0.10,
            quarantine_harm: 0.40,
            quarantine_taint: 0.70,
            distill_budget_micro: 0,
            shadow_mode: true,
            revalidate_batch: 50,
            cusum_alarm_h: 4.0,
            demote_brier: 0.25,
            policy_version: "tp-memory.policy.v1".to_string(),
        }
    }
}

impl Config {
    pub fn from_env() -> Result<Self, crate::Error> {
        let mut c = Config::default();
        if let Some(v) = std::env::var_os("MITP_DISTILL_BUDGET_MICRO") {
            let s = v.to_string_lossy();
            c.distill_budget_micro = s
                .parse::<u64>()
                .map_err(|_| crate::Error::Config(format!("MITP_DISTILL_BUDGET_MICRO not u64: {s}")))?;
        }
        if let Some(v) = std::env::var_os("MITP_SHADOW_MODE") {
            c.shadow_mode = matches!(v.to_string_lossy().as_ref(), "1" | "true" | "TRUE" | "yes");
        }
        if let Some(v) = std::env::var_os("MITP_POLICY_VERSION") {
            let s = v.to_string_lossy().to_string();
            if s.is_empty() || s.len() > 64 {
                return Err(crate::Error::Config("MITP_POLICY_VERSION empty or >64 chars".into()));
            }
            c.policy_version = s;
        }
        Ok(c)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_fail_closed() {
        let c = Config::default();
        assert_eq!(c.distill_budget_micro, 0, "no signed budget -> no model calls (E8)");
        assert!(c.shadow_mode, "shadow mode default on (D3)");
        assert_eq!(c.min_evidence_rows, 1, "E1");
        assert_eq!(c.advisory_lock_id, 883_921, "parity with curation_worker.py");
    }

    #[test]
    fn bad_budget_env_fails_closed() {
        std::env::set_var("MITP_DISTILL_BUDGET_MICRO", "not-a-number");
        assert!(Config::from_env().is_err());
        std::env::remove_var("MITP_DISTILL_BUDGET_MICRO");
    }
}
