//! Store abstraction. All Postgres access in the estate goes through this
//! trait (wired to sqlx there); tests use MockStore. The trait's shape encodes
//! the RLS discipline: every operation is tenant-scoped, and `run_tenant_tx`
//! guarantees SET_TENANT runs inside the same transaction as the closure.

use crate::quality::QualityRow;
use crate::{distill::Episode, evidence::EvidenceRow, Result};

/// A memory row as the cycle sees it.
#[derive(Debug, Clone, PartialEq)]
pub struct MemoryRow {
    pub id: String,
    pub tenant_id: String,
    pub namespace: String,
    pub key: String,
    pub content: String,
    pub rho: f64,
    pub tau: f64,
    pub harm: f64,
    pub taint: f64,
    pub created_ms: i64,
    pub evidence_count: u64,
}

pub trait MemoryStore {
    /// E11: acquire the advisory lock inside a transaction; false = follower.
    fn try_leader(&self, lock_id: i64) -> Result<bool>;
    fn list_tenants(&self) -> Result<Vec<String>>;

    /// Run `f` in a per-tenant transaction with app.tenant_id set (E3).
    /// The estate implementation: BEGIN; SET_TENANT; f; COMMIT/ROLLBACK.
    fn run_tenant_tx<T>(&self, tenant_id: &str, f: &mut dyn FnMut(&dyn TenantTx) -> Result<T>) -> Result<T>;

    /// Housekeeping at estate level already handled per-tenant inside the tx;
    /// these are the tx-scoped operations:
    fn tenants_count(&self) -> Result<u64>;
}

/// Tenant-transaction-scoped operations. Every method maps to one sql.rs
/// statement; implementations MUST assert RETURNING rowcounts (E3).
pub trait TenantTx {
    fn staging_candidates(&self, limit: u32) -> Result<Vec<MemoryRow>>;
    fn evidence_for(&self, memory_id: &str) -> Result<Vec<EvidenceRow>>;
    fn promote_shared(&self, memory_id: &str) -> Result<u64>;
    fn quarantine(&self, memory_id: &str) -> Result<u64>;
    fn upsert_quality(&self, q: &QualityRow) -> Result<u64>;
    fn insert_evidence(&self, e: &EvidenceRow, tenant_id: &str) -> Result<u64>;
    fn insert_distilled(&self, tenant_id: &str, namespace: &str, key: &str, content: &str, provenance_json: &str) -> Result<u64>;
    fn revalidation_sample(&self, limit: u32) -> Result<Vec<MemoryRow>>;
    fn quality_of(&self, memory_id: &str) -> Result<Option<QualityRow>>;
    fn existing_distilled(&self, namespace: &str) -> Result<(Vec<String>, Vec<String>)>;
    fn recent_episodes(&self, limit: u32) -> Result<Vec<Episode>>;
    fn insert_receipt(&self, cycle_id: &str, payload_json: &str) -> Result<u64>;
    fn housekeeping(&self, recurrence_max_age_days: u32) -> Result<(u64, u64)>;
}

// ---------------------------------------------------------------------------
// MockStore: in-memory implementation for the full test suite.
// ---------------------------------------------------------------------------

#[cfg(test)]
pub mod mock {
    use super::*;
    use std::cell::RefCell;
    use std::collections::HashMap;

    #[derive(Default)]
    pub struct MockStore {
        pub leader: bool,
        pub tenants: RefCell<Vec<String>>,
        pub memories: RefCell<Vec<MemoryRow>>,
        pub shared: RefCell<HashMap<String, bool>>,
        pub quarantined: RefCell<HashMap<String, bool>>,
        pub evidence: RefCell<HashMap<String, Vec<EvidenceRow>>>,
        pub quality: RefCell<HashMap<String, QualityRow>>,
        pub episodes: RefCell<Vec<Episode>>,
        pub distilled: RefCell<Vec<(String, String, String)>>, // (ns, key, content)
        pub receipts: RefCell<Vec<String>>,
        /// Forensic log of every "SQL" the cycle issued — acceptance test 2
        /// asserts no `memories` bookkeeping UPDATE appears here.
        pub issued: RefCell<Vec<String>>,
        /// Set to simulate the idp#6507 failure: GUC unset -> writes match 0.
        pub simulate_guc_unset: bool,
    }

    impl MockStore {
        pub fn leader() -> Self {
            MockStore { leader: true, ..Default::default() }
        }
        fn log(&self, s: &str) {
            self.issued.borrow_mut().push(s.to_string());
        }
    }

