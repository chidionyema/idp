use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

/// Pack 2 (TP-BAYES-EIG): Discrete Bayesian posterior with explicit catch-all h_unknown,
/// Lindley EIG, Howard VOI, cost-normalized probe ranking, and Wald SPRT stopping law.

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HypothesisSpace {
    /// Posterior probabilities keyed by hypothesis_id; MUST include "h_unknown" catch-all.
    pub probs: BTreeMap<String, f64>,
}

impl HypothesisSpace {
    pub fn new(mut raw_priors: BTreeMap<String, f64>, unknown_floor: f64) -> Result<Self, String> {
        let floor = unknown_floor.clamp(0.01, 0.5);
        raw_priors
            .entry("h_unknown".to_string())
            .and_modify(|p| {
                if *p < floor {
                    *p = floor;
                }
            })
            .or_insert(floor);

        let sum: f64 = raw_priors.values().copied().filter(|v| *v > 0.0).sum();
        if sum <= 0.0 {
            return Err("ERR_INVALID_PRIOR: total probability mass must be > 0".to_string());
        }
        let probs = raw_priors
            .into_iter()
            .map(|(k, v)| (k, v.max(0.0) / sum))
            .collect();
        Ok(Self { probs })
    }

    pub fn entropy_bits(&self) -> f64 {
        self.probs
            .values()
            .filter(|&&p| p > 1e-12)
            .map(|&p| -p * p.log2())
            .sum()
    }

    /// Bayes rule update given likelihood P(outcome | h) for each h.
    pub fn update(&self, likelihoods: &BTreeMap<String, f64>) -> Result<Self, String> {
        let mut unnorm = BTreeMap::new();
        let mut z = 0.0;
        for (h, &prior) in &self.probs {
            let lik = likelihoods.get(h).copied().unwrap_or(0.5).clamp(1e-9, 1.0);
            let post = prior * lik;
            unnorm.insert(h.clone(), post);
            z += post;
        }
        if z <= 1e-15 {
            return Err("ERR_ZERO_EVIDENCE_LIKELIHOOD: observation impossible under all hypotheses".to_string());
        }
        let probs = unnorm.into_iter().map(|(k, v)| (k, v / z)).collect();
        Ok(Self { probs })
    }

    pub fn map_hypothesis(&self) -> Option<(String, f64)> {
        self.probs
            .iter()
            .max_by(|a, b| a.1.total_cmp(b.1))
            .map(|(k, v)| (k.clone(), *v))
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CandidateProbe {
    pub probe_id: String,
    pub cost_usd: f64,
    /// outcome_label -> (hypothesis_id -> P(outcome | hypothesis))
    pub outcome_likelihoods: BTreeMap<String, BTreeMap<String, f64>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProbeValuation {
    pub probe_id: String,
    pub eig_bits: f64,
    pub voi_utility: f64,
    pub net_value: f64,
    pub voi_per_dollar: f64,
}

/// Compute Lindley Expected Information Gain I(H; Y_a | E_t) in bits.
pub fn expected_information_gain(space: &HypothesisSpace, probe: &CandidateProbe) -> f64 {
    let prior_h = space.entropy_bits();
    let mut expected_post_h = 0.0;

    for lik_map in probe.outcome_likelihoods.values() {
        let p_y: f64 = space
            .probs
            .iter()
            .map(|(h, &p)| p * lik_map.get(h).copied().unwrap_or(0.5).clamp(0.0, 1.0))
            .sum();
        if p_y > 1e-12 {
            if let Ok(post) = space.update(lik_map) {
                expected_post_h += p_y * post.entropy_bits();
            }
        }
    }
    (prior_h - expected_post_h).max(0.0)
}

/// Compute Decision-Theoretic Value of Information VOI_t(a).
/// `utilities`: decision_id -> (hypothesis_id -> utility U(d, h)).
pub fn value_of_information(
    space: &HypothesisSpace,
    probe: &CandidateProbe,
    utilities: &BTreeMap<String, BTreeMap<String, f64>>,
) -> f64 {
    let best_expected_u = |sp: &HypothesisSpace| -> f64 {
        utilities
            .values()
            .map(|u_map| {
                sp.probs
                    .iter()
                    .map(|(h, &p)| p * u_map.get(h).copied().unwrap_or(0.0))
                    .sum::<f64>()
            })
            .fold(f64::NEG_INFINITY, f64::max)
    };

    let base_u = best_expected_u(space);
    if !base_u.is_finite() {
        return 0.0;
    }

    let mut post_expected_u = 0.0;
    for lik_map in probe.outcome_likelihoods.values() {
        let p_y: f64 = space
            .probs
            .iter()
            .map(|(h, &p)| p * lik_map.get(h).copied().unwrap_or(0.5).clamp(0.0, 1.0))
            .sum();
        if p_y > 1e-12 {
            if let Ok(post) = space.update(lik_map) {
                post_expected_u += p_y * best_expected_u(&post);
            }
        }
    }
    (post_expected_u - base_u).max(0.0)
}

pub fn select_best_probe(
    space: &HypothesisSpace,
    probes: &[CandidateProbe],
    utilities: &BTreeMap<String, BTreeMap<String, f64>>,
    cost_weight_lambda: f64,
    min_net_voi: f64,
) -> Option<ProbeValuation> {
    let mut ranked: Vec<ProbeValuation> = probes
        .iter()
        .map(|p| {
            let eig = expected_information_gain(space, p);
            let voi = value_of_information(space, p, utilities);
            let cost = p.cost_usd.max(1e-6);
            let net = voi - cost_weight_lambda * cost;
            ProbeValuation {
                probe_id: p.probe_id.clone(),
                eig_bits: eig,
                voi_utility: voi,
                net_value: net,
                voi_per_dollar: voi / cost,
            }
        })
        .collect();

    ranked.sort_by(|a, b| b.voi_per_dollar.total_cmp(&a.voi_per_dollar));
    ranked.into_iter().find(|v| v.net_value > min_net_voi)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SprtDecision {
    AcceptH1,
    AcceptH0,
    ContinueSampling,
}

/// Wald Sequential Probability Ratio Test (SPRT).
pub fn wald_sprt(likelihood_ratio: f64, alpha: f64, beta: f64) -> SprtDecision {
    let a = (1.0 - beta) / alpha.max(1e-9);
    let b = beta / (1.0 - alpha).max(1e-9);
    if likelihood_ratio >= a {
        SprtDecision::AcceptH1
    } else if likelihood_ratio <= b {
        SprtDecision::AcceptH0
    } else {
        SprtDecision::ContinueSampling
    }
}
