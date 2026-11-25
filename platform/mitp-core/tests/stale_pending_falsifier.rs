use mitp_core_switching_gate::{Digest32, EffectClass, EnvelopeState, HysteresisPolicy, HysteresisSequencer, PriorityMicros, SwitchingDecision, ValuationProposal};

fn digest(id: u8) -> Digest32 { [id; 32] }

#[test]
fn reconciliation_must_not_activate_expired_pinned_challenger() {
    let mandate = digest(0xaa);
    let mut seq = HysteresisSequencer::new(mandate, 4, HysteresisPolicy {
        max_active_slots: 1, admit_floor: PriorityMicros(20), base_deadband: PriorityMicros(15),
        confirm_window_ms: 1, min_dwell_ms: 2, class_inertia_r: PriorityMicros(10),
        class_inertia_i: PriorityMicros(20), class_inertia_c: PriorityMicros(40),
        class_inertia_p_pre_dispatch: PriorityMicros(60),
    }).unwrap();
    let i = digest(1);
    let j = digest(2);
    seq.register_staged_envelope(i, mandate, EffectClass::ReadEpistemic, 3).unwrap();
    seq.register_staged_envelope(j, mandate, EffectClass::ReadEpistemic, 3).unwrap();
    let proposal = |target, priority, at, ttl| ValuationProposal {
        target_envelope_digest: target, parent_mandate_digest: mandate,
        priority: PriorityMicros(priority), est_compensation_minor: 0,
        computed_at_ms: at, staleness_ttl_ms: ttl,
        provenance_digest: digest(9), unsupported_constraints: false,
    };
    seq.submit_valuation(proposal(i, 25, 0, 10)).unwrap();
    assert_eq!(seq.evaluate_and_apply_switch(i, None).unwrap(), SwitchingDecision::AdmitFromHeadroom { challenger_digest: i });
    seq.advance_time(1).unwrap();
    seq.submit_valuation(proposal(j, 100, 1, 2)).unwrap();
    seq.advance_time(2).unwrap();
    assert!(matches!(seq.evaluate_and_apply_switch(j, Some(i)).unwrap(), SwitchingDecision::PreemptAndDrain { fast_path_admitted: false, .. }));
    assert_eq!(seq.envelopes[&j].state, EnvelopeState::PendingDrain);
    seq.advance_time(4).unwrap();
    assert!(!seq.envelopes[&j].latest_proposal.as_ref().unwrap().is_fresh(seq.now_ms));
    seq.reconcile_quarantined(i, 1).unwrap();
    assert_eq!(seq.envelopes[&j].state, EnvelopeState::Staged, "expired challenger must be restaged, never activated");
    assert_eq!(seq.free_minor, 3);
    assert_eq!(seq.spent_minor, 1);
    seq.assert_invariants();
}
