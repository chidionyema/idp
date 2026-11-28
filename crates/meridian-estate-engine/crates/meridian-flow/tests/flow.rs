use meridian_dof::*;
use meridian_flow::*;
use meridian_karma::*;
use meridian_muster::*;

fn registry(verified: bool) -> Vec<EstateCapability> {
    vec![EstateCapability {
        id: "zoneb.phalanx.parallel-patch".into(),
        keywords: vec!["parallel".into(), "patch".into()],
        target_paths: vec!["crates/meridian-muster/src/lib.rs".into()],
        default_formation: LegionFormation::Phalanx,
        readiness_verified: verified,
    }]
}

fn units(n: usize, cost: i64, passed: bool) -> Vec<FractalNode> {
    (0..n)
        .map(|i| FractalNode::Unit {
            unit_id: format!("u{i}"),
            cost_minor_units: cost,
            passed,
        })
        .collect()
}

struct World {
    dof: DofLeaseEngine,
    karma: KarmaProjection,
}

fn world() -> World {
    World {
        dof: DofLeaseEngine::zone_b_default(),
        karma: KarmaProjection::default(),
    }
}

fn run(
    w: &mut World,
    id: &str,
    intent: &str,
    oracle: &str,
    reg: &[EstateCapability],
    nodes: &[FractalNode],
    budget: i64,
) -> Result<FlowDecision, FlowError> {
    execute_flow_end_to_end(
        id,
        intent,
        "urn:aid:worker-1",
        oracle,
        reg,
        w.dof.lease_epoch,
        &mut w.dof,
        &mut w.karma,
        nodes,
        budget,
    )
}

#[test]
fn matched_capability_is_reused_and_settled_by_an_independent_oracle() {
    let mut w = world();
    let r = run(
        &mut w,
        "I1",
        "run parallel patch",
        "urn:aid:oracle-1",
        &registry(true),
        &units(2, 100, true),
        500,
    );
    assert_eq!(
        r.expect("flow succeeds"),
        FlowDecision::ReuseExisting {
            capability_id: "zoneb.phalanx.parallel-patch".into(),
            formation: LegionFormation::Phalanx
        }
    );
    let o = &w.karma.obligations["I1"];
    assert_eq!(
        (o.state, o.verified_yield, o.money_minor_units),
        (ObligationState::Settled, true, Some(200))
    );
    assert!(w.karma.gaps.is_empty());
}

#[test]
fn intent_match_is_case_insensitive() {
    let mut w = world();
    let r = run(
        &mut w,
        "I1",
        "RUN PARALLEL PATCH",
        "urn:aid:oracle-1",
        &registry(true),
        &units(1, 1, true),
        10,
    );
    assert!(matches!(r, Ok(FlowDecision::ReuseExisting { .. })));
}

#[test]
fn unmatched_or_unverified_capability_means_implement_new_and_opens_no_debt() {
    let mut w = world();
    let r = run(
        &mut w,
        "I1",
        "rotate the moon",
        "urn:aid:oracle-1",
        &registry(true),
        &units(1, 1, true),
        10,
    );
    assert!(matches!(r, Ok(FlowDecision::ImplementNew)));
    let r = run(
        &mut w,
        "I2",
        "run parallel patch",
        "urn:aid:oracle-1",
        &registry(false),
        &units(1, 1, true),
        10,
    );
    assert!(
        matches!(r, Ok(FlowDecision::DeclaredNotVerified { .. })),
        "declared-but-unverified route must be reported as declared and must not be reused: {r:?}"
    );
    assert!(w.karma.obligations.is_empty());
}

#[test]
fn dof_outage_blocks_before_any_debt_or_work() {
    let mut w = world();
    w.dof.evaluate_probe(&DualProbeReading {
        component_id: "ROUTER-EDGE-01".into(),
        method_a: ProbeStatus::Fail,
        method_b: ProbeStatus::Fail,
    });
    let r = run(
        &mut w,
        "I1",
        "run parallel patch",
        "urn:aid:oracle-1",
        &registry(true),
        &units(2, 100, true),
        500,
    );
    assert!(matches!(r, Err(FlowError::DofRefused(_))));
    assert!(w.karma.obligations.is_empty());
}

