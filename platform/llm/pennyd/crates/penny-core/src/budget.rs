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
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::sync::RwLock;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Budget {
    daily_limit_usd: f64,
    spent_usd: f64,
    reserved_usd: f64,
    day: u64,
}

/// One reservation, persisted with the ledger. The money behind it is still
/// at risk until the operation is reconciled, and a retry of the same
/// operation must move it exactly once.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Reservation {
    pub op_id: String,
    /// Budget fingerprint of the key that holds the money.
    pub key: String,
    pub est_usd: f64,
    pub day: u64,
    /// True once the reservation has been reconciled. A settled reservation is
    /// kept, not deleted, so a retried operation is recognised as settled and
    /// moves no money a second time.
    #[serde(default)]
    pub settled: bool,
}

#[derive(Default, Serialize, Deserialize)]
struct BudgetFile {
    entries: HashMap<String, Budget>,
    /// Unsettled reservations, keyed by operation id. Ledgers written before
    /// this field existed deserialize as empty.
    #[serde(default)]
    reservations: HashMap<String, Reservation>,
    /// Write counter. A writer whose in-memory seq is older than the file's
    /// seq refuses to write instead of clobbering newer financial records.
    #[serde(default)]
    seq: u64,
}

/// Optional persistence backing. When `path` is set, every mutation is
/// written through (small file, worst-case a few hundred keys).
/// Clone is cheap: the map lives behind an Arc.
#[derive(Default, Clone)]
pub struct Budgets {
    map: std::sync::Arc<RwLock<HashMap<String, Budget>>>,
    reservations: std::sync::Arc<RwLock<HashMap<String, Reservation>>>,
    path: Option<PathBuf>,
    /// Set when the ledger on disk could not be parsed. A corrupt ledger is
    /// never read as an empty one: that would grant a fresh budget.
    poisoned: Arc<AtomicBool>,
    /// Monotonic write counter, compared with the file's seq before a write.
    seq: Arc<AtomicU64>,
    /// Counter for the operation ids used by callers that have none.
    auto_op: Arc<AtomicU64>,
}

impl Budgets {
    pub fn new() -> Self {
        Self::default()
    }

    /// P0-5: load persisted spend at boot so a restart never resets the day.
    pub fn with_persistence(path: impl AsRef<Path>) -> Self {
        let path = path.as_ref().to_path_buf();
        let mut entries = HashMap::new();
        let mut reservations = HashMap::new();
        let mut seq = 0u64;
        let mut poisoned = false;
        if let Ok(text) = fs::read_to_string(&path) {
            match serde_json::from_str::<BudgetFile>(&text) {
                Ok(file) => {
                    // Migrate legacy raw-key rows in place and keep the stored
                    // day intact. The stored reserved amount is KEPT: the money
                    // behind an unsettled reservation is still at risk, and
                    // zeroing it here handed back budget that was already
                    // committed.
                    let today = now_day();
                    for (stored_key, mut b) in file.entries {
                        let k = if stored_key.len() == 64
                            && stored_key.chars().all(|c| c.is_ascii_hexdigit())
                        {
                            stored_key
                        } else {
                            budget_fingerprint(&stored_key)
                        };
                        if b.day > today {
                            // A future day came from clock skew. Do not grant a
                            // reset merely because the wall clock moved backwards.
                            b.day = today;
                        }
                        entries.insert(k, b);
                    }
                    for (op_id, mut res) in file.reservations {
                        if res.key.len() != 64 || !res.key.chars().all(|c| c.is_ascii_hexdigit()) {
                            res.key = budget_fingerprint(&res.key);
                        }
                        reservations.insert(op_id, res);
                    }
                    seq = file.seq;
                }
                Err(e) => {
                    eprintln!("pennyd: budget ledger {} unreadable: {}", path.display(), e);
                    poisoned = true;
                }
            }
        }
        Self {
            map: std::sync::Arc::new(RwLock::new(entries)),
            reservations: std::sync::Arc::new(RwLock::new(reservations)),
            path: Some(path),
            poisoned: std::sync::Arc::new(AtomicBool::new(poisoned)),
            seq: std::sync::Arc::new(AtomicU64::new(seq)),
            auto_op: std::sync::Arc::new(AtomicU64::new(0)),
        }
    }

