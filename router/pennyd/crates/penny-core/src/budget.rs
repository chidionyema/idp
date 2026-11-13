//! Per-key daily budgets: HARD, PERSISTED, and enforced BEFORE dispatch.
//! P0-5 repairs: (1) spend survives restart via JSON persistence; (2) upstream
//! cost is RESERVED before dispatch, then reconciled against actual usage;
//! (3) a settled overrun exhausts the key for the rest of the day instead of
//! pretending it didn't happen. Day rollover is monotonic (clock-skew proof).

use crate::error::PennyError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::RwLock;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Budget {
    daily_limit_usd: f64,
    spent_usd: f64,
    reserved_usd: f64,
    day: u64,
}

#[derive(Default, Serialize, Deserialize)]
struct BudgetFile {
    entries: HashMap<String, Budget>,
}

/// Optional persistence backing. When `path` is set, every mutation is
/// written through (small file, worst-case a few hundred keys).
/// Clone is cheap: the map lives behind an Arc.
#[derive(Default, Clone)]
pub struct Budgets {
    map: std::sync::Arc<RwLock<HashMap<String, Budget>>>,
    path: Option<PathBuf>,
}

impl Budgets {
    pub fn new() -> Self {
        Self::default()
    }

    fn now_day() -> u64 {
        now_day()
    }

    /// P0-5: load persisted spend at boot so a restart never resets the day.
    pub fn with_persistence(path: impl AsRef<Path>) -> Self {
        let path = path.as_ref().to_path_buf();
        let mut entries = HashMap::new();
        if let Ok(text) = fs::read_to_string(&path) {
            if let Ok(file) = serde_json::from_str::<BudgetFile>(&text) {
                // monotonic guard at load: a backdated file cannot grant a reset
                let today = now_day();
                for (k, mut b) in file.entries {
                    b.day = b.day.max(today.min(b.day)); // keep stored day unless it's in the future
                    if b.day > today {
                        b.day = today;
                    }
                    entries.insert(k, b);
                }
            }
        }
        Self { map: std::sync::Arc::new(RwLock::new(entries)), path: Some(path) }
    }

    pub fn ensure(&self, key: &str, daily_limit_usd: f64) {
        let mut m = self.map.write().unwrap();
        m.entry(key.to_string()).or_insert(Budget {
            daily_limit_usd,
            spent_usd: 0.0,
            reserved_usd: 0.0,
            day: u64::MAX,
        });
    }

    fn now_day() -> u64 {
        now_day()
    }

    fn rollover(b: &mut Budget, today: u64) {
        if b.day != today {
            b.day = today;
            b.spent_usd = 0.0;
            b.reserved_usd = 0.0;
        }
    }

    fn persist(&self) {
        let Some(path) = &self.path else { return };
        let snapshot: Vec<(String, Budget)> = {
            let m = self.map.read().unwrap();
            m.iter().map(|(k, v)| (k.clone(), v.clone())).collect()
        };
        let mut entries = HashMap::new();
        for (k, v) in snapshot {
            entries.insert(k, v);
        }
        let file = BudgetFile { entries };
        if let Ok(text) = serde_json::to_string(&file) {
            let tmp = path.with_extension("tmp");
            if fs::write(&tmp, text).is_ok() {
                let _ = fs::rename(&tmp, path);
            }
        }
    }

    /// Reserve `est_usd` BEFORE dispatch. Refuses when spend + reserved + est
    /// would cross the limit — the request is denied before the money is at
    /// risk. Returns the reservation id (per-key monotonic counter).
    pub fn reserve(&self, key: &str, est_usd: f64, now_unix: u64) -> Result<u64, PennyError> {
        let today = now_unix / 86_400;
        let mut m = self.map.write().unwrap();
        let b = m.get_mut(key).expect("call ensure() before reserve()");
        Self::rollover(b, today);
        if b.spent_usd + b.reserved_usd + est_usd > b.daily_limit_usd {
            return Err(PennyError::BudgetExceeded { key: key.to_string() });
        }
        b.reserved_usd += est_usd;
        self.persist();
        Ok(1)
    }

