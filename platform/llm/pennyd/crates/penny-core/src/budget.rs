//! Per-key daily budgets: HARD, PERSISTED, and enforced BEFORE dispatch.
//! P0-5 repairs: (1) spend survives restart via JSON persistence; (2) upstream
//! cost is RESERVED before dispatch, then reconciled against actual usage;
//! (3) a settled overrun exhausts the key for the rest of the day instead of
//! pretending it didn't happen. Day rollover is monotonic (clock-skew proof).

use crate::error::PennyError;
use crate::keys::{budget_fingerprint, fingerprint};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::RwLock;

static SNAPSHOT_SEQUENCE: AtomicU64 = AtomicU64::new(0);

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
    unavailable: std::sync::Arc<AtomicBool>,
    load_failed: bool,
}

impl Budgets {
    pub fn new() -> Self {
        Self::default()
    }

    /// Load persisted spend and unresolved holds without granting a new budget.
    pub fn with_persistence(path: impl AsRef<Path>) -> Self {
        let path = path.as_ref().to_path_buf();
        let mut entries = HashMap::new();
        let mut unavailable = false;
        match fs::read_to_string(&path) {
            Ok(text) => match serde_json::from_str::<BudgetFile>(&text) {
                Ok(file) => {
                    for (stored_key, b) in file.entries {
                        let k = if stored_key.len() == 64
                            && stored_key.chars().all(|c| c.is_ascii_hexdigit())
                        {
                            stored_key
                        } else {
                            budget_fingerprint(&stored_key)
                        };
                        // Preserve unresolved reservations across restart. A
                        // missing settlement is NOT proof of zero provider spend.
                        // Keep the stored day as a monotonic high-water mark.
                        if !valid_amount(b.daily_limit_usd)
                            || !valid_amount(b.spent_usd)
                            || !valid_amount(b.reserved_usd)
                            || !(b.spent_usd + b.reserved_usd).is_finite()
                            || entries.insert(k, b).is_some()
                        {
                            unavailable = true;
                        }
                    }
                }
                Err(_) => unavailable = true,
            },
            Err(e) if e.kind() == io::ErrorKind::NotFound => {}
            Err(_) => unavailable = true,
        }
        Self {
            map: std::sync::Arc::new(RwLock::new(entries)),
            path: Some(path),
            unavailable: std::sync::Arc::new(AtomicBool::new(unavailable)),
            load_failed: unavailable,
        }
    }

    pub fn ensure(&self, key: &str, daily_limit_usd: f64) {
        let key = budget_fingerprint(key);
        let mut m = self.map.write().unwrap();
        if !valid_amount(daily_limit_usd) {
            self.unavailable.store(true, Ordering::Release);
            return;
        }
        m.entry(key).and_modify(|b| b.daily_limit_usd = daily_limit_usd).or_insert(Budget {
            daily_limit_usd,
            spent_usd: 0.0,
            reserved_usd: 0.0,
            day: 0,
        });
    }

    fn rollover(b: &mut Budget, today: u64) {
        if b.day != today {
            b.day = today;
            b.spent_usd = 0.0;
            // Outstanding requests can cross midnight. Do not release their hold.
        }
    }

    fn unavailable_error(&self) -> PennyError {
        PennyError::Config("budget persistence unavailable; dispatch refused".into())
    }

    fn check_available(&self) -> Result<(), PennyError> {
        if self.unavailable.load(Ordering::Acquire) {
            Err(self.unavailable_error())
        } else {
            Ok(())
        }
    }

