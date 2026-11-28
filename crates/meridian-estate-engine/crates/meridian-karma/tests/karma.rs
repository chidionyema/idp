use meridian_karma::*;

fn ev(id: &str, ins: &str, agent: &str, parents: &[&str], payload: KarmaEventKind) -> KarmaEvent {
    KarmaEvent {
        event_id: id.to_string(),
        instruction_id: ins.to_string(),
        agent_urn: agent.to_string(),
        parent_event_ids: parents.iter().map(|p| p.to_string()).collect(),
        externally_verified_authority: true,
        payload,
    }
}

fn accept(id: &str, ins: &str, agent: &str) -> KarmaEvent {
    ev(
        id,
        ins,
        agent,
        &[],
        KarmaEventKind::InstructionAccepted {
            expected_outcome_digest: "exp".into(),
        },
    )
}

fn submit(id: &str, ins: &str, agent: &str, parent: &str, digest: &str) -> KarmaEvent {
    ev(
        id,
        ins,
        agent,
        &[parent],
        KarmaEventKind::YieldSubmitted {
            evidence_digest: digest.into(),
        },
    )
}

fn verify(id: &str, ins: &str, agent: &str, parent: &str, digest: &str) -> KarmaEvent {
    ev(
        id,
        ins,
        agent,
        &[parent],
        KarmaEventKind::YieldIndependentlyVerified {
            evidence_digest: digest.into(),
        },
    )
}

fn reasons(k: &KarmaProjection) -> Vec<&str> {
    k.gaps.iter().map(|g| g.reason.as_str()).collect()
}

#[test]
fn unverified_authority_issues_no_debt() {
    let mut k = KarmaProjection::default();
    let mut e = accept("a1", "I1", "urn:w");
    e.externally_verified_authority = false;
    k.apply(&e);
    assert!(k.obligations.is_empty());
    assert_eq!(reasons(&k), vec!["UNVERIFIED_EXTERNAL_AUTHORITY"]);
}

#[test]
fn out_of_order_parent_is_rejected_not_sorted() {
    let mut k = KarmaProjection::default();
    k.apply(&ev(
        "c1",
        "I1",
        "urn:w",
        &["a1"],
        KarmaEventKind::CostObserved {
            tokens_in: 1,
            tokens_out: 1,
            money_minor_units: None,
        },
    ));
    assert!(k.obligations.is_empty());
    assert_eq!(reasons(&k), vec!["CAUSAL_PARENT_NOT_YET_OBSERVED"]);
    // Arriving later does not retroactively apply the rejected event.
    k.apply(&accept("a1", "I1", "urn:w"));
    assert_eq!(k.obligations["I1"].tokens_in, 0);
}

#[test]
fn duplicate_event_is_ignored_and_not_double_counted() {
    let mut k = KarmaProjection::default();
    k.apply(&accept("a1", "I1", "urn:w"));
    let cost = ev(
        "c1",
        "I1",
        "urn:w",
        &["a1"],
        KarmaEventKind::CostObserved {
            tokens_in: 10,
            tokens_out: 5,
            money_minor_units: Some(7),
        },
    );
    k.apply(&cost);
    k.apply(&cost);
    let o = &k.obligations["I1"];
    assert_eq!(
        (o.tokens_in, o.tokens_out, o.money_minor_units),
        (10, 5, Some(7))
    );
    assert_eq!(reasons(&k), vec!["DUPLICATE_EVENT_IGNORED"]);
}

#[test]
fn independent_oracle_settles_exact_digest() {
    let mut k = KarmaProjection::default();
    k.apply(&accept("a1", "I1", "urn:w"));
    k.apply(&submit("s1", "I1", "urn:w", "a1", "d1"));
    assert_eq!(
        k.obligations["I1"].state,
        ObligationState::AwaitingIndependentYield
    );
    assert_eq!(k.unresolved_ids(), vec!["I1".to_string()]);
    k.apply(&verify("v1", "I1", "urn:o", "s1", "d1"));
    let o = &k.obligations["I1"];
    assert_eq!(
        (o.state, o.verified_yield),
        (ObligationState::Settled, true)
    );
    assert!(k.unresolved_ids().is_empty());
    assert!(k.gaps.is_empty());
}

#[test]
fn self_graded_yield_is_blocked() {
    let mut k = KarmaProjection::default();
    k.apply(&accept("a1", "I1", "urn:w"));
    k.apply(&submit("s1", "I1", "urn:w", "a1", "d1"));
    k.apply(&verify("v1", "I1", "urn:w", "s1", "d1"));
    assert!(!k.obligations["I1"].verified_yield);
    assert_eq!(
        k.obligations["I1"].state,
        ObligationState::AwaitingIndependentYield
    );
    assert_eq!(reasons(&k), vec!["SELF_GRADED_OR_UNLINKED_YIELD"]);
}

