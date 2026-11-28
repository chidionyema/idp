//! Standalone static Rust enforcement binary (`meridian-gate`).
//!
//! Zero Python, zero venv, zero `|| true` swallowing. Every non-ALLOW verdict exits non-zero
//! and prints a machine-actionable `GateVerdict` JSON document on stdout.

use ed25519_dalek::{Signer, SigningKey};
use mitp_core::{
    check_diff_scope_and_seal, verify_and_settle, AuthoritySequencer, BillingClass,
    DeterministicKernel, EffectClass, EffectEnvelope, Footprint, FounderSeal, GateError,
    GateVerdict, LaneHealth, Monotonicity, ParentMandate, ProviderLane, ResourceKey,
    SettlementTransition, ShipContract, VerifierReceipt, VerifyingObligation,
};
use serde::Deserialize;
use std::collections::{BTreeMap, BTreeSet, HashSet};
use std::env;
use std::fs;
use std::io::{self, Read};
use std::process::ExitCode;

#[derive(Deserialize)]
struct AdmitRequest {
    mandate: ParentMandate,
    lanes: Vec<ProviderLane>,
    envelope: EffectEnvelope,
    now_utc: u64,
}

#[derive(Deserialize)]
struct SettlementRequest {
    obligation: VerifyingObligation,
    receipt: Option<VerifierReceipt>,
    trusted_certifiers_hex: Vec<String>,
    current_revocation_epoch: u64,
    now_utc: u64,
}

#[derive(Deserialize)]
struct ScopeRequest {
    changed_files: BTreeMap<String, String>,
    claimed_patterns: Vec<String>,
    trusted_founder_pubkey_hex: String,
    seal: Option<FounderSeal>,
}

fn read_input(path_arg: Option<&str>) -> Result<String, String> {
    match path_arg {
        Some(p) if p != "-" => fs::read_to_string(p).map_err(|e| format!("read {p}: {e}")),
        _ => {
            let mut buf = String::new();
            io::stdin()
                .read_to_string(&mut buf)
                .map_err(|e| format!("stdin: {e}"))?;
            Ok(buf)
        }
    }
}

fn emit(v: &GateVerdict, ok: bool) -> ExitCode {
    match serde_json::to_string(v) {
        Ok(s) => println!("{s}"),
        Err(e) => println!("{{\"verdict\":\"BLIND\",\"reason\":\"serialize_error:{e}\"}}"),
    }
    if ok {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(2)
    }
}

