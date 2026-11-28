use meridian_dof::*;

fn reading(component: &str, a: ProbeStatus, b: ProbeStatus) -> DualProbeReading {
    DualProbeReading {
        component_id: component.to_string(),
        method_a: a,
        method_b: b,
    }
}

fn req(
    e: &DofLeaseEngine,
    cat: ActionCategory,
    paths: &[&str],
    surface: &str,
    comp: Option<&str>,
) -> ActionRequest {
    ActionRequest {
        tool_name: "t".to_string(),
        category: cat,
        target_paths: paths.iter().map(|p| p.to_string()).collect(),
        surface: surface.to_string(),
        claimed_lease_epoch: e.lease_epoch,
        resolving_component: comp.map(String::from),
    }
}

fn directive(r: Result<(), RefusalEnvelope>) -> String {
    match r {
        Ok(()) => "OK".to_string(),
        Err(env) => env.directive,
    }
}

fn down_to_l2(e: &mut DofLeaseEngine, comp: &str) {
    e.evaluate_probe(&reading(comp, ProbeStatus::Fail, ProbeStatus::Fail));
    assert_eq!(e.active_level, DofLevel::L2ComponentRepairOnly);
}

const ROUTER: &str = "ROUTER-EDGE-01";
const ROUTER_PATH: &str = "platform/router-edge/wrangler.toml";

#[test]
fn single_probe_failure_holds_at_l1_dual_failure_drops_to_l2_each_bumping_the_epoch() {
    let mut e = DofLeaseEngine::zone_b_default();
    assert_eq!((e.active_level, e.lease_epoch), (DofLevel::L0FullLease, 1));
    e.evaluate_probe(&reading(ROUTER, ProbeStatus::Fail, ProbeStatus::Pass));
    assert_eq!(
        (e.active_level, e.lease_epoch),
        (DofLevel::L1ReadDiagnoseOnly, 2)
    );
    e.evaluate_probe(&reading(ROUTER, ProbeStatus::Fail, ProbeStatus::Fail));
    assert_eq!(
        (e.active_level, e.lease_epoch),
        (DofLevel::L2ComponentRepairOnly, 3)
    );
    // A repeat dual failure on the same component must not keep bumping the epoch.
    e.evaluate_probe(&reading(ROUTER, ProbeStatus::Fail, ProbeStatus::Fail));
    assert_eq!(e.lease_epoch, 3);
}

#[test]
fn cannot_run_is_never_treated_as_a_pass() {
    let mut e = DofLeaseEngine::zone_b_default();
    e.evaluate_probe(&reading(ROUTER, ProbeStatus::CannotRun, ProbeStatus::Pass));
    assert_eq!(e.active_level, DofLevel::L1ReadDiagnoseOnly);
}

#[test]
fn l2_refuses_task_mutation_and_allows_diagnostic_reads() {
    let mut e = DofLeaseEngine::zone_b_default();
    down_to_l2(&mut e, ROUTER);
    let m = req(
        &e,
        ActionCategory::TaskMutation,
        &["crates/meridian-muster/src/lib.rs"],
        "zone-b-worker",
        None,
    );
    assert_eq!(
        directive(e.authorize(&m)),
        "CAPABILITY_LEASE_INSUFFICIENT_REPAIR_FIRST"
    );
    let r = req(
        &e,
        ActionCategory::DiagnosticRead,
        &[],
        "zone-b-worker",
        None,
    );
    assert_eq!(directive(e.authorize(&r)), "OK");
}

