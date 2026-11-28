use ed25519_dalek::SigningKey;
use meridian_ledger::{
    BillingClass, BudgetLedger, LaneFitnessRecord, LaneStatus, LedgerError, RoutingState,
};
use std::collections::HashSet;
use std::sync::{Arc, Barrier, Mutex};
use std::thread;

fn record(lane: &str, class: BillingClass, p99: u32, expires: u64) -> LaneFitnessRecord {
    LaneFitnessRecord {
        schema: LaneFitnessRecord::SCHEMA_V1.to_string(),
        lane_id: lane.to_string(),
        provider: "p".to_string(),
        model: "m".to_string(),
        secret_env: "SEED_X_API_KEY".to_string(),
        billing_class: class,
        status: LaneStatus::Fit,
        checked_at_utc: 1_000,
        expires_at_utc: expires,
        p99_ms: p99,
        golden_pass: true,
        reason: "PRE_EDIT_RED->FIX_GREEN".to_string(),
        signer_pubkey_hex: String::new(),
        signature_hex: String::new(),
    }
}

fn ledger() -> BudgetLedger {
    BudgetLedger::new("GBP", BillingClass::ApiCredit, 1_000)
}

fn reserve(l: &mut BudgetLedger, id: &str, amt: i64, nonce: &str) -> Result<(), LedgerError> {
    l.reserve(id, "lane", BillingClass::ApiCredit, amt, "GBP", nonce, l.revocation_epoch, l.fencing_token)
        .map(|_| ())
}

#[test]
fn sixteen_threads_at_a_barrier_admit_exactly_five_of_two_hundred_against_a_thousand_ceiling() {
    let shared = Arc::new(Mutex::new(ledger()));
    let barrier = Arc::new(Barrier::new(16));
    let handles: Vec<_> = (0..16)
        .map(|i| {
            let shared = Arc::clone(&shared);
            let barrier = Arc::clone(&barrier);
            thread::spawn(move || {
                barrier.wait();
                let mut g = shared.lock().expect("ledger mutex poisoned");
                reserve(&mut g, &format!("res-{i}"), 200, &format!("nonce-race-{i:04}"))
            })
        })
        .collect();
    let results: Vec<_> = handles.into_iter().map(|h| h.join().expect("thread panicked")).collect();
    let admitted = results.iter().filter(|r| r.is_ok()).count();
    let rejected = results
        .iter()
        .filter(|r| matches!(r, Err(LedgerError::InsufficientEscrow { .. })))
        .count();
    assert_eq!(admitted, 5);
    assert_eq!(rejected, 11);
    let g = shared.lock().expect("ledger mutex poisoned");
    assert_eq!(g.total_reserved(), 1_000);
    assert_eq!(g.available_minor_units(), 0);
}

#[test]
fn a_reservation_id_cannot_be_reused_to_overwrite_a_live_escrow() {
    let mut l = ledger();
    assert!(reserve(&mut l, "dup", 600, "nonce-dup-0001").is_ok());
    let again = reserve(&mut l, "dup", 100, "nonce-dup-0002");
    assert_eq!(again, Err(LedgerError::DuplicateReservation { id: "dup".to_string() }));
    assert_eq!(l.total_reserved(), 600);
    assert_eq!(l.available_minor_units(), 400);
}

#[test]
fn a_committed_reservation_id_cannot_be_reserved_again() {
    let mut l = ledger();
    assert!(reserve(&mut l, "once", 300, "nonce-once-01").is_ok());
    assert!(l.commit("once", 300).is_ok());
    assert_eq!(
        reserve(&mut l, "once", 300, "nonce-once-02"),
        Err(LedgerError::DuplicateReservation { id: "once".to_string() })
    );
    assert_eq!(l.spent_minor_units, 300);
}

#[test]
fn currency_class_and_cost_guards_reject_without_touching_the_ledger() {
    let mut l = ledger();
    assert_eq!(
        l.reserve("a", "lane", BillingClass::ApiCredit, 10, "USD", "nonce-cur-01", 1, 1),
        Err(LedgerError::CurrencyMismatch { expected: "GBP".to_string(), got: "USD".to_string() })
    );
    assert_eq!(
        l.reserve("b", "lane", BillingClass::FreeAllowance, 10, "GBP", "nonce-cls-01", 1, 1),
        Err(LedgerError::CrossClassSubstitution {
            expected: BillingClass::ApiCredit,
            got: BillingClass::FreeAllowance
        })
    );
    assert_eq!(reserve(&mut l, "c", 0, "nonce-zero-01"), Err(LedgerError::InvalidCost { cost: 0 }));
    assert_eq!(reserve(&mut l, "d", -5, "nonce-neg-001"), Err(LedgerError::InvalidCost { cost: -5 }));
    assert_eq!(l.total_reserved(), 0);
    assert_eq!(l.spent_minor_units, 0);
}

#[test]
fn replayed_and_short_nonces_are_rejected_after_normalisation() {
    let mut l = ledger();
    assert!(reserve(&mut l, "n1", 10, "Nonce-Abc-001").is_ok());
    assert!(matches!(
        reserve(&mut l, "n2", 10, "  nonce-abc-001 "),
        Err(LedgerError::ReplayNonceDetected { .. })
    ));
    assert!(matches!(reserve(&mut l, "n3", 10, "short"), Err(LedgerError::ReplayNonceDetected { .. })));
    assert_eq!(l.total_reserved(), 10);
}

