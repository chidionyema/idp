use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

/// Pack 5 (TP-AGM-FALSIFY): de Kleer ATMS Nogood Store, AGM Levi Belief Revision,
/// and Mayo Severe Testing criterion blocking proxy-green verification.

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EpistemicRank {
    Hypothesis = 1,
    FlowInFlight = 2,
    CertifiedEmpirical = 3,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BeliefNode {
    pub belief_id: String,
    pub rank: EpistemicRank,
    pub assumptions: BTreeSet<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct AtmsBeliefBase {
    pub beliefs: BTreeMap<String, BeliefNode>,
    /// Minimal inconsistent assumption sets; any superset is permanently pruned.
    pub nogoods: Vec<BTreeSet<String>>,
}

impl AtmsBeliefBase {
    pub fn record_nogood(&mut self, env: BTreeSet<String>) {
        if env.is_empty() {
            return;
        }
        if self.nogoods.iter().any(|ng| ng.is_subset(&env)) {
            return;
        }
        self.nogoods.retain(|ng| !env.is_subset(ng));
        self.nogoods.push(env);
        // AGM contraction: excise any belief whose assumptions contain a nogood.
        // retain holds a mutable borrow of self.beliefs, so the nogood set is read
        // through a clone rather than through &self (E0502 at this line before the fix).
        let nogoods = self.nogoods.clone();
        self.beliefs
            .retain(|_, b| !nogoods.iter().any(|ng| ng.is_subset(&b.assumptions)));
    }

    pub fn is_environment_nogood(&self, env: &BTreeSet<String>) -> bool {
        self.nogoods.iter().any(|ng| ng.is_subset(env))
    }

    /// AGM Levi Revision: K * phi = (K - ~phi) + phi respecting epistemic entrenchment.
    pub fn revise_add_belief(&mut self, node: BeliefNode) -> Result<(), String> {
        if self.is_environment_nogood(&node.assumptions) {
            return Err(format!(
                "ERR_ATMS_NOGOOD_REGRESSION: belief '{}' depends on a falsified nogood environment",
                node.belief_id
            ));
        }
        if let Some(existing) = self.beliefs.get(&node.belief_id) {
            if existing.rank > node.rank {
                return Err(format!(
                    "ERR_AGM_ENTRENCHMENT_VIOLATION: cannot downgrade '{}' from {:?} to {:?}",
                    node.belief_id, existing.rank, node.rank
                ));
            }
        }
        self.beliefs.insert(node.belief_id.clone(), node);
        Ok(())
    }
}

/// Mayo Severe Testing check: SEV(T, H) = P(fail T | not H) >= 1 - epsilon.
/// Proxy-green checks (e.g., raw.githubusercontent.com returning 200 even when code is broken)
/// have P(fail T | not H) = 0.0 and are rejected mechanically.
pub fn verify_mayo_severity(
    p_fail_given_false: f64,
    required_severity: f64,
    bad_canary_failed: bool,
    good_canary_passed: bool,
) -> Result<(), String> {
    if !bad_canary_failed || !good_canary_passed {
        return Err(format!(
            "ERR_MAYO_CANARY_FAILED: adversarial canary requires bad_failed=true (got {bad_canary_failed}) and good_passed=true (got {good_canary_passed})"
        ));
    }
    if p_fail_given_false < required_severity {
        return Err(format!(
            "ERR_PROXY_GREEN_LOW_SEVERITY: SEV(T,H)={p_fail_given_false:.3} < threshold {required_severity:.3}"
        ));
    }
    Ok(())
}
