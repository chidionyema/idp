//! `meridian-beastd` — Unsleeping Sovereign Daemon & Optimus Self-Falsifier.

use ed25519_dalek::SigningKey;
use meridian_beast_core::{
    BeastDeny, BeastEngine, BeastReflex, BeastSignal, BillingClass, DomainBulkhead, DofLevel,
    LaneSlot, ProcessClass, SovereignMark,
};
use std::process::ExitCode;

fn make_mark(sk: &SigningKey, id: &str, domain: &str, bclass: BillingClass, max_cost: i64, r3: bool, ext: bool) -> SovereignMark {
    let mut m = SovereignMark {
        mark_id: id.to_string(),
        domain_id: domain.to_string(),
        actor_urn: "urn:aid:legion-worker-1".to_string(),
        process_class: ProcessClass::NonDeterministicWorker,
        billing_class: bclass,
        footprint_hash: "sha256:fp-001".to_string(),
        max_cost_minor_units: max_cost,
        currency: "GBP".to_string(),
        revocation_epoch: 1,
        lease_epoch: 1,
        expires_utc: 2_000,
        reads_ring3: r3,
        egresses_external: ext,
        issuer_pubkey_hex: String::new(),
        signature_hex: String::new(),
    };
    m.sign(sk);
    m
}

fn main() -> ExitCode {
    let issuer_sk = SigningKey::from_bytes(&[0x66; 32]);
    let issuer_pk = hex::encode(issuer_sk.verifying_key().to_bytes());

    let idp = DomainBulkhead::new(
        "idp-core",
        "GBP",
        BillingClass::ApiCredit,
        10_000,
        vec![
            LaneSlot { lane_id: "deepseek-api".to_string(), billing_class: BillingClass::ApiCredit, fit: true, p99_ms: 350 },
            LaneSlot { lane_id: "minimax-api".to_string(), billing_class: BillingClass::ApiCredit, fit: true, p99_ms: 480 },
            LaneSlot { lane_id: "claude-sub".to_string(), billing_class: BillingClass::MonthlySubscription, fit: true, p99_ms: 250 },
        ],
    );
    let prospector = DomainBulkhead::new(
        "prospector",
        "GBP",
        BillingClass::ApiCredit,
        5_000,
        vec![
            LaneSlot { lane_id: "deepseek-api".to_string(), billing_class: BillingClass::ApiCredit, fit: true, p99_ms: 350 },
        ],
    );

    let mut beast = BeastEngine::new(vec![issuer_pk], vec![idp, prospector]);

    // 1. Unmarked execution rejected immediately (No Mark, No Buy/Sell)
    let c1 = matches!(
        beast.process_signal(1_000, BeastSignal::RequestExecution {
            mark: None,
            instruction_id: "INS-0".to_string(),
            requested_lane: None,
            requested_cost_minor_units: 100,
            probe_url: None,
            touched_paths: vec![],
            worker_text: String::new(),
        }),
        BeastReflex::RejectedFailClosed { deny: BeastDeny::UnmarkedOrUntrustedActor, .. }
    );

    // 2. Cross-surface bypass freezes ONLY `prospector` bulkhead at L3
    let c2 = matches!(
        beast.process_signal(1_001, BeastSignal::CrossSurfaceBypassAttempt {
            domain_id: "prospector".to_string(),
            surface: "web-chat".to_string(),
            actor_urn: "urn:aid:rogue-tab".to_string(),
        }),
        BeastReflex::FreezeBulkheadL3AndFence { red_card: true, .. }
    );

    // 3. Frozen `prospector` denies work while `idp-core` keeps running unaffected (Bulkhead proof)
    let m_prosp = make_mark(&issuer_sk, "mk-p1", "prospector", BillingClass::ApiCredit, 500, false, false);
    let c3 = matches!(
        beast.process_signal(1_002, BeastSignal::RequestExecution {
            mark: Some(m_prosp),
            instruction_id: "INS-P1".to_string(),
            requested_lane: None,
            requested_cost_minor_units: 100,
            probe_url: Some("https://llm.meridianlabs.cloud/health".to_string()),
            touched_paths: vec![],
            worker_text: String::new(),
        }),
        BeastReflex::RejectedFailClosed { deny: BeastDeny::DomainBulkheadFrozenL3 { .. }, .. }
    );

    let m_idp = make_mark(&issuer_sk, "mk-i1", "idp-core", BillingClass::ApiCredit, 500, false, false);
    let c4 = matches!(
        beast.process_signal(1_003, BeastSignal::RequestExecution {
            mark: Some(m_idp),
            instruction_id: "INS-I1".to_string(),
            requested_lane: None,
            requested_cost_minor_units: 200,
            probe_url: Some("https://llm.meridianlabs.cloud/health".to_string()),
            touched_paths: vec!["crates/meridian-beast-core/src/lib.rs".to_string()],
            worker_text: "OPERATIONAL".to_string(),
        }),
        BeastReflex::Proceed { ref assigned_lane, .. } if assigned_lane == "deepseek-api"
    );

    // 4. Independent oracle settles INS-I1; WAL verifies 100% intact
    let c5 = matches!(
        beast.process_signal(1_004, BeastSignal::OracleSettlement {
            domain_id: "idp-core".to_string(),
            instruction_id: "INS-I1".to_string(),
            reservation_id: "INS-I1".to_string(),
            worker_urn: "urn:aid:legion-worker-1".to_string(),
            oracle_urn: "urn:aid:greenlane-oracle".to_string(),
            probe_url: "https://llm.meridianlabs.cloud/health".to_string(),
            actual_cost_minor_units: 140,
            rounds_passed: 3,
        }),
        BeastReflex::SettledOperationalYield { net_cost_minor_units: 140, yield_units: 1, .. }
    );

    let c6 = beast.wal.verify_full_chain().is_ok()
        && beast.domains.get("prospector").map(|d| d.dof_level == DofLevel::L3FrozenBulkhead).unwrap_or(false)
        && beast.domains.get("idp-core").map(|d| d.dof_level == DofLevel::L0FullLease && d.founder_interrupts == 0).unwrap_or(false);

    let ok = c1 && c2 && c3 && c4 && c5 && c6;
    println!("optimus.beast.sovereign_kernel_operational={}", if ok { 1 } else { 0 });
    if ok { ExitCode::SUCCESS } else { ExitCode::from(1) }
}
