use serde::{Deserialize, Serialize};
use std::collections::{BTreeSet, VecDeque};

/// Pack 1 (TP-RCA-SCM): Reiter HS-DAG minimal hitting sets, Halpern-Pearl counterfactual check,
/// Ochiai suspiciousness, and deterministic ddmin delta debugging.

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CounterfactualWitness {
    pub cause_component: String,
    pub observed_failure_present: bool,
    pub intervention_removed_failure: bool,
    pub is_minimal_subset: bool,
}

impl CounterfactualWitness {
    /// Halpern-Pearl (HP) Modified Actual Causality check.
    pub fn verify_hp_actual_cause(&self) -> Result<(), String> {
        if !self.observed_failure_present {
            return Err("ERR_HP_CAUSE_INVALID: factual condition (X=x and failure) not empirically observed".to_string());
        }
        if !self.intervention_removed_failure {
            return Err(format!(
                "ERR_HP_COUNTERFACTUAL_FAILED: intervening on '{}' did not eliminate failure",
                self.cause_component
            ));
        }
        if !self.is_minimal_subset {
            return Err(format!(
                "ERR_HP_NOT_MINIMAL: cause '{}' is not a minimal subset",
                self.cause_component
            ));
        }
        Ok(())
    }
}

/// Computes exact minimal hitting sets (Reiter HS-DAG BFS) over minimal conflict sets.
/// Handles compound multi-fault outages where no single component explains all conflicts.
pub fn minimal_hitting_sets(
    conflict_sets: &[BTreeSet<String>],
    max_cardinality: usize,
) -> Vec<BTreeSet<String>> {
    let non_empty: Vec<&BTreeSet<String>> = conflict_sets.iter().filter(|c| !c.is_empty()).collect();
    if non_empty.is_empty() {
        return vec![];
    }

    let mut solutions: Vec<BTreeSet<String>> = Vec::new();
    let mut visited: BTreeSet<BTreeSet<String>> = BTreeSet::new();
    let mut queue: VecDeque<BTreeSet<String>> = VecDeque::new();
    queue.push_back(BTreeSet::new());

    while let Some(candidate) = queue.pop_front() {
        // Prune supersets of already-found minimal hitting sets.
        if solutions.iter().any(|sol| sol.is_subset(&candidate)) {
            continue;
        }
        // Find first conflict set not yet hit by candidate.
        let unhit = non_empty
            .iter()
            .find(|conflict| conflict.is_disjoint(&candidate));

        match unhit {
            None => {
                // Remove any strictly larger existing solution (defensive) and push.
                solutions.retain(|s| !candidate.is_subset(s));
                solutions.push(candidate);
            }
            Some(conflict) => {
                if candidate.len() >= max_cardinality {
                    continue;
                }
                for comp in *conflict {
                    let mut next = candidate.clone();
                    next.insert(comp.clone());
                    if visited.insert(next.clone()) {
                        queue.push_back(next);
                    }
                }
            }
        }
    }

    solutions.sort_by(|a, b| a.len().cmp(&b.len()).then_with(|| a.cmp(b)));
    solutions
}

/// Spectrum-Based Fault Localization (Ochiai metric).
pub fn ochiai_score(ef: u64, nf: u64, ep: u64) -> f64 {
    let denom = ((ef + nf) as f64) * ((ef + ep) as f64);
    if denom <= 0.0 {
        0.0
    } else {
        (ef as f64) / denom.sqrt()
    }
}

/// Zeller's ddmin: isolates a 1-minimal failing subset in O(log n) typical tests.
pub fn ddmin<T: Clone, F>(items: &[T], mut fails: F) -> Vec<T>
where
    F: FnMut(&[T]) -> bool,
{
    let mut current = items.to_vec();
    if current.len() <= 1 {
        return current;
    }
    let mut n = 2usize;

    while current.len() >= 2 {
        let chunk_size = (current.len() + n - 1) / n;
        let mut reduced = false;

        // 1. Try individual subsets
        let mut idx = 0;
        while idx < current.len() {
            let end = (idx + chunk_size).min(current.len());
            let subset = &current[idx..end];
            if !subset.is_empty() && subset.len() < current.len() && fails(subset) {
                current = subset.to_vec();
                n = 2;
                reduced = true;
                break;
            }
            idx = end;
        }
        if reduced {
            continue;
        }

        // 2. Try complements
        let mut idx = 0;
        while idx < current.len() {
            let end = (idx + chunk_size).min(current.len());
            let mut complement = Vec::with_capacity(current.len() - (end - idx));
            complement.extend_from_slice(&current[..idx]);
            complement.extend_from_slice(&current[end..]);
            if !complement.is_empty() && fails(&complement) {
                current = complement;
                n = (n.saturating_sub(1)).max(2);
                reduced = true;
                break;
            }
            idx = end;
        }
        if reduced {
            continue;
        }

        if n >= current.len() {
            break;
        }
        n = (n * 2).min(current.len());
    }
    current
}
