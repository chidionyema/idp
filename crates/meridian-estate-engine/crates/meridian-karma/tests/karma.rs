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