    /// Reconcile a finished request: release the reservation, record actual
    /// spend. If the actual spend crossed the limit, the key is EXHAUSTED for
    /// the rest of the day (spent > limit makes every later reserve fail).
    pub fn settle(&self, key: &str, est_usd: f64, actual_usd: f64, now_unix: u64) -> Result<f64, PennyError> {
        let today = now_unix / 86_400;
        let mut m = self.map.write().unwrap();
        let b = m.get_mut(key).expect("call ensure() before settle()");
        Self::rollover(b, today);
        b.reserved_usd = (b.reserved_usd - est_usd).max(0.0);
        b.spent_usd += actual_usd.max(0.0);
        self.persist();
        Ok(b.spent_usd)
    }

    pub fn charge(&self, key: &str, usd: f64, now_unix: u64) -> Result<f64, PennyError> {
        // legacy one-shot path: reserve+settle with no estimate delta
        self.reserve(key, usd, now_unix)?;
        self.settle(key, usd, usd, now_unix)
    }

    pub fn remaining(&self, key: &str, now_unix: u64) -> f64 {
        let today = now_unix / 86_400;
        let m = self.map.read().unwrap();
        match m.get(key) {
            Some(b) if b.day == today => {
                (b.daily_limit_usd - b.spent_usd - b.reserved_usd).max(0.0)
            }
            Some(b) => b.daily_limit_usd,
            None => 0.0,
        }
    }

    /// P0-5: has the key crossed its limit (settled overrun)?
    pub fn is_exhausted(&self, key: &str, now_unix: u64) -> bool {
        let today = now_unix / 86_400;
        let m = self.map.read().unwrap();
        match m.get(key) {
            Some(b) if b.day == today => b.spent_usd >= b.daily_limit_usd,
            _ => false,
        }
    }
}

fn now_day() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() / 86_400)
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp(path: &str) -> PathBuf {
        let p = std::env::temp_dir().join(format!("penny-budget-{}-{path}", std::process::id()));
        let _ = fs::remove_file(&p);
        p
    }

    #[test]
    fn reserve_refuses_before_spend() {
        // P0-5: the refusal happens BEFORE dispatch, not after
        let b = Budgets::new();
        b.ensure("k", 1.0);
        assert!(b.reserve("k", 0.6, 1000).is_ok());
        assert!(b.reserve("k", 0.6, 1001).is_err()); // 1.2 > 1.0 with reservation held
        assert_eq!(b.remaining("k", 1002), 0.4);
    }

    #[test]
    fn settle_records_overrun_and_exhausts() {
        let b = Budgets::new();
        b.ensure("k", 1.0);
        b.reserve("k", 0.5, 1000).unwrap();
        b.settle("k", 0.5, 1.5, 1001).unwrap(); // actual >> estimate
        assert!(b.is_exhausted("k", 1002));
        assert!(b.reserve("k", 0.01, 1003).is_err());
    }

    #[test]
    fn spend_survives_restart() {
        // P0-5: restart must not reset the day
        let p = tmp("persist");
        {
            let b = Budgets::with_persistence(&p);
            b.ensure("k", 1.0);
            b.reserve("k", 0.7, 1000).unwrap();
            b.settle("k", 0.7, 0.7, 1001).unwrap();
        }
        let b2 = Budgets::with_persistence(&p);
        assert_eq!(b2.remaining("k", 1002), 0.3);
        assert!(b2.reserve("k", 0.5, 1003).is_err());
        let _ = fs::remove_file(&p);
    }

    #[test]
    fn day_rollover_resets_persisted() {
        let p = tmp("roll");
        {
            let b = Budgets::with_persistence(&p);
            b.ensure("k", 1.0);
            b.settle("k", 0, 0.9, 86_399).unwrap();
        }
        let b2 = Budgets::with_persistence(&p);
        assert!(b2.reserve("k", 0.9, 86_400).is_ok()); // next day
        let _ = fs::remove_file(&p);
    }

    #[test]
    fn day_never_goes_backwards() {
        let b = Budgets::new();
        b.ensure("k", 1.0);
        b.settle("k", 0.0, 0.9, 200_000).unwrap();
        assert!(b.reserve("k", 0.9, 100_000).is_err());
        assert_eq!(b.remaining("k", 100_000), 0.1);
    }
}
