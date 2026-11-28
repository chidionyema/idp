use ed25519_dalek::SigningKey;
use meridian_ledger::{BillingClass, BudgetLedger, LaneFitnessRecord, LaneStatus, LedgerError, RoutingState};
use meridian_legion::{
    dispatch_with_failover, DispatchError, LaneExecutor, MissionRequest, WorkerExecResult,
};
use std::collections::HashMap;

fn routing(lanes: &[(&str, BillingClass, u32)]) -> RoutingState {
    let sk = SigningKey::from_bytes(&[0x44; 32]);
    let mut rs = RoutingState::new(vec![hex::encode(sk.verifying_key().to_bytes())]);
    for (lane, class, p99) in lanes {
        let mut r = LaneFitnessRecord {
            schema: LaneFitnessRecord::SCHEMA_V1.to_string(),
            lane_id: (*lane).to_string(),
            provider: "p".to_string(),
            model: format!("model-{lane}"),
            secret_env: "SEED_X_API_KEY".to_string(),
            billing_class: *class,
            status: LaneStatus::Fit,
            checked_at_utc: 1_000,
            expires_at_utc: 9_999,
            p99_ms: *p99,
            golden_pass: true,
            reason: "PRE_EDIT_RED->FIX_GREEN".to_string(),
            signer_pubkey_hex: String::new(),
            signature_hex: String::new(),
        };
        r.sign(&sk);
        assert!(rs.upsert_signed(r).is_ok());
    }
    rs
}

fn request(max: i64) -> MissionRequest {
    MissionRequest {
        instruction_id: "INS-1".to_string(),
        billing_class: BillingClass::ApiCredit,
        max_cost_minor_units: max,
        currency: "GBP".to_string(),
        nonce_prefix: "nonce-legion".to_string(),
    }
}

/// Scripted executor: per-lane outcome, records every lane it was asked to run.
struct Script {
    outcomes: HashMap<String, WorkerExecResult>,
    calls: Vec<String>,
}

impl Script {
    fn new(outcomes: &[(&str, WorkerExecResult)]) -> Self {
        Self {
            outcomes: outcomes.iter().map(|(k, v)| ((*k).to_string(), v.clone())).collect(),
            calls: Vec::new(),
        }
    }
}

impl LaneExecutor for Script {
    fn execute(&mut self, lane_id: &str, _model: &str, _req: &MissionRequest) -> WorkerExecResult {
        self.calls.push(lane_id.to_string());
        self.outcomes.get(lane_id).cloned().unwrap_or(WorkerExecResult::Fault {
            reason: "UNSCRIPTED".to_string(),
            drain_lane: false,
        })
    }
}

fn ok(cost: i64) -> WorkerExecResult {
    WorkerExecResult::Success { patch_sha: "sha256:abc".to_string(), actual_cost_minor_units: cost }
}

fn fault(reason: &str, drain: bool) -> WorkerExecResult {
    WorkerExecResult::Fault { reason: reason.to_string(), drain_lane: drain }
}

#[test]
fn fastest_lane_in_class_wins_and_only_actual_cost_is_spent() {
    let mut rs = routing(&[
        ("deepseek", BillingClass::ApiCredit, 380),
        ("minimax", BillingClass::ApiCredit, 520),
    ]);
    let mut l = BudgetLedger::new("GBP", BillingClass::ApiCredit, 1_000);
    let mut ex = Script::new(&[("deepseek", ok(120))]);
    let r = dispatch_with_failover(&request(300), 1_100, &mut l, &mut rs, &mut ex).expect("dispatch");
    assert_eq!(r.winning_lane_id, "deepseek");
    assert_eq!(r.winning_model, "model-deepseek");
    assert!(r.failed_over_from.is_empty());
    assert_eq!(r.committed_minor_units, 120);
    assert_eq!(l.spent_minor_units, 120);
    assert_eq!(l.total_reserved(), 0);
    assert_eq!(ex.calls, vec!["deepseek".to_string()]);
}

