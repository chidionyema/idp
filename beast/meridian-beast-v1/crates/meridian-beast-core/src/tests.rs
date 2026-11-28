//! Falsifiers for the Beast kernel: each test feeds known-bad input a gate must reject
//! and known-good input it must accept.

use super::*;
use ed25519_dalek::SigningKey;
use std::collections::HashSet;

fn sk(byte: u8) -> SigningKey {
    SigningKey::from_bytes(&[byte; 32])
}

fn pk_hex(k: &SigningKey) -> String {
    hex::encode(k.verifying_key().to_bytes())
}

fn mark(k: &SigningKey, id: &str, domain: &str, max_cost: i64) -> SovereignMark {
    let mut m = SovereignMark {
        mark_id: id.to_string(),
        domain_id: domain.to_string(),
        actor_urn: "urn:aid:legion-worker-1".to_string(),
        process_class: ProcessClass::NonDeterministicWorker,
        billing_class: BillingClass::ApiCredit,
        footprint_hash: "sha256:fp-001".to_string(),
        max_cost_minor_units: max_cost,
        currency: "GBP".to_string(),
        revocation_epoch: 1,
        lease_epoch: 1,
        expires_utc: 2_000,
        reads_ring3: false,
        egresses_external: false,
        issuer_pubkey_hex: String::new(),
        signature_hex: String::new(),
    };
    m.sign(k);
    m
}

fn trusted(k: &SigningKey) -> HashSet<String> {
    let mut s = HashSet::new();
    s.insert(pk_hex(k));
    s
}

fn domain(id: &str, budget: i64) -> DomainBulkhead {
    DomainBulkhead::new(
        id,
        "GBP",
        BillingClass::ApiCredit,
        budget,
        vec![LaneSlot {
            lane_id: "deepseek-api".to_string(),
            billing_class: BillingClass::ApiCredit,
            fit: true,
            p99_ms: 350,
        }],
    )
}

fn request(m: Option<SovereignMark>, id: &str, cost: i64) -> BeastSignal {
    BeastSignal::RequestExecution {
        mark: m,
        instruction_id: id.to_string(),
        requested_lane: None,
        requested_cost_minor_units: cost,
        probe_url: None,
        touched_paths: vec![],
        worker_text: String::new(),
    }
}

fn deny_of(r: BeastReflex) -> Option<BeastDeny> {
    match r {
        BeastReflex::RejectedFailClosed { deny, .. } => Some(deny),
        _ => None,
    }
}

#[test]
fn good_mark_verifies() {
    let k = sk(1);
    assert!(mark(&k, "m1", "d", 100).verify_strict(&trusted(&k)).is_ok());
}

#[test]
fn untrusted_issuer_is_rejected() {
    let good = sk(1);
    let rogue = sk(2);
    let m = mark(&rogue, "m1", "d", 100);
    assert_eq!(m.verify_strict(&trusted(&good)), Err(BeastDeny::UnmarkedOrUntrustedActor));
}

#[test]
fn field_mutated_after_signing_is_rejected() {
    let k = sk(1);
    let mut m = mark(&k, "m1", "d", 100);
    m.max_cost_minor_units = 1_000_000;
    assert_eq!(m.verify_strict(&trusted(&k)), Err(BeastDeny::InvalidMarkSignature));
}

#[test]
fn flipped_signature_bit_is_rejected() {
    let k = sk(1);
    let mut m = mark(&k, "m1", "d", 100);
    let mut raw = hex::decode(&m.signature_hex).expect("hex");
    raw[0] ^= 0x01;
    m.signature_hex = hex::encode(raw);
    assert_eq!(m.verify_strict(&trusted(&k)), Err(BeastDeny::InvalidMarkSignature));
}

#[test]
fn garbage_signature_hex_is_rejected_not_panicking() {
    let k = sk(1);
    let mut m = mark(&k, "m1", "d", 100);
    m.signature_hex = "zz".to_string();
    assert_eq!(m.verify_strict(&trusted(&k)), Err(BeastDeny::InvalidMarkSignature));
}