    // The caller MUST hold the map write lock until this returns. Otherwise
    // an older snapshot can overwrite a newer admitted reservation.
    fn persist_locked(&self, entries: &HashMap<String, Budget>) -> Result<(), PennyError> {
        let Some(path) = &self.path else { return Ok(()) };
        let result = (|| -> io::Result<()> {
            let parent = path.parent().filter(|p| !p.as_os_str().is_empty())
                .unwrap_or_else(|| Path::new("."));
            let name = path.file_name().ok_or_else(|| {
                io::Error::new(io::ErrorKind::InvalidInput, "budget path has no filename")
            })?;
            let mut tmp_name = name.to_os_string();
            tmp_name.push(format!(
                ".{}.{}.tmp",
                std::process::id(),
                SNAPSHOT_SEQUENCE.fetch_add(1, Ordering::Relaxed)
            ));
            let tmp = parent.join(tmp_name);
            let text = serde_json::to_vec(&BudgetFile { entries: entries.clone() })
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
            let mut options = fs::OpenOptions::new();
            options.write(true).create_new(true);
            #[cfg(unix)]
            {
                use std::os::unix::fs::OpenOptionsExt;
                options.mode(0o600);
            }
            let mut file = options.open(&tmp)?;
            let written = (|| -> io::Result<()> {
                file.write_all(&text)?;
                file.sync_all()?;
                drop(file);
                fs::rename(&tmp, path)?;
                fs::File::open(parent)?.sync_all()?;
                Ok(())
            })();
            if written.is_err() {
                let _ = fs::remove_file(&tmp);
            }
            written
        })();
        if let Err(e) = result {
            // The external effect may already have happened (settlement).
            // Keep the in-memory liability and stop new dispatch until recovery.
            self.unavailable.store(true, Ordering::Release);
            tracing::error!(error = %e, "PennyD budget persistence failed");
            return Err(self.unavailable_error());
        }
        Ok(())
    }

    /// Reserve `est_usd` BEFORE dispatch. Refuses when spend + reserved + est
    /// would cross the limit — the request is denied before the money is at
    /// risk. The existing API returns a success marker, not a unique reservation ID.
    pub fn reserve(&self, key: &str, est_usd: f64, now_unix: u64) -> Result<u64, PennyError> {
        let display_key = fingerprint(key);
        let key = budget_fingerprint(key);
        let mut m = self.map.write().unwrap();
        self.check_available()?;
        if !valid_amount(est_usd) {
            return Err(PennyError::BadRequest("invalid budget estimate".into()));
        }
        let b = m.get_mut(&key).ok_or_else(|| PennyError::BudgetExceeded {
            key: display_key.clone(),
        })?;
        let today = (now_unix / 86_400).max(b.day);
        Self::rollover(b, today);
        let proposed = b.spent_usd + b.reserved_usd + est_usd;
        if !valid_amount(b.daily_limit_usd) || !proposed.is_finite()
            || proposed > b.daily_limit_usd
        {
            return Err(PennyError::BudgetExceeded { key: display_key });
        }
        b.reserved_usd += est_usd;
        self.persist_locked(&m)?;
        Ok(1)
    }

    /// Reconcile a finished request: release the reservation, record actual
    /// spend. If the actual spend crossed the limit, the key is EXHAUSTED for
    /// the rest of the day (spent > limit makes every later reserve fail).
    pub fn settle(
        &self,
        key: &str,
        est_usd: f64,
        actual_usd: f64,
        now_unix: u64,
    ) -> Result<f64, PennyError> {
        let key = budget_fingerprint(key);
        let mut m = self.map.write().unwrap();
        // Never overwrite an untrusted or partially loaded on-disk ledger.
        if self.load_failed {
            return Err(self.unavailable_error());
        }
        if !valid_amount(est_usd) || !valid_amount(actual_usd) {
            self.unavailable.store(true, Ordering::Release);
            return Err(self.unavailable_error());
        }
        let Some(b) = m.get_mut(&key) else {
            self.unavailable.store(true, Ordering::Release);
            return Err(self.unavailable_error());
        };
        let today = (now_unix / 86_400).max(b.day);
        Self::rollover(b, today);
        let total = b.spent_usd + actual_usd;
        if !total.is_finite() {
            self.unavailable.store(true, Ordering::Release);
            return Err(self.unavailable_error());
        }
        b.reserved_usd = (b.reserved_usd - est_usd).max(0.0);
        b.spent_usd = total;
        // Even if a previous write failed, record completion of in-flight work.
        // Do not clear the refusal latch merely because a later write succeeds.
        self.persist_locked(&m)?;
        self.check_available()?;
        Ok(total)
    }