#[test]
fn oracle_for_a_different_digest_does_not_settle() {
    let mut k = KarmaProjection::default();
    k.apply(&accept("a1", "I1", "urn:w"));
    k.apply(&submit("s1", "I1", "urn:w", "a1", "d1"));
    k.apply(&verify("v1", "I1", "urn:o", "s1", "OTHER"));
    assert!(!k.obligations["I1"].verified_yield);
}

#[test]
fn handover_keeps_initial_agent_and_ancestral_failure_until_an_independent_falsifier() {
    let mut k = KarmaProjection::default();
    k.apply(&accept("a1", "I1", "urn:A"));
    k.apply(&ev(
        "f1",
        "I1",
        "urn:A",
        &["a1"],
        KarmaEventKind::AncestralFailure {
            ancestor_event_id: "F".into(),
            failure_class: "ruff:B905".into(),
        },
    ));
    k.apply(&ev(
        "h1",
        "I1",
        "urn:A",
        &["f1"],
        KarmaEventKind::OwnershipHandback {
            successor_agent_urn: "urn:B".into(),
        },
    ));
    let o = &k.obligations["I1"];
    assert_eq!(
        (o.initial_agent.as_str(), o.current_agent.as_str()),
        ("urn:A", "urn:B")
    );
    assert!(o.open_ancestor_failures.contains("F"));

    k.apply(&submit("s1", "I1", "urn:B", "h1", "d1"));
    k.apply(&verify("v1", "I1", "urn:C", "s1", "d1"));
    assert!(
        !k.obligations["I1"].verified_yield,
        "open ancestral failure blocks settlement"
    );

    for (id, who) in [("x1", "urn:A"), ("x2", "urn:B")] {
        k.apply(&ev(
            id,
            "I1",
            who,
            &["s1"],
            KarmaEventKind::CorrectionVerified {
                ancestor_event_id: "F".into(),
                falsifier_digest: "fd".into(),
            },
        ));
    }
    assert!(
        k.obligations["I1"].open_ancestor_failures.contains("F"),
        "self-certified correction is forbidden"
    );

    k.apply(&ev(
        "x3",
        "I1",
        "urn:C",
        &["s1"],
        KarmaEventKind::CorrectionVerified {
            ancestor_event_id: "F".into(),
            falsifier_digest: "fd".into(),
        },
    ));
    assert!(k.obligations["I1"].open_ancestor_failures.is_empty());
    k.apply(&verify("v2", "I1", "urn:C", "s1", "d1"));
    assert!(k.obligations["I1"].verified_yield);
    assert_eq!(
        k.obligations["I1"].initial_agent, "urn:A",
        "initial agent is never erased"
    );
}

#[test]
fn reaccepting_an_instruction_cannot_erase_its_debt() {
    let mut k = KarmaProjection::default();
    k.apply(&accept("a1", "I1", "urn:A"));
    k.apply(&ev(
        "f1",
        "I1",
        "urn:A",
        &["a1"],
        KarmaEventKind::AncestralFailure {
            ancestor_event_id: "F".into(),
            failure_class: "x".into(),
        },
    ));
    k.apply(&ev(
        "c1",
        "I1",
        "urn:A",
        &["f1"],
        KarmaEventKind::CostObserved {
            tokens_in: 9,
            tokens_out: 9,
            money_minor_units: Some(9),
        },
    ));
    // Same instruction, fresh event id, different agent.
    k.apply(&accept("a2", "I1", "urn:Z"));
    let o = &k.obligations["I1"];
    assert!(
        o.open_ancestor_failures.contains("F"),
        "ancestral failure was wiped by a re-accept"
    );
    assert_eq!(o.initial_agent, "urn:A");
    assert_eq!(o.tokens_in, 9, "cost was wiped by a re-accept");
}

// ---- failure-mode hardening: each test below failed on the code that preceded it ----

fn handback(id: &str, ins: &str, agent: &str, parent: &str, to: &str) -> KarmaEvent {
    ev(
        id,
        ins,
        agent,
        &[parent],
        KarmaEventKind::OwnershipHandback {
            successor_agent_urn: to.into(),
        },
    )
}

fn settled_world() -> KarmaProjection {
    let mut k = KarmaProjection::default();
    k.apply(&accept("a", "I1", "urn:A"));
    k.apply(&submit("s", "I1", "urn:A", "a", "D"));
    k.apply(&verify("v", "I1", "urn:V", "s", "D"));
    assert!(k.obligations["I1"].verified_yield);
    k
}