#[test]
fn unmarked_request_fails_closed() {
    let k = sk(1);
    let mut e = BeastEngine::new(vec![pk_hex(&k)], vec![domain("d", 10_000)]);
    let r = e.process_signal(1_000, request(None, "I0", 100));
    assert_eq!(deny_of(r), Some(BeastDeny::UnmarkedOrUntrustedActor));
}

#[test]
fn forged_mark_fails_closed_and_spends_nothing() {
    let k = sk(1);
    let rogue = sk(9);
    let mut e = BeastEngine::new(vec![pk_hex(&k)], vec![domain("d", 10_000)]);
    let r = e.process_signal(1_000, request(Some(mark(&rogue, "m1", "d", 500)), "I1", 100));
    assert!(deny_of(r).is_some(), "forged mark must be denied");
    let d = e.domains.get("d").expect("domain");
    assert_eq!(d.total_reserved(), 0);
    assert_eq!(d.available_minor_units(), 10_000);
}

#[test]
fn expired_mark_is_denied() {
    let k = sk(1);
    let mut e = BeastEngine::new(vec![pk_hex(&k)], vec![domain("d", 10_000)]);
    let r = e.process_signal(5_000, request(Some(mark(&k, "m1", "d", 500)), "I1", 100));
    assert!(matches!(deny_of(r), Some(BeastDeny::MarkExpired { .. })));
}

#[test]
fn good_request_proceeds_then_replay_is_denied() {
    let k = sk(1);
    let mut e = BeastEngine::new(vec![pk_hex(&k)], vec![domain("d", 10_000)]);
    let m = mark(&k, "m1", "d", 500);
    let first = e.process_signal(1_000, request(Some(m.clone()), "I1", 100));
    assert!(matches!(first, BeastReflex::Proceed { .. }), "got {first:?}");
    let second = e.process_signal(1_001, request(Some(m), "I2", 100));
    assert!(matches!(deny_of(second), Some(BeastDeny::ReplayMarkDetected { .. })));
}

#[test]
fn unknown_domain_is_denied() {
    let k = sk(1);
    let mut e = BeastEngine::new(vec![pk_hex(&k)], vec![domain("d", 10_000)]);
    let r = e.process_signal(1_000, request(Some(mark(&k, "m1", "nope", 500)), "I1", 100));
    assert!(matches!(deny_of(r), Some(BeastDeny::UnknownDomain { .. })));
}

#[test]
fn escrow_cannot_be_overspent() {
    let k = sk(1);
    let mut e = BeastEngine::new(vec![pk_hex(&k)], vec![domain("d", 1_000)]);
    let r = e.process_signal(1_000, request(Some(mark(&k, "m1", "d", 50_000)), "I1", 20_000));
    assert!(deny_of(r).is_some(), "request above escrow must be denied");
    let d = e.domains.get("d").expect("domain");
    assert_eq!(d.total_reserved(), 0);
}

#[test]
fn freezing_one_bulkhead_leaves_the_other_running() {
    let k = sk(1);
    let mut e = BeastEngine::new(vec![pk_hex(&k)], vec![domain("a", 10_000), domain("b", 10_000)]);
    let frozen = e.process_signal(
        1_000,
        BeastSignal::CrossSurfaceBypassAttempt {
            domain_id: "b".to_string(),
            surface: "web-chat".to_string(),
            actor_urn: "urn:aid:rogue-tab".to_string(),
        },
    );
    assert!(matches!(frozen, BeastReflex::FreezeBulkheadL3AndFence { .. }));
    let b = e.process_signal(1_001, request(Some(mark(&k, "mb", "b", 500)), "IB", 100));
    assert!(matches!(deny_of(b), Some(BeastDeny::DomainBulkheadFrozenL3 { .. })));
    let a = e.process_signal(1_002, request(Some(mark(&k, "ma", "a", 500)), "IA", 100));
    assert!(matches!(a, BeastReflex::Proceed { .. }), "other domain must be unaffected: {a:?}");
}

