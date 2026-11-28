use ed25519_dalek::SigningKey;
use meridian_battalion::{qualify_pool, CandidateLaneSpec, GoldenMissionProber, ProbeOutcome};
use meridian_ledger::{BillingClass, LaneFitnessRecord, LaneStatus, RoutingState};
use std::collections::HashSet;
use std::fs;
use std::path::PathBuf;

struct Table(Vec<(&'static str, ProbeOutcome)>);

impl GoldenMissionProber for Table {
    fn probe_lane(&self, lane: &CandidateLaneSpec) -> ProbeOutcome {
        self.0
            .iter()
            .find(|(id, _)| *id == lane.lane_id)
            .map(|(_, o)| o.clone())
            .unwrap_or(ProbeOutcome::ProviderDegraded { http_status: 599 })
    }
}

fn lane(id: &str, secret: &str, class: BillingClass) -> CandidateLaneSpec {
    CandidateLaneSpec {
        lane_id: id.to_string(),
        provider: format!("prov-{id}"),
        model: format!("model-{id}"),
        secret_env: secret.to_string(),
        billing_class: class,
        ttl_secs: 3_600,
    }
}

fn signer() -> SigningKey {
    SigningKey::from_bytes(&[0x66; 32])
}

fn routing_for(sk: &SigningKey) -> RoutingState {
    RoutingState::new(vec![hex::encode(sk.verifying_key().to_bytes())])
}

fn pool() -> Vec<CandidateLaneSpec> {
    vec![
        lane("good", "SEED_GOOD_API_KEY", BillingClass::ApiCredit),
        lane("empty", "SEED_EMPTY_API_KEY", BillingClass::ApiCredit),
        lane("denied", "SEED_OPENROUTER_API_KEY", BillingClass::ApiCredit),
        lane("flaky", "SEED_FLAKY_API_KEY", BillingClass::ApiCredit),
    ]
}

fn prober() -> Table {
    Table(vec![
        ("good", ProbeOutcome::GoldenPass { p99_ms: 400 }),
        ("empty", ProbeOutcome::EmptyOrFailedPatch { p99_ms: 900, detail: "exit_2_empty_diff".to_string() }),
        ("denied", ProbeOutcome::SecretBoundary { http_status: 401 }),
        ("flaky", ProbeOutcome::ProviderDegraded { http_status: 429 }),
    ])
}

fn unique_dir(tag: &str) -> PathBuf {
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    std::env::temp_dir().join(format!("meridian-battalion-{tag}-{}-{nanos}", std::process::id()))
}

#[test]
fn only_a_golden_pass_is_fit_and_every_other_outcome_is_unfit_with_its_reason() {
    let sk = signer();
    let mut rs = routing_for(&sk);
    let report = qualify_pool(&pool(), &prober(), &sk, 1_000, &mut rs, None).expect("qualify");
    assert_eq!(report.fit_lanes, vec!["good".to_string()]);
    assert_eq!(
        report.unfit_lanes,
        vec!["empty".to_string(), "denied".to_string(), "flaky".to_string()]
    );

    let by_id = |id: &str| rs.all_records().into_iter().find(|r| r.lane_id == id).expect(id).clone();
    let good = by_id("good");
    assert!(good.is_live_fit(1_000) && good.p99_ms == 400);
    assert_eq!(good.reason, "PRE_EDIT_RED->FIX_GREEN");
    assert_eq!(good.expires_at_utc, 4_600);
    let empty = by_id("empty");
    assert_eq!(empty.status, LaneStatus::Unfit);
    assert!(!empty.golden_pass);
    assert_eq!(empty.reason, "EMPTY_OR_FAILED_PATCH:exit_2_empty_diff");
    let denied = by_id("denied");
    assert_eq!(denied.status, LaneStatus::Drained);
    assert_eq!(denied.reason, "SECRET_BOUNDARY_HTTP_401:SEED_OPENROUTER_API_KEY");
    let flaky = by_id("flaky");
    assert_eq!(flaky.status, LaneStatus::Drained);
    assert_eq!(flaky.reason, "PROVIDER_DEGRADED_HTTP_429");
    for r in [&empty, &denied, &flaky] {
        assert!(!r.is_live_fit(1_000));
    }
}

#[test]
fn a_secret_boundary_names_the_exact_seed_variable_and_a_clean_pool_escalates_nothing() {
    let sk = signer();
    let mut rs = routing_for(&sk);
    let report = qualify_pool(&pool(), &prober(), &sk, 1_000, &mut rs, None).expect("qualify");
    assert_eq!(report.secret_escalations, vec!["SEED_OPENROUTER_API_KEY".to_string()]);
    assert_eq!(
        report.escalation_line(),
        Some("ESCALATE/1 founder secret boundary: missing_or_refused=SEED_OPENROUTER_API_KEY".to_string())
    );

    let clean = Table(vec![("good", ProbeOutcome::GoldenPass { p99_ms: 100 })]);
    let mut rs2 = routing_for(&sk);
    let only_good = vec![lane("good", "SEED_GOOD_API_KEY", BillingClass::ApiCredit)];
    let report2 = qualify_pool(&only_good, &clean, &sk, 1_000, &mut rs2, None).expect("qualify");
    assert_eq!(report2.escalation_line(), None);
}

#[test]
fn exported_files_round_trip_and_verify_strict_against_the_trusted_key() {
    let sk = signer();
    let mut rs = routing_for(&sk);
    let dir = unique_dir("export");
    qualify_pool(&pool(), &prober(), &sk, 1_000, &mut rs, Some(&dir)).expect("qualify");

    let trusted: HashSet<String> = [hex::encode(sk.verifying_key().to_bytes())].into_iter().collect();
    for id in ["good", "empty", "denied", "flaky"] {
        let body = fs::read_to_string(dir.join(format!("{id}.json"))).expect("exported file");
        let rec: LaneFitnessRecord = serde_json::from_str(&body).expect("valid estate.lane-fitness.v1 json");
        assert_eq!(rec.schema, "estate.lane-fitness.v1");
        assert_eq!(rec.lane_id, id);
        assert!(rec.verify_strict(&trusted).is_ok(), "{id} must verify");
    }

    // Tampering with an exported file breaks verification.
    let body = fs::read_to_string(dir.join("good.json")).expect("exported file");
    let mut rec: LaneFitnessRecord = serde_json::from_str(&body).expect("json");
    rec.p99_ms = 1;
    assert!(rec.verify_strict(&trusted).is_err());
    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn a_signer_the_routing_state_does_not_trust_cannot_publish_leases() {
    let sk = signer();
    let other = SigningKey::from_bytes(&[0x99; 32]);
    let mut rs = routing_for(&other);
    let err = qualify_pool(&pool(), &prober(), &sk, 1_000, &mut rs, None).expect_err("must refuse");
    assert!(err.contains("UntrustedFitnessSigner"), "{err}");
    assert!(rs.all_records().is_empty());
}

#[test]
fn an_unwritable_export_dir_is_an_error_not_a_silent_skip() {
    let sk = signer();
    let mut rs = routing_for(&sk);
    let blocker = unique_dir("blocker");
    fs::write(&blocker, b"not a directory").expect("write blocker file");
    let err = qualify_pool(&pool(), &prober(), &sk, 1_000, &mut rs, Some(&blocker.join("sub")))
        .expect_err("must fail");
    assert!(err.starts_with("create_dir_all"), "{err}");
    let _ = fs::remove_file(&blocker);
}
