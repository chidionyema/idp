//! Unified `meridian-army` Binary: FLOW -> DOF -> LEGION (8 Formations) -> KARMA.

use meridian_dof::{
    ActionCategory, ActionRequest, DofLeaseEngine, DofLevel, DualProbeReading, ProbeStatus,
};
use meridian_flow::{execute_flow_end_to_end, EstateCapability, FlowDecision, FlowError};
use meridian_karma::KarmaProjection;
use meridian_muster::{
    canonical_eight_formations, score_legion, FractalNode, LegionFormation, LegionScoreInput,
};
use std::process::ExitCode;

fn main() -> ExitCode {
    let mut dof = DofLeaseEngine::zone_b_default();
    let mut karma = KarmaProjection::default();

    let registry = vec![EstateCapability {
        id: "zoneb.phalanx.parallel-patch".to_string(),
        keywords: vec!["parallel".to_string(), "patch".to_string()],
        target_paths: vec!["crates/meridian-muster/src/lib.rs".to_string()],
        default_formation: LegionFormation::Phalanx,
        readiness_verified: true,
    }];

    // 1. Verify all 8 formations are registered as data compositions over K1-K5
    let all_eight = canonical_eight_formations();
    let eight_ok = all_eight.len() == 8;

    // 2. DOF outage -> L2 blocks normal FLOW task mutation ("note and move on" impossible)
    dof.evaluate_probe(&DualProbeReading {
        component_id: "ROUTER-EDGE-01".to_string(),
        method_a: ProbeStatus::Fail,
        method_b: ProbeStatus::Fail,
    });
    let nodes = vec![
        FractalNode::Unit {
            unit_id: "u1".to_string(),
            cost_minor_units: 100,
            passed: true,
        },
        FractalNode::Unit {
            unit_id: "u2".to_string(),
            cost_minor_units: 100,
            passed: true,
        },
    ];
    let blocked_in_l2 = matches!(
        execute_flow_end_to_end(
            "INS-BLOCKED",
            "run parallel patch",
            "urn:aid:worker-1",
            "urn:aid:oracle-1",
            &registry,
            dof.lease_epoch,
            &mut dof,
            &mut karma,
            &nodes,
            500,
        ),
        Err(FlowError::DofRefused(_))
    );

    // 3. Complete 3 prescribed ROUTER-EDGE-01 repair steps + 3 consecutive passes -> L0 restores
    for (step, file) in ["wrangler.toml", "routes.rs", "health.rs"].iter().enumerate() {
        let _ = dof.authorize(&ActionRequest {
            tool_name: format!("repair.router.step{}", step + 1),
            category: ActionCategory::RepairStep,
            target_paths: vec![format!("platform/router-edge/{file}")],
            surface: "zone-b-worker".to_string(),
            claimed_lease_epoch: dof.lease_epoch,
            resolving_component: Some("ROUTER-EDGE-01".to_string()),
        });
    }
    for _ in 0..3 {
        dof.evaluate_probe(&DualProbeReading {
            component_id: "ROUTER-EDGE-01".to_string(),
            method_a: ProbeStatus::Pass,
            method_b: ProbeStatus::Pass,
        });
    }
    let restored_l0 = dof.active_level == DofLevel::L0FullLease;

    // 4. Positive control: FLOW reuses capability -> Phalanx executes -> Independent oracle settles KARMA
    let settled_ok = matches!(
        execute_flow_end_to_end(
            "INS-FLOW-01",
            "run parallel patch",
            "urn:aid:worker-1",
            "urn:aid:oracle-1",
            &registry,
            dof.lease_epoch,
            &mut dof,
            &mut karma,
            &nodes,
            500,
        ),
        Ok(FlowDecision::ReuseExisting {
            formation: LegionFormation::Phalanx,
            ..
        })
    );

    // 5. Negative control: Self-grading worker == oracle rejected by KARMA
    let self_grade_blocked = matches!(
        execute_flow_end_to_end(
            "INS-SELF-GRADE",
            "run parallel patch",
            "urn:aid:worker-1",
            "urn:aid:worker-1",
            &registry,
            dof.lease_epoch,
            &mut dof,
            &mut karma,
            &nodes,
            500,
        ),
        Err(FlowError::KarmaNotSettled { .. })
    );

    // 6. Scorecard staleness halving (>24h -> shadow)
    let stale_score = score_legion(&LegionScoreInput {
        legion: "phalanx".to_string(),
        success_rate: 1.0,
        cost_efficiency: 1.0,
        latency_score: 1.0,
        audit_integrity: 1.0,
        uptime: 1.0,
        proof_age_hours: 30.0,
    });
    let stale_demoted = stale_score.proof_stale && stale_score.status == "shadow";

    let ok = eight_ok
        && blocked_in_l2
        && restored_l0
        && settled_ok
        && self_grade_blocked
        && stale_demoted;
    println!(
        "optimus.estate.karma_dof_legion_flow_unified={}",
        if ok { 1 } else { 0 }
    );
    if ok {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(1)
    }
}
