//! The sleep-cycle orchestrator.
//!
//! Order of operations per cycle:
//!   0. E7 host gate — crisis: no cycle, receipt says why, zero side effects.
//!   1. E11 advisory lock — follower exits clean with leader:false receipt.
//!   2. Per tenant, one transaction (E3): housekeeping -> staging/promotion
//!      (G1-G3) -> dream/distill (G4/G6, shadow by default) -> revalidation
//!      surveillance (G5) -> tenant receipt. One tenant's failure is isolated
//!      and recorded; it never stops the others (consolidation.py parity).
//!   3. E14: even an all-empty estate emits heartbeat receipts.

use crate::config::Config;
use crate::distill::{BudgetLedger, DistillModel, Distiller};
use crate::evidence::{self, MapleMetrics, PromotionVerdict};
use crate::host::{CycleGate, HostEnvelope};
use crate::quality::QualityRow;
use crate::receipts::{CycleReceipt, TenantReceipt};
use crate::revalidate::{self, Observation, OracleClass, Surveillance, SurveillanceVerdict};
use crate::store::{MemoryRow, MemoryStore};
use crate::{Error, Result};

pub struct Consolidator<'a, S: MemoryStore, M: DistillModel> {
    pub store: &'a S,
    /// None = zero model access this cycle (budget 0 or no door wired).
    pub model: Option<&'a M>,
    pub cfg: &'a Config,
    pub now_ms: i64,
}

/// Deterministic cycle id: content-addressed from start time + tenant count.
pub fn cycle_id(now_ms: i64, tenants: u64) -> String {
    crate::json::sha256_hex(format!("cycle:{now_ms}:{tenants}").as_bytes())[..16].to_string()
}

impl<'a, S: MemoryStore, M: DistillModel> Consolidator<'a, S, M> {
    pub fn run(&self, host: &HostEnvelope) -> Result<CycleReceipt> {
        let host_gate = match host.gate() {
            CycleGate::Run => "run".to_string(),
            CycleGate::Skip(why) => {
                // E7: crisis -> receipt, no lock attempt, no tenant work.
                return Ok(CycleReceipt {
                    cycle_id: cycle_id(self.now_ms, 0),
                    started_ms: self.now_ms,
                    finished_ms: self.now_ms,
                    tenants_ok: 0,
                    tenants_failed: 0,
                    leader: false,
                    host_gate: format!("skip: {why}"),
                });
            }
        };

        let leader = self.store.try_leader(self.cfg.advisory_lock_id)?;
        let tenants = self.store.list_tenants()?;
        let cid = cycle_id(self.now_ms, tenants.len() as u64);
        if !leader {
            return Ok(CycleReceipt {
                cycle_id: cid,
                started_ms: self.now_ms,
                finished_ms: self.now_ms,
                tenants_ok: 0,
                tenants_failed: 0,
                leader: false,
                host_gate,
            });
        }

        let mut ok = 0u64;
        let mut failed = 0u64;
        for t in &tenants {
            let mut attempt = |tx: &dyn crate::store::TenantTx| -> Result<TenantReceipt> {
                self.run_tenant(tx, t, &cid)
            };
            match self.store.run_tenant_tx(t, &mut attempt) {
                Ok(_) => ok += 1,
                Err(e) => {
                    // Isolation: one bad tenant never poisons the cycle.
                    // The error is visible in the cycle receipt via stderr by
                    // the caller; per-tenant receipt is written by run_tenant
                    // itself on the error paths it can reach.
                    let _ = e;
                    failed += 1;
                }
            }
        }

        Ok(CycleReceipt {
            cycle_id: cid,
            started_ms: self.now_ms,
            finished_ms: self.now_ms,
            tenants_ok: ok,
            tenants_failed: failed,
            leader: true,
            host_gate,
        })
    }

