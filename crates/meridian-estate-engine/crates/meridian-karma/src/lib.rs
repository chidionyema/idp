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
    /// Every agent that has ever held this debt, in order. Never shrinks.
    pub custody_chain: Vec<String>,
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
    fn gap(&mut self, ev: &KarmaEvent, reason: &str) {
        self.gaps.push(KarmaGap {
            event_id: ev.event_id.clone(),
            reason: reason.to_string(),
        });
    }

    pub fn apply(&mut self, ev: &KarmaEvent) {
        // A blank identity cannot be held to a debt: refuse it before it can key anything.
        if [&ev.event_id, &ev.instruction_id, &ev.agent_urn]
            .iter()
            .any(|f| f.trim().is_empty())
        {
            self.gap(ev, "BLANK_IDENTITY");
            return;
        }
        if self.seen_events.contains(&ev.event_id) {
            self.gap(ev, "DUPLICATE_EVENT_IGNORED");
            return;
        }
        if !ev.externally_verified_authority {
            self.gap(ev, "UNVERIFIED_EXTERNAL_AUTHORITY");
            return;
        }
        for parent in &ev.parent_event_ids {
            if !self.seen_events.contains(parent) {
                self.gap(ev, "CAUSAL_PARENT_NOT_YET_OBSERVED");
                return;
            }
        }

        if let KarmaEventKind::InstructionAccepted { .. } = &ev.payload {
            // A debt is issued once per instruction; re-accepting must never reset its ledger.
            if self.obligations.contains_key(&ev.instruction_id) {
                self.gap(ev, "INSTRUCTION_ALREADY_ISSUED");
                return;
            }
            self.obligations.insert(
                ev.instruction_id.clone(),
                ObligationRecord {
                    instruction_id: ev.instruction_id.clone(),
                    initial_agent: ev.agent_urn.clone(),
                    current_agent: ev.agent_urn.clone(),
                    custody_chain: vec![ev.agent_urn.clone()],
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
            return;
        }

        // Every other event mutates an existing debt. Dropping one silently would look like
        // "nothing happened", so an unknown obligation is a recorded gap.
        let Some(ob) = self.obligations.get_mut(&ev.instruction_id) else {
            self.gap(ev, "UNKNOWN_OBLIGATION");
            return;
        };

        let refusal: Option<&str> = match &ev.payload {
            KarmaEventKind::InstructionAccepted { .. } => None,
            KarmaEventKind::CostObserved {
                tokens_in,
                tokens_out,
                money_minor_units,
            } => {
                if matches!(money_minor_units, Some(m) if *m < 0) {
                    // Negative money would erase recorded cost.
                    Some("NEGATIVE_COST_REFUSED")
                } else {
                    ob.tokens_in = ob.tokens_in.saturating_add(*tokens_in);
                    ob.tokens_out = ob.tokens_out.saturating_add(*tokens_out);
                    if let Some(m) = money_minor_units {
                        ob.money_minor_units =
                            Some(ob.money_minor_units.unwrap_or(0).saturating_add(*m));
                    }
                    None
                }
            }
            KarmaEventKind::AncestralFailure {
                ancestor_event_id, ..
            } => {
                ob.open_ancestor_failures.insert(ancestor_event_id.clone());
                // A settled debt with an open ancestral failure is not settled.
                if ob.state == ObligationState::Settled || ob.verified_yield {
                    ob.verified_yield = false;
                    ob.state = ObligationState::AwaitingIndependentYield;
                }
                None
            }
            KarmaEventKind::OwnershipHandback {
                successor_agent_urn,
            } => {
                if successor_agent_urn.trim().is_empty() {
                    Some("BLANK_IDENTITY")
                } else if ev.agent_urn != ob.current_agent {
                    Some("HANDBACK_NOT_BY_CURRENT_CUSTODIAN")
                } else {
                    // Preserves `initial_agent` and `open_ancestor_failures` without erasure.
                    ob.current_agent = successor_agent_urn.clone();
                    if !ob.custody_chain.contains(successor_agent_urn) {
                        ob.custody_chain.push(successor_agent_urn.clone());
                    }
                    None
                }
            }
            KarmaEventKind::CorrectionVerified {
                ancestor_event_id, ..
            } => {
                // Anyone who has ever held the debt is party to it and cannot certify a correction.
                if ob.custody_chain.contains(&ev.agent_urn) {
                    Some("SELF_CERTIFIED_CORRECTION_FORBIDDEN")
                } else {
                    ob.open_ancestor_failures.remove(ancestor_event_id);
                    None
                }
            }
            KarmaEventKind::YieldSubmitted { evidence_digest } => {
                if ob.state == ObligationState::Settled {
                    // Settled is terminal: resubmission must not rewrite settled evidence.
                    Some("OBLIGATION_ALREADY_SETTLED")
                } else {
                    ob.submitted_digest = Some(evidence_digest.clone());
                    ob.submitted_by = Some(ev.agent_urn.clone());
                    ob.state = ObligationState::AwaitingIndependentYield;
                    None
                }
            }
            KarmaEventKind::YieldIndependentlyVerified { evidence_digest } => {
                let matches_digest =
                    ob.submitted_digest.as_deref() == Some(evidence_digest.as_str());
                let is_independent = ob.submitted_by.as_deref() != Some(ev.agent_urn.as_str())
                    && !ob.custody_chain.contains(&ev.agent_urn);
                if matches_digest && is_independent && ob.open_ancestor_failures.is_empty() {
                    ob.verified_yield = true;
                    ob.state = ObligationState::Settled;
                    None
                } else {
                    Some("SELF_GRADED_OR_UNLINKED_YIELD")
                }
            }
        };

        match refusal {
            Some(reason) => self.gap(ev, reason),
            None => {
                self.seen_events.insert(ev.event_id.clone());
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