#[test]
fn bumping_the_epoch_fences_stale_reserves_and_stale_commits() {
    let mut l = ledger();
    assert!(reserve(&mut l, "pre", 100, "nonce-pre-0001").is_ok());
    let fence_before = l.fencing_token;
    assert_eq!(l.bump_revocation_epoch(), 2);
    assert!(l.fencing_token > fence_before);
    assert_eq!(
        l.reserve("post", "lane", BillingClass::ApiCredit, 10, "GBP", "nonce-post-001", 1, l.fencing_token),
        Err(LedgerError::StaleEpoch { got: 1, current: 2 })
    );
    assert_eq!(l.commit("pre", 50), Err(LedgerError::StaleEpoch { got: 1, current: 2 }));
    assert!(matches!(
        l.reserve("post2", "lane", BillingClass::ApiCredit, 10, "GBP", "nonce-post-002", 2, 0),
        Err(LedgerError::StaleFencingToken { .. })
    ));
}

#[test]
fn escrow_state_machine_allows_each_transition_once() {
    let mut l = ledger();
    assert!(reserve(&mut l, "s1", 400, "nonce-sm-0001").is_ok());
    assert_eq!(l.commit("s1", 401), Err(LedgerError::InvalidCost { cost: 401 }));
    assert!(l.commit("s1", 250).is_ok());
    assert!(matches!(l.commit("s1", 250), Err(LedgerError::InvalidStateTransition { .. })));
    assert!(matches!(l.release("s1"), Err(LedgerError::InvalidStateTransition { .. })));
    assert!(matches!(l.release("missing"), Err(LedgerError::UnknownReservation { .. })));
    assert_eq!(l.spent_minor_units, 250);
    assert_eq!(l.total_reserved(), 0);

    assert!(reserve(&mut l, "s2", 300, "nonce-sm-0002").is_ok());
    assert_eq!(l.release("s2"), Ok(300));
    assert!(matches!(l.commit("s2", 1), Err(LedgerError::InvalidStateTransition { .. })));
    assert_eq!(l.available_minor_units(), 750);
}

#[test]
fn forged_tampered_and_wrong_schema_fitness_records_are_refused() {
    let trusted = SigningKey::from_bytes(&[0x11; 32]);
    let forger = SigningKey::from_bytes(&[0x22; 32]);
    let mut rs = RoutingState::new(vec![hex::encode(trusted.verifying_key().to_bytes())]);

    let mut forged = record("forged", BillingClass::ApiCredit, 100, 9_999);
    forged.sign(&forger);
    assert_eq!(rs.upsert_signed(forged), Err(LedgerError::UntrustedFitnessSigner));

    let mut tampered = record("tampered", BillingClass::ApiCredit, 900, 9_999);
    tampered.sign(&trusted);
    tampered.p99_ms = 1;
    assert_eq!(rs.upsert_signed(tampered), Err(LedgerError::InvalidFitnessSignature));

    let mut wrong_schema = record("schema", BillingClass::ApiCredit, 100, 9_999);
    wrong_schema.schema = "estate.lane-fitness.v0".to_string();
    wrong_schema.sign(&trusted);
    assert_eq!(rs.upsert_signed(wrong_schema), Err(LedgerError::InvalidFitnessSignature));

    assert!(rs.all_records().is_empty());
}

#[test]
fn selection_is_class_strict_lowest_p99_and_ignores_expired_drained_and_excluded_lanes() {
    let sk = SigningKey::from_bytes(&[0x33; 32]);
    let mut rs = RoutingState::new(vec![hex::encode(sk.verifying_key().to_bytes())]);
    for (lane, class, p99, exp) in [
        ("sub-fastest", BillingClass::MonthlySubscription, 100, 9_999),
        ("api-fast-expired", BillingClass::ApiCredit, 150, 1_050),
        ("api-fast-drained", BillingClass::ApiCredit, 200, 9_999),
        ("api-mid", BillingClass::ApiCredit, 400, 9_999),
        ("api-slow", BillingClass::ApiCredit, 800, 9_999),
    ] {
        let mut r = record(lane, class, p99, exp);
        r.sign(&sk);
        assert!(rs.upsert_signed(r).is_ok());
    }
    rs.drain_lane("api-fast-drained", "429");

    let none: HashSet<String> = HashSet::new();
    let pick = |rs: &RoutingState, ex: &HashSet<String>| {
        rs.select_best_fit(BillingClass::ApiCredit, 1_100, ex).map(|r| r.lane_id.clone())
    };
    assert_eq!(pick(&rs, &none), Some("api-mid".to_string()));
    let ex: HashSet<String> = ["api-mid".to_string()].into_iter().collect();
    assert_eq!(pick(&rs, &ex), Some("api-slow".to_string()));
    let ex: HashSet<String> = ["api-mid".to_string(), "api-slow".to_string()].into_iter().collect();
    assert_eq!(pick(&rs, &ex), None);
}