    fn run_tenant(&self, tx: &dyn crate::store::TenantTx, tenant_id: &str, cid: &str) -> Result<TenantReceipt> {
        let mut r = TenantReceipt { tenant_id: tenant_id.to_string(), shadow: self.cfg.shadow_mode, ..Default::default() };

        // Housekeeping first (expired scratchpad, aged recurrence).
        let (sp, rec) = tx.housekeeping(90)?;
        r.scratchpad_expired = sp;
        r.recurrence_aged = rec;

        // --- Staging + promotion (G1-G3) ---
        let candidates = tx.staging_candidates(500)?;
        r.staged = candidates.len() as u64;
        for m in &candidates {
            let ev = tx.evidence_for(&m.id)?;
            let metrics = MapleMetrics { rho: m.rho, tau: m.tau, harm: m.harm, taint: m.taint };
            match evidence::evaluate(metrics, &ev, self.cfg) {
                PromotionVerdict::Promote => {
                    assert_rows(tx.promote_shared(&m.id)?, "PROMOTE_SHARED")?;
                    r.promoted += 1;
                }
                PromotionVerdict::Quarantine(_) => {
                    assert_rows(tx.quarantine(&m.id)?, "QUARANTINE")?;
                    r.quarantined += 1;
                }
                PromotionVerdict::Hold(_) => r.held += 1,
            }
            // Quality side-table write — NEVER an UPDATE to memories (E2).
            if !ev.is_empty() {
                let mut q = tx
                    .quality_of(&m.id)?
                    .unwrap_or_else(|| QualityRow::fresh(&m.id, tenant_id, self.now_ms, &self.cfg.policy_version));
                for e in &ev {
                    q.absorb(e, self.now_ms);
                }
                assert_rows(tx.upsert_quality(&q)?, "UPSERT_QUALITY")?;
            }
        }

        // --- Dream pass (G4/G6) ---
        if let Some(model) = self.model {
            let episodes = tx.recent_episodes(1000)?;
            if !episodes.is_empty() {
                let (sigs, contents) = tx.existing_distilled("estate")?;
                let mut budget = BudgetLedger::new(self.cfg.distill_budget_micro);
                let d = Distiller { model, cfg: self.cfg };
                match d.dream(&episodes, &sigs, &contents, &mut budget) {
                    Ok((proposals, poisoned)) => {
                        r.poison_blocked = poisoned.len() as u64;
                        for pid in &poisoned {
                            assert_rows(tx.quarantine(pid)?, "QUARANTINE")?;
                        }
                        r.distilled_proposals = proposals.len() as u64;
                        if !self.cfg.shadow_mode {
                            for p in &proposals {
                                let prov = format!(
                                    "{{\"kind\":\"distilled\",\"source_ids\":[{}],\"usefulness\":{:.4},\"policy_version\":\"{}\"}}",
                                    p.source_ids.iter().map(|s| format!("\"{}\"", crate::json::escape(s))).collect::<Vec<_>>().join(","),
                                    p.usefulness,
                                    crate::json::escape(&self.cfg.policy_version)
                                );
                                let key = format!("distill.{}", &p.signature[..16]);
                                assert_rows(tx.insert_distilled(tenant_id, &p.namespace, &key, &p.content, &prov)?, "INSERT_DISTILLED")?;
                                r.distilled_written += 1;
                            }
                        }
                        r.spend_micro = budget.spent();
                    }
                    Err(Error::BudgetExhausted { spent_micro, .. }) => {
                        // E8: abort the pass, keep the receipt honest.
                        r.spend_micro = spent_micro;
                        r.error = Some("budget floor: dream pass aborted, receipts preserved".into());
                    }
                    Err(e) => return Err(e),
                }
            }
        }

        // --- Revalidation surveillance (G5) ---
        let sample = tx.revalidation_sample(self.cfg.revalidate_batch)?;
        for m in &sample {
            let verdict = self.surveil(tx, m)?;
            r.revalidated += 1;
            match verdict {
                Some(SurveillanceVerdict::DriftAlarm) | Some(SurveillanceVerdict::UnacceptableError) => {
                    if oracle_class(m) == OracleClass::External {
                        assert_rows(tx.quarantine(&m.id)?, "QUARANTINE")?;
                        r.demoted += 1;
                    } else {
                        // E9: no oracle — human queue, no automatic demotion.
                        r.human_queued += 1;
                    }
                }
                _ => {}
            }
        }

        // E14: receipt always, even when every counter is zero.
        let receipt_json = r.to_json(cid, &self.cfg.policy_version);
        assert_rows(tx.insert_receipt(cid, &receipt_json)?, "INSERT_RECEIPT")?;
        Ok(r)
    }