fn run_optimus_both_ways() -> ExitCode {
    let cert_sk = SigningKey::from_bytes(&[0x41; 32]);
    let worker_sk = SigningKey::from_bytes(&[0x42; 32]);
    let cert_pk = hex::encode(cert_sk.verifying_key().to_bytes());
    let worker_pk = hex::encode(worker_sk.verifying_key().to_bytes());

    let mandate = ParentMandate {
        root_h_digest: "h-opt".to_string(),
        max_effect_class: EffectClass::C,
        allowed_billing_class: BillingClass::ApiCredit,
        policy_hash: "pol-opt".to_string(),
        currency: "GBP".to_string(),
        budget_ceiling_minor_units: 10_000,
    };
    let lanes = vec![
        ProviderLane {
            lane_id: "deepseek".to_string(),
            billing_class: BillingClass::ApiCredit,
            health: LaneHealth::Fit,
            fitness_expires_at_utc: 2_000,
        },
        ProviderLane {
            lane_id: "claude-sub".to_string(),
            billing_class: BillingClass::MonthlySubscription,
            health: LaneHealth::Fit,
            fitness_expires_at_utc: 2_000,
        },
    ];
    let mut k = DeterministicKernel::new(mandate, lanes, vec![cert_pk.clone()], vec![worker_pk.clone()]);

    let mut writes = BTreeSet::new();
    writes.insert(ResourceKey::RepoPath {
        repo: "chidionyema/idp".to_string(),
        path_prefix: "crates/mitp-core/src/lib.rs".to_string(),
    });
    let good_env = EffectEnvelope {
        instruction_id: "INS-OPT-1".to_string(),
        attempt_id: "att-1".to_string(),
        effect_digest: "eff-opt-1".to_string(),
        parent_m_digest: "m-opt".to_string(),
        root_h_digest: "h-opt".to_string(),
        policy_hash: "pol-opt".to_string(),
        objective_hash: "obj-opt".to_string(),
        acceptance_predicate_hash: "pred-opt".to_string(),
        lane_id: "deepseek".to_string(),
        requested_billing_class: BillingClass::ApiCredit,
        class: EffectClass::I,
        monotonicity: Monotonicity::Monotonic,
        footprint: Footprint {
            reads: BTreeSet::new(),
            writes,
        },
        cost_minor_units: 1_000,
        currency: "GBP".to_string(),
        revocation_epoch: 1,
        fencing_token: 1,
        base_revisions: BTreeMap::new(),
        nonce_hex: "aa11bb22cc33dd44".to_string(),
        verification_deadline_utc: 1_500,
        requested_reserved_power: None,
    };

    // Positive control: valid admit
    let pos_ok = k.admit_effect(&good_env, 1_000).is_ok();
    // Negative control 1: cross-class substitution rejected
    let mut bad_class = good_env.clone();
    bad_class.lane_id = "claude-sub".to_string();
    bad_class.nonce_hex = "bb11bb22cc33dd44".to_string();
    let neg_billing = matches!(
        k.admit_effect(&bad_class, 1_000),
        Err(GateError::CrossClassSubstitution { .. })
    );
    // Negative control 2: proxy-green SHIP-CONTRACT rejected
    let neg_proxy = matches!(
        ShipContract::parse("SHIP-CONTRACT\naccept: GET https://github.com/x/y expect 200 within 30m\noptimus: a baseline=0 target=1\nfailure-classes: f\ndebug-pack: DBG-001\n"),
        Err(GateError::ProxyGreenSubstitution { .. })
    );
    // Negative control 3: deadline expiry forces recovery instead of hanging/settling
    let ob = VerifyingObligation {
        instruction_id: "INS-OPT-2".to_string(),
        attempt_id: "att-1".to_string(),
        execution_epoch: 1,
        objective_hash: "obj".to_string(),
        acceptance_predicate_hash: "pred".to_string(),
        policy_hash: "pol-opt".to_string(),
        verification_deadline_utc: 1_500,
        worker_pubkey_hex: worker_pk,
    };
    let mut reg = HashSet::new();
    let mut rc = VerifierReceipt {
        instruction_id: "INS-OPT-2".to_string(),
        attempt_id: "att-1".to_string(),
        execution_epoch: 1,
        objective_hash: "obj".to_string(),
        acceptance_predicate_hash: "pred".to_string(),
        target_identity: "idp".to_string(),
        artifact_digest: "sha256:ok".to_string(),
        observed_at_utc: 1_100,
        evidence_expires_utc: 1_900,
        observation_url: "https://llm.meridianlabs.cloud/health".to_string(),
        verifier_pubkey_hex: cert_pk.clone(),
        policy_hash: "pol-opt".to_string(),
        signature_hex: String::new(),
    };
    rc.signature_hex = hex::encode(cert_sk.sign(&rc.canonical_message()).to_bytes());
    let trusted: HashSet<String> = [cert_pk].into_iter().collect();
    let neg_timeout = matches!(
        verify_and_settle(&ob, Some(&rc), &trusted, 1, 1_501, &mut reg),
        Ok(SettlementTransition::RecoveryRequired { .. })
    );
    let pos_settle = matches!(
        verify_and_settle(&ob, Some(&rc), &trusted, 1, 1_200, &mut reg),
        Ok(SettlementTransition::Settled(_))
    );

    let all_ok = pos_ok && neg_billing && neg_proxy && neg_timeout && pos_settle;
    println!("optimus.kernel.rust_invariant_gate_enforced={}", if all_ok { 1 } else { 0 });
    if all_ok {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(1)
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().collect();
    let cmd = args.get(1).map(String::as_str).unwrap_or("");
    let path_arg = args.get(2).map(String::as_str);

    match cmd {
        "--optimus" => run_optimus_both_ways(),
        "admit" => {
            let raw = match read_input(path_arg) {
                Ok(s) => s,
                Err(e) => return emit(&GateVerdict::blind(&e), false),
            };
            let req: AdmitRequest = match serde_json::from_str(&raw) {
                Ok(r) => r,
                Err(e) => return emit(&GateVerdict::blind(&format!("json:{e}")), false),
            };
            let mut kernel = DeterministicKernel::new(req.mandate, req.lanes, vec![], vec![]);
            match kernel.admit_effect(&req.envelope, req.now_utc) {
                Ok(tok) => emit(&GateVerdict::allow(kernel.revocation_epoch, tok), true),
                Err(err) => emit(&GateVerdict::deny(err, "ADMISSION_CONTRACT", "ZERO_SHOT_REJECT", "FIX_ENVELOPE"), false),
            }
        }
        "verify-contract" => {
            let raw = match read_input(path_arg) {
                Ok(s) => s,
                Err(e) => return emit(&GateVerdict::blind(&e), false),
            };
            match ShipContract::parse(&raw) {
                Ok(_) => emit(&GateVerdict::allow(0, 0), true),
                Err(err) => emit(&GateVerdict::deny(err, "B08_NON_PROXY_CONTRACT", "ZERO_SHOT_REJECT", "FIX_SHIP_CONTRACT"), false),
            }
        }
        "verify-settlement" => {
            let raw = match read_input(path_arg) {
                Ok(s) => s,
                Err(e) => return emit(&GateVerdict::blind(&e), false),
            };
            let req: SettlementRequest = match serde_json::from_str(&raw) {
                Ok(r) => r,
                Err(e) => return emit(&GateVerdict::blind(&format!("json:{e}")), false),
            };
            let trusted: HashSet<String> = req
                .trusted_certifiers_hex
                .into_iter()
                .map(|s| s.to_ascii_lowercase())
                .collect();
            let mut reg = HashSet::new();
            match verify_and_settle(
                &req.obligation,
                req.receipt.as_ref(),
                &trusted,
                req.current_revocation_epoch,
                req.now_utc,
                &mut reg,
            ) {
                Ok(SettlementTransition::Settled(_)) => emit(&GateVerdict::allow(req.current_revocation_epoch, 0), true),
                Ok(SettlementTransition::RecoveryRequired { reason, .. }) => {
                    emit(&GateVerdict::reconcile(reason, "B06_BOUNDED_LIVENESS", "TRIGGER_BOUNDED_RECOVERY"), false)
                }
                Err(err) => emit(&GateVerdict::deny(err, "B08_OPERATIONAL_TRUTH", "ZERO_SHOT_REJECT", "REJECT_SETTLEMENT"), false),
            }
        }
        "check-scope" => {
            let raw = match read_input(path_arg) {
                Ok(s) => s,
                Err(e) => return emit(&GateVerdict::blind(&e), false),
            };
            let req: ScopeRequest = match serde_json::from_str(&raw) {
                Ok(r) => r,
                Err(e) => return emit(&GateVerdict::blind(&format!("json:{e}")), false),
            };
            match check_diff_scope_and_seal(
                &req.changed_files,
                &req.claimed_patterns,
                &req.trusted_founder_pubkey_hex,
                req.seal.as_ref(),
            ) {
                Ok(()) => emit(&GateVerdict::allow(0, 0), true),
                Err(err) => emit(&GateVerdict::deny(err, "B10_GOVERNANCE_INTEGRITY", "ZERO_SHOT_REJECT", "REQUIRE_CLAIM_OR_FOUNDER_SEAL"), false),
            }
        }
        _ => emit(&GateVerdict::blind("usage: meridian-gate <admit|verify-contract|verify-settlement|check-scope|--optimus> [file|-]"), false),
    }
}