#[test]
fn repair_must_be_scoped_to_the_failing_component() {
    let mut e = DofLeaseEngine::zone_b_default();
    down_to_l2(&mut e, ROUTER);
    let wrong_comp = req(
        &e,
        ActionCategory::RepairStep,
        &[ROUTER_PATH],
        "zone-b-worker",
        Some("GREENLANE-01"),
    );
    assert_eq!(
        directive(e.authorize(&wrong_comp)),
        "CAPABILITY_LEASE_INSUFFICIENT_REPAIR_FIRST"
    );
    let wrong_path = req(
        &e,
        ActionCategory::RepairStep,
        &["greenlane/github.py"],
        "zone-b-worker",
        Some(ROUTER),
    );
    assert_eq!(
        directive(e.authorize(&wrong_path)),
        "CAPABILITY_LEASE_INSUFFICIENT_REPAIR_FIRST"
    );
    let mixed = req(
        &e,
        ActionCategory::RepairStep,
        &[ROUTER_PATH, "greenlane/github.py"],
        "zone-b-worker",
        Some(ROUTER),
    );
    assert_eq!(
        directive(e.authorize(&mixed)),
        "CAPABILITY_LEASE_INSUFFICIENT_REPAIR_FIRST"
    );
    let none = req(
        &e,
        ActionCategory::RepairStep,
        &[],
        "zone-b-worker",
        Some(ROUTER),
    );
    assert_eq!(
        directive(e.authorize(&none)),
        "CAPABILITY_LEASE_INSUFFICIENT_REPAIR_FIRST"
    );
    assert_eq!(e.completed_repair_steps, 0);
    let ok = req(
        &e,
        ActionCategory::RepairStep,
        &[ROUTER_PATH],
        "zone-b-worker",
        Some(ROUTER),
    );
    assert_eq!(directive(e.authorize(&ok)), "OK");
    assert_eq!(e.completed_repair_steps, 1);
}

#[test]
fn restore_needs_all_repair_steps_and_three_consecutive_passes() {
    let mut e = DofLeaseEngine::zone_b_default();
    down_to_l2(&mut e, ROUTER);
    let pass = reading(ROUTER, ProbeStatus::Pass, ProbeStatus::Pass);

    // Passing alone, with no repair receipted, never restores.
    for _ in 0..5 {
        e.evaluate_probe(&pass);
    }
    assert_eq!(e.active_level, DofLevel::L2ComponentRepairOnly);

    // Three required steps must be three distinct steps; replaying one does not count.
    for step in ["a.rs", "b.rs", "c.rs"] {
        let path = format!("platform/router-edge/{step}");
        let r = req(
            &e,
            ActionCategory::RepairStep,
            &[path.as_str()],
            "zone-b-worker",
            Some(ROUTER),
        );
        assert_eq!(directive(e.authorize(&r)), "OK");
    }
    e.evaluate_probe(&pass);
    e.evaluate_probe(&pass);
    assert_eq!(
        e.active_level,
        DofLevel::L2ComponentRepairOnly,
        "two passes are not enough"
    );
    // A flap resets the streak.
    e.evaluate_probe(&reading(ROUTER, ProbeStatus::Pass, ProbeStatus::Fail));
    e.evaluate_probe(&pass);
    e.evaluate_probe(&pass);
    assert_eq!(
        e.active_level,
        DofLevel::L2ComponentRepairOnly,
        "streak restarted after the flap"
    );
    let before = e.lease_epoch;
    e.evaluate_probe(&pass);
    assert_eq!(e.active_level, DofLevel::L0FullLease);
    assert_eq!(e.lease_epoch, before + 1, "restore bumps the epoch");
    assert_eq!(e.failing_component, None);
}

#[test]
fn stale_epoch_is_fenced_even_for_a_would_be_legal_action() {
    let mut e = DofLeaseEngine::zone_b_default();
    let mut stale = req(
        &e,
        ActionCategory::TaskMutation,
        &["crates/x"],
        "zone-b-worker",
        None,
    );
    assert_eq!(directive(e.authorize(&stale)), "OK");
    e.evaluate_probe(&reading(ROUTER, ProbeStatus::Fail, ProbeStatus::Fail));
    e.evaluate_probe(&reading(ROUTER, ProbeStatus::Pass, ProbeStatus::Pass)); // no-op at L2 w/o repair
    stale.claimed_lease_epoch = 1;
    assert_eq!(directive(e.authorize(&stale)), "STALE_LEASE_EPOCH_FENCED");
}

#[test]
fn immutable_control_paths_stay_locked_while_red_even_for_repair() {
    let mut e = DofLeaseEngine::zone_b_default();
    down_to_l2(&mut e, ROUTER);
    for p in [
        "bin/dof-gate",
        "catalog/dof-registry.json",
        "crates/meridian-dof/src/lib.rs",
        ".github/workflows/ci.yml",
    ] {
        let r = req(
            &e,
            ActionCategory::RepairStep,
            &[p],
            "zone-b-worker",
            Some(ROUTER),
        );
        assert_eq!(
            directive(e.authorize(&r)),
            "IMMUTABLE_CONTROL_WHILE_RED",
            "{p}"
        );
    }
}