#[test]
fn wal_chain_verifies_and_tamper_is_caught_at_the_right_seq() {
    let mut w = MerkleWal::default();
    for i in 0..10u64 {
        w.append(i, "d", &format!("e{i}"), "r");
    }
    assert_eq!(w.verify_full_chain(), Ok(()));
    w.entries[4].event_summary.push('x');
    assert_eq!(w.verify_full_chain(), Err(5));
}

#[test]
fn wal_relinked_prev_hash_is_caught() {
    let mut w = MerkleWal::default();
    for i in 0..5u64 {
        w.append(i, "d", "e", "r");
    }
    w.entries[2].prev_hash = "1".repeat(64);
    assert_eq!(w.verify_full_chain(), Err(3));
}

#[test]
fn proxy_green_urls_are_blocked_and_real_probe_allowed() {
    assert!(!is_proxy_green_url("https://llm.meridianlabs.cloud/health"));
    assert!(is_proxy_green_url("http://127.0.0.1:4000/health"));
}

// ---- reflex coverage: worker fault, Ring-3 taint, self-certification, settlement,
// ---- cross-class, note/blocker, infra anomaly, invalid cost.

const GOOD_PROBE: &str = "https://llm.meridianlabs.cloud/health";

fn mark_with(
    k: &SigningKey,
    id: &str,
    domain: &str,
    max_cost: i64,
    tweak: impl FnOnce(&mut SovereignMark),
) -> SovereignMark {
    let mut m = mark(k, id, domain, max_cost);
    tweak(&mut m);
    m.sign(k);
    m
}

fn lane(id: &str, class: BillingClass, p99_ms: u32) -> LaneSlot {
    LaneSlot { lane_id: id.to_string(), billing_class: class, fit: true, p99_ms }
}

fn two_api_one_sub(budget: i64) -> DomainBulkhead {
    DomainBulkhead::new(
        "d",
        "GBP",
        BillingClass::ApiCredit,
        budget,
        vec![
            lane("api-fast", BillingClass::ApiCredit, 100),
            lane("api-slow", BillingClass::ApiCredit, 200),
            // fastest of all, but the wrong billing class: must never be chosen.
            lane("sub-fastest", BillingClass::MonthlySubscription, 10),
        ],
    )
}

fn engine(k: &SigningKey, d: DomainBulkhead) -> BeastEngine {
    BeastEngine::new(vec![pk_hex(k)], vec![d])
}

fn fault(lane_id: &str, reservation: &str, secret: Option<&str>) -> BeastSignal {
    BeastSignal::WorkerFault {
        domain_id: "d".to_string(),
        lane_id: lane_id.to_string(),
        reservation_id: reservation.to_string(),
        reason: "429".to_string(),
        is_external_secret_401: secret.map(str::to_string),
    }
}

fn settle(worker: &str, oracle: &str, probe: &str, cost: i64, rounds: u8) -> BeastSignal {
    BeastSignal::OracleSettlement {
        domain_id: "d".to_string(),
        instruction_id: "I1".to_string(),
        reservation_id: "I1".to_string(),
        worker_urn: worker.to_string(),
        oracle_urn: oracle.to_string(),
        probe_url: probe.to_string(),
        actual_cost_minor_units: cost,
        rounds_passed: rounds,
    }
}