#[test]
fn self_grading_worker_is_not_settled() {
    let mut w = world();
    let r = run(
        &mut w,
        "I1",
        "run parallel patch",
        "urn:aid:worker-1",
        &registry(true),
        &units(2, 100, true),
        500,
    );
    assert!(matches!(r, Err(FlowError::KarmaNotSettled { .. })));
    assert!(!w.karma.obligations["I1"].verified_yield);
}

#[test]
fn failed_unit_never_settles() {
    let mut w = world();
    let mut nodes = units(1, 10, true);
    nodes.extend(units(1, 10, false));
    let r = run(
        &mut w,
        "I1",
        "run parallel patch",
        "urn:aid:oracle-1",
        &registry(true),
        &nodes,
        500,
    );
    assert!(matches!(r, Err(FlowError::MusterFailed(_))), "got {r:?}");
    assert!(w.karma.unresolved_ids().contains(&"I1".to_string()) || w.karma.obligations.is_empty());
    assert!(!w
        .karma
        .obligations
        .get("I1")
        .map(|o| o.verified_yield)
        .unwrap_or(false));
}

#[test]
fn failed_unit_in_an_ungated_formation_never_settles_either() {
    let mut w = world();
    let reg = vec![EstateCapability {
        id: "zoneb.swarm".into(),
        keywords: vec!["swarm".into()],
        target_paths: vec![],
        default_formation: LegionFormation::Swarm, // K2 only, no K1/K5
        readiness_verified: true,
    }];
    let r = run(
        &mut w,
        "I1",
        "swarm it",
        "urn:aid:oracle-1",
        &reg,
        &units(2, 1, false),
        100,
    );
    assert!(matches!(r, Err(FlowError::MusterFailed(_))), "got {r:?}");
    assert!(!w
        .karma
        .obligations
        .get("I1")
        .map(|o| o.verified_yield)
        .unwrap_or(false));
}

#[test]
fn budget_overrun_is_a_muster_failure() {
    let mut w = world();
    let r = run(
        &mut w,
        "I1",
        "run parallel patch",
        "urn:aid:oracle-1",
        &registry(true),
        &units(2, 100, true),
        150,
    );
    assert!(matches!(
        r,
        Err(FlowError::MusterFailed(MusterError::BudgetExhausted { .. }))
    ));
}

#[test]
fn flow_cannot_reuse_an_instruction_id_to_launder_a_settled_debt() {
    let mut w = world();
    let ok = run(
        &mut w,
        "I1",
        "run parallel patch",
        "urn:aid:oracle-1",
        &registry(true),
        &units(1, 1, true),
        10,
    );
    assert!(ok.is_ok());
    let again = run(
        &mut w,
        "I1",
        "run parallel patch",
        "urn:aid:oracle-1",
        &registry(true),
        &units(1, 1, true),
        10,
    );
    assert!(
        again.is_err(),
        "second run under the same instruction id must be refused, got {again:?}"
    );
}

// ---- failure-mode hardening: each test below failed on the code that preceded it ----

#[test]
fn flow_does_not_invent_token_counts() {
    let mut w = world();
    let reg = registry(true);
    let nodes = units(2, 10, true);
    run(
        &mut w,
        "T1",
        "parallel patch",
        "urn:oracle",
        &reg,
        &nodes,
        100,
    )
    .unwrap();
    let o = &w.karma.obligations["T1"];
    assert_eq!(
        (o.tokens_in, o.tokens_out),
        (0, 0),
        "tokens were never measured, so none are recorded"
    );
    assert_eq!(o.money_minor_units, Some(20));
}

#[test]
fn an_empty_keyword_does_not_match_every_intent() {
    let mut reg = registry(true);
    reg[0].keywords = vec!["".into(), "  ".into()];
    let mut w = world();
    let d = run(
        &mut w,
        "K1",
        "something unrelated",
        "urn:oracle",
        &reg,
        &units(1, 1, true),
        10,
    )
    .unwrap();
    assert_eq!(d, FlowDecision::ImplementNew);
}

