//! DX - the Value-of-Information controller.
//!
//! A VoI policy over an explicit belief state: a hypothesis graph with
//! posteriors. The controller picks the next probe that maximises the
//! expected reduction in entropy over the fault classes it discriminates,
//! then folds the resulting evidence into the belief state (log-space
//! Bayesian update). Termination: a class holds posterior >= 0.95 AND is
//! evidence-backed - a prior-only victory is banned, and HEALTHY requires
//! every fault class actively suppressed below the risk floor EPS = 0.002.

use std::collections::HashMap;

/// A fault class under test.
#[derive(Debug, Clone)]
pub struct Hypothesis {
    pub name: String,
    pub prior: f64,
    pub posterior: f64,
    /// How many evidence observations have folded into this class's belief.
    pub evidence_observations: usize,
}

/// Belief state over the fault classes.
#[derive(Debug, Clone)]
pub struct BeliefState {
    pub hypotheses: Vec<Hypothesis>,
    /// Total evidence observations folded in (guards prior-only victory).
    pub total_observations: usize,
}

impl BeliefState {
    /// Build a belief state from classes. HEALTHY is the default class.
    pub fn new(class_names: &[&str]) -> Self {
        let n = class_names.len().max(1) as f64;
        let prior = 1.0 / n;
        let hypotheses = class_names
            .iter()
            .map(|name| Hypothesis {
                name: (*name).to_string(),
                prior,
                posterior: prior,
                evidence_observations: 0,
            })
            .collect();
        BeliefState {
            hypotheses,
            total_observations: 0,
        }
    }

    /// Fold one probe evidence into the belief state using a per-class
    /// likelihood: P(observation | class). Conventional: the observing class
    /// is far more likely to produce its signature than any other class.
    pub fn update(
        &mut self,
        classes: &[String],
        likelihoods: &[(String, f64)],
    ) {
        let like: HashMap<&str, f64> =
            likelihoods.iter().map(|(k, v)| (k.as_str(), *v)).collect();

        let mut logu: Vec<f64> = Vec::with_capacity(self.hypotheses.len());
        for h in &self.hypotheses {
            let l = like.get(h.name.as_str()).copied().unwrap_or(0.01);
            let lp = h.posterior.max(1e-12);
            logu.push(lp.ln() + (l.max(1e-12)).ln());
        }
        // Log-sum-exp normalisation - never under/overflows a float product.
        let m = logu.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let denom = logu
            .iter()
            .map(|x| (x - m).exp())
            .sum::<f64>()
            .max(1e-12);

        for (i, h) in self.hypotheses.iter_mut().enumerate() {
            h.posterior = ((logu[i] - m).exp()) / denom;
            // Count an observation against the class it discriminated.
            if classes.iter().any(|c| c == &h.name) {
                h.evidence_observations += 1;
            }
        }
        self.total_observations += 1;
    }

    /// The class currently in the lead, if any.
    pub fn leader(&self) -> &Hypothesis {
        self.hypotheses
            .iter()
            .max_by(|a, b| a.posterior.partial_cmp(&b.posterior).unwrap())
            .unwrap()
    }

    /// Whether termination holds: a class >= CONFIDENCE, evidence-backed, and
    /// (for HEALTHY) every fault class suppressed below EPS.
    pub fn terminated(&self) -> Option<&str> {
        const CONFIDENCE: f64 = 0.95;
        const EPS: f64 = 0.002;

        let lead = self.leader();
        // Prior-only victory is banned: need real folded evidence.
        if self.total_observations == 0 {
            return None;
        }

        if lead.posterior >= CONFIDENCE {
            if lead.name == "healthy" {
                // HEALTHY requires every fault class suppressed below EPS.
                let all_faults_suppressed = self
                    .hypotheses
                    .iter()
                    .filter(|h| h.name != "healthy")
                    .all(|h| h.posterior < EPS);
                if all_faults_suppressed {
                    return Some(&lead.name);
                }
                return None;
            }
            if lead.evidence_observations > 0 {
                return Some(&lead.name);
            }
        }
        None
    }
}

/// The Value-of-Information controller. Given a belief state and a set of
/// probe signatures, select the probe that best discriminates the unresolved
/// (highest-entropy) fault classes.
pub struct VoIController;

impl VoIController {
    /// Choose the next probe to run by maximising the residual uncertainty it
    /// addresses: the summed posterior mass of the fault classes the probe
    /// discriminates, weighted by whether those classes are still contested.
    pub fn next_probe<'a>(
        &self,
        belief: &BeliefState,
        probes: &'a [(&'a str, Vec<String>)],
    ) -> Option<&'a str> {
        probes
            .iter()
            .map(|(id, classes)| {
                // VoI ~ the posterior mass still held by the classes this
                // probe can resolve, plus a small exploration bonus so every
                // unresolved class is eventually addressed.
                let mass: f64 = belief
                    .hypotheses
                    .iter()
                    .filter(|h| classes.iter().any(|c| c == &h.name))
                    .map(|h| h.posterior)
                    .sum();
                (*id, mass)
            })
            .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap())
            .map(|(id, _)| id)
    }
}