    pub fn ensure(&self, key: &str, daily_limit_usd: f64) {
        let key = budget_fingerprint(key);
        let mut m = self.map.write().unwrap();
        m.entry(key).or_insert(Budget {
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
            // reserved_usd is NOT released at midnight: the money behind an
            // unsettled reservation is still at risk until it is reconciled.
        }
    }

    /// Write the ledger through a temp file and rename. Err when the write
    /// failed or when another writer holds a newer ledger: a stale writer must
    /// never clobber newer financial records, and a budget that could not be
    /// written down must never authorise a dispatch.
    fn persist(&self) -> Result<(), PennyError> {
        let Some(path) = &self.path else {
            return Ok(());
        };
        let entries = self.map.read().unwrap().clone();
        let reservations = self.reservations.read().unwrap().clone();
        let local_seq = self.seq.load(Ordering::SeqCst);
        let seq = local_seq + 1;
        let file = BudgetFile {
            entries,
            reservations,
            seq,
        };
        let text =
            serde_json::to_string(&file).map_err(|e| self.ledger_err(path, e.to_string()))?;
        if let Ok(on_disk) = fs::read_to_string(path) {
            if let Ok(disk) = serde_json::from_str::<BudgetFile>(&on_disk) {
                if disk.seq > local_seq {
                    return Err(self.ledger_err(
                        path,
                        format!(
                            "stale writer: ledger seq {} is newer than local seq {}",
                            disk.seq, local_seq
                        ),
                    ));
                }
            }
        }
        let tmp = path.with_extension("tmp");
        fs::write(&tmp, text).map_err(|e| self.ledger_err(path, e.to_string()))?;
        fs::rename(&tmp, path).map_err(|e| self.ledger_err(path, e.to_string()))?;
        self.seq.store(seq, Ordering::SeqCst);
        Ok(())
    }

    fn ledger_err(&self, path: &Path, detail: String) -> PennyError {
        PennyError::Ledger {
            path: path.display().to_string(),
            detail,
        }
    }

    /// Reserve `est_usd` BEFORE dispatch. Refuses when spend + reserved + est
    /// would cross the limit — the request is denied before the money is at
    /// risk. Returns the reservation id (per-key monotonic counter).
    pub fn reserve_op(
        &self,
        op_id: &str,
        key: &str,
        est_usd: f64,
        now_unix: u64,
    ) -> Result<u64, PennyError> {
        if self.poisoned.load(Ordering::SeqCst) {
            return Err(self.ledger_err(
                &self.ledger_path(),
                "ledger unreadable; refusing to grant a fresh budget".to_string(),
            ));
        }
        let display_key = fingerprint(key);
        let key = budget_fingerprint(key);
        let id = res_id(op_id);
        if self.reservations.read().unwrap().contains_key(op_id) {
            return Ok(id);
        }
        let (result, snapshot) = {
            let mut m = self.map.write().unwrap();
            // A key with no entry is not "unlimited": it is an unknown key, and
            // an unknown key gets a zero budget. A panic here would be a remote
            // crash; a refusal is the fail-closed answer.
            let b = m.entry(key.clone()).or_insert(Budget {
                daily_limit_usd: 0.0,
                spent_usd: 0.0,
                reserved_usd: 0.0,
                day: 0,
            });
            let today = (now_unix / 86_400).max(b.day);
            Self::rollover(b, today);
            let result = if b.spent_usd + b.reserved_usd + est_usd > b.daily_limit_usd {
                Err(PennyError::BudgetExceeded {
                    key: display_key.clone(),
                })
            } else {
                b.reserved_usd += est_usd;
                Ok(1)
            };
            let snapshot: Vec<(String, Budget)> =
                m.iter().map(|(k, v)| (k.clone(), v.clone())).collect();
            (result, snapshot)
        };
        let _ = snapshot;
        if result.is_ok() {
            let day = self
                .map
                .read()
                .unwrap()
                .get(&key)
                .map(|b| b.day)
                .unwrap_or(0);
            self.reservations.write().unwrap().insert(
                op_id.to_string(),
                Reservation {
                    op_id: op_id.to_string(),
                    key: key.clone(),
                    est_usd,
                    day,
                    settled: false,
                },
            );
            if let Err(e) = self.persist() {
                self.roll_back(op_id, &key, est_usd);
                return Err(e);
            }
        }
        result
    }

    /// Legacy reservation for callers that carry no operation id.
    pub fn reserve(&self, key: &str, est_usd: f64, now_unix: u64) -> Result<u64, PennyError> {
        let op = self.next_auto_op();
        self.reserve_op(&op, key, est_usd, now_unix)
    }

    /// Reconcile a finished request: release the reservation, record actual
    /// spend. If the actual spend crossed the limit, the key is EXHAUSTED for
    /// the rest of the day (spent > limit makes every later reserve fail).
    pub fn settle_op(
        &self,
        op_id: &str,
        actual_usd: f64,
        now_unix: u64,
    ) -> Result<f64, PennyError> {
        if self.poisoned.load(Ordering::SeqCst) {
            return Err(self.ledger_err(
                &self.ledger_path(),
                "ledger unreadable; refusing to settle against unknown state".to_string(),
            ));
        }
        let res = match self.reservations.read().unwrap().get(op_id) {
            Some(r) => r.clone(),
            None => return Ok(self.spent_of(op_id)),
        };
        if res.settled {
            return Ok(self.spent_of(&res.key));
        }
        let key = res.key.clone();
        let (result, prev_reserved, prev_spent) = {
            let mut m = self.map.write().unwrap();
            let b = m
                .get_mut(&key)
                .ok_or_else(|| PennyError::Config(format!("budget for {key} was not ensured")))?;
            let today = (now_unix / 86_400).max(b.day);
            Self::rollover(b, today);
            let prev_reserved = b.reserved_usd;
            let prev_spent = b.spent_usd;
            b.reserved_usd = (b.reserved_usd - res.est_usd).max(0.0);
            b.spent_usd += actual_usd.max(0.0);
            (b.spent_usd, prev_reserved, prev_spent)
        };
        if let Some(r) = self.reservations.write().unwrap().get_mut(op_id) {
            r.settled = true;
        }
        if let Err(e) = self.persist() {
            let mut m = self.map.write().unwrap();
            if let Some(b) = m.get_mut(&key) {
                b.reserved_usd = prev_reserved;
                b.spent_usd = prev_spent;
            }
            drop(m);
            if let Some(r) = self.reservations.write().unwrap().get_mut(op_id) {
                r.settled = false;
            }
            return Err(e);
        }
        Ok(result)
    }

    /// Legacy one-shot path: reserve and settle the same operation.
    pub fn charge(&self, key: &str, usd: f64, now_unix: u64) -> Result<f64, PennyError> {
        let op = self.next_auto_op();
        self.reserve_op(&op, key, usd, now_unix)?;
        self.settle_op(&op, usd, now_unix)
    }

    pub fn remaining(&self, key: &str, now_unix: u64) -> f64 {
        let key = budget_fingerprint(key);
        let m = self.map.read().unwrap();
        match m.get(&key) {
            Some(b) if b.day >= now_unix / 86_400 => {
                (b.daily_limit_usd - b.spent_usd - b.reserved_usd).max(0.0)
            }
            Some(b) => b.daily_limit_usd,
            None => 0.0,
        }
    }

    /// P0-5: has the key crossed its limit (settled overrun)?
    pub fn is_exhausted(&self, key: &str, now_unix: u64) -> bool {
        let key = budget_fingerprint(key);
        let m = self.map.read().unwrap();
        match m.get(&key) {
            Some(b) if b.day >= now_unix / 86_400 => b.spent_usd >= b.daily_limit_usd,
            _ => false,
        }
    }

    fn ledger_path(&self) -> PathBuf {
        self.path
            .clone()
            .unwrap_or_else(|| PathBuf::from("<memory>"))
    }

    /// Undo a reservation that could not be persisted: the money was never
    /// committed, so the budget must not stay encumbered.
    fn roll_back(&self, op_id: &str, key: &str, est_usd: f64) {
        self.reservations.write().unwrap().remove(op_id);
        let mut m = self.map.write().unwrap();
        if let Some(b) = m.get_mut(key) {
            b.reserved_usd = (b.reserved_usd - est_usd).max(0.0);
        }
    }

    fn spent_of(&self, key: &str) -> f64 {
        self.map
            .read()
            .unwrap()
            .get(key)
            .map(|b| b.spent_usd)
            .unwrap_or(0.0)
    }

    fn next_auto_op(&self) -> String {
        let n = self.auto_op.fetch_add(1, Ordering::SeqCst);
        format!("auto-{n}")
    }
}

fn now_day() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() / 86_400)
        .unwrap_or(0)
}