#[test]
fn worker_fault_drains_lane_and_fails_over_within_the_same_class() {
    let k = sk(1);
    let mut e = engine(&k, two_api_one_sub(10_000));
    let first = e.process_signal(1_000, request(Some(mark(&k, "m1", "d", 500)), "I1", 100));
    assert!(
        matches!(&first, BeastReflex::Proceed { assigned_lane, .. } if assigned_lane == "api-fast"),
        "got {first:?}"
    );
    let r = e.process_signal(1_001, fault("api-fast", "I1", None));
    match r {
        BeastReflex::DrainLaneAndFailoverSameClass { drained_lane, replacement_lane, released_minor_units, .. } => {
            assert_eq!(drained_lane, "api-fast");
            assert_eq!(replacement_lane.as_deref(), Some("api-slow"), "must not jump to the subscription lane");
            assert_eq!(released_minor_units, 100);
        }
        other => panic!("expected failover, got {other:?}"),
    }
    assert_eq!(e.domains["d"].total_reserved(), 0, "the faulted reservation must be released");
    let next = e.process_signal(1_002, request(Some(mark(&k, "m2", "d", 500)), "I2", 100));
    assert!(
        matches!(&next, BeastReflex::Proceed { assigned_lane, .. } if assigned_lane == "api-slow"),
        "drained lane must stay out of rotation, got {next:?}"
    );
}

#[test]
fn worker_fault_with_no_same_class_lane_left_reports_no_replacement() {
    let k = sk(1);
    let d = DomainBulkhead::new(
        "d",
        "GBP",
        BillingClass::ApiCredit,
        10_000,
        vec![lane("only-api", BillingClass::ApiCredit, 100), lane("sub", BillingClass::MonthlySubscription, 10)],
    );
    let mut e = engine(&k, d);
    let r = e.process_signal(1_000, fault("only-api", "none", None));
    assert!(
        matches!(r, BeastReflex::DrainLaneAndFailoverSameClass { replacement_lane: None, .. }),
        "a subscription lane must not substitute for an API lane"
    );
    let denied = e.process_signal(1_001, request(Some(mark(&k, "m1", "d", 500)), "I1", 100));
    assert!(matches!(deny_of(denied), Some(BeastDeny::NoFitLaneInClass { .. })));
}

#[test]
fn worker_fault_with_secret_401_drains_the_secret_by_name_only() {
    let k = sk(1);
    let mut e = engine(&k, two_api_one_sub(10_000));
    let r = e.process_signal(1_000, fault("api-fast", "none", Some("DEEPSEEK_API_KEY")));
    assert!(
        matches!(&r, BeastReflex::DrainExternalSecretSilently { env_var, .. } if env_var == "DEEPSEEK_API_KEY"),
        "got {r:?}"
    );
}

#[test]
fn worker_fault_in_unknown_domain_fails_closed() {
    let k = sk(1);
    let mut e = engine(&k, two_api_one_sub(10_000));
    let r = e.process_signal(
        1_000,
        BeastSignal::WorkerFault {
            domain_id: "ghost".to_string(),
            lane_id: "x".to_string(),
            reservation_id: "x".to_string(),
            reason: "r".to_string(),
            is_external_secret_401: None,
        },
    );
    assert!(matches!(deny_of(r), Some(BeastDeny::UnknownDomain { .. })));
}

#[test]
fn ring3_read_plus_external_egress_is_blocked_but_each_alone_is_allowed() {
    let k = sk(1);
    let mut e = engine(&k, two_api_one_sub(10_000));
    let both = mark_with(&k, "both", "d", 500, |m| {
        m.reads_ring3 = true;
        m.egresses_external = true;
    });
    let r = e.process_signal(1_000, request(Some(both), "I1", 100));
    assert_eq!(deny_of(r), Some(BeastDeny::Ring3EgressTaintBlocked));
    assert_eq!(e.domains["d"].total_reserved(), 0);

    let read_only = mark_with(&k, "ro", "d", 500, |m| m.reads_ring3 = true);
    let r = e.process_signal(1_001, request(Some(read_only), "I2", 100));
    assert!(matches!(r, BeastReflex::Proceed { .. }), "Ring-3 read alone must pass, got {r:?}");

    let egress_only = mark_with(&k, "eo", "d", 500, |m| m.egresses_external = true);
    let r = e.process_signal(1_002, request(Some(egress_only), "I3", 100));
    assert!(matches!(r, BeastReflex::Proceed { .. }), "external egress alone must pass, got {r:?}");
}

