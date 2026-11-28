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
        matches!(r, Ok(FlowDecision::ImplementNew)),
        "declared-but-unverified route must not be reused"
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