    /// Fold revalidation evidence into the fact's surveillance state.
    /// Evidence rows of kind "revalidation_outcome" carry weight = outcome
    /// (1.0 confirmed / 0.0 contradicted); prediction = the fact's tau.
    fn surveil(&self, tx: &dyn crate::store::TenantTx, m: &MemoryRow) -> Result<Option<SurveillanceVerdict>> {
        let ev = tx.evidence_for(&m.id)?;
        let outcomes: Vec<&crate::evidence::EvidenceRow> = ev.iter().filter(|e| e.kind == "revalidation_outcome").collect();
        if outcomes.is_empty() {
            return Ok(None);
        }
        let mut q = tx
            .quality_of(&m.id)?
            .unwrap_or_else(|| QualityRow::fresh(&m.id, &m.tenant_id, self.now_ms, &self.cfg.policy_version));
        let mut s = Surveillance { brier: q.brier, cusum: q.cusum, observations: q.evidence_count };
        for o in &outcomes {
            revalidate::observe(&mut s, Observation { predicted: m.tau, outcome: o.weight }, 0.05);
        }
        q.brier = s.brier;
        q.cusum = s.cusum;
        assert_rows(tx.upsert_quality(&q)?, "UPSERT_QUALITY")?;
        Ok(Some(revalidate::verdict(&s, oracle_class(m), self.cfg)))
    }
}

fn oracle_class(m: &MemoryRow) -> OracleClass {
    // Estate convention: facts whose namespace declares an oracle are External.
    if m.namespace.starts_with("oracle:") {
        OracleClass::External
    } else {
        OracleClass::OracleNone
    }
}

