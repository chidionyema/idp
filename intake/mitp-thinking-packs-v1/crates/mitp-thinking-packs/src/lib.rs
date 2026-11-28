pub mod bayes;
pub mod belief;
pub mod bounds;
pub mod control;
pub mod decision;
pub mod formal;
pub mod gateway;
pub mod rca;
pub mod scenario;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::bayes::{CandidateProbe, HypothesisSpace, SprtDecision, select_best_probe, wald_sprt};
    use crate::belief::{AtmsBeliefBase, BeliefNode, EpistemicRank, verify_mayo_severity};
    use crate::bounds::ExecutionConsumption;
    use crate::control::{CbfConfig, HostBarrierState, check_queue_stability, evaluate_cbf, verify_lyapunov_progress};
    use crate::decision::{
        CandidatePlan, brier_score, conformal_prediction_set, conformal_quantile, cusum_drift_alarm,
        find_dependency_cycles, minimax_regret_choice, pareto_frontier, uct_prm_score,
    };
    use crate::formal::{PolicyRule, check_bounded_liveness, find_minimal_unsat_core};
    use crate::gateway::{PreToolUseGateway, StepAction, ToolStepProposal};
    use crate::rca::{CounterfactualWitness, ddmin, minimal_hitting_sets, ochiai_score};
    use crate::scenario::{EffectClass, ScenarioClass, ScenarioInput, classify_scenario};
    use std::collections::{BTreeMap, BTreeSet};

    #[test]
    fn scenario_classifier_respects_survival_and_ratchet_precedence() {
        let host_crisis = ScenarioInput {
            effect_class: EffectClass::I,
            is_failure_event: true,
            is_architectural_design: false,
            simultaneous_failing_invariants: 3,
            previously_eradicated_recurrence: true,
            uncataloged_error: false,
            conformal_ambiguity_set_size: 1,
            host_disk_free_mb: 1428,
            host_swap_used_mb: 2854,
            host_load_1m: 417.0,
        };
        let c = classify_scenario(&host_crisis);
        assert_eq!(c.scenario, ScenarioClass::S4HostSurvivalCrisis);
        assert!(c.llm_deliberation_bypassed);

        let mut breach = host_crisis;
        breach.host_disk_free_mb = 5000;
        breach.host_swap_used_mb = 200;
        breach.host_load_1m = 1.5;
        let c2 = classify_scenario(&breach);
        assert_eq!(c2.scenario, ScenarioClass::S5RecurringRatchetBreach);
        assert!(c2.require_reproducer_before_mutation);
    }

    #[test]
    fn rca_hitting_sets_ddmin_ochiai_and_hp_causality() {
        // Compound outage: conflict 1 = {disk-floor, swap-spiral}, conflict 2 = {plan-gate, disk-reclaim}
        let c1 = BTreeSet::from(["disk-floor".to_string(), "swap-spiral".to_string()]);
        let c2 = BTreeSet::from(["plan-gate".to_string(), "disk-reclaim".to_string()]);
        let hs = minimal_hitting_sets(&[c1, c2], 3);
        assert_eq!(hs.len(), 4);
        assert!(hs.iter().all(|s| s.len() == 2));

        // ddmin isolates 1-minimal failing item
        let items = vec![1, 2, 3, 4, 5, 6, 7, 8];
        let min_fail = ddmin(&items, |subset| subset.contains(&6));
        assert_eq!(min_fail, vec![6]);

        assert!((ochiai_score(4, 0, 0) - 1.0).abs() < 1e-9);

        let w = CounterfactualWitness {
            cause_component: "plan-gate".to_string(),
            observed_failure_present: true,
            intervention_removed_failure: true,
            is_minimal_subset: true,
        };
        assert!(w.verify_hp_actual_cause().is_ok());
    }

    #[test]
    fn bayes_eig_voi_unknown_floor_and_sprt() {
        let priors = BTreeMap::from([
            ("h_certifier_gap".to_string(), 0.6),
            ("h_proxy_url".to_string(), 0.4),
        ]);
        let space = HypothesisSpace::new(priors, 0.05).unwrap();
        assert!(space.probs.contains_key("h_unknown"));

        let probe = CandidateProbe {
            probe_id: "check_judge_receipt_code".to_string(),
            cost_usd: 0.02,
            outcome_likelihoods: BTreeMap::from([
                (
                    "requires_3_signed".to_string(),
                    BTreeMap::from([
                        ("h_certifier_gap".to_string(), 0.95),
                        ("h_proxy_url".to_string(), 0.05),
                        ("h_unknown".to_string(), 0.30),
                    ]),
                ),
                (
                    "accepts_raw_url".to_string(),
                    BTreeMap::from([
                        ("h_certifier_gap".to_string(), 0.05),
                        ("h_proxy_url".to_string(), 0.95),
                        ("h_unknown".to_string(), 0.70),
                    ]),
                ),
            ]),
        };

        let utilities = BTreeMap::from([
            (
                "build_certifier".to_string(),
                BTreeMap::from([
                    ("h_certifier_gap".to_string(), 10.0),
                    ("h_proxy_url".to_string(), -2.0),
                    ("h_unknown".to_string(), -1.0),
                ]),
            ),
            (
                "fix_url".to_string(),
                BTreeMap::from([
                    ("h_certifier_gap".to_string(), -5.0),
                    ("h_proxy_url".to_string(), 8.0),
                    ("h_unknown".to_string(), -1.0),
                ]),
            ),
        ]);

        let best = select_best_probe(&space, &[probe], &utilities, 1.0, 0.01).unwrap();
        assert!(best.eig_bits > 0.3);
        assert!(best.voi_utility > 1.0);
        assert_eq!(wald_sprt(25.0, 0.05, 0.05), SprtDecision::AcceptH1);
        assert_eq!(wald_sprt(0.01, 0.05, 0.05), SprtDecision::AcceptH0);
    }

    #[test]
    fn formal_unsat_core_localizes_hook_deadlock() {
        // A TWO-RULE deadlock needs a requirement against a prohibition. The original fixture
        // set plan-gate to forbid BOTH candidate actions, which is unsatisfiable on its own, so
        // the minimal core is legitimately that single rule -- the assertion expecting a pair
        // could never hold (found 2026-11-28: cargo test, 5 passed 1 failed, left=[plan_gate]).
        // The real 2026-11-28 conflict is: the disk floor DEMANDS disk-reclaim, and the plan gate
        // FORBIDS disk-reclaim. Encoded that way, neither rule is unsatisfiable alone and their
        // pair is the minimal conflict.
        let rules = vec![
            PolicyRule {
                rule_id: "disk_floor_1500mb".to_string(),
                allows: BTreeSet::new(),
                forbids: BTreeSet::new(),
                requires_one_of: BTreeSet::from(["disk-reclaim".to_string()]),
            },
            PolicyRule {
                rule_id: "plan_gate_no_declared_plan".to_string(),
                allows: BTreeSet::new(),
                forbids: BTreeSet::from(["disk-reclaim".to_string()]),
                requires_one_of: BTreeSet::new(),
            },
            PolicyRule {
                rule_id: "unrelated_lint_rule".to_string(),
                allows: BTreeSet::new(),
                forbids: BTreeSet::new(),
                requires_one_of: BTreeSet::new(),
            },
        ];
        let actions = BTreeSet::from(["disk-reclaim".to_string(), "git-push".to_string()]);
        let core = find_minimal_unsat_core(&rules, &actions).unwrap();
        assert_eq!(core, vec!["disk_floor_1500mb", "plan_gate_no_declared_plan"]);

        // A blanket prohibition is a singleton core, and saying so is the actionable diagnosis:
        // one rule forbids every candidate action, so no pair is at fault.
        let blanket = vec![PolicyRule {
            rule_id: "plan_gate_no_declared_plan".to_string(),
            allows: BTreeSet::new(),
            forbids: actions.clone(),
            requires_one_of: BTreeSet::new(),
        }];
        assert_eq!(
            find_minimal_unsat_core(&blanket, &actions).unwrap(),
            vec!["plan_gate_no_declared_plan"]
        );
        assert!(check_bounded_liveness(100, 200, 60, false).is_err());
    }

    #[test]
    fn cbf_triggers_preemptive_offload_before_cliff_and_atms_blocks_regression() {
        // Disk is still 1600MB (>1500MB floor) but dropping at -120MB/min -> CBF margin = -120 + 0.5*100 = -70 < 0!
        let approaching = HostBarrierState {
            disk_free_mb: 1600.0,
            disk_delta_mb_per_min: -120.0,
            swap_used_mb: 800.0,
            swap_delta_mb_per_min: 10.0,
            load_1m: 3.0,
            active_heavy_sessions: 1,
        };
        let v = evaluate_cbf(&approaching, &CbfConfig::default());
        assert!(!v.safe_for_local_heavy_work);
        assert_eq!(v.required_reflex, "PREEMPTIVE_CBF_OFFLOAD_TO_CLOUD_CI");
        assert!(verify_lyapunov_progress(5.0, 5.0, 0.5).is_err());
        assert!(check_queue_stability(10.0, 5.0).is_err());

        // ATMS nogood prevents compaction regression to raw.githubusercontent.com hypothesis
        let mut atms = AtmsBeliefBase::default();
        atms.record_nogood(BTreeSet::from(["raw_url_valid_proxy".to_string()]));
        let bad_belief = BeliefNode {
            belief_id: "b1".to_string(),
            rank: EpistemicRank::Hypothesis,
            assumptions: BTreeSet::from(["raw_url_valid_proxy".to_string(), "extra".to_string()]),
        };
        assert!(atms.revise_add_belief(bad_belief).is_err());
        assert!(verify_mayo_severity(0.0, 0.95, false, true).is_err());
        assert!(verify_mayo_severity(0.99, 0.95, true, true).is_ok());
    }

    #[test]
    fn pareto_minimax_tarjan_conformal_brier_cusum_and_gateway() {
        let plans = vec![
            CandidatePlan {
                plan_id: "unsafe_fast".to_string(),
                passes_constitutional_safety: false,
                expected_yield: 100.0,
                cost_usd: 0.01,
                latency_sec: 1.0,
                blast_radius: 1.0,
            },
            CandidatePlan {
                plan_id: "dominated".to_string(),
                passes_constitutional_safety: true,
                expected_yield: 5.0,
                cost_usd: 2.0,
                latency_sec: 10.0,
                blast_radius: 3.0,
            },
            CandidatePlan {
                plan_id: "pareto_opt".to_string(),
                passes_constitutional_safety: true,
                expected_yield: 9.0,
                cost_usd: 0.5,
                latency_sec: 5.0,
                blast_radius: 1.0,
            },
        ];
        let front = pareto_frontier(&plans);
        assert_eq!(front.len(), 1);
        assert_eq!(front[0].plan_id, "pareto_opt");

        let payoffs = BTreeMap::from([
            ("safe_fix".to_string(), BTreeMap::from([("s1".to_string(), 6.0), ("s2".to_string(), 5.0)])),
            ("risky_fix".to_string(), BTreeMap::from([("s1".to_string(), 10.0), ("s2".to_string(), -20.0)])),
        ]);
        let (winner, _) = minimax_regret_choice(&payoffs).unwrap();
        assert_eq!(winner, "safe_fix");

        let graph = BTreeMap::from([
            ("A".to_string(), vec!["B".to_string()]),
            ("B".to_string(), vec!["A".to_string()]),
        ]);
        assert_eq!(find_dependency_cycles(&graph).len(), 1);
        assert!(uct_prm_score(0.9, 10, 2, 1.4, 0.1, 0.5) > 0.0);

        let q = conformal_quantile(&[0.1, 0.2, 0.3, 0.4, 0.5], 0.2).unwrap();
        let set = conformal_prediction_set(&BTreeMap::from([("c1".to_string(), 0.2), ("c2".to_string(), 0.9)]), q);
        assert_eq!(set, vec!["c1"]);
        assert!(brier_score(&[(0.9, true), (0.1, false)]).unwrap() < 0.02);
        assert!(cusum_drift_alarm(&[0.8, 0.9, 0.85, 0.9], 0.1, 0.1, 1.5).0);

        // PreToolUse Gateway blocks speculative patch before reproducer on S2
        let s2 = classify_scenario(&ScenarioInput {
            effect_class: EffectClass::I,
            is_failure_event: true,
            is_architectural_design: false,
            simultaneous_failing_invariants: 1,
            previously_eradicated_recurrence: false,
            uncataloged_error: false,
            conformal_ambiguity_set_size: 1,
            host_disk_free_mb: 5000,
            host_swap_used_mb: 100,
            host_load_1m: 1.0,
        });
        let decision = PreToolUseGateway::evaluate_step(
            &s2,
            &ExecutionConsumption::default(),
            &HostBarrierState {
                disk_free_mb: 5000.0,
                disk_delta_mb_per_min: 0.0,
                swap_used_mb: 100.0,
                swap_delta_mb_per_min: 0.0,
                load_1m: 1.0,
                active_heavy_sessions: 1,
            },
            &CbfConfig::default(),
            &AtmsBeliefBase::default(),
            &BTreeSet::new(),
            &ToolStepProposal {
                tool_name: "edit_file".to_string(),
                target_resource: "greenlane/engine.py".to_string(),
                is_mutating: true,
                is_local_heavy_build: false,
                is_zero_disk_coordination_or_repair: false,
                estimated_cost_micro_usd: 1000,
                expected_net_voi: 0.5,
                reproducer_verified: false,
                assumption_env: BTreeSet::new(),
                target_in_dependency_closure: true,
            },
        );
        assert_eq!(decision.action, StepAction::RefuseRetryOrReroute);
        assert_eq!(decision.error_code, "ERR_SPECULATIVE_PATCH_BEFORE_REPRO");
    }
}
