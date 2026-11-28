//! Revalidation (G5): promoted facts are re-checked continuously; quality is
//! surveilled with Brier scoring + one-sided CUSUM drift alarms, the same math
//! as decision.rs cusum_drift_alarm. Drift demotes to quarantine and emits a
//! recalibration task — a stale specialist fact loses its promotion
//! empirically, exactly as the thinking-packs policy demands.

use crate::config::Config;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OracleClass {
    /// An external oracle exists (simulator, reproducible check): outcomes are
    /// ground truth; CUSUM demotion is automatic.
    External,
    /// No oracle (E9): surveilled by retrieval-outcome Brier only; never
    /// auto-demoted — drift routes to the human review queue instead.
    OracleNone,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Surveillance {
    /// Running Brier score of this fact's predictions/claims vs outcomes.
    pub brier: f64,
    /// One-sided CUSUM accumulator on (observed error - allowed error).
    pub cusum: f64,
    pub observations: u64,
}

impl Surveillance {
    pub fn new() -> Self {
        Surveillance { brier: 0.0, cusum: 0.0, observations: 0 }
    }
}

impl Default for Surveillance {
    fn default() -> Self {
        Self::new()
    }
}

/// What one revalidation observation says: predicted confidence vs outcome.
#[derive(Debug, Clone, Copy)]
pub struct Observation {
    /// Confidence the fact implied when used, in [0,1].
    pub predicted: f64,
    /// 1.0 = outcome confirmed the fact, 0.0 = outcome contradicted it.
    pub outcome: f64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SurveillanceVerdict {
    Healthy,
    /// CUSUM crossed the alarm: demote (External) or route to human (OracleNone).
    DriftAlarm,
    /// Brier alone is unacceptable: demote (External) or human queue (OracleNone).
    UnacceptableError,
}

/// Fold one observation in. `allowed_error` is the reference slack (drift
/// parameter k in CUSUM terms): errors at or below it are normal noise.
pub fn observe(s: &mut Surveillance, o: Observation, allowed_error: f64) {
    let p = o.predicted.clamp(0.0, 1.0);
    let y = o.outcome.clamp(0.0, 1.0);
    let err = (p - y) * (p - y); // Brier term
    s.brier = if s.observations == 0 {
        err
    } else {
        let n = s.observations as f64;
        (s.brier * n + err) / (n + 1.0)
    };
    // One-sided upward CUSUM on excess error; reset to 0 on healthy reads.
    s.cusum = (s.cusum + err - allowed_error).max(0.0);
    s.observations += 1;
}

pub fn verdict(s: &Surveillance, oracle: OracleClass, cfg: &Config) -> SurveillanceVerdict {
    if s.observations == 0 {
        return SurveillanceVerdict::Healthy; // cold start: no verdict without data
    }
    if s.brier > cfg.demote_brier {
        return SurveillanceVerdict::UnacceptableError;
    }
    if s.cusum >= cfg.cusum_alarm_h {
        return SurveillanceVerdict::DriftAlarm;
    }
    let _ = oracle; // oracle class decides the ACTION (demote vs human queue), taken by cycle.rs
    SurveillanceVerdict::Healthy
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cfg() -> Config {
        Config::default()
    }

    #[test]
    fn healthy_stream_stays_healthy() {
        let mut s = Surveillance::new();
        for _ in 0..100 {
            observe(&mut s, Observation { predicted: 0.9, outcome: 1.0 }, 0.05);
        }
        assert_eq!(verdict(&s, OracleClass::External, &cfg()), SurveillanceVerdict::Healthy);
        assert!(s.brier < 0.05);
        assert_eq!(s.cusum, 0.0, "healthy reads reset the accumulator");
    }

    #[test]
    fn sustained_drift_trips_cusum() {
        let mut s = Surveillance::new();
        // Confident but wrong half the time: brier term (0.9-0)^2 = 0.81 on failures.
        for i in 0..20 {
            let outcome = if i % 2 == 0 { 1.0 } else { 0.0 };
            observe(&mut s, Observation { predicted: 0.9, outcome }, 0.05);
            if matches!(verdict(&s, OracleClass::External, &cfg()), SurveillanceVerdict::UnacceptableError | SurveillanceVerdict::DriftAlarm) {
                return; // tripped, as required
            }
        }
        panic!("sustained 50% contradiction at 0.9 confidence must trip surveillance");
    }

    #[test]
    fn cold_start_gives_no_verdict() {
        let s = Surveillance::new();
        assert_eq!(verdict(&s, OracleClass::External, &cfg()), SurveillanceVerdict::Healthy);
    }

    #[test]
    fn brier_running_mean_is_correct() {
        let mut s = Surveillance::new();
        observe(&mut s, Observation { predicted: 1.0, outcome: 0.0 }, 0.05); // err 1.0
        observe(&mut s, Observation { predicted: 0.0, outcome: 0.0 }, 0.05); // err 0.0
        assert!((s.brier - 0.5).abs() < 1e-9);
    }
}
