use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

/// Pack 6 (TP-PARETO-MECH): Constrained Lexicographic Pareto + Wald Minimax Regret
/// Pack 7 (TP-SEARCH-MCTS): PRM-Guided UCT + Tarjan SCC Acyclicity Check
/// Pack 8 (TP-CONFORMAL-OOD): Split Conformal Prediction + Brier Score + Page CUSUM Drift Alarm

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CandidatePlan {
    pub plan_id: String,
    pub passes_constitutional_safety: bool,
    pub expected_yield: f64,
    pub cost_usd: f64,
    pub latency_sec: f64,
    pub blast_radius: f64,
}

/// Lexicographic constrained Pareto frontier: Safety > Pareto(Yield, -Cost, -Latency, -BlastRadius).
pub fn pareto_frontier(candidates: &[CandidatePlan]) -> Vec<CandidatePlan> {
    let safe: Vec<&CandidatePlan> = candidates
        .iter()
        .filter(|c| c.passes_constitutional_safety)
        .collect();

    safe.iter()
        .copied()
        .filter(|a| {
            !safe.iter().copied().any(|b| {
                let no_worse = b.expected_yield >= a.expected_yield
                    && b.cost_usd <= a.cost_usd
                    && b.latency_sec <= a.latency_sec
                    && b.blast_radius <= a.blast_radius;
                let strictly_better = b.expected_yield > a.expected_yield
                    || b.cost_usd < a.cost_usd
                    || b.latency_sec < a.latency_sec
                    || b.blast_radius < a.blast_radius;
                no_worse && strictly_better
            })
        })
        .cloned()
        .collect()
}

/// Wald Minimax Regret under Knightian uncertainty (uncalibrated priors).
/// `payoffs`: decision_id -> (state_id -> utility).
pub fn minimax_regret_choice(
    payoffs: &BTreeMap<String, BTreeMap<String, f64>>,
) -> Option<(String, f64)> {
    let mut states: BTreeSet<String> = BTreeSet::new();
    for m in payoffs.values() {
        for s in m.keys() {
            states.insert(s.clone());
        }
    }
    if states.is_empty() || payoffs.is_empty() {
        return None;
    }

    let mut best_per_state: BTreeMap<String, f64> = BTreeMap::new();
    for s in &states {
        let best = payoffs
            .values()
            .map(|m| m.get(s).copied().unwrap_or(f64::NEG_INFINITY))
            .fold(f64::NEG_INFINITY, f64::max);
        best_per_state.insert(s.clone(), best);
    }

    payoffs
        .iter()
        .map(|(dec, m)| {
            let max_regret = states
                .iter()
                .map(|s| {
                    let best = best_per_state[s];
                    let actual = m.get(s).copied().unwrap_or(f64::NEG_INFINITY);
                    (best - actual).max(0.0)
                })
                .fold(0.0_f64, f64::max);
            (dec.clone(), max_regret)
        })
        .min_by(|a, b| a.1.total_cmp(&b.1).then_with(|| a.0.cmp(&b.0)))
}

/// PRM-Guided UCT score for bounded verified search (Pack 7).
pub fn uct_prm_score(
    mean_prm_reward: f64,
    total_visits: u64,
    branch_visits: u64,
    exploration_c: f64,
    branch_cost: f64,
    cost_eta: f64,
) -> f64 {
    if branch_visits == 0 {
        return f64::INFINITY;
    }
    let n = (total_visits.max(1)) as f64;
    let nj = branch_visits as f64;
    mean_prm_reward + exploration_c * (n.ln() / nj).sqrt() - cost_eta * branch_cost
}

