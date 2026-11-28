//! KARMA: Causal Debt Ledger & Epistemic Yield Firewall (`meridian-karma`).
//!
//! Enforces `2026-11-12-karma-operating-doctrine.md` in compiled Rust:
//!   - An instruction is a debt issuance ONLY when accepted by verified external authority.
//!   - Out-of-order causality (missing parent_event_ids) is rejected, never sorted by wall clock.
//!   - A green CI run is `ExecutionReportedSuccessNotYield`, NEVER settled yield.
//!   - Self-graded yield (verifier == submitting actor) is rejected (`SelfGradedYieldForbidden`).
//!   - Ancestral failure attribution survives handover without erasure.

use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ObligationState {
    Open,
    AwaitingIndependentYield,
    Settled,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum KarmaEventKind {
    InstructionAccepted {
        expected_outcome_digest: String,
    },
    CostObserved {
        tokens_in: u64,
        tokens_out: u64,
        money_minor_units: Option<i64>,
    },
    AncestralFailure {
        ancestor_event_id: String,
        failure_class: String,
    },
    OwnershipHandback {
        successor_agent_urn: String,
    },
    CorrectionVerified {
        ancestor_event_id: String,
        falsifier_digest: String,
    },
    YieldSubmitted {
        evidence_digest: String,
    },
    YieldIndependentlyVerified {
        evidence_digest: String,
    },
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct KarmaEvent {
    pub event_id: String,
    pub instruction_id: String,
    pub agent_urn: String,
    pub parent_event_ids: Vec<String>,
    pub externally_verified_authority: bool,
    pub payload: KarmaEventKind,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct KarmaGap {
    pub event_id: String,
    pub reason: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ObligationRecord {
    pub instruction_id: String,
    pub initial_agent: String,
    pub current_agent: String,
    pub state: ObligationState,
    pub tokens_in: u64,
    pub tokens_out: u64,
    pub money_minor_units: Option<i64>,
    pub submitted_digest: Option<String>,
    pub submitted_by: Option<String>,
    pub verified_yield: bool,
    pub open_ancestor_failures: HashSet<String>,
}

#[derive(Clone, Debug, Default)]
pub struct KarmaProjection {
    pub obligations: BTreeMap<String, ObligationRecord>,
    pub gaps: Vec<KarmaGap>,
    seen_events: HashSet<String>,
}

impl KarmaProjection {
    pub fn apply(&mut self, ev: &KarmaEvent) {
        if self.seen_events.contains(&ev.event_id) {
            self.gaps.push(KarmaGap {
                event_id: ev.event_id.clone(),
                reason: "DUPLICATE_EVENT_IGNORED".to_string(),
            });
            return;
        }
        if !ev.externally_verified_authority {
            self.gaps.push(KarmaGap {
                event_id: ev.event_id.clone(),
                reason: "UNVERIFIED_EXTERNAL_AUTHORITY".to_string(),
            });
            return;
        }
        for parent in &ev.parent_event_ids {
            if !self.seen_events.contains(parent) {
                self.gaps.push(KarmaGap {
                    event_id: ev.event_id.clone(),
                    reason: "CAUSAL_PARENT_NOT_YET_OBSERVED".to_string(),
                });
                return;
            }
        }

        match &ev.payload {
            KarmaEventKind::InstructionAccepted { .. } => {
                // A debt is issued once per instruction; re-accepting must never reset its ledger.
                if self.obligations.contains_key(&ev.instruction_id) {
                    self.gaps.push(KarmaGap {
                        event_id: ev.event_id.clone(),
                        reason: "INSTRUCTION_ALREADY_ISSUED".to_string(),
                    });
                    return;
                }
                self.obligations.insert(
                    ev.instruction_id.clone(),
                    ObligationRecord {
                        instruction_id: ev.instruction_id.clone(),
                        initial_agent: ev.agent_urn.clone(),
                        current_agent: ev.agent_urn.clone(),
                        state: ObligationState::Open,
                        tokens_in: 0,
                        tokens_out: 0,
                        money_minor_units: None,
                        submitted_digest: None,
                        submitted_by: None,
                        verified_yield: false,
                        open_ancestor_failures: HashSet::new(),
                    },
                );
                self.seen_events.insert(ev.event_id.clone());
            }
            KarmaEventKind::CostObserved {
                tokens_in,
                tokens_out,
                money_minor_units,
            } => {
                if let Some(ob) = self.obligations.get_mut(&ev.instruction_id) {
                    ob.tokens_in = ob.tokens_in.saturating_add(*tokens_in);
                    ob.tokens_out = ob.tokens_out.saturating_add(*tokens_out);
                    if let Some(m) = money_minor_units {
                        ob.money_minor_units =
                            Some(ob.money_minor_units.unwrap_or(0).saturating_add(*m));
                    }
                    self.seen_events.insert(ev.event_id.clone());
                } else {
                    self.gaps.push(KarmaGap {
                        event_id: ev.event_id.clone(),
                        reason: "UNKNOWN_OBLIGATION".to_string(),
                    });
                }
            }
            KarmaEventKind::AncestralFailure {
                ancestor_event_id, ..
            } => {
                if let Some(ob) = self.obligations.get_mut(&ev.instruction_id) {
                    ob.open_ancestor_failures.insert(ancestor_event_id.clone());
                    self.seen_events.insert(ev.event_id.clone());
                }
            }
            KarmaEventKind::OwnershipHandback {
                successor_agent_urn,
            } => {
                if let Some(ob) = self.obligations.get_mut(&ev.instruction_id) {
                    // Preserves `initial_agent` and `open_ancestor_failures` without erasure
                    ob.current_agent = successor_agent_urn.clone();
                    self.seen_events.insert(ev.event_id.clone());
                }
            }
            KarmaEventKind::CorrectionVerified {
                ancestor_event_id, ..
            } => {
                if let Some(ob) = self.obligations.get_mut(&ev.instruction_id) {
                    if ev.agent_urn != ob.current_agent && ev.agent_urn != ob.initial_agent {
                        ob.open_ancestor_failures.remove(ancestor_event_id);
                        self.seen_events.insert(ev.event_id.clone());
                    } else {
                        self.gaps.push(KarmaGap {
                            event_id: ev.event_id.clone(),
                            reason: "SELF_CERTIFIED_CORRECTION_FORBIDDEN".to_string(),
                        });
                    }
                }
            }
            KarmaEventKind::YieldSubmitted { evidence_digest } => {
                if let Some(ob) = self.obligations.get_mut(&ev.instruction_id) {
                    ob.submitted_digest = Some(evidence_digest.clone());
                    ob.submitted_by = Some(ev.agent_urn.clone());
                    ob.state = ObligationState::AwaitingIndependentYield;
                    self.seen_events.insert(ev.event_id.clone());
                }
            }
            KarmaEventKind::YieldIndependentlyVerified { evidence_digest } => {
                if let Some(ob) = self.obligations.get_mut(&ev.instruction_id) {
                    let matches_digest =
                        ob.submitted_digest.as_deref() == Some(evidence_digest.as_str());
                    let is_independent = ob.submitted_by.as_deref() != Some(ev.agent_urn.as_str())
                        && ob.current_agent != ev.agent_urn;
                    if matches_digest && is_independent && ob.open_ancestor_failures.is_empty() {
                        ob.verified_yield = true;
                        ob.state = ObligationState::Settled;
                        self.seen_events.insert(ev.event_id.clone());
                    } else {
                        self.gaps.push(KarmaGap {
                            event_id: ev.event_id.clone(),
                            reason: "SELF_GRADED_OR_UNLINKED_YIELD".to_string(),
                        });
                    }
                }
            }
        }
    }

    pub fn unresolved_ids(&self) -> Vec<String> {
        self.obligations
            .values()
            .filter(|o| !o.verified_yield)
            .map(|o| o.instruction_id.clone())
            .collect()
    }
}
