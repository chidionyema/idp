use mitp_core_switching_gate::{
    Digest32, EffectClass, EnvelopeState, HysteresisPolicy, HysteresisSequencer, PriorityMicros,
    SwitchingDecision, ValuationProposal,
};
use proptest::prelude::*;

fn digest(id: u8) -> Digest32 {
    [id; 32]
}

#[derive(Clone, Debug)]
enum Op {
    Tick(u64),
    Propose { env_idx: usize, prio: i64, unsupported: bool },
    Admit(usize),
    DispatchP(usize),
    Preempt { challenger: usize, incumbent: usize },
    Reconcile { env_idx: usize, spend_pct: u8 },
    Settle { env_idx: usize, spend_pct: u8 },
    ReStage(usize),
}

fn op_strategy() -> impl Strategy<Value = Op> {
    prop_oneof![
        (1u64..=3).prop_map(Op::Tick),
        (0usize..4, prop::sample::select(vec![0i64, 20, 70, 100, 150]), any::<bool>()).prop_map(
            |(env_idx, prio, unsupported)| Op::Propose {
                env_idx,
                prio,
                unsupported,
            }
        ),
        (0usize..4).prop_map(Op::Admit),
        (0usize..4).prop_map(Op::DispatchP),
        (0usize..4, 0usize..4).prop_map(|(challenger, incumbent)| Op::Preempt {
            challenger,
            incumbent,
        }),
        (0usize..4, 0u8..=100).prop_map(|(env_idx, spend_pct)| Op::Reconcile {
            env_idx,
            spend_pct,
        }),
        (0usize..4, 0u8..=100).prop_map(|(env_idx, spend_pct)| Op::Settle {
            env_idx,
            spend_pct,
        }),
        (0usize..4).prop_map(Op::ReStage),
    ]
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(512))]

    #[test]
    fn switching_gate_preserves_all_five_tla_invariants(ops in prop::collection::vec(op_strategy(), 1..120)) {
        let mandate = digest(0xAA);
        let policy = HysteresisPolicy {
            max_active_slots: 1,
            admit_floor: PriorityMicros(20),
            base_deadband: PriorityMicros(15),
            confirm_window_ms: 1,
            min_dwell_ms: 2,
            class_inertia_r: PriorityMicros(10),
            class_inertia_i: PriorityMicros(20),
            class_inertia_c: PriorityMicros(40),
            class_inertia_p_pre_dispatch: PriorityMicros(60),
        };
        let mut seq = HysteresisSequencer::new(mandate, 4, policy).unwrap();

        let ids = [digest(1), digest(2), digest(3), digest(4)];
        seq.register_staged_envelope(ids[0], mandate, EffectClass::ReadEpistemic, 3).unwrap();
        seq.register_staged_envelope(ids[1], mandate, EffectClass::ExternalCompensatable, 3).unwrap();
        seq.register_staged_envelope(ids[2], mandate, EffectClass::ExternalPivot, 3).unwrap();
        // ids[3] belongs to an external/unsealed mandate H' -> must escalate to Trusted Summary Card
        seq.register_staged_envelope(ids[3], digest(0xBB), EffectClass::ReadEpistemic, 1).unwrap();

        seq.assert_invariants();

        for op in ops {
            let prev_epoch = seq.revocation_epoch;
            match op {
                Op::Tick(dt) => {
                    let next = seq.now_ms + dt;
                    seq.advance_time(next).unwrap();
                }
                Op::Propose { env_idx, prio, unsupported } => {
                    let target = ids[env_idx];
                    let parent = seq.envelopes[&target].parent_mandate_digest;
                    let proposal = ValuationProposal {
                        target_envelope_digest: target,
                        parent_mandate_digest: parent,
                        priority: PriorityMicros(prio),
                        est_compensation_minor: 0,
                        computed_at_ms: seq.now_ms,
                        staleness_ttl_ms: 2,
                        provenance_digest: digest(0xEE),
                        unsupported_constraints: unsupported,
                    };
                    seq.submit_valuation(proposal).unwrap();
                }
                Op::Admit(idx) => {
                    let id = ids[idx];
                    let was_fresh = seq.envelopes[&id]
                        .latest_proposal
                        .as_ref()
                        .map(|p| p.is_fresh(seq.now_ms) && !p.unsupported_constraints)
                        .unwrap_or(false);
                    let decision = seq.evaluate_and_apply_switch(id, None).unwrap();
                    if matches!(decision, SwitchingDecision::AdmitFromHeadroom { .. }) {
                        prop_assert!(was_fresh, "NoStaleAdmissionOrSwitch violated on admit");
                        prop_assert_ne!(id, ids[3], "External mandate must never self-admit");
                    }
                    if id == ids[3] && was_fresh {
                        let p = seq.envelopes[&id].latest_proposal.as_ref().unwrap();
                        if p.priority >= PriorityMicros(20) {
                            prop_assert_eq!(
                                decision,
                                SwitchingDecision::SurfaceTrustedSummaryCard { staged_digest: id }
                            );
                        }
                    }
                }
                Op::DispatchP(idx) => {
                    let _ = seq.dispatch_class_p(ids[idx]);
                }
                Op::Preempt { challenger, incumbent } => {
                    let j = ids[challenger];
                    let i = ids[incumbent];
                    let j_fresh = seq.envelopes[&j]
                        .latest_proposal
                        .as_ref()
                        .map(|p| p.is_fresh(seq.now_ms) && !p.unsupported_constraints)
                        .unwrap_or(false);
                    let decision = seq.evaluate_and_apply_switch(j, Some(i)).unwrap();
                    if matches!(decision, SwitchingDecision::PreemptAndDrain { .. }) {
                        prop_assert!(j_fresh, "NoStaleAdmissionOrSwitch violated on preempt");
                        prop_assert!(!seq.ever_dispatched_p.contains(&i), "Dispatched Class P pre-empted");
                    }
                }
                Op::Reconcile { env_idx, spend_pct } => {
                    let id = ids[env_idx];
                    if seq.envelopes[&id].state == EnvelopeState::Quarantined {
                        let locked = seq.envelopes[&id].quarantined_minor;
                        let spend = (locked * (spend_pct as u64)) / 100;
                        seq.reconcile_quarantined(id, spend).unwrap();
                    }
                }
                Op::Settle { env_idx, spend_pct } => {
                    let id = ids[env_idx];
                    if matches!(
                        seq.envelopes[&id].state,
                        EnvelopeState::Active | EnvelopeState::DispatchedP
                    ) {
                        let locked = seq.envelopes[&id].reserved_minor;
                        let spend = (locked * (spend_pct as u64)) / 100;
                        seq.settle_active(id, spend).unwrap();
                    }
                }
                Op::ReStage(idx) => {
                    let _ = seq.restage_reconciled(ids[idx]);
                }
            }

            // Action Property: MonotonicEpoch
            prop_assert!(seq.revocation_epoch >= prev_epoch, "MonotonicEpoch violated");
            // All 5 State Safety Invariants
            seq.assert_invariants();
        }
    }
}

