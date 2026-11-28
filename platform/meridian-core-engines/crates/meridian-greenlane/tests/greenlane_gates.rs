use meridian_greenlane::{
    is_proxy_green_url, parse_and_validate_contract_presubmit, settle_or_auto_recover,
    verify_presubmit_parity, BlackboxProbeRound, PresubmitError, ReleaseVerdict, ShipContract,
};
use meridian_ledger::{BillingClass, BudgetLedger, LedgerError};

const GOOD_URL: &str = "https://llm.meridianlabs.cloud/health";

fn contract_text(url: &str, optimus: &str) -> String {
    format!(
        "SHIP-CONTRACT\naccept: GET {url} expect 200 within 30m\noptimus: {optimus}\nfailure-classes: proxy-green-bypass,no-fit-lane\ndebug-pack: DBG-001\n"
    )
}

fn good_contract() -> ShipContract {
    parse_and_validate_contract_presubmit(&contract_text(GOOD_URL, "m baseline=0 target=1"))
        .expect("good contract must parse")
}

#[test]
fn every_proxy_url_shape_is_refused() {
    for url in [
        "https://github.com/chidionyema/idp",
        "https://www.github.com/x",
        "https://api.github.com/repos/chidionyema/idp/commits/main",
        "https://API.GitHub.com/x",
        "https://raw.githubusercontent.com/chidionyema/idp/main/x",
        "https://gist.github.com/x",
        "https://objects.githubusercontent.com/x",
        "https://api.github.com./x",
        "https://api.github.com:443/x",
        "https://user:pw@api.github.com/x",
        "https://llm.meridianlabs.cloud@api.github.com/x",
        "https://localhost/health",
        "https://127.0.0.1/health",
        "https://127.0.0.2/health",
        "https://0.0.0.0/health",
        "https://[::1]/health",
        "https://[::1]:8443/health",
        "http://llm.meridianlabs.cloud/health",
        "llm.meridianlabs.cloud/health",
        "https:///health",
    ] {
        assert!(is_proxy_green_url(url), "proxy shape slipped through: {url}");
    }
}

#[test]
fn real_endpoints_are_not_flagged_as_proxies() {
    for url in [
        GOOD_URL,
        "https://llm.mumchimp.com/health",
        "https://notgithub.com/health",
        "https://github.com.evil.example/health",
        "https://api-github.com/health",
    ] {
        // github.com.evil.example is a different registrable domain and a real external host.
        assert!(!is_proxy_green_url(url), "real endpoint wrongly flagged: {url}");
    }
}

#[test]
fn contract_parser_rejects_proxy_zero_delta_and_malformed_contracts() {
    assert!(matches!(
        parse_and_validate_contract_presubmit(&contract_text(
            "https://api.github.com/repos/chidionyema/idp/commits/main",
            "m baseline=0 target=1"
        )),
        Err(PresubmitError::ProxyGreenSubstitution { .. })
    ));
    assert_eq!(
        parse_and_validate_contract_presubmit(&contract_text(GOOD_URL, "m baseline=1 target=1")),
        Err(PresubmitError::ZeroDeltaContract { metric: "m".to_string(), value: "1".to_string() })
    );
    assert!(matches!(
        parse_and_validate_contract_presubmit("accept: GET https://x.example/h expect 200 within 30m\n"),
        Err(PresubmitError::InvalidShipContract { .. })
    ));
    assert!(matches!(
        parse_and_validate_contract_presubmit("SHIP-CONTRACT\naccept: GET nonsense\n"),
        Err(PresubmitError::InvalidShipContract { .. })
    ));
    assert!(matches!(
        parse_and_validate_contract_presubmit(&contract_text(GOOD_URL, "m baseline=0")),
        Err(PresubmitError::InvalidShipContract { .. })
    ));
    let no_debug = "SHIP-CONTRACT\naccept: GET https://llm.meridianlabs.cloud/health expect 200 within 30m\noptimus: m baseline=0 target=1\nfailure-classes: x\n";
    assert!(matches!(
        parse_and_validate_contract_presubmit(no_debug),
        Err(PresubmitError::InvalidShipContract { .. })
    ));
    let sc = good_contract();
    assert_eq!(sc.accept_url, GOOD_URL);
    assert_eq!(sc.baseline, "0");
    assert_eq!(sc.target, "1");
}

#[test]
fn parity_rejects_unknown_missing_unmet_and_non_executable() {
    let sc = good_contract();
    let ok_bin: &[(&str, u32)] = &[("bin/a", 0o755)];
    assert_eq!(verify_presubmit_parity(&sc, "optimus.m=1", true, ok_bin), Ok(1));
    assert!(matches!(
        verify_presubmit_parity(&sc, "optimus.m=UNKNOWN", true, ok_bin),
        Err(PresubmitError::OptimusMeasureUnknown { .. })
    ));
    assert!(matches!(
        verify_presubmit_parity(&sc, "optimus.m=unknown", true, ok_bin),
        Err(PresubmitError::OptimusMeasureUnknown { .. })
    ));
    assert!(matches!(
        verify_presubmit_parity(&sc, "no metric here", true, ok_bin),
        Err(PresubmitError::OptimusMeasureUnknown { .. })
    ));
    assert!(matches!(
        verify_presubmit_parity(&sc, "optimus.m=banana", true, ok_bin),
        Err(PresubmitError::OptimusMeasureUnknown { .. })
    ));
    assert_eq!(
        verify_presubmit_parity(&sc, "optimus.m=0", true, ok_bin),
        Err(PresubmitError::OptimusTargetNotMet { metric: "m".to_string(), observed: 0, target: 1 })
    );
    assert_eq!(
        verify_presubmit_parity(&sc, "optimus.m=1", true, &[("bin/ok", 0o755), ("bin/bad", 0o644)]),
        Err(PresubmitError::NonExecutableBinScript { path: "bin/bad".to_string(), mode: 0o644 })
    );
    // lower-is-better direction
    let lower = parse_and_validate_contract_presubmit(&contract_text(GOOD_URL, "lat baseline=900 target=100"))
        .expect("lower-is-better contract parses");
    assert_eq!(verify_presubmit_parity(&lower, "optimus.lat=80", false, ok_bin), Ok(80));
    assert!(matches!(
        verify_presubmit_parity(&lower, "optimus.lat=101", false, ok_bin),
        Err(PresubmitError::OptimusTargetNotMet { .. })
    ));
}

