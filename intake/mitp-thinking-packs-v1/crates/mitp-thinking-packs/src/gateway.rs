use crate::belief::AtmsBeliefBase;
use crate::bounds::ExecutionConsumption;
use crate::control::{CbfConfig, HostBarrierState, evaluate_cbf};
use crate::scenario::{ReasoningContract, ScenarioInput, classify_scenario};
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

/// Proof-Carrying PreToolUse Enforcement Gateway (solves report-only Stop hook flaw).
/// Enforces deterministic-first ordering and handles all operational edge cases without deadlocking.

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ToolStepProposal {
    pub tool_name: String,
    pub target_resource: String,
    pub is_mutating: bool,
    pub is_local_heavy_build: bool,
    pub is_zero_disk_coordination_or_repair: bool,
    pub estimated_cost_micro_usd: u64,
    pub expected_net_voi: f64,
    pub reproducer_verified: bool,
    pub assumption_env: BTreeSet<String>,
    pub target_in_dependency_closure: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum StepAction {
    AllowExecute,
    AllowZeroDiskReflex,
    RefuseRetryOrReroute,
    OffloadToCloudCi,
    TransitionToActionStopProbing,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GatewayDecision {
    pub action: StepAction,
    pub error_code: String,
    pub detail: String,
}

pub struct PreToolUseGateway;

impl PreToolUseGateway {
    /// Deterministic-first <5ms admission check executed BEFORE every tool call.
    pub fn evaluate_step(
        contract: &ReasoningContract,
        consumption: &ExecutionConsumption,
        host: &HostBarrierState,
        cbf_cfg: &CbfConfig,
        atms: &AtmsBeliefBase,
        seen_probe_keys: &BTreeSet<String>,
        proposal: &ToolStepProposal,
    ) -> GatewayDecision {
        // Edge Case 1: Self-repair, peer UDS coordination, and zero-disk cloud commands NEVER deadlock on host barriers.
        if proposal.is_zero_disk_coordination_or_repair {
            return GatewayDecision {
                action: StepAction::AllowZeroDiskReflex,
                error_code: "OK_ZERO_DISK_BYPASS".to_string(),
                detail: "Zero-disk coordination/self-repair exempted from local barrier and plan deadlock.".to_string(),
            };
        }

        // Edge Case 2: Under S4 Host Crisis or CBF breach, offload local heavy builds to Cloud CI instead of freezing.
        let cbf = evaluate_cbf(host, cbf_cfg);
        if proposal.is_local_heavy_build && !cbf.safe_for_local_heavy_work {
            return GatewayDecision {
                action: StepAction::OffloadToCloudCi,
                error_code: "ERR_CBF_OFFLOAD_CLOUD_CI".to_string(),
                detail: format!(
                    "CBF reflex={} (h_disk={:.1}MB, margin={:.1}; h_swap={:.1}MB, margin={:.1}); route build/test to CI.",
                    cbf.required_reflex, cbf.h_disk, cbf.cbf_disk_margin, cbf.h_swap, cbf.cbf_swap_margin
                ),
            };
        }

        // Check 3: Hard 6-tuple Bounding Envelope (guaranteed finite termination).
        if let Err(err) = consumption_check(contract, consumption, proposal.estimated_cost_micro_usd) {
            return GatewayDecision {
                action: StepAction::RefuseRetryOrReroute,
                error_code: err.split(':').next().unwrap_or("ERR_BOUND_EXCEEDED").to_string(),
                detail: err,
            };
        }

        // Check 4: Dependency closure containment for mutating actions.
        if proposal.is_mutating && !proposal.target_in_dependency_closure {
            return GatewayDecision {
                action: StepAction::RefuseRetryOrReroute,
                error_code: "ERR_OUT_OF_CLOSURE_MUTATION".to_string(),
                detail: format!(
                    "Mutating target '{}' is outside declared ReasoningContract dependency closure.",
                    proposal.target_resource
                ),
            };
        }

        // Check 5: ATMS Nogood Firewall (blocks regression to any previously falsified assumption set).
        if !proposal.assumption_env.is_empty() && atms.is_environment_nogood(&proposal.assumption_env) {
            return GatewayDecision {
                action: StepAction::RefuseRetryOrReroute,
                error_code: "ERR_ATMS_NOGOOD_REGRESSION".to_string(),
                detail: "Proposed step depends on a previously falsified ATMS nogood environment.".to_string(),
            };
        }

        // Check 6: RCA Reproducer-Before-Patch lock (S2/S3/S5/S7).
        if proposal.is_mutating && contract.require_reproducer_before_mutation && !proposal.reproducer_verified {
            return GatewayDecision {
                action: StepAction::RefuseRetryOrReroute,
                error_code: "ERR_SPECULATIVE_PATCH_BEFORE_REPRO".to_string(),
                detail: format!(
                    "Scenario {:?} forbids mutating '{}' before deterministic failing reproducer is verified.",
                    contract.scenario, proposal.target_resource
                ),
            };
        }

        // Check 7: Non-mutating probe checks (duplicate probe + Bayesian VOI stopping rule).
        if !proposal.is_mutating {
            let probe_key = format!("{}:{}", proposal.tool_name, proposal.target_resource);
            if seen_probe_keys.contains(&probe_key) {
                return GatewayDecision {
                    action: StepAction::RefuseRetryOrReroute,
                    error_code: "ERR_ZERO_EIG_DUPLICATE_PROBE".to_string(),
                    detail: format!("Probe '{probe_key}' already executed in current session; EIG = 0."),
                };
            }
            if proposal.expected_net_voi <= contract.bounds.min_net_voi && contract.bounds.min_net_voi > 0.0 {
                return GatewayDecision {
                    action: StepAction::TransitionToActionStopProbing,
                    error_code: "STOP_PROBING_VOI_FLOOR".to_string(),
                    detail: format!(
                        "Net VOI {:.4} <= floor {:.4}; stop gathering evidence and execute best MAP/minimax action.",
                        proposal.expected_net_voi, contract.bounds.min_net_voi
                    ),
                };
            }
        }

        GatewayDecision {
            action: StepAction::AllowExecute,
            error_code: "OK".to_string(),
            detail: format!("Admitted under {:?} ({:?}).", contract.scenario, contract.enforcement_mode),
        }
    }

    pub fn classify(input: &ScenarioInput) -> ReasoningContract {
        classify_scenario(input)
    }
}

fn consumption_check(
    contract: &ReasoningContract,
    used: &ExecutionConsumption,
    next_cost_micro: u64,
) -> Result<(), String> {
    contract.bounds.check_admissible(used, next_cost_micro)
}