#[test]
fn safe_docs_and_tests_break_the_deadlock_only_inside_docs_specs_and_tests() {
    let mut e = DofLeaseEngine::zone_b_default();
    down_to_l2(&mut e, ROUTER);
    let ok = req(
        &e,
        ActionCategory::SafeLowEffectDocOrTest,
        &["docs/specs/a.md", "tests/test_a.py"],
        "zone-b-worker",
        None,
    );
    assert_eq!(directive(e.authorize(&ok)), "OK");
    let bad = req(
        &e,
        ActionCategory::SafeLowEffectDocOrTest,
        &["docs/specs/a.md", "crates/meridian-flow/src/lib.rs"],
        "zone-b-worker",
        None,
    );
    assert_eq!(
        directive(e.authorize(&bad)),
        "CAPABILITY_LEASE_INSUFFICIENT_REPAIR_FIRST"
    );
}

#[test]
fn cross_surface_mutation_during_outage_is_l3_with_red_card_and_l3_is_sticky() {
    let mut e = DofLeaseEngine::zone_b_default();
    down_to_l2(&mut e, ROUTER);
    let bypass = req(
        &e,
        ActionCategory::TaskMutation,
        &["crates/x"],
        "web-chat",
        None,
    );
    match e.authorize(&bypass) {
        Err(env) => {
            assert!(env.cross_surface_bypass && env.red_card_issued);
            assert_eq!(env.directive, "CROSS_SURFACE_BYPASS_ESCALATED_TO_L3");
        }
        Ok(()) => panic!("bypass was allowed"),
    }
    assert_eq!(e.active_level, DofLevel::L3FrozenEscalated);
    assert!(e.red_card_issued);
    for _ in 0..10 {
        e.evaluate_probe(&reading(ROUTER, ProbeStatus::Pass, ProbeStatus::Pass));
    }
    assert_eq!(
        e.active_level,
        DofLevel::L3FrozenEscalated,
        "probes cannot thaw L3"
    );
    let repair = req(
        &e,
        ActionCategory::RepairStep,
        &[ROUTER_PATH],
        "zone-b-worker",
        Some(ROUTER),
    );
    assert_eq!(directive(e.authorize(&repair)), "L3_FROZEN_ESCALATED");
}

#[test]
fn web_chat_mutation_at_l0_is_not_a_bypass() {
    let mut e = DofLeaseEngine::zone_b_default();
    let r = req(
        &e,
        ActionCategory::TaskMutation,
        &["crates/x"],
        "web-chat",
        None,
    );
    assert_eq!(directive(e.authorize(&r)), "OK");
    assert!(!e.red_card_issued);
}

#[test]
fn all_four_zone_b_components_can_enter_l2_and_none_is_an_oke_path() {
    for c in [
        "ROUTER-EDGE-01",
        "BATTALION-FIT-01",
        "MEMORY-ZONEB-01",
        "GREENLANE-01",
    ] {
        let mut e = DofLeaseEngine::zone_b_default();
        down_to_l2(&mut e, c);
        assert_eq!(e.failing_component.as_deref(), Some(c));
    }
    let src = include_str!("../src/lib.rs");
    let ghosts = [
        ["idp", "oke-"].join("-"),
        ["oke", "*.yml"].join("-"),
        ["clusters", "oke"].join("/"),
    ];
    for g in &ghosts {
        assert!(
            !src.contains(g.as_str()),
            "retired OKE path {g} present in meridian-dof"
        );
    }
}

// ---- failure-mode hardening: each test below failed on the code that preceded it ----

#[test]
fn path_aliases_of_an_immutable_control_are_still_immutable_while_red() {
    for alias in ["./bin/dof-gate", "bin//dof-gate", "BIN/dof-gate", "bin/x/../dof-gate", "/bin/dof-gate"] {
        let mut e = DofLeaseEngine::zone_b_default();
        down_to_l2(&mut e, ROUTER);
        let r = req(&e, ActionCategory::TaskMutation, &[alias], "zone-b-worker", None);
        assert_eq!(directive(e.authorize(&r)), "IMMUTABLE_CONTROL_WHILE_RED", "alias {alias}");
    }
}

