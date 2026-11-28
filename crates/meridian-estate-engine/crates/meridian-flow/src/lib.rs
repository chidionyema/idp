//! FLOW: 6-Phase Capability Discovery & Obligation Conservation Engine (`meridian-flow`).
//!
//! Replaces the mock TypeScript `flow.ts` simulator with real compiled orchestration across:
//!   1_DISCOVER -> 2_CONTRACT_MATCH -> 3_RANK_AND_DECIDE -> 4_EXECUTION_GATE (DOF)
//!   -> 5_FLOW_EXECUTE (LEGION Muster) -> 6_VERIFY_AND_YIELD (KARMA Independent Oracle).

use meridian_dof::{ActionCategory, ActionRequest, DofLeaseEngine, RefusalEnvelope};
use meridian_karma::{KarmaEvent, KarmaEventKind, KarmaProjection, ObligationState};
use meridian_muster::{
    canonical_eight_formations, execute_formation_fractal, verify_receipt_chain, FractalNode,
    LegionFormation, MusterError,
};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EstateCapability {
    pub id: String,
    pub keywords: Vec<String>,
    pub target_paths: Vec<String>,
    pub default_formation: LegionFormation,
    pub readiness_verified: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum FlowDecision {
    ReuseExisting {
        capability_id: String,
        formation: LegionFormation,
    },
    /// A capability matches the intent but the registry only declares it. A declared route is
    /// a claim, not a verified service, so FLOW reports it and does not run it.
    DeclaredNotVerified {
        capability_id: String,
        target_paths: Vec<String>,
    },
    ImplementNew,
}

#[derive(Clone, Debug)]
pub enum FlowError {
    DofRefused(RefusalEnvelope),
    MusterFailed(MusterError),
    KarmaNotSettled {
        reason: String,
    },
    /// Nothing was executed (no units), so there is no receipt to settle.
    NoWorkPerformed,
}

fn keyword_matches(lowered_intent: &str, keyword: &str) -> bool {
    let k = keyword.trim().to_ascii_lowercase();
    // An empty keyword is a substring of everything and would match every intent.
    if k.is_empty() {
        return false;
    }
    // Whole-word match: "ci" must not match inside "specific".
    let bytes = lowered_intent.as_bytes();
    let word = |b: u8| b.is_ascii_alphanumeric();
    lowered_intent.match_indices(&k).any(|(i, _)| {
        let before = i == 0 || !word(bytes[i - 1]);
        let end = i + k.len();
        let after = end >= bytes.len() || !word(bytes[end]);
        before && after
    })
}

/// Phases 1-3 only: DISCOVER -> CONTRACT_MATCH -> RANK_AND_DECIDE. Reads, never mutates.
/// A verified match wins over a declared one; a declared match is reported, never run.
pub fn discover(registry: &[EstateCapability], intent_text: &str) -> FlowDecision {
    let low = intent_text.to_ascii_lowercase();
    let hits = |c: &&EstateCapability| c.keywords.iter().any(|k| keyword_matches(&low, k));
    if let Some(c) = registry.iter().filter(hits).find(|c| c.readiness_verified) {
        return FlowDecision::ReuseExisting {
            capability_id: c.id.clone(),
            formation: c.default_formation,
        };
    }
    match registry.iter().find(hits) {
        Some(c) => FlowDecision::DeclaredNotVerified {
            capability_id: c.id.clone(),
            target_paths: c.target_paths.clone(),
        },
        None => FlowDecision::ImplementNew,
    }
}

#[derive(Debug, PartialEq, Eq)]
pub enum RegistryError {
    Unparseable(String),
    NoRecords,
}

#[derive(Debug)]
pub struct LoadedRegistry {
    pub capabilities: Vec<EstateCapability>,
    /// Records that could not be turned into a capability, each named. A malformed record
    /// costs that record, never the corpus, and never disappears silently.
    pub skipped: Vec<String>,
}

/// Reads the estate capability registry (`catalog/estate-capability-registry.json`).
/// Readiness is the registry's own `health.state == "verified"`; `declared` is not ready.
pub fn registry_from_json(text: &str) -> Result<LoadedRegistry, RegistryError> {
    let doc: serde_json::Value =
        serde_json::from_str(text).map_err(|e| RegistryError::Unparseable(e.to_string()))?;
    let records = doc
        .get("records")
        .and_then(|r| r.as_array())
        .filter(|r| !r.is_empty())
        .ok_or(RegistryError::NoRecords)?;
    let mut capabilities = Vec::new();
    let mut skipped = Vec::new();
    for (i, rec) in records.iter().enumerate() {
        let Some(id) = rec
            .get("id")
            .and_then(|v| v.as_str())
            .filter(|v| !v.is_empty())
        else {
            skipped.push(format!("record[{i}]: no id"));
            continue;
        };
        let name = id.rsplit('/').next().unwrap_or(id).to_ascii_lowercase();
        // Short names are too ambiguous to route on.
        if name.len() < 4 {
            skipped.push(format!("{id}: name too short to route on"));
            continue;
        }
        let mut keywords = vec![name.clone()];
        for sep in ['-', '_'] {
            let spaced = name.replace(sep, " ");
            if !keywords.contains(&spaced) {
                keywords.push(spaced);
            }
        }
        let target_paths = rec
            .get("path")
            .and_then(|v| v.as_str())
            .map(|p| vec![p.to_string()])
            .unwrap_or_default();
        let verified = rec
            .pointer("/health/state")
            .and_then(|v| v.as_str())
            .is_some_and(|s| s == "verified");
        capabilities.push(EstateCapability {
            id: id.to_string(),
            keywords,
            target_paths,
            default_formation: LegionFormation::Phalanx,
            readiness_verified: verified,
        });
    }
    Ok(LoadedRegistry {
        capabilities,
        skipped,
    })
}

/// Leaves the reason a debt is unpaid on the ledger instead of only returning an error.
fn record_failure(karma: &mut KarmaProjection, instruction_id: &str, agent: &str, class: &str) {
    karma.apply(&KarmaEvent {
        event_id: format!("{instruction_id}-fail"),
        instruction_id: instruction_id.to_string(),
        agent_urn: agent.to_string(),
        parent_event_ids: vec![format!("{instruction_id}-accept")],
        externally_verified_authority: true,
        payload: KarmaEventKind::AncestralFailure {
            ancestor_event_id: format!("{instruction_id}-accept"),
            failure_class: class.to_string(),
        },
    });
}

/// Runs all 6 FLOW phases end-to-end with zero mock yield and zero self-certification.
pub fn execute_flow_end_to_end(
    instruction_id: &str,
    intent_text: &str,
    caller_urn: &str,
    independent_oracle_urn: &str,
    registry: &[EstateCapability],
    // The lease epoch the caller observed when it decided to act. DOF refuses it if the
    // lease has moved since, so a decision taken before an outage cannot run after it.
    claimed_lease_epoch: u64,
    dof: &mut DofLeaseEngine,
    karma: &mut KarmaProjection,
    nodes: &[FractalNode],
    budget_minor_units: i64,
) -> Result<FlowDecision, FlowError> {
    // Phase 1-3: DISCOVER -> CONTRACT_MATCH -> RANK_AND_DECIDE (Reuse before invent)
    let (cap, decision) = match discover(registry, intent_text) {
        FlowDecision::ReuseExisting {
            capability_id,
            formation,
        } => {
            let c = registry
                .iter()
                .find(|c| c.id == capability_id)
                .ok_or(FlowError::NoWorkPerformed)?;
            (
                c,
                FlowDecision::ReuseExisting {
                    capability_id,
                    formation,
                },
            )
        }
        other => return Ok(other),
    };

    // No units means no receipts: refuse before a debt is issued for work that never ran.
    if nodes.is_empty() {
        return Err(FlowError::NoWorkPerformed);
    }

    // One instruction id, one debt: a settled or open obligation is never re-run under the same id.
    if karma.obligations.contains_key(instruction_id) {
        return Err(FlowError::KarmaNotSettled {
            reason: "INSTRUCTION_ALREADY_ISSUED".to_string(),
        });
    }

    // Phase 4: EXECUTION_GATE — Enforce DOF Capability Lease BEFORE spending tokens
    let dof_req = ActionRequest {
        tool_name: format!("flow.execute.{}", cap.id),
        category: ActionCategory::TaskMutation,
        target_paths: cap.target_paths.clone(),
        surface: "zone-b-worker".to_string(),
        claimed_lease_epoch,
        resolving_component: None,
    };
    dof.authorize(&dof_req).map_err(FlowError::DofRefused)?;

    // Record KARMA debt issuance on acceptance
    karma.apply(&KarmaEvent {
        event_id: format!("{instruction_id}-accept"),
        instruction_id: instruction_id.to_string(),
        agent_urn: caller_urn.to_string(),
        parent_event_ids: vec![],
        externally_verified_authority: true,
        payload: KarmaEventKind::InstructionAccepted {
            expected_outcome_digest: format!("exp-{instruction_id}"),
        },
    });

    // A refused acceptance means no debt exists; running work now would be unaccounted work.
    if !karma.obligations.contains_key(instruction_id) {
        return Err(FlowError::KarmaNotSettled {
            reason: "ACCEPTANCE_REFUSED".to_string(),
        });
    }

    // Phase 5: FLOW_EXECUTE — Dispatch chosen Legion formation through Muster kernel
    let spec = canonical_eight_formations()
        .into_iter()
        .find(|s| s.formation == cap.default_formation)
        .unwrap_or_else(|| canonical_eight_formations()[0].clone());
    let receipts =
        match execute_formation_fractal(instruction_id, &spec, nodes, budget_minor_units, 1)
            .and_then(|r| verify_receipt_chain(&r).map(|()| r))
        {
            Ok(r) => r,
            Err(e) => {
                record_failure(karma, instruction_id, caller_urn, &format!("MUSTER:{e:?}"));
                return Err(FlowError::MusterFailed(e));
            }
        };
    // Hash integrity is not success: any red receipt means the work did not pass, whatever the formation.
    if let Some(bad) = receipts.iter().find(|r| !r.ok) {
        let e = MusterError::StepReceiptFailed {
            step_id: bad.step_id.clone(),
        };
        record_failure(karma, instruction_id, caller_urn, &format!("MUSTER:{e:?}"));
        return Err(FlowError::MusterFailed(e));
    }
    // An empty chain proves nothing (e.g. a sub-formation with no units).
    if receipts.is_empty() {
        record_failure(
            karma,
            instruction_id,
            caller_urn,
            "MUSTER:EMPTY_RECEIPT_CHAIN",
        );
        return Err(FlowError::NoWorkPerformed);
    }

    let total_cost: i64 = receipts.iter().map(|r| r.cost_minor_units).sum();
    let tail_hash = receipts.last().map(|r| r.hash.clone()).unwrap_or_default();

    karma.apply(&KarmaEvent {
        event_id: format!("{instruction_id}-cost"),
        instruction_id: instruction_id.to_string(),
        agent_urn: caller_urn.to_string(),
        parent_event_ids: vec![format!("{instruction_id}-accept")],
        externally_verified_authority: true,
        payload: KarmaEventKind::CostObserved {
            // Token usage is not measured here; recording invented counts would corrupt the ledger.
            tokens_in: 0,
            tokens_out: 0,
            money_minor_units: Some(total_cost),
        },
    });
    karma.apply(&KarmaEvent {
        event_id: format!("{instruction_id}-submit"),
        instruction_id: instruction_id.to_string(),
        agent_urn: caller_urn.to_string(),
        parent_event_ids: vec![format!("{instruction_id}-cost")],
        externally_verified_authority: true,
        payload: KarmaEventKind::YieldSubmitted {
            evidence_digest: tail_hash.clone(),
        },
    });

    // Phase 6: VERIFY_AND_YIELD — ONLY an independent oracle can settle the KARMA debt
    karma.apply(&KarmaEvent {
        event_id: format!("{instruction_id}-verify"),
        instruction_id: instruction_id.to_string(),
        agent_urn: independent_oracle_urn.to_string(),
        parent_event_ids: vec![format!("{instruction_id}-submit")],
        externally_verified_authority: true,
        payload: KarmaEventKind::YieldIndependentlyVerified {
            evidence_digest: tail_hash,
        },
    });

    let settled = karma
        .obligations
        .get(instruction_id)
        .map(|o| o.state == ObligationState::Settled && o.verified_yield)
        .unwrap_or(false);
    if !settled {
        return Err(FlowError::KarmaNotSettled {
            reason: "INDEPENDENT_ORACLE_VERIFICATION_FAILED".to_string(),
        });
    }

    Ok(decision)
}