#[test]
fn self_certification_is_blocked_case_insensitively_and_keeps_the_reservation() {
    let k = sk(1);
    let mut e = engine(&k, two_api_one_sub(10_000));
    e.process_signal(1_000, request(Some(mark(&k, "m1", "d", 500)), "I1", 100));
    let r = e.process_signal(1_001, settle("urn:aid:Legion-1", "URN:AID:LEGION-1", GOOD_PROBE, 100, 3));
    assert!(matches!(deny_of(r), Some(BeastDeny::SelfCertificationBlocked { .. })));
    assert_eq!(e.domains["d"].total_reserved(), 100, "a blocked settlement must not release escrow");
    assert_eq!(e.domains["d"].settled_yield_count, 0);
}

#[test]
fn oracle_settlement_pays_actual_cost_once_and_only_with_three_rounds() {
    let k = sk(1);
    let mut e = engine(&k, two_api_one_sub(10_000));
    e.process_signal(1_000, request(Some(mark(&k, "m1", "d", 500)), "I1", 200));

    let two = e.process_signal(1_001, settle("urn:aid:w", "urn:aid:oracle", GOOD_PROBE, 140, 2));
    assert!(matches!(two, BeastReflex::AutoSpawnDirectAttack { .. }), "2 rounds must not settle, got {two:?}");
    assert_eq!(e.domains["d"].total_reserved(), 200);
    assert_eq!(e.domains["d"].spent_minor_units, 0);

    let proxy = e.process_signal(1_002, settle("urn:aid:w", "urn:aid:oracle", "http://127.0.0.1:4000/health", 140, 3));
    assert!(matches!(deny_of(proxy), Some(BeastDeny::ProxyGreenUrlBlocked { .. })));
    assert_eq!(e.domains["d"].spent_minor_units, 0);

    let over = e.process_signal(1_003, settle("urn:aid:w", "urn:aid:oracle", GOOD_PROBE, 201, 3));
    assert!(matches!(deny_of(over), Some(BeastDeny::InvalidCost { cost: 201 })));
    assert_eq!(e.domains["d"].total_reserved(), 200, "an over-cost settlement must restore the reservation");
    assert_eq!(e.domains["d"].spent_minor_units, 0);

    let ok = e.process_signal(1_004, settle("urn:aid:w", "urn:aid:oracle", GOOD_PROBE, 140, 3));
    assert!(
        matches!(ok, BeastReflex::SettledOperationalYield { net_cost_minor_units: 140, yield_units: 1, .. }),
        "got {ok:?}"
    );
    let d = &e.domains["d"];
    assert_eq!((d.spent_minor_units, d.total_reserved(), d.available_minor_units()), (140, 0, 9_860));

    let again = e.process_signal(1_005, settle("urn:aid:w", "urn:aid:oracle", GOOD_PROBE, 140, 3));
    assert!(deny_of(again).is_some(), "the same reservation must not settle twice");
    assert_eq!(e.domains["d"].spent_minor_units, 140);
}

#[test]
fn cross_class_and_currency_substitution_are_denied() {
    let k = sk(1);
    let mut e = engine(&k, two_api_one_sub(10_000));
    let sub_mark = mark_with(&k, "sub", "d", 500, |m| m.billing_class = BillingClass::MonthlySubscription);
    let r = e.process_signal(1_000, request(Some(sub_mark), "I1", 100));
    assert!(matches!(deny_of(r), Some(BeastDeny::CrossClassSubstitution { .. })));

    let usd = mark_with(&k, "usd", "d", 500, |m| m.currency = "USD".to_string());
    let r = e.process_signal(1_001, request(Some(usd), "I2", 100));
    assert!(matches!(deny_of(r), Some(BeastDeny::CurrencyMismatch { .. })));

    // an API-class mark that asks for the subscription lane by name is still a substitution.
    let r = e.process_signal(
        1_002,
        BeastSignal::RequestExecution {
            mark: Some(mark(&k, "lane", "d", 500)),
            instruction_id: "I3".to_string(),
            requested_lane: Some("sub-fastest".to_string()),
            requested_cost_minor_units: 100,
            probe_url: None,
            touched_paths: vec![],
            worker_text: String::new(),
        },
    );
    assert!(matches!(deny_of(r), Some(BeastDeny::CrossClassSubstitution { .. })));
    assert_eq!(e.domains["d"].total_reserved(), 0);
}