#[test]
fn pending_drain_blocks_lane_theft_by_cheaper_candidate() {
    let mandate = digest(0xAA);
    let policy = HysteresisPolicy {
        max_active_slots: 1,
        admit_floor: PriorityMicros(20),
        base_deadband: PriorityMicros(15),
        confirm_window_ms: 1,
        min_dwell_ms: 2,
        class_inertia_r: PriorityMicros(10),
        class_inertia_i: PriorityMicros(20),
        class_inertia_c: PriorityMicros(40),
        class_inertia_p_pre_dispatch: PriorityMicros(60),
    };
    let mut seq = HysteresisSequencer::new(mandate, 4, policy).unwrap();
    let e1 = digest(1);
    let e2 = digest(2);
    let e3 = digest(3);
    seq.register_staged_envelope(e1, mandate, EffectClass::ReadEpistemic, 3).unwrap();
    seq.register_staged_envelope(e2, mandate, EffectClass::ReadEpistemic, 3).unwrap();
    seq.register_staged_envelope(e3, mandate, EffectClass::ReadEpistemic, 1).unwrap();

    // Admit e1 at t=0 (free=1)
    seq.submit_valuation(ValuationProposal {
        target_envelope_digest: e1,
        parent_mandate_digest: mandate,
        priority: PriorityMicros(25),
        est_compensation_minor: 0,
        computed_at_ms: 0,
        staleness_ttl_ms: 10,
        provenance_digest: digest(9),
        unsupported_constraints: false,
    }).unwrap();
    assert_eq!(
        seq.evaluate_and_apply_switch(e1, None).unwrap(),
        SwitchingDecision::AdmitFromHeadroom { challenger_digest: e1 }
    );

    // Propose e2 with high priority at t=1, confirm window holds at t=2 (also satisfies min_dwell=2)
    seq.advance_time(1).unwrap();
    seq.submit_valuation(ValuationProposal {
        target_envelope_digest: e2,
        parent_mandate_digest: mandate,
        priority: PriorityMicros(100),
        est_compensation_minor: 0,
        computed_at_ms: 1,
        staleness_ttl_ms: 10,
        provenance_digest: digest(9),
        unsupported_constraints: false,
    }).unwrap();
    seq.advance_time(2).unwrap();

    // Preempt e1 -> e2 enters PENDING_DRAIN (free=1 < cost_e2=3)
    let dec = seq.evaluate_and_apply_switch(e2, Some(e1)).unwrap();
    assert!(matches!(
        dec,
        SwitchingDecision::PreemptAndDrain { fast_path_admitted: false, .. }
    ));
    assert_eq!(seq.envelopes[&e2].state, EnvelopeState::PendingDrain);
    assert_eq!(seq.reserved_slots(), 1);

    // Attempt lane theft by cheap e3 (cost=1 <= free=1): MUST HOLD because e2 holds the slot!
    seq.submit_valuation(ValuationProposal {
        target_envelope_digest: e3,
        parent_mandate_digest: mandate,
        priority: PriorityMicros(90),
        est_compensation_minor: 0,
        computed_at_ms: 2,
        staleness_ttl_ms: 10,
        provenance_digest: digest(9),
        unsupported_constraints: false,
    }).unwrap();
    assert_eq!(
        seq.evaluate_and_apply_switch(e3, None).unwrap(),
        SwitchingDecision::HoldCurrent
    );

    // Reconcile e1 with spend=1 -> residual=2, next_pool=3 -> e2 atomically becomes ACTIVE
    seq.reconcile_quarantined(e1, 1).unwrap();
    assert_eq!(seq.envelopes[&e2].state, EnvelopeState::Active);
    assert_eq!(seq.free_minor, 0);
    assert_eq!(seq.spent_minor, 1);
    seq.assert_invariants();
}