fn round(status: u16, zone: &str, sha: &str, ms: u32) -> BlackboxProbeRound {
    BlackboxProbeRound {
        http_status: status,
        zone_header: zone.to_string(),
        deployed_sha: sha.to_string(),
        latency_ms: ms,
    }
}

fn good_round(ms: u32) -> BlackboxProbeRound {
    round(200, "zone-b-cloudflare-edge", "ea201e7", ms)
}

fn ledger() -> BudgetLedger {
    BudgetLedger::new("GBP", BillingClass::ApiCredit, 1_000)
}

fn failure_reason(v: ReleaseVerdict) -> String {
    match v {
        ReleaseVerdict::AutoRecoveryTriggered(l) => l.reason,
        ReleaseVerdict::Operational { .. } => "OPERATIONAL".to_string(),
    }
}

#[test]
fn three_of_three_good_probes_settle_operational_without_touching_the_epoch() {
    let mut l = ledger();
    let rounds = vec![good_round(42), good_round(48), good_round(45)];
    assert_eq!(
        settle_or_auto_recover("idp#1", "ea201e7", "9b4d68d", 250, &rounds, &mut l),
        ReleaseVerdict::Operational { commit_sha: "ea201e7".to_string(), rounds_passed: 3, p99_ms: 48 }
    );
    assert_eq!(l.revocation_epoch, 1);
}

#[test]
fn each_failed_probe_property_freezes_and_bumps_the_epoch() {
    let cases: Vec<(&str, Vec<BlackboxProbeRound>, &str)> = vec![
        ("two rounds", vec![good_round(1), good_round(1)], "INSUFFICIENT_BLACKBOX_ROUNDS:2"),
        ("zero rounds", vec![], "INSUFFICIENT_BLACKBOX_ROUNDS:0"),
        ("http 525", vec![good_round(1), round(525, "zone-b-cloudflare-edge", "ea201e7", 1), good_round(1)], "ROUND_2_HTTP_525"),
        ("wrong zone", vec![good_round(1), good_round(1), round(200, "origin-dead", "ea201e7", 1)], "ROUND_3_WRONG_ZONE:origin-dead"),
        ("sha mismatch", vec![round(200, "zone-b-cloudflare-edge", "deadbee", 1), good_round(1), good_round(1)], "ROUND_1_SHA_MISMATCH:deadbee"),
        ("slo breach", vec![good_round(1), good_round(251), good_round(1)], "ROUND_2_SLO_BREACH:251ms"),
    ];
    for (name, rounds, want) in cases {
        let mut l = ledger();
        let verdict = settle_or_auto_recover("idp#1", "ea201e7", "9b4d68d", 250, &rounds, &mut l);
        match verdict {
            ReleaseVerdict::AutoRecoveryTriggered(lease) => {
                assert_eq!(lease.reason, want, "{name}");
                assert!(lease.dof_freeze_active, "{name}");
                assert_eq!(lease.new_revocation_epoch, 2, "{name}");
                assert_eq!(lease.rollback_sha, "9b4d68d", "{name}");
                assert_eq!(lease.issue, "idp#1", "{name}");
            }
            other => panic!("{name}: expected recovery, got {other:?}"),
        }
        assert_eq!(l.revocation_epoch, 2, "{name}");
    }
}

#[test]
fn a_sla_exactly_at_the_limit_passes_and_one_over_fails() {
    let mut l = ledger();
    let at = vec![good_round(250), good_round(250), good_round(250)];
    assert_eq!(failure_reason(settle_or_auto_recover("i", "ea201e7", "x", 250, &at, &mut l)), "OPERATIONAL");
    let over = vec![good_round(250), good_round(250), good_round(251)];
    assert_eq!(
        failure_reason(settle_or_auto_recover("i", "ea201e7", "x", 250, &over, &mut l)),
        "ROUND_3_SLO_BREACH:251ms"
    );
}

#[test]
fn a_failed_canary_fences_workers_still_holding_the_old_epoch() {
    let mut l = ledger();
    let stale_epoch = l.revocation_epoch;
    let stale_token = l.fencing_token;
    let bad = vec![round(525, "origin-dead", "none", 1200); 3];
    assert!(matches!(
        settle_or_auto_recover("idp#1", "ea201e7", "9b4d68d", 250, &bad, &mut l),
        ReleaseVerdict::AutoRecoveryTriggered(_)
    ));
    assert_eq!(
        l.reserve("stale", "lane", BillingClass::ApiCredit, 10, "GBP", "nonce-stale-01", stale_epoch, stale_token),
        Err(LedgerError::StaleEpoch { got: 1, current: 2 })
    );
}