/// Tarjan Strongly Connected Components (Pack 7): returns any non-trivial cycles in task/contract DAG.
pub fn find_dependency_cycles(graph: &BTreeMap<String, Vec<String>>) -> Vec<Vec<String>> {
    struct State<'a> {
        graph: &'a BTreeMap<String, Vec<String>>,
        index: usize,
        indices: BTreeMap<String, usize>,
        lowlink: BTreeMap<String, usize>,
        stack: Vec<String>,
        on_stack: BTreeSet<String>,
        cycles: Vec<Vec<String>>,
    }

    fn strongconnect(v: &str, st: &mut State<'_>) {
        st.indices.insert(v.to_string(), st.index);
        st.lowlink.insert(v.to_string(), st.index);
        st.index += 1;
        st.stack.push(v.to_string());
        st.on_stack.insert(v.to_string());

        if let Some(neighbors) = st.graph.get(v) {
            for w in neighbors {
                if !st.indices.contains_key(w) {
                    strongconnect(w, st);
                    let lw = st.lowlink[w];
                    let lv = st.lowlink[v];
                    st.lowlink.insert(v.to_string(), lv.min(lw));
                } else if st.on_stack.contains(w) {
                    let iw = st.indices[w];
                    let lv = st.lowlink[v];
                    st.lowlink.insert(v.to_string(), lv.min(iw));
                }
            }
        }

        if st.lowlink[v] == st.indices[v] {
            let mut scc = Vec::new();
            while let Some(w) = st.stack.pop() {
                st.on_stack.remove(&w);
                let done = w == v;
                scc.push(w);
                if done {
                    break;
                }
            }
            let self_loop = scc.len() == 1
                && st
                    .graph
                    .get(&scc[0])
                    .is_some_and(|nbrs| nbrs.contains(&scc[0]));
            if scc.len() > 1 || self_loop {
                scc.sort();
                st.cycles.push(scc);
            }
        }
    }

    let mut all_nodes: BTreeSet<String> = graph.keys().cloned().collect();
    for nbrs in graph.values() {
        for w in nbrs {
            all_nodes.insert(w.clone());
        }
    }

    let mut st = State {
        graph,
        index: 0,
        indices: BTreeMap::new(),
        lowlink: BTreeMap::new(),
        stack: Vec::new(),
        on_stack: BTreeSet::new(),
        cycles: Vec::new(),
    };

    for v in all_nodes {
        if !st.indices.contains_key(&v) {
            strongconnect(&v, &mut st);
        }
    }
    st.cycles
}

/// Split Conformal Prediction quantile threshold q_hat (Pack 8).
pub fn conformal_quantile(calibration_scores: &[f64], alpha: f64) -> Result<f64, String> {
    if calibration_scores.is_empty() {
        return Err("ERR_CONFORMAL_EMPTY_CALIBRATION: cannot calibrate without historical receipts".to_string());
    }
    let mut sorted = calibration_scores.to_vec();
    sorted.sort_by(|a, b| a.total_cmp(b));
    let n = sorted.len();
    let rank = (((n as f64 + 1.0) * (1.0 - alpha.clamp(0.001, 0.5))).ceil() as usize).clamp(1, n);
    Ok(sorted[rank - 1])
}

pub fn conformal_prediction_set(
    candidate_nonconformity: &BTreeMap<String, f64>,
    q_hat: f64,
) -> Vec<String> {
    candidate_nonconformity
        .iter()
        .filter(|&(_, &s)| s <= q_hat)
        .map(|(label, _)| label.clone())
        .collect()
}

/// Strictly proper Brier Score for earned specialist promotion (replaces heuristic efda confidence).
pub fn brier_score(predictions_and_outcomes: &[(f64, bool)]) -> Option<f64> {
    if predictions_and_outcomes.is_empty() {
        return None;
    }
    let sum: f64 = predictions_and_outcomes
        .iter()
        .map(|(p, y)| {
            let yv = if *y { 1.0 } else { 0.0 };
            let diff = p.clamp(0.0, 1.0) - yv;
            diff * diff
        })
        .sum();
    Some(sum / (predictions_and_outcomes.len() as f64))
}

/// Page CUSUM sequential drift alarm (Pack 8): detects silent degradation of specialist priors.
pub fn cusum_drift_alarm(errors: &[f64], baseline_mean: f64, slack_k: f64, alarm_h: f64) -> (bool, f64) {
    let mut g = 0.0_f64;
    let mut max_g = 0.0_f64;
    for &e in errors {
        g = (g + (e - baseline_mean - slack_k)).max(0.0);
        if g > max_g {
            max_g = g;
        }
    }
    (max_g > alarm_h, max_g)
}
