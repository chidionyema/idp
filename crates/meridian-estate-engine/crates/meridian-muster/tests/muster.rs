use meridian_muster::*;

fn unit(id: &str, cost: i64, passed: bool) -> FractalNode {
    FractalNode::Unit {
        unit_id: id.to_string(),
        cost_minor_units: cost,
        passed,
    }
}

fn spec(f: LegionFormation) -> FormationSpec {
    canonical_eight_formations()
        .into_iter()
        .find(|s| s.formation == f)
        .expect("formation present in canonical set")
}

#[test]
fn eight_formations_have_unique_ids_and_declared_kernels() {
    let all = canonical_eight_formations();
    assert_eq!(all.len(), 8);
    let ids: Vec<u8> = all.iter().map(|s| s.id).collect();
    assert_eq!(ids, (1..=8).collect::<Vec<u8>>());
    for s in &all {
        assert!(!s.kernels.is_empty(), "{:?} has no kernel", s.formation);
        assert!(s.max_fanout >= 1 && s.max_recursion_depth >= 1);
        // K3 (debate) and K4 (bracket) are meaningless without an independent judge.
        let judged = s.kernels.contains(&ExecutionKernel::K3Debate)
            || s.kernels.contains(&ExecutionKernel::K4Bracket);
        if judged {
            assert!(
                s.requires_independent_judge,
                "{:?} lacks an independent judge",
                s.formation
            );
        }
    }
}

#[test]
fn every_formation_executes_and_its_chain_verifies() {
    for s in canonical_eight_formations() {
        let nodes: Vec<FractalNode> = (0..s.max_fanout.min(3))
            .map(|i| unit(&format!("u{i}"), 10, true))
            .collect();
        let chain = execute_formation_fractal("run-1", &s, &nodes, 1_000, 1)
            .unwrap_or_else(|e| panic!("{:?} failed: {e:?}", s.formation));
        assert_eq!(chain.len(), nodes.len());
        assert_eq!(verify_receipt_chain(&chain), Ok(()), "{:?}", s.formation);
    }
}

#[test]
fn tampered_receipt_is_detected_at_its_index() {
    let s = spec(LegionFormation::Phalanx);
    let nodes = vec![
        unit("a", 10, true),
        unit("b", 20, true),
        unit("c", 30, true),
    ];
    let good = execute_formation_fractal("run-t", &s, &nodes, 1_000, 1).expect("executes");
    assert_eq!(verify_receipt_chain(&good), Ok(()));

    let mut cost = good.clone();
    cost[1].cost_minor_units += 1;
    assert_eq!(
        verify_receipt_chain(&cost),
        Err(MusterError::ChainTampered { index: 1 })
    );

    let mut flipped = good.clone();
    flipped[2].ok = !flipped[2].ok;
    assert_eq!(
        verify_receipt_chain(&flipped),
        Err(MusterError::ChainTampered { index: 2 })
    );

    let dropped_head: Vec<StepReceipt> = good[1..].to_vec();
    assert_eq!(
        verify_receipt_chain(&dropped_head),
        Err(MusterError::ChainTampered { index: 0 })
    );
}

#[test]
fn fanout_over_cap_is_refused_before_any_work() {
    let s = spec(LegionFormation::Phalanx);
    let nodes: Vec<FractalNode> = (0..s.max_fanout + 1)
        .map(|i| unit(&format!("u{i}"), 1, true))
        .collect();
    assert_eq!(
        execute_formation_fractal("run-f", &s, &nodes, 1_000, 1),
        Err(MusterError::RunawayFanout {
            requested: 9,
            max_fanout: 8
        })
    );
}

#[test]
fn recursion_over_depth_cap_is_refused() {
    let s = spec(LegionFormation::Phalanx); // max depth 2
    let deep = vec![FractalNode::SubFormation {
        formation: LegionFormation::Phalanx,
        children: vec![FractalNode::SubFormation {
            formation: LegionFormation::Phalanx,
            children: vec![FractalNode::SubFormation {
                formation: LegionFormation::Phalanx,
                children: vec![unit("leaf", 1, true)],
            }],
        }],
    }];
    assert_eq!(
        execute_formation_fractal("run-d", &s, &deep, 1_000, 1),
        Err(MusterError::RecursionDepthExceeded {
            depth: 3,
            max_depth: 2
        })
    );
}