#[test]
fn forbidden_note_paths_and_blocker_phrases_are_blocked_but_clean_work_passes() {
    assert!(is_forbidden_note_or_blocker(&["docs/notes/x.md".into()], "").is_some());
    assert!(is_forbidden_note_or_blocker(&["./docs/diagnoses/y.yaml".into()], "").is_some());
    assert!(is_forbidden_note_or_blocker(&["a/HANDOFF.md".into()], "").is_some());
    assert!(is_forbidden_note_or_blocker(&[], "BLOCKER: cannot proceed").is_some());
    assert!(is_forbidden_note_or_blocker(&[], "this is Outside This Lane").is_some());
    assert!(is_forbidden_note_or_blocker(&["crates/x/src/lib.rs".into()], "implemented and tested").is_none());

    let k = sk(1);
    let mut e = engine(&k, two_api_one_sub(10_000));
    let r = e.process_signal(
        1_000,
        BeastSignal::RequestExecution {
            mark: Some(mark(&k, "m1", "d", 500)),
            instruction_id: "I1".to_string(),
            requested_lane: None,
            requested_cost_minor_units: 100,
            probe_url: None,
            touched_paths: vec!["docs/notes/excuse.md".to_string()],
            worker_text: String::new(),
        },
    );
    assert!(matches!(deny_of(r), Some(BeastDeny::ForbiddenNoteOrBlockerBlocked { .. })));
    assert_eq!(e.domains["d"].total_reserved(), 0);
}

#[test]
fn severe_infra_anomaly_escalates_and_invalidates_older_leases() {
    let k = sk(1);
    let mut e = engine(&k, two_api_one_sub(10_000));
    let anomaly = |severe: bool| BeastSignal::DeterministicInfraAnomaly {
        domain_id: "d".to_string(),
        component_id: "router".to_string(),
        detail: "http-525".to_string(),
        severe_dual_probe_fail: severe,
    };
    let r = e.process_signal(1_000, anomaly(false));
    assert!(matches!(r, BeastReflex::AutoSpawnDirectAttack { .. }));
    assert_eq!(e.domains["d"].dof_level, DofLevel::L0FullLease, "a non-severe anomaly must not escalate");
    assert_eq!(e.domains["d"].lease_epoch, 1);

    e.process_signal(1_001, anomaly(true));
    assert_eq!(e.domains["d"].dof_level, DofLevel::L2ComponentRepairOnly);
    assert_eq!(e.domains["d"].lease_epoch, 2);

    let old = e.process_signal(1_002, request(Some(mark(&k, "m1", "d", 500)), "I1", 100));
    assert!(matches!(deny_of(old), Some(BeastDeny::StaleLeaseEpoch { got: 1, current: 2 })));
}

#[test]
fn zero_negative_and_over_ceiling_costs_are_invalid() {
    let k = sk(1);
    let mut e = engine(&k, two_api_one_sub(10_000));
    for (i, cost) in [0i64, -5, 501].into_iter().enumerate() {
        let r = e.process_signal(1_000 + i as u64, request(Some(mark(&k, &format!("m{i}"), "d", 500)), "I", cost));
        assert!(matches!(deny_of(r), Some(BeastDeny::InvalidCost { .. })), "cost {cost}");
    }
    assert_eq!(e.domains["d"].total_reserved(), 0);
}