#[test]
fn a_429_drains_the_lane_and_fails_over_inside_the_class_never_to_a_faster_other_class() {
    let mut rs = routing(&[
        ("claude-sub", BillingClass::MonthlySubscription, 310),
        ("deepseek", BillingClass::ApiCredit, 380),
        ("minimax", BillingClass::ApiCredit, 520),
    ]);
    let mut l = BudgetLedger::new("GBP", BillingClass::ApiCredit, 1_000);
    let mut ex = Script::new(&[("deepseek", fault("HTTP_429", true)), ("minimax", ok(120))]);
    let r = dispatch_with_failover(&request(300), 1_100, &mut l, &mut rs, &mut ex).expect("dispatch");
    assert_eq!(r.winning_lane_id, "minimax");
    assert_eq!(r.failed_over_from, vec!["deepseek".to_string()]);
    assert_eq!(ex.calls, vec!["deepseek".to_string(), "minimax".to_string()]);
    assert!(!ex.calls.contains(&"claude-sub".to_string()));
    assert_eq!(l.spent_minor_units, 120);
    assert_eq!(l.total_reserved(), 0);
    // The drained lane is no longer selectable on the next dispatch.
    let drained = rs.all_records().into_iter().find(|x| x.lane_id == "deepseek").expect("record");
    assert_eq!(drained.status, LaneStatus::Drained);
    assert!(!drained.golden_pass);
}

#[test]
fn every_lane_failing_returns_no_fit_lane_with_all_escrow_released() {
    let mut rs = routing(&[
        ("a", BillingClass::ApiCredit, 100),
        ("b", BillingClass::ApiCredit, 200),
        ("sub", BillingClass::MonthlySubscription, 50),
    ]);
    let mut l = BudgetLedger::new("GBP", BillingClass::ApiCredit, 1_000);
    let mut ex = Script::new(&[("a", fault("HTTP_500", false)), ("b", fault("HTTP_500", false))]);
    let err = dispatch_with_failover(&request(300), 1_100, &mut l, &mut rs, &mut ex).expect_err("must fail");
    assert_eq!(
        err,
        DispatchError::NoFitLane {
            billing_class: BillingClass::ApiCredit,
            tried: vec!["a".to_string(), "b".to_string()]
        }
    );
    assert_eq!(l.spent_minor_units, 0);
    assert_eq!(l.total_reserved(), 0);
    assert_eq!(l.available_minor_units(), 1_000);
    assert!(!ex.calls.contains(&"sub".to_string()));
}

#[test]
fn a_non_draining_fault_still_excludes_the_lane_for_this_dispatch_only() {
    let mut rs = routing(&[("a", BillingClass::ApiCredit, 100), ("b", BillingClass::ApiCredit, 200)]);
    let mut l = BudgetLedger::new("GBP", BillingClass::ApiCredit, 1_000);
    let mut ex = Script::new(&[("a", fault("TIMEOUT", false)), ("b", ok(10))]);
    let r = dispatch_with_failover(&request(300), 1_100, &mut l, &mut rs, &mut ex).expect("dispatch");
    assert_eq!(r.winning_lane_id, "b");
    let a = rs.all_records().into_iter().find(|x| x.lane_id == "a").expect("record");
    assert_eq!(a.status, LaneStatus::Fit);
}

#[test]
fn insufficient_escrow_stops_before_any_inference_runs() {
    let mut rs = routing(&[("a", BillingClass::ApiCredit, 100)]);
    let mut l = BudgetLedger::new("GBP", BillingClass::ApiCredit, 200);
    let mut ex = Script::new(&[("a", ok(10))]);
    let err = dispatch_with_failover(&request(300), 1_100, &mut l, &mut rs, &mut ex).expect_err("must fail");
    assert_eq!(
        err,
        DispatchError::Ledger(LedgerError::InsufficientEscrow { requested: 300, available: 200 })
    );
    assert!(ex.calls.is_empty());
    assert_eq!(l.spent_minor_units, 0);
}

#[test]
fn a_mission_in_a_class_the_ledger_forbids_is_refused_before_inference() {
    let mut rs = routing(&[("sub", BillingClass::MonthlySubscription, 50)]);
    let mut l = BudgetLedger::new("GBP", BillingClass::ApiCredit, 1_000);
    let mut req = request(100);
    req.billing_class = BillingClass::MonthlySubscription;
    let mut ex = Script::new(&[("sub", ok(10))]);
    let err = dispatch_with_failover(&req, 1_100, &mut l, &mut rs, &mut ex).expect_err("must fail");
    assert!(matches!(err, DispatchError::Ledger(LedgerError::CrossClassSubstitution { .. })));
    assert!(ex.calls.is_empty());
}

#[test]
fn an_expired_lease_is_never_dispatched() {
    let mut rs = routing(&[("a", BillingClass::ApiCredit, 100)]);
    let mut l = BudgetLedger::new("GBP", BillingClass::ApiCredit, 1_000);
    let mut ex = Script::new(&[("a", ok(10))]);
    let err = dispatch_with_failover(&request(100), 10_000, &mut l, &mut rs, &mut ex).expect_err("must fail");
    assert!(matches!(err, DispatchError::NoFitLane { .. }));
    assert!(ex.calls.is_empty());
}