#[test]
fn keywords_match_without_regard_to_case() {
    let mut reg = registry(true);
    reg[0].keywords = vec!["PaTcH".into()];
    let mut w = world();
    let d = run(
        &mut w,
        "K2",
        "please PATCH this",
        "urn:oracle",
        &reg,
        &units(1, 1, true),
        10,
    )
    .unwrap();
    assert!(matches!(d, FlowDecision::ReuseExisting { .. }));
}

#[test]
fn no_work_is_not_settled_yield() {
    let mut w = world();
    let reg = registry(true);
    let r = run(&mut w, "E1", "parallel patch", "urn:oracle", &reg, &[], 100);
    assert!(r.is_err(), "an empty receipt chain proved nothing: {r:?}");
    assert!(!w
        .karma
        .obligations
        .get("E1")
        .map(|o| o.verified_yield)
        .unwrap_or(false));
}

#[test]
fn a_subformation_with_no_units_is_not_work_either() {
    let mut w = world();
    let reg = registry(true);
    let nodes = vec![FractalNode::SubFormation {
        formation: LegionFormation::Phalanx,
        children: vec![],
    }];
    let r = run(
        &mut w,
        "E2",
        "parallel patch",
        "urn:oracle",
        &reg,
        &nodes,
        100,
    );
    assert!(r.is_err(), "{r:?}");
    assert!(!w
        .karma
        .obligations
        .get("E2")
        .map(|o| o.verified_yield)
        .unwrap_or(false));
}

#[test]
fn a_failed_execution_leaves_a_failure_on_the_debt() {
    let mut w = world();
    let reg = registry(true);
    let r = run(
        &mut w,
        "F1",
        "parallel patch",
        "urn:oracle",
        &reg,
        &units(2, 1, false),
        100,
    );
    assert!(r.is_err());
    let o = &w.karma.obligations["F1"];
    assert!(!o.verified_yield);
    assert!(
        !o.open_ancestor_failures.is_empty(),
        "the debt must record why it is unpaid"
    );
}

#[test]
fn a_refused_acceptance_stops_before_any_work_runs() {
    let mut w = world();
    let reg = registry(true);
    let r = execute_flow_end_to_end(
        "B1",
        "parallel patch",
        "",
        "urn:oracle",
        &reg,
        w.dof.lease_epoch,
        &mut w.dof,
        &mut w.karma,
        &units(1, 1, true),
        10,
    );
    // Work costing more than the budget would fail in Muster if it ran; it must stop earlier.
    let r2 = execute_flow_end_to_end(
        "B2",
        "parallel patch",
        "",
        "urn:oracle",
        &reg,
        w.dof.lease_epoch,
        &mut w.dof,
        &mut w.karma,
        &units(1, 999, true),
        10,
    );
    assert!(
        matches!(r2, Err(FlowError::KarmaNotSettled { .. })),
        "work ran after a refused acceptance: {r2:?}"
    );
    assert!(r.is_err());
    assert!(w.karma.obligations.is_empty());
}

#[test]
fn a_decision_taken_before_an_outage_is_fenced_after_it() {
    let mut w = world();
    let reg = registry(true);
    let observed = w.dof.lease_epoch;
    w.dof.evaluate_probe(&DualProbeReading {
        component_id: "ROUTER-EDGE-01".into(),
        method_a: ProbeStatus::Fail,
        method_b: ProbeStatus::Fail,
    });
    // The lease moved while the caller was deciding; its stale epoch must not execute.
    let r = execute_flow_end_to_end(
        "S1",
        "parallel patch",
        "urn:aid:worker-1",
        "urn:oracle",
        &reg,
        observed,
        &mut w.dof,
        &mut w.karma,
        &units(1, 1, true),
        10,
    );
    assert!(
        matches!(r, Err(FlowError::DofRefused(ref e)) if e.directive == "STALE_LEASE_EPOCH_FENCED"),
        "{r:?}"
    );
    assert!(w.karma.obligations.is_empty());
}