#[test]
fn resubmitting_after_settlement_is_refused() {
    let mut k = settled_world();
    let before = k.gaps.len();
    k.apply(&submit("s2", "I1", "urn:A", "v", "OTHER"));
    let o = &k.obligations["I1"];
    assert_eq!(o.state, ObligationState::Settled, "a settled debt must not reopen by resubmission");
    assert_eq!(o.submitted_digest.as_deref(), Some("D"));
    assert!(k.gaps.len() > before, "the refusal must be recorded, not silent");
}

#[test]
fn ancestral_failure_after_settlement_reopens_the_debt() {
    let mut k = settled_world();
    k.apply(&ev(
        "f",
        "I1",
        "urn:X",
        &["v"],
        KarmaEventKind::AncestralFailure {
            ancestor_event_id: "A1".into(),
            failure_class: "x".into(),
        },
    ));
    let o = &k.obligations["I1"];
    assert!(!o.verified_yield, "a settled debt with an open ancestral failure is not settled");
    assert_ne!(o.state, ObligationState::Settled);
}

#[test]
fn events_for_an_unknown_obligation_leave_a_gap() {
    let kinds = [
        KarmaEventKind::YieldSubmitted { evidence_digest: "D".into() },
        KarmaEventKind::YieldIndependentlyVerified { evidence_digest: "D".into() },
        KarmaEventKind::AncestralFailure { ancestor_event_id: "A".into(), failure_class: "c".into() },
        KarmaEventKind::OwnershipHandback { successor_agent_urn: "urn:B".into() },
        KarmaEventKind::CorrectionVerified { ancestor_event_id: "A".into(), falsifier_digest: "d".into() },
    ];
    for (i, kind) in kinds.into_iter().enumerate() {
        let mut k = KarmaProjection::default();
        k.apply(&ev(&format!("e{i}"), "NOPE", "urn:A", &[], kind.clone()));
        assert!(!k.gaps.is_empty(), "silent drop of {kind:?}");
    }
}

#[test]
fn a_former_custodian_cannot_certify_a_correction() {
    let mut k = KarmaProjection::default();
    k.apply(&accept("a", "I1", "urn:A"));
    k.apply(&ev(
        "f",
        "I1",
        "urn:A",
        &["a"],
        KarmaEventKind::AncestralFailure { ancestor_event_id: "F".into(), failure_class: "c".into() },
    ));
    k.apply(&handback("h1", "I1", "urn:A", "f", "urn:B"));
    k.apply(&handback("h2", "I1", "urn:B", "h1", "urn:C"));
    k.apply(&ev(
        "c",
        "I1",
        "urn:B",
        &["h2"],
        KarmaEventKind::CorrectionVerified { ancestor_event_id: "F".into(), falsifier_digest: "d".into() },
    ));
    assert!(
        k.obligations["I1"].open_ancestor_failures.contains("F"),
        "B held the debt and cannot certify its own correction"
    );
}

#[test]
fn the_initial_debtor_cannot_verify_the_yield_after_handing_it_back() {
    let mut k = KarmaProjection::default();
    k.apply(&accept("a", "I1", "urn:A"));
    k.apply(&handback("h", "I1", "urn:A", "a", "urn:B"));
    k.apply(&submit("s", "I1", "urn:B", "h", "D"));
    k.apply(&verify("v", "I1", "urn:A", "s", "D"));
    assert!(!k.obligations["I1"].verified_yield, "A is the debtor; A grading it is self-graded");
}

#[test]
fn blank_identities_are_refused() {
    let mut k = KarmaProjection::default();
    k.apply(&accept("a1", "", "urn:A"));
    k.apply(&accept("a2", "I1", ""));
    k.apply(&accept("", "I2", "urn:A"));
    assert!(k.obligations.is_empty(), "blank identity issued a debt: {:?}", k.obligations.keys());
    assert_eq!(k.gaps.len(), 3);
}

#[test]
fn negative_money_cannot_reduce_recorded_cost() {
    let mut k = KarmaProjection::default();
    k.apply(&accept("a", "I1", "urn:A"));
    k.apply(&ev(
        "c1",
        "I1",
        "urn:A",
        &["a"],
        KarmaEventKind::CostObserved { tokens_in: 0, tokens_out: 0, money_minor_units: Some(100) },
    ));
    k.apply(&ev(
        "c2",
        "I1",
        "urn:A",
        &["c1"],
        KarmaEventKind::CostObserved { tokens_in: 0, tokens_out: 0, money_minor_units: Some(-100) },
    ));
    assert_eq!(k.obligations["I1"].money_minor_units, Some(100));
}
