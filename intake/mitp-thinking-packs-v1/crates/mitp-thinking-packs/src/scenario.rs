use crate::bounds::BoundingEnvelope;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EffectClass {
    R,
    I,
    C,
    P,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ThinkingPackId {
    TpRcaScm,
    TpBayesEig,
    TpFormalSmt,
    TpControlCbf,
    TpAgmFalsify,
    TpParetoMech,
    TpSearchMcts,
    TpConformalOod,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ScenarioClass {
    S1RoutineBounded,
    S2FirstFailureP0,
    S3CompoundMultiFault,
    S4HostSurvivalCrisis,
    S5RecurringRatchetBreach,
    S6HighRiskExternalPivot,
    S7AmbiguousUncataloged,
    S8ArchitecturalDesign,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EnforcementMode {
    PreActionGateAndAsyncCi,
    HardBlockingStateMachine,
    HardBlockingFleetPartition,
    AutonomicKernelReflex,
    SubsystemMergeFreeze,
    FailClosedPreAndPost3of3,
    BudgetedDiscoveryMode,
    ConceptionVaultQuarantine,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScenarioInput {
    pub effect_class: EffectClass,
    pub is_failure_event: bool,
    pub is_architectural_design: bool,
    pub simultaneous_failing_invariants: u32,
    pub previously_eradicated_recurrence: bool,
    pub uncataloged_error: bool,
    pub conformal_ambiguity_set_size: u32,
    pub host_disk_free_mb: i64,
    pub host_swap_used_mb: i64,
    pub host_load_1m: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ReasoningContract {
    pub scenario: ScenarioClass,
    pub mandatory_packs: Vec<ThinkingPackId>,
    pub bounds: BoundingEnvelope,
    pub enforcement_mode: EnforcementMode,
    pub require_reproducer_before_mutation: bool,
    pub llm_deliberation_bypassed: bool,
}

/// Deterministic Scenario Classifier Gamma: pure lookup, zero LLM tokens, strict safety precedence.
pub fn classify_scenario(input: &ScenarioInput) -> ReasoningContract {
    // Highest precedence: S4 Host Resource / Survival Crisis (autonomic reflex, zero LLM deliberation).
    if input.host_disk_free_mb < 1500 || input.host_swap_used_mb > 1500 || input.host_load_1m > 8.0 {
        return ReasoningContract {
            scenario: ScenarioClass::S4HostSurvivalCrisis,
            mandatory_packs: vec![ThinkingPackId::TpControlCbf, ThinkingPackId::TpParetoMech],
            bounds: BoundingEnvelope {
                max_steps: 3,
                max_wall_sec: 30,
                max_cost_micro_usd: 50_000,
                max_depth: 1,
                min_net_voi: 0.0,
                max_attempts: 1,
            },
            enforcement_mode: EnforcementMode::AutonomicKernelReflex,
            require_reproducer_before_mutation: false,
            llm_deliberation_bypassed: true,
        };
    }

    // S5 Recurring Defect (CRITICAL_RATCHET_BREACH)
    if input.previously_eradicated_recurrence {
        return ReasoningContract {
            scenario: ScenarioClass::S5RecurringRatchetBreach,
            mandatory_packs: vec![
                ThinkingPackId::TpRcaScm,
                ThinkingPackId::TpFormalSmt,
                ThinkingPackId::TpConformalOod,
                ThinkingPackId::TpAgmFalsify,
            ],
            bounds: BoundingEnvelope {
                max_steps: 6,
                max_wall_sec: 120,
                max_cost_micro_usd: 1_500_000,
                max_depth: 4,
                min_net_voi: 0.01,
                max_attempts: 2,
            },
            enforcement_mode: EnforcementMode::SubsystemMergeFreeze,
            require_reproducer_before_mutation: true,
            llm_deliberation_bypassed: false,
        };
    }

    // S3 Compound / Multi-Fault Outage
    if input.simultaneous_failing_invariants >= 2 {
        return ReasoningContract {
            scenario: ScenarioClass::S3CompoundMultiFault,
            mandatory_packs: vec![
                ThinkingPackId::TpRcaScm,
                ThinkingPackId::TpFormalSmt,
                ThinkingPackId::TpControlCbf,
                ThinkingPackId::TpAgmFalsify,
            ],
            bounds: BoundingEnvelope {
                max_steps: 8,
                max_wall_sec: 90,
                max_cost_micro_usd: 1_000_000,
                max_depth: 4,
                min_net_voi: 0.01,
                max_attempts: 3,
            },
            enforcement_mode: EnforcementMode::HardBlockingFleetPartition,
            require_reproducer_before_mutation: true,
            llm_deliberation_bypassed: false,
        };
    }

    // S6 High-Risk External Pivot (Class C / P)
    if matches!(input.effect_class, EffectClass::C | EffectClass::P) {
        return ReasoningContract {
            scenario: ScenarioClass::S6HighRiskExternalPivot,
            mandatory_packs: vec![
                ThinkingPackId::TpFormalSmt,
                ThinkingPackId::TpParetoMech,
                ThinkingPackId::TpConformalOod,
            ],
            bounds: BoundingEnvelope {
                max_steps: 5,
                max_wall_sec: 90,
                max_cost_micro_usd: 750_000,
                max_depth: 3,
                min_net_voi: 0.01,
                max_attempts: 2,
            },
            enforcement_mode: EnforcementMode::FailClosedPreAndPost3of3,
            require_reproducer_before_mutation: false,
            llm_deliberation_bypassed: false,
        };
    }

    // S7 Ambiguous / Uncataloged Failure
    if input.uncataloged_error || input.conformal_ambiguity_set_size > 1 {
        return ReasoningContract {
            scenario: ScenarioClass::S7AmbiguousUncataloged,
            mandatory_packs: vec![
                ThinkingPackId::TpBayesEig,
                ThinkingPackId::TpRcaScm,
                ThinkingPackId::TpConformalOod,
                ThinkingPackId::TpAgmFalsify,
            ],
            bounds: BoundingEnvelope {
                max_steps: 8,
                max_wall_sec: 90,
                max_cost_micro_usd: 1_000_000,
                max_depth: 4,
                min_net_voi: 0.02,
                max_attempts: 3,
            },
            enforcement_mode: EnforcementMode::BudgetedDiscoveryMode,
            require_reproducer_before_mutation: true,
            llm_deliberation_bypassed: false,
        };
    }

    // S2 First-Occurrence CI / Gate Failure (P0)
    if input.is_failure_event {
        return ReasoningContract {
            scenario: ScenarioClass::S2FirstFailureP0,
            mandatory_packs: vec![
                ThinkingPackId::TpRcaScm,
                ThinkingPackId::TpBayesEig,
                ThinkingPackId::TpAgmFalsify,
            ],
            bounds: BoundingEnvelope {
                max_steps: 5,
                max_wall_sec: 90,
                max_cost_micro_usd: 500_000,
                max_depth: 3,
                min_net_voi: 0.02,
                max_attempts: 3,
            },
            enforcement_mode: EnforcementMode::HardBlockingStateMachine,
            require_reproducer_before_mutation: true,
            llm_deliberation_bypassed: false,
        };
    }

    // S8 Architectural / Multi-Agent Design
    if input.is_architectural_design {
        return ReasoningContract {
            scenario: ScenarioClass::S8ArchitecturalDesign,
            mandatory_packs: vec![
                ThinkingPackId::TpParetoMech,
                ThinkingPackId::TpSearchMcts,
                ThinkingPackId::TpAgmFalsify,
            ],
            bounds: BoundingEnvelope {
                max_steps: 6,
                max_wall_sec: 120,
                max_cost_micro_usd: 1_000_000,
                max_depth: 3,
                min_net_voi: 0.01,
                max_attempts: 2,
            },
            enforcement_mode: EnforcementMode::ConceptionVaultQuarantine,
            require_reproducer_before_mutation: false,
            llm_deliberation_bypassed: false,
        };
    }

    // S1 Routine Bounded Change (Class R / I)
    ReasoningContract {
        scenario: ScenarioClass::S1RoutineBounded,
        mandatory_packs: vec![ThinkingPackId::TpFormalSmt, ThinkingPackId::TpAgmFalsify],
        bounds: BoundingEnvelope {
            max_steps: 5,
            max_wall_sec: 60,
            max_cost_micro_usd: 250_000,
            max_depth: 2,
            min_net_voi: 0.0,
            max_attempts: 2,
        },
        enforcement_mode: EnforcementMode::PreActionGateAndAsyncCi,
        require_reproducer_before_mutation: false,
        llm_deliberation_bypassed: false,
    }
}