#[test]
fn a_current_epoch_still_executes() {
    let mut w = world();
    let reg = registry(true);
    let r = run(
        &mut w,
        "S2",
        "parallel patch",
        "urn:oracle",
        &reg,
        &units(1, 1, true),
        10,
    );
    assert!(matches!(r, Ok(FlowDecision::ReuseExisting { .. })), "{r:?}");
}

// ---- live registry loading and the declared-route decision ----

mod registry {
    use meridian_flow::{discover, registry_from_json, FlowDecision, RegistryError};

    fn doc(records: &str) -> String {
        format!(r#"{{"records":[{records}]}}"#)
    }
    fn rec(id: &str, state: &str, path: &str) -> String {
        format!(r#"{{"id":"{id}","path":"{path}","health":{{"state":"{state}"}}}}"#)
    }

    #[test]
    fn a_declared_capability_is_reported_never_run() {
        let l = registry_from_json(&doc(&rec(
            "cap:intent/agent-invoke",
            "declared",
            "p/a.yaml",
        )))
        .unwrap();
        let d = discover(&l.capabilities, "please agent invoke the incident agent");
        assert_eq!(
            d,
            FlowDecision::DeclaredNotVerified {
                capability_id: "cap:intent/agent-invoke".into(),
                target_paths: vec!["p/a.yaml".into()],
            }
        );
    }

    #[test]
    fn a_verified_match_wins_over_a_declared_one() {
        let both = format!(
            "{},{}",
            rec("cap:tool/deploy-app", "declared", "a"),
            rec("cap:intent/deploy-app", "verified", "b")
        );
        let l = registry_from_json(&doc(&both)).unwrap();
        assert!(matches!(
            discover(&l.capabilities, "deploy app now"),
            FlowDecision::ReuseExisting { capability_id, .. } if capability_id == "cap:intent/deploy-app"
        ));
    }

    #[test]
    fn a_name_inside_another_word_does_not_match() {
        let l = registry_from_json(&doc(&rec("cap:tool/lint", "verified", "x"))).unwrap();
        assert_eq!(
            discover(&l.capabilities, "make a splinter"),
            FlowDecision::ImplementNew
        );
        assert!(matches!(
            discover(&l.capabilities, "run lint, please"),
            FlowDecision::ReuseExisting { .. }
        ));
    }

    #[test]
    fn a_short_name_is_skipped_by_name_and_does_not_poison_the_rest() {
        let both = format!(
            "{},{}",
            rec("cap:tool/ci", "verified", "x"),
            rec("cap:tool/gh-pr", "declared", "y")
        );
        let l = registry_from_json(&doc(&both)).unwrap();
        assert_eq!(l.capabilities.len(), 1);
        assert_eq!(l.skipped.len(), 1);
        assert!(l.skipped[0].contains("cap:tool/ci"));
    }

    #[test]
    fn a_record_without_an_id_is_named_not_dropped_silently() {
        let both = format!(
            r#"{{"path":"x"}},{}"#,
            rec("cap:tool/gh-pr", "declared", "y")
        );
        let l = registry_from_json(&doc(&both)).unwrap();
        assert_eq!(l.capabilities.len(), 1);
        assert_eq!(l.skipped, vec!["record[0]: no id".to_string()]);
    }

    #[test]
    fn an_unproven_state_is_not_ready() {
        for s in ["declared", "observed", "VERIFIED", ""] {
            let l = registry_from_json(&doc(&rec("cap:tool/gh-pr", s, "y"))).unwrap();
            assert!(
                !l.capabilities[0].readiness_verified,
                "state {s:?} must not be ready"
            );
        }
    }

    #[test]
    fn garbage_and_empty_registries_fail_closed() {
        assert!(matches!(
            registry_from_json("not json"),
            Err(RegistryError::Unparseable(_))
        ));
        assert_eq!(
            registry_from_json(r#"{"records":[]}"#).unwrap_err(),
            RegistryError::NoRecords
        );
        assert_eq!(
            registry_from_json(r#"{"x":1}"#).unwrap_err(),
            RegistryError::NoRecords
        );
    }
}
