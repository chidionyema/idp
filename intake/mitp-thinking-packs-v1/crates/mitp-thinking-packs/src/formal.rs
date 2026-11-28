use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

/// Pack 3 (TP-FORMAL-SMT): Hoare pre-/post-condition contract verifier,
/// minimal unsatisfiable-core deadlock localizer, bounded TLA+ liveness check, and CEGIS accumulator.

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PredicateCheck {
    pub name: String,
    pub satisfied: bool,
    pub observed_evidence: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct HoareContract {
    pub action_name: String,
    pub preconditions: Vec<PredicateCheck>,
    pub postconditions: Vec<PredicateCheck>,
}

impl HoareContract {
    pub fn verify_preconditions(&self) -> Result<(), String> {
        let failed: Vec<String> = self
            .preconditions
            .iter()
            .filter(|p| !p.satisfied)
            .map(|p| format!("{} ({})", p.name, p.observed_evidence))
            .collect();
        if failed.is_empty() {
            Ok(())
        } else {
            Err(format!(
                "ERR_HOARE_PRECONDITION_FAILED on '{}': [{}]",
                self.action_name,
                failed.join("; ")
            ))
        }
    }

    pub fn verify_postconditions(&self) -> Result<(), String> {
        let failed: Vec<String> = self
            .postconditions
            .iter()
            .filter(|p| !p.satisfied)
            .map(|p| format!("{} ({})", p.name, p.observed_evidence))
            .collect();
        if failed.is_empty() {
            Ok(())
        } else {
            Err(format!(
                "ERR_HOARE_POSTCONDITION_FAILED on '{}': [{}]",
                self.action_name,
                failed.join("; ")
            ))
        }
    }
}

/// Horn-style rule constraint for deterministic minimal UNSAT-core localization (e.g., hook deadlocks).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PolicyRule {
    pub rule_id: String,
    /// Action/fact allowed or forbidden under this rule.
    pub allows: BTreeSet<String>,
    pub forbids: BTreeSet<String>,
    pub requires_one_of: BTreeSet<String>,
}

/// Detects whether the rule set leaves zero admissible recovery actions and extracts a minimal UNSAT core.
pub fn find_minimal_unsat_core(
    rules: &[PolicyRule],
    candidate_actions: &BTreeSet<String>,
) -> Option<Vec<String>> {
    let is_sat = |subset: &[&PolicyRule]| -> bool {
        candidate_actions.iter().any(|act| {
            subset.iter().all(|r| {
                let not_forbidden = !r.forbids.contains(act);
                let in_required = r.requires_one_of.is_empty() || r.requires_one_of.contains(act);
                let in_allowed = r.allows.is_empty() || r.allows.contains(act);
                not_forbidden && in_required && in_allowed
            })
        })
    };

    let all_refs: Vec<&PolicyRule> = rules.iter().collect();
    if is_sat(&all_refs) {
        return None;
    }

    // Deletion-based minimal unsatisfiable core extraction (O(|rules|)).
    let mut core = all_refs;
    let mut i = 0;
    while i < core.len() {
        let mut trial = Vec::with_capacity(core.len() - 1);
        trial.extend_from_slice(&core[..i]);
        trial.extend_from_slice(&core[i + 1..]);
        if !is_sat(&trial) {
            core = trial;
        } else {
            i += 1;
        }
    }

    Some(core.into_iter().map(|r| r.rule_id.clone()).collect())
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CegisLoop {
    pub counterexamples: Vec<String>,
}

impl CegisLoop {
    pub fn record_counterexample(&mut self, cx: impl Into<String>) {
        let s = cx.into();
        if !self.counterexamples.contains(&s) {
            self.counterexamples.push(s);
        }
    }
}

/// Bounded TLA+ liveness check: Triggered => <>_{<= delta_t} Resolved.
pub fn check_bounded_liveness(
    triggered_at_sec: u64,
    now_sec: u64,
    deadline_sec: u64,
    resolved: bool,
) -> Result<(), String> {
    if resolved {
        return Ok(());
    }
    let elapsed = now_sec.saturating_sub(triggered_at_sec);
    if elapsed > deadline_sec {
        return Err(format!(
            "ERR_BOUNDED_LIVENESS_VIOLATION: unresolved for {}s > deadline {}s",
            elapsed, deadline_sec
        ));
    }
    Ok(())
}