#[test]
fn budget_ceiling_stops_the_run() {
    let s = spec(LegionFormation::Pipeline);
    let nodes = vec![
        unit("a", 100, true),
        unit("b", 100, true),
        unit("c", 100, true),
    ];
    assert_eq!(
        execute_formation_fractal("run-b", &s, &nodes, 250, 1),
        Err(MusterError::BudgetExhausted {
            spent: 300,
            ceiling: 250
        })
    );
}

#[test]
fn nested_formation_chain_is_one_verifiable_chain() {
    let s = spec(LegionFormation::Centurion);
    let nodes = vec![
        unit("plan", 5, true),
        FractalNode::SubFormation {
            formation: LegionFormation::Phalanx,
            children: vec![unit("w1", 7, true), unit("w2", 9, true)],
        },
    ];
    let chain = execute_formation_fractal("run-n", &s, &nodes, 1_000, 1).expect("executes");
    assert_eq!(chain.len(), 3);
    assert_eq!(verify_receipt_chain(&chain), Ok(()));
    assert_eq!(chain.iter().map(|r| r.cost_minor_units).sum::<i64>(), 21);
}

#[test]
fn failed_unit_fails_every_gated_formation() {
    // Sniper is K1+K5, Phalanx is K2+K5: a red unit must never come back as an Ok chain.
    for f in [
        LegionFormation::Sniper,
        LegionFormation::Phalanx,
        LegionFormation::Pipeline,
    ] {
        let s = spec(f);
        let nodes = vec![unit("good", 1, true), unit("bad", 1, false)];
        let r = execute_formation_fractal("run-g", &s, &nodes[..s.max_fanout.min(2)], 1_000, 1);
        if s.max_fanout >= 2 {
            assert!(
                matches!(r, Err(MusterError::StepReceiptFailed { .. })),
                "{f:?} returned {r:?} for a failed unit"
            );
        }
    }
    // Sniper's single node case.
    let s = spec(LegionFormation::Sniper);
    assert!(matches!(
        execute_formation_fractal("run-s", &s, &[unit("bad", 1, false)], 100, 1),
        Err(MusterError::StepReceiptFailed { .. })
    ));
}

fn score(success: f64, cost: f64, lat: f64, audit: f64, up: f64, age: f64) -> LegionScoreOutput {
    score_legion(&LegionScoreInput {
        legion: "t".into(),
        success_rate: success,
        cost_efficiency: cost,
        latency_score: lat,
        audit_integrity: audit,
        uptime: up,
        proof_age_hours: age,
    })
}

#[test]
fn scorecard_weights_are_30_20_20_15_15() {
    assert_eq!(score(1.0, 0.0, 0.0, 0.0, 0.0, 0.0).composite, 0.30);
    assert_eq!(score(0.0, 1.0, 0.0, 0.0, 0.0, 0.0).composite, 0.20);
    assert_eq!(score(0.0, 0.0, 1.0, 0.0, 0.0, 0.0).composite, 0.20);
    assert_eq!(score(0.0, 0.0, 0.0, 1.0, 0.0, 0.0).composite, 0.15);
    assert_eq!(score(0.0, 0.0, 0.0, 0.0, 1.0, 0.0).composite, 0.15);
}

#[test]
fn scorecard_staleness_halves_and_demotes() {
    let fresh = score(1.0, 1.0, 1.0, 1.0, 1.0, 1.0);
    assert_eq!(
        (fresh.composite, fresh.proof_stale, fresh.status.as_str()),
        (1.0, false, "active")
    );
    let at_limit = score(1.0, 1.0, 1.0, 1.0, 1.0, 24.0);
    assert!(!at_limit.proof_stale, "24.0h is not older than 24h");
    let stale = score(1.0, 1.0, 1.0, 1.0, 1.0, 24.01);
    assert_eq!(
        (stale.composite, stale.proof_stale, stale.status.as_str()),
        (0.5, true, "shadow")
    );
}

#[test]
fn scorecard_threshold_is_exactly_point_six() {
    assert_eq!(score(1.0, 1.0, 0.5, 0.0, 0.0, 0.0).status, "active"); // 0.60
    assert_eq!(score(1.0, 1.0, 0.45, 0.0, 0.0, 0.0).status, "shadow"); // 0.59
}