    pub fn charge(&self, key: &str, usd: f64, now_unix: u64) -> Result<f64, PennyError> {
        // legacy one-shot path: reserve+settle with no estimate delta
        self.reserve(key, usd, now_unix)?;
        self.settle(key, usd, usd, now_unix)
    }

    pub fn remaining(&self, key: &str, now_unix: u64) -> f64 {
        let key = budget_fingerprint(key);
        let m = self.map.read().unwrap();
        if self.unavailable.load(Ordering::Acquire) {
            return 0.0;
        }
        match m.get(&key) {
            Some(b) if b.day >= now_unix / 86_400 => {
                (b.daily_limit_usd - b.spent_usd - b.reserved_usd).max(0.0)
            }
            Some(b) => (b.daily_limit_usd - b.reserved_usd).max(0.0),
            None => 0.0,
        }
    }

    /// P0-5: has the key crossed its limit (settled overrun)?
    pub fn is_exhausted(&self, key: &str, now_unix: u64) -> bool {
        let key = budget_fingerprint(key);
        let m = self.map.read().unwrap();
        if self.unavailable.load(Ordering::Acquire) {
            return true;
        }
        match m.get(&key) {
            Some(b) if b.day >= now_unix / 86_400 => b.spent_usd >= b.daily_limit_usd,
            _ => false,
        }
    }
}

fn valid_amount(value: f64) -> bool {
    value.is_finite() && value >= 0.0
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
        assert!((b2.remaining("k", 1002) - 0.3).abs() < 1e-9);
        assert!(b2.reserve("k", 0.5, 1003).is_err());
        let persisted = fs::read_to_string(&p).unwrap();
        assert!(!persisted.contains("\"k\""), "{persisted}");
        assert!(!persisted.contains("k1"), "{persisted}");
        let _ = fs::remove_file(&p);
    }

    #[test]
    fn day_rollover_resets_persisted() {
        let p = tmp("roll");
        {
            let b = Budgets::with_persistence(&p);
            b.ensure("k", 1.0);
            b.settle("k", 0.0, 0.9, 86_399).unwrap();
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
        assert!((b.remaining("k", 100_000) - 0.1).abs() < 1e-9);
    }
}

#[cfg(test)]
mod unknown_key_tests {
    use super::*;

    #[test]
    fn an_unknown_key_is_refused_not_panicked() {
        let b = Budgets::new();
        // No ensure(): this used to panic inside reserve(), which is a remote crash
        // for any key the config did not pre-register.
        let r = b.reserve("never-seen", 0.01, 1_700_000_000);
        assert!(matches!(r, Err(PennyError::BudgetExceeded { .. })));
    }

    #[test]
    fn an_ensured_key_can_reserve() {
        let b = Budgets::new();
        b.ensure("known", 5.0);
        assert!(b.reserve("known", 0.01, 1_700_000_000).is_ok());
    }
}

#[cfg(test)]
mod persistence_boundary_tests {
    use super::*;

    fn path(name: &str) -> PathBuf {
        let p = std::env::temp_dir().join(format!(
            "penny-budget-boundary-{}-{name}", std::process::id()
        ));
        let _ = fs::remove_file(&p);
        let _ = fs::remove_dir_all(&p);
        p
    }

    #[test]
    fn no_dispatch_when_snapshot_cannot_be_committed() {
        let p = path("write-failure");
        let b = Budgets::with_persistence(&p);
        b.ensure("k", 1.0);
        fs::create_dir(&p).unwrap();
        assert!(b.reserve("k", 0.25, 1000).is_err());
        assert_eq!(b.remaining("k", 1000), 0.0);
        fs::remove_dir(&p).unwrap();
        assert!(b.reserve("k", 0.25, 1001).is_err());
    }