/// Deterministic reservation id for an operation id: the same operation
/// always maps to the same id, so a retry is recognisable as a retry.
pub fn res_id(op_id: &str) -> u64 {
    let mut h: u64 = 0xcbf29ce484222325;
    for b in op_id.as_bytes() {
        h ^= *b as u64;
        h = h.wrapping_mul(0x100000001b3);
    }
    h | 1
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
        b.reserve_op("op-1", "k", 0.5, 1000).unwrap();
        b.settle_op("op-1", 1.5, 1001).unwrap(); // actual >> estimate
        assert!(b.is_exhausted("k", 1002));
        assert!(b.reserve_op("op-2", "k", 0.01, 1003).is_err());
    }

    #[test]
    fn spend_survives_restart() {
        // P0-5: restart must not reset the day
        let p = tmp("persist");
        {
            let b = Budgets::with_persistence(&p);
            b.ensure("k", 1.0);
            b.reserve_op("op-1", "k", 0.7, 1000).unwrap();
            b.settle_op("op-1", 0.7, 1001).unwrap();
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
            b.reserve_op("op-1", "k", 0.0, 86_398).unwrap();
            b.settle_op("op-1", 0.9, 86_399).unwrap();
        }
        let b2 = Budgets::with_persistence(&p);
        assert!(b2.reserve_op("op-2", "k", 0.9, 86_400).is_ok()); // next day
        let _ = fs::remove_file(&p);
    }

    #[test]
    fn day_never_goes_backwards() {
        let b = Budgets::new();
        b.ensure("k", 1.0);
        b.reserve_op("op-1", "k", 0.0, 200_000).unwrap();
        b.settle_op("op-1", 0.9, 200_000).unwrap();
        assert!(b.reserve_op("op-2", "k", 0.9, 100_000).is_err());
        assert!((b.remaining("k", 100_000) - 0.1).abs() < 1e-9);
    }

    #[test]
    fn a_reservation_that_cannot_be_written_is_refused() {
        let p = std::env::temp_dir().join(format!(
            "penny-no-such-dir-{}/ledger.json",
            std::process::id()
        ));
        let b = Budgets::with_persistence(&p);
        b.ensure("k", 1.0);
        assert!(b.reserve_op("op-1", "k", 0.5, 1000).is_err());
        // the money was never encumbered: the caller must not dispatch
        assert_eq!(b.remaining("k", 1000), 1.0);
    }

    #[test]
    fn an_unsettled_reservation_survives_a_restart() {
        let p = tmp("restart");
        {
            let b = Budgets::with_persistence(&p);
            b.ensure("k", 1.0);
            b.reserve_op("op-1", "k", 0.4, 1000).unwrap();
        }
        let b2 = Budgets::with_persistence(&p);
        b2.ensure("k", 1.0);
        assert_eq!(b2.remaining("k", 1000), 0.6);
        // a retry of the same operation after the restart moves no money
        b2.reserve_op("op-1", "k", 0.4, 1000).unwrap();
        assert_eq!(b2.remaining("k", 1000), 0.6);
        let _ = fs::remove_file(&p);
    }

    #[test]
    fn midnight_rollover_does_not_release_unsettled_funds() {
        let b = Budgets::new();
        b.ensure("k", 1.0);
        b.reserve_op("op-1", "k", 0.4, 1000).unwrap();
        let day1 = 86_400 + 1000;
        b.reserve_op("op-2", "k", 0.1, day1).unwrap();
        // the money behind op-1 is still at risk after midnight
        assert_eq!(b.remaining("k", day1), 0.5);
    }

    #[test]
    fn a_corrupt_ledger_never_grants_a_fresh_budget() {
        let p = tmp("corrupt");
        fs::write(&p, b"{ this is not json").unwrap();
        let b = Budgets::with_persistence(&p);
        b.ensure("k", 1.0);
        assert!(b.reserve_op("op-1", "k", 0.1, 1000).is_err());
        let _ = fs::remove_file(&p);
    }

    #[test]
    fn a_duplicate_operation_moves_money_once() {
        let b = Budgets::new();
        b.ensure("k", 1.0);
        b.reserve_op("op-1", "k", 0.3, 1000).unwrap();
        b.reserve_op("op-1", "k", 0.3, 1000).unwrap();
        assert_eq!(b.remaining("k", 1000), 0.7);
    }

    #[test]
    fn a_retried_settlement_does_not_charge_twice() {
        let b = Budgets::new();
        b.ensure("k", 1.0);
        b.reserve_op("op-1", "k", 0.3, 1000).unwrap();
        b.settle_op("op-1", 0.25, 1000).unwrap();
        b.settle_op("op-1", 0.25, 1000).unwrap();
        assert_eq!(b.remaining("k", 1000), 0.75);
    }

    #[test]
    fn a_settled_operation_stays_settled_across_a_restart() {
        let p = tmp("settled-restart");
        {
            let b = Budgets::with_persistence(&p);
            b.ensure("k", 1.0);
            b.reserve_op("op-1", "k", 0.3, 1000).unwrap();
            b.settle_op("op-1", 0.25, 1000).unwrap();
        }
        let b2 = Budgets::with_persistence(&p);
        b2.ensure("k", 1.0);
        // the retry after the restart must not charge the money twice
        b2.settle_op("op-1", 0.25, 1000).unwrap();
        assert_eq!(b2.remaining("k", 1000), 0.75);
        let _ = fs::remove_file(&p);
    }

    #[test]
    fn a_stale_writer_refuses_to_clobber_a_newer_ledger() {
        let p = tmp("stale");
        let a = Budgets::with_persistence(&p);
        let b = Budgets::with_persistence(&p);
        a.ensure("k", 1.0);
        b.ensure("k", 1.0);
        a.reserve_op("op-a", "k", 0.2, 1000).unwrap();
        // b loaded the ledger before a wrote it: b is stale and must refuse
        assert!(b.reserve_op("op-b", "k", 0.3, 1000).is_err());
        let text = fs::read_to_string(&p).unwrap();
        assert!(text.contains("op-a"), "{text}");
        assert!(!text.contains("op-b"), "{text}");
        let _ = fs::remove_file(&p);
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