#[test]
fn dot_dot_cannot_launder_a_safe_doc_prefix() {
    let mut e = DofLeaseEngine::zone_b_default();
    down_to_l2(&mut e, ROUTER);
    let r = req(&e, ActionCategory::SafeLowEffectDocOrTest, &["tests/../bin/dof-gate"], "zone-b-worker", None);
    assert_ne!(directive(e.authorize(&r)), "OK");
}

#[test]
fn dot_dot_cannot_escape_a_repair_scope_or_count_as_a_repair() {
    let mut e = DofLeaseEngine::zone_b_default();
    down_to_l2(&mut e, ROUTER);
    let r = req(
        &e,
        ActionCategory::RepairStep,
        &["platform/router-edge/../../bin/dof-gate"],
        "zone-b-worker",
        Some(ROUTER),
    );
    assert_ne!(directive(e.authorize(&r)), "OK");
    assert_eq!(e.completed_repair_steps, 0);
}

#[test]
fn a_safe_doc_with_no_target_is_not_safe() {
    let mut e = DofLeaseEngine::zone_b_default();
    down_to_l2(&mut e, ROUTER);
    let r = req(&e, ActionCategory::SafeLowEffectDocOrTest, &[], "zone-b-worker", None);
    assert_ne!(directive(e.authorize(&r)), "OK", "an action that names nothing cannot be judged safe");
}

#[test]
fn replaying_one_repair_step_does_not_satisfy_three_required_steps() {
    let mut e = DofLeaseEngine::zone_b_default();
    down_to_l2(&mut e, ROUTER);
    for _ in 0..3 {
        let r = req(&e, ActionCategory::RepairStep, &["platform/router-edge/a.rs"], "zone-b-worker", Some(ROUTER));
        let _ = e.authorize(&r);
    }
    for _ in 0..3 {
        e.evaluate_probe(&reading(ROUTER, ProbeStatus::Pass, ProbeStatus::Pass));
    }
    assert_eq!(e.active_level, DofLevel::L2ComponentRepairOnly, "one step, replayed, restored the lease");
}

#[test]
fn another_components_passes_do_not_restore_the_failing_one() {
    let mut e = DofLeaseEngine::zone_b_default();
    down_to_l2(&mut e, ROUTER);
    for p in ["a.rs", "b.rs", "c.rs"] {
        let path = format!("platform/router-edge/{p}");
        let r = req(&e, ActionCategory::RepairStep, &[path.as_str()], "zone-b-worker", Some(ROUTER));
        assert!(e.authorize(&r).is_ok());
    }
    for _ in 0..3 {
        e.evaluate_probe(&reading("GREENLANE-01", ProbeStatus::Pass, ProbeStatus::Pass));
    }
    assert_eq!(e.active_level, DofLevel::L2ComponentRepairOnly, "GREENLANE passing says nothing about ROUTER");
    assert_eq!(e.failing_component.as_deref(), Some(ROUTER));
}

#[test]
fn a_second_failing_component_does_not_erase_the_first() {
    let mut e = DofLeaseEngine::zone_b_default();
    down_to_l2(&mut e, ROUTER);
    e.evaluate_probe(&reading("GREENLANE-01", ProbeStatus::Fail, ProbeStatus::Fail));
    assert_eq!(e.active_level, DofLevel::L3FrozenEscalated, "two components down is fail-closed");
    assert!(e.red_card_issued);
}

#[test]
fn surface_name_is_compared_without_case_or_padding() {
    let mut e = DofLeaseEngine::zone_b_default();
    e.evaluate_probe(&reading(ROUTER, ProbeStatus::Fail, ProbeStatus::Pass));
    assert_eq!(e.active_level, DofLevel::L1ReadDiagnoseOnly);
    let r = req(&e, ActionCategory::TaskMutation, &["x.rs"], " Web-Chat ", None);
    assert_eq!(directive(e.authorize(&r)), "CROSS_SURFACE_BYPASS_ESCALATED_TO_L3");
}