    impl MemoryStore for MockStore {
        fn try_leader(&self, _lock_id: i64) -> Result<bool> {
            Ok(self.leader)
        }
        fn list_tenants(&self) -> Result<Vec<String>> {
            Ok(self.tenants.borrow().clone())
        }
        fn run_tenant_tx<T>(&self, tenant_id: &str, f: &mut dyn FnMut(&dyn TenantTx) -> Result<T>) -> Result<T> {
            self.log(&format!("SET_TENANT {tenant_id}"));
            let tx = MockTx { store: self, tenant: tenant_id.to_string() };
            f(&tx)
        }
        fn tenants_count(&self) -> Result<u64> {
            Ok(self.tenants.borrow().len() as u64)
        }
    }

    struct MockTx<'a> {
        store: &'a MockStore,
        tenant: String,
    }

    impl<'a> MockTx<'a> {
        fn write_guard(&self, statement: &'static str, expected: u64) -> Result<u64> {
            self.store.log(statement);
            if self.store.simulate_guc_unset && expected > 0 {
                // E3: silent no-op must be a hard error, never a green receipt.
                return Err(crate::Error::RlsSilentNoOp { statement, expected });
            }
            Ok(expected)
        }
    }

    impl<'a> TenantTx for MockTx<'a> {
        fn staging_candidates(&self, _limit: u32) -> Result<Vec<MemoryRow>> {
            Ok(self
                .store
                .memories
                .borrow()
                .iter()
                .filter(|m| m.tenant_id == self.tenant)
                .filter(|m| !self.store.shared.borrow().get(&m.id).copied().unwrap_or(false))
                .filter(|m| !self.store.quarantined.borrow().get(&m.id).copied().unwrap_or(false))
                .cloned()
                .collect())
        }
        fn evidence_for(&self, memory_id: &str) -> Result<Vec<EvidenceRow>> {
            Ok(self.store.evidence.borrow().get(memory_id).cloned().unwrap_or_default())
        }
        fn promote_shared(&self, memory_id: &str) -> Result<u64> {
            self.write_guard("PROMOTE_SHARED", 1)?;
            self.store.shared.borrow_mut().insert(memory_id.into(), true);
            Ok(1)
        }
        fn quarantine(&self, memory_id: &str) -> Result<u64> {
            self.write_guard("QUARANTINE", 1)?;
            self.store.quarantined.borrow_mut().insert(memory_id.into(), true);
            Ok(1)
        }
        fn upsert_quality(&self, q: &QualityRow) -> Result<u64> {
            self.write_guard("UPSERT_QUALITY", 1)?;
            self.store.quality.borrow_mut().insert(q.memory_id.clone(), q.clone());
            Ok(1)
        }
        fn insert_evidence(&self, e: &EvidenceRow, _tenant_id: &str) -> Result<u64> {
            self.store.log("INSERT_EVIDENCE");
            self.store.evidence.borrow_mut().entry(e.memory_id.clone()).or_default().push(e.clone());
            Ok(1)
        }
        fn insert_distilled(&self, _tenant_id: &str, namespace: &str, key: &str, content: &str, provenance_json: &str) -> Result<u64> {
            self.store.log(&format!("INSERT_DISTILLED {provenance_json}"));
            self.store.distilled.borrow_mut().push((namespace.into(), key.into(), content.into()));
            Ok(1)
        }
        fn revalidation_sample(&self, _limit: u32) -> Result<Vec<MemoryRow>> {
            Ok(self
                .store
                .memories
                .borrow()
                .iter()
                .filter(|m| m.tenant_id == self.tenant)
                .filter(|m| self.store.shared.borrow().get(&m.id).copied().unwrap_or(false))
                .cloned()
                .collect())
        }
        fn quality_of(&self, memory_id: &str) -> Result<Option<QualityRow>> {
            Ok(self.store.quality.borrow().get(memory_id).cloned())
        }
        fn existing_distilled(&self, namespace: &str) -> Result<(Vec<String>, Vec<String>)> {
            let d = self.store.distilled.borrow();
            let sigs = d.iter().filter(|(ns, _, _)| ns == namespace).map(|(_, _, c)| crate::json::sha256_hex(c.to_lowercase().as_bytes())).collect();
            let contents = d.iter().filter(|(ns, _, _)| ns == namespace).map(|(_, _, c)| c.clone()).collect();
            Ok((sigs, contents))
        }
        fn recent_episodes(&self, _limit: u32) -> Result<Vec<Episode>> {
            Ok(self.store.episodes.borrow().clone())
        }
        fn insert_receipt(&self, cycle_id: &str, payload_json: &str) -> Result<u64> {
            self.store.log("INSERT_RECEIPT");
            self.store.receipts.borrow_mut().push(format!("{cycle_id}:{payload_json}"));
            Ok(1)
        }
        fn housekeeping(&self, _days: u32) -> Result<(u64, u64)> {
            self.store.log("HOUSEKEEPING");
            Ok((0, 0))
        }
    }
}