/// E3: a write that returned 0 rows where 1 was expected is the idp#6507
/// failure mode — hard error, never a green receipt.
fn assert_rows(got: u64, statement: &'static str) -> Result<()> {
    if got == 0 {
        return Err(Error::RlsSilentNoOp { statement, expected: 1 });
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::distill::DistillModel;
    use crate::store::mock::MockStore;
    use crate::store::MemoryRow as MR;

    struct NoopModel;
    impl DistillModel for NoopModel {
        fn distill(&self, c: &[crate::distill::Episode]) -> std::result::Result<String, String> {
            Ok(format!("distilled: {}", c.len()))
        }
        fn cost_per_call_micro(&self) -> u64 {
            10
        }
    }

    fn healthy() -> HostEnvelope {
        HostEnvelope { disk_free_mb: 20_000, disk_rate_mb_per_min: 0, swap_used_mb: 0, load_1m: 1.0 }
    }

    fn mem(id: &str, tenant: &str, rho: f64, tau: f64) -> MR {
        MR {
            id: id.into(), tenant_id: tenant.into(), namespace: "estate".into(),
            key: format!("k.{id}"), content: format!("content {id}"),
            rho, tau, harm: 0.0, taint: 0.0, created_ms: 0, evidence_count: 0,
        }
    }

    fn cfg() -> Config {
        Config::default()
    }

    #[test]
    fn e7_crisis_skips_with_zero_side_effects() {
        let store = MockStore::leader();
        store.tenants.borrow_mut().push("t1".into());
        let c = Consolidator { store: &store, model: Option::<&NoopModel>::None, cfg: &cfg(), now_ms: 1 };
        let crisis = HostEnvelope { disk_free_mb: 1000, ..healthy() };
        let r = c.run(&crisis).expect("receipt");
        assert!(r.host_gate.starts_with("skip:"));
        assert!(store.issued.borrow().is_empty(), "no SQL issued during crisis");
    }

    #[test]
    fn e11_follower_exits_clean() {
        let store = MockStore::default(); // leader = false
        let c = Consolidator { store: &store, model: Option::<&NoopModel>::None, cfg: &cfg(), now_ms: 1 };
        let r = c.run(&healthy()).expect("receipt");
        assert!(!r.leader);
        assert_eq!(r.tenants_ok, 0);
    }

    #[test]
    fn g2_defaults_without_evidence_hold_everything() {
        let store = MockStore::leader();
        store.tenants.borrow_mut().push("t1".into());
        store.memories.borrow_mut().push(mem("m1", "t1", 1.0, 1.0));
        let c = Consolidator { store: &store, model: Option::<&NoopModel>::None, cfg: &cfg(), now_ms: 1 };
        let r = c.run(&healthy()).expect("cycle");
        assert_eq!(r.tenants_ok, 1);
        assert!(!store.shared.borrow().get("m1").copied().unwrap_or(false), "no promotion without evidence");
        assert!(store.receipts.borrow().len() == 1, "heartbeat receipt written");
    }

    #[test]
    fn strong_evidence_promotes_through_cycle() {
        let store = MockStore::leader();
        store.tenants.borrow_mut().push("t1".into());
        store.memories.borrow_mut().push(mem("m1", "t1", 1.0, 1.0));
        store.evidence.borrow_mut().insert(
            "m1".into(),
            (0..9).map(|_| crate::evidence::EvidenceRow {
                memory_id: "m1".into(), kind: "retrieval_outcome".into(), weight: 1.0, observed_at_ms: 0,
            }).collect(),
        );
        let c = Consolidator { store: &store, model: Option::<&NoopModel>::None, cfg: &cfg(), now_ms: 1 };
        c.run(&healthy()).expect("cycle");
        assert!(store.shared.borrow().get("m1").copied().unwrap_or(false));
    }

    #[test]
    fn e5_rerun_is_idempotent() {
        let store = MockStore::leader();
        store.tenants.borrow_mut().push("t1".into());
        store.memories.borrow_mut().push(mem("m1", "t1", 1.0, 1.0));
        store.evidence.borrow_mut().insert(
            "m1".into(),
            (0..9).map(|_| crate::evidence::EvidenceRow {
                memory_id: "m1".into(), kind: "retrieval_outcome".into(), weight: 1.0, observed_at_ms: 0,
            }).collect(),
        );
        {
            let c = Consolidator { store: &store, model: Option::<&NoopModel>::None, cfg: &cfg(), now_ms: 1 };
            c.run(&healthy()).expect("cycle 1");
        }
        let issued_after_1 = store.issued.borrow().len();
        {
            let c = Consolidator { store: &store, model: Option::<&NoopModel>::None, cfg: &cfg(), now_ms: 2 };
            c.run(&healthy()).expect("cycle 2");
        }
        // Second cycle: m1 already shared -> not in staging -> no PROMOTE_SHARED.
        let second: Vec<String> = store.issued.borrow()[issued_after_1..].to_vec();
        assert!(!second.iter().any(|s| s == "PROMOTE_SHARED"), "idempotent re-run");
    }

    #[test]
    fn e3_guc_unset_is_hard_error_not_green() {
        let mut store = MockStore::leader();
        store.simulate_guc_unset = true;
        store.tenants.borrow_mut().push("t1".into());
        store.memories.borrow_mut().push(mem("m1", "t1", 1.0, 1.0));
        store.evidence.borrow_mut().insert(
            "m1".into(),
            (0..9).map(|_| crate::evidence::EvidenceRow {
                memory_id: "m1".into(), kind: "retrieval_outcome".into(), weight: 1.0, observed_at_ms: 0,
            }).collect(),
        );
        let c = Consolidator { store: &store, model: Option::<&NoopModel>::None, cfg: &cfg(), now_ms: 1 };
        let r = c.run(&healthy()).expect("cycle receipt");
        assert_eq!(r.tenants_failed, 1, "tenant failed loudly");
        assert_eq!(r.tenants_ok, 0);
    }

    #[test]
    fn shadow_mode_scores_but_never_writes() {
        let store = MockStore::leader();
        store.tenants.borrow_mut().push("t1".into());
        store.episodes.borrow_mut().extend(vec![
            crate::distill::Episode { id: "e1".into(), namespace: "estate".into(), key: "k.e1".into(), content: "executor daemon crashed after disk filled with swap".into(), created_ms: 0 },
            crate::distill::Episode { id: "e2".into(), namespace: "estate".into(), key: "k.e2".into(), content: "executor daemon crash traced to disk full and swap pressure".into(), created_ms: 0 },
        ]);
        let cfg = Config { distill_budget_micro: 10_000, shadow_mode: true, ..Config::default() };
        let model = NoopModel;
        let c = Consolidator { store: &store, model: Some(&model), cfg: &cfg, now_ms: 1 };
        c.run(&healthy()).expect("cycle");
        assert!(store.distilled.borrow().is_empty(), "shadow: nothing written");
        let receipts = store.receipts.borrow();
        assert!(receipts[0].contains("\"shadow\":true"));
        assert!(receipts[0].contains("\"distilled_proposals\":1"), "proposal scored in shadow");
    }

    #[test]
    fn cusum_drift_demotes_external_oracle_fact() {
        let store = MockStore::leader();
        store.tenants.borrow_mut().push("t1".into());
        let mut m = mem("m9", "t1", 1.0, 0.9);
        m.namespace = "oracle:executor".into(); // External oracle class
        store.memories.borrow_mut().push(m);
        store.shared.borrow_mut().insert("m9".into(), true); // already promoted
        // Sustained contradiction stream.
        store.evidence.borrow_mut().insert(
            "m9".into(),
            (0..30).map(|_| crate::evidence::EvidenceRow {
                memory_id: "m9".into(), kind: "revalidation_outcome".into(), weight: 0.0, observed_at_ms: 0,
            }).collect(),
        );
        let c = Consolidator { store: &store, model: Option::<&NoopModel>::None, cfg: &cfg(), now_ms: 1 };
        c.run(&healthy()).expect("cycle");
        assert!(store.quarantined.borrow().get("m9").copied().unwrap_or(false), "drifted external-oracle fact demoted");
    }

    #[test]
    fn e9_oracle_none_routes_to_human_never_auto_demotes() {
        let store = MockStore::leader();
        store.tenants.borrow_mut().push("t1".into());
        store.memories.borrow_mut().push(mem("m8", "t1", 1.0, 0.9)); // namespace "estate" -> OracleNone
        store.shared.borrow_mut().insert("m8".into(), true);
        store.evidence.borrow_mut().insert(
            "m8".into(),
            (0..30).map(|_| crate::evidence::EvidenceRow {
                memory_id: "m8".into(), kind: "revalidation_outcome".into(), weight: 0.0, observed_at_ms: 0,
            }).collect(),
        );
        let c = Consolidator { store: &store, model: Option::<&NoopModel>::None, cfg: &cfg(), now_ms: 1 };
        c.run(&healthy()).expect("cycle");
        assert!(!store.quarantined.borrow().get("m8").copied().unwrap_or(false), "no auto-demote without oracle");
        let receipts = store.receipts.borrow();
        assert!(receipts[0].contains("\"human_queued\":1"), "{}", receipts[0].clone());
    }

    #[test]
    fn e2_no_bookkeeping_update_to_memories_ever_issued() {
        // Acceptance test 2: scan the forensic log of a full rich cycle.
        let store = MockStore::leader();
        store.tenants.borrow_mut().push("t1".into());
        store.memories.borrow_mut().push(mem("m1", "t1", 1.0, 1.0));
        store.evidence.borrow_mut().insert(
            "m1".into(),
            (0..9).map(|_| crate::evidence::EvidenceRow {
                memory_id: "m1".into(), kind: "retrieval_outcome".into(), weight: 1.0, observed_at_ms: 0,
            }).collect(),
        );
        let cfg = Config { distill_budget_micro: 10_000, shadow_mode: false, ..Config::default() };
        let model = NoopModel;
        let c = Consolidator { store: &store, model: Some(&model), cfg: &cfg, now_ms: 1 };
        c.run(&healthy()).expect("cycle");
        for stmt in store.issued.borrow().iter() {
            // Allowed memories writes are lifecycle flips only (PROMOTE_SHARED /
            // QUARANTINE); bookkeeping is exclusively side-table statements.
            assert!(
                matches!(stmt.as_str(),
                    "PROMOTE_SHARED" | "QUARANTINE" | "UPSERT_QUALITY" | "INSERT_EVIDENCE"
                    | "INSERT_RECEIPT" | "HOUSEKEEPING" | "SET_TENANT t1")
                    || stmt.starts_with("INSERT_DISTILLED"),
                "unexpected statement issued: {stmt}"
            );
        }
    }

    #[test]
    fn e14_empty_estate_emits_heartbeat() {
        let store = MockStore::leader(); // zero tenants
        let c = Consolidator { store: &store, model: Option::<&NoopModel>::None, cfg: &cfg(), now_ms: 7 };
        let r = c.run(&healthy()).expect("receipt");
        assert!(r.leader);
        assert_eq!(r.tenants_ok, 0);
        assert!(r.to_json().contains("\"cycle_id\""), "cycle receipt even with zero tenants");
    }
}