    #[test]
    fn an_unreadable_or_corrupt_ledger_cannot_mint_a_fresh_budget() {
        let p = path("corrupt");
        fs::write(&p, "{broken").unwrap();
        let b = Budgets::with_persistence(&p);
        b.ensure("k", 1.0);
        assert!(b.reserve("k", 0.25, 1000).is_err());
        assert!(b.is_exhausted("k", 1000));
        assert!(b.settle("k", 0.0, 0.25, 1001).is_err());
        assert_eq!(fs::read_to_string(&p).unwrap(), "{broken");
        fs::remove_file(&p).unwrap();
    }

    #[test]
    fn crash_does_not_refund_unsettled_money() {
        let p = path("restart");
        {
            let b = Budgets::with_persistence(&p);
            b.ensure("k", 1.0);
            b.reserve("k", 0.75, 1000).unwrap();
        }
        let b = Budgets::with_persistence(&p);
        assert_eq!(b.remaining("k", 1001), 0.25);
        assert!(b.reserve("k", 0.5, 1001).is_err());
        assert!(b.reserve("k", 0.25, 1001).is_ok());
        b.settle("k", 0.25, 0.125, 1002).unwrap();
        assert_eq!(b.remaining("k", 1002), 0.125);
        fs::remove_file(&p).unwrap();
    }

    #[test]
    fn new_day_does_not_refund_inflight_money() {
        let b = Budgets::new();
        b.ensure("k", 1.0);
        b.reserve("k", 0.75, 86_399).unwrap();
        assert_eq!(b.remaining("k", 86_400), 0.25);
        assert!(b.reserve("k", 0.5, 86_400).is_err());
        b.reserve("k", 0.25, 86_400).unwrap();
        b.settle("k", 0.75, 0.5, 86_401).unwrap();
        assert_eq!(b.remaining("k", 86_401), 0.25);
    }

    #[test]
    fn concurrent_admissions_cannot_regress_durable_snapshot() {
        let p = path("concurrent");
        let b = Budgets::with_persistence(&p);
        b.ensure("k", 1.0);
        let handles: Vec<_> = (0..24).map(|_| {
            let b = b.clone();
            std::thread::spawn(move || b.reserve("k", 0.125, 1000).is_ok())
        }).collect();
        let admitted: usize = handles.into_iter().map(|h| if h.join().unwrap() { 1usize } else { 0usize }).sum();
        assert_eq!(admitted, 8);
        let restarted = Budgets::with_persistence(&p);
        assert_eq!(restarted.remaining("k", 1001), 0.0);
        assert!(restarted.reserve("k", 0.125, 1001).is_err());
        fs::remove_file(&p).unwrap();
    }

    #[test]
    fn invalid_amounts_and_unknown_zero_cost_are_refused() {
        let b = Budgets::new();
        b.ensure("k", 1.0);
        for n in [-1.0, f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
            assert!(b.reserve("k", n, 1000).is_err());
        }
        assert!(b.reserve("unknown", 0.0, 1000).is_err());
        assert_eq!(b.remaining("k", 1000), 1.0);
    }

    #[test]
    fn failed_settlement_stops_additional_admission() {
        let p = path("settlement");
        let b = Budgets::with_persistence(&p);
        b.ensure("k", 1.0);
        b.reserve("k", 0.25, 1000).unwrap();
        fs::remove_file(&p).unwrap();
        fs::create_dir(&p).unwrap();
        assert!(b.settle("k", 0.25, 0.25, 1001).is_err());
        assert!(b.reserve("k", 0.25, 1002).is_err());
        fs::remove_dir(&p).unwrap();
    }
}

#[cfg(test)]
#[test]
fn config_limit_reduction_does_not_reset_accumulated_spend() {
    let b = Budgets::new();
    b.ensure("k", 1.0);
    b.charge("k", 0.5, 1000).unwrap();
    b.ensure("k", 0.5);
    assert!(b.reserve("k", 0.125, 1001).is_err());
}
