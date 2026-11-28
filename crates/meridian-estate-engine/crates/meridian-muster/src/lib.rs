//! LEGION / Muster Engine (`meridian-muster`).
//!
//! Implements `legion-muster-design.md` (5 execution kernels K1-K5, modular fractal recursion,
//! SHA-256 hash-chained receipts, and 30/20/20/15/15 scorecard with 24h staleness halving and
//! 0.60 shadow demotion) driving ALL 8 canonical Legion formations as data compositions.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// The ONLY 5 Execution Kernels (P4: Kernels over implementations).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionKernel {
    K1Chain,   // Sequential / topological DAG with strict contracts
    K2Scatter, // Bounded map-reduce fan-out over N cheap workers
    K3Debate,  // Bounded adversarial loop + independent judge receipt
    K4Bracket, // Cost-aware tournament with Elo updates
    K5Gate,    // Deterministic / HITL approval gate
}

/// All 8 Canonical Legion Formations (from `legionRuns.ts` + Muster compositions).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum LegionFormation {
    Sniper,      // 1: Single scoped worker, red-to-green repair (K1[1] + K5)
    Phalanx,     // 2: Parallel disjoint workers + combined-SHA proof (K2 -> K5)
    Pipeline,    // 3: Durable stage handoffs + crash recovery (K1[stages] + Castra snapshots)
    Swarm,       // 4: Leases, fencing, bounded work stealing (K2[fenced] + blackboard)
    Centurion,   // 5: Dependency DAG + supervised leaves (Fractal K1 tree / LegateStaff)
    Adversarial, // 6: Independent red & blue workers + judge (K3 Pincer / Inquisitor)
    Tournament,  // 7: Independent candidates + measured winner + Elo (K4 Bracket)
    Sieve,       // 8: Mutation survivors + falsifying tests (K2 mutants -> K3/K5 falsifiers)
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct FormationSpec {
    pub id: u8,
    pub formation: LegionFormation,
    pub muster_equivalent: &'static str,
    pub kernels: Vec<ExecutionKernel>,
    pub max_fanout: usize,
    pub max_recursion_depth: u8,
    pub max_turns: u8,
    pub requires_independent_judge: bool,
}

/// Returns the exact data-driven specification for all 8 canonical Legion formations.
pub fn canonical_eight_formations() -> Vec<FormationSpec> {
    vec![
        FormationSpec {
            id: 1,
            formation: LegionFormation::Sniper,
            muster_equivalent: "Single-Unit K1 + Praetor K5",
            kernels: vec![ExecutionKernel::K1Chain, ExecutionKernel::K5Gate],
            max_fanout: 1,
            max_recursion_depth: 1,
            max_turns: 4,
            requires_independent_judge: false,
        },
        FormationSpec {
            id: 2,
            formation: LegionFormation::Phalanx,
            muster_equivalent: "Line: Phalanx / Cohort (K2 disjoint + combined-SHA K5)",
            kernels: vec![ExecutionKernel::K2Scatter, ExecutionKernel::K5Gate],
            max_fanout: 8,
            max_recursion_depth: 2,
            max_turns: 2,
            requires_independent_judge: false,
        },
        FormationSpec {
            id: 3,
            formation: LegionFormation::Pipeline,
            muster_equivalent: "Defensive/Line: Castra + Echelon (K1 durable stages)",
            kernels: vec![ExecutionKernel::K1Chain, ExecutionKernel::K5Gate],
            max_fanout: 4,
            max_recursion_depth: 2,
            max_turns: 6,
            requires_independent_judge: false,
        },
        FormationSpec {
            id: 4,
            formation: LegionFormation::Swarm,
            muster_equivalent: "Maneuver: Maniple / Velites (K2 leased work-stealing)",
            kernels: vec![ExecutionKernel::K2Scatter],
            max_fanout: 12,
            max_recursion_depth: 2,
            max_turns: 3,
            requires_independent_judge: false,
        },
        FormationSpec {
            id: 5,
            formation: LegionFormation::Centurion,
            muster_equivalent: "Command: LegateStaff / PrimusPilus (Fractal K1 DAG)",
            kernels: vec![
                ExecutionKernel::K1Chain,
                ExecutionKernel::K2Scatter,
                ExecutionKernel::K5Gate,
            ],
            max_fanout: 8,
            max_recursion_depth: 3,
            max_turns: 4,
            requires_independent_judge: false,
        },
        FormationSpec {
            id: 6,
            formation: LegionFormation::Adversarial,
            muster_equivalent: "Contest: Pincer / RedTeam / Inquisitor (K3 Debate)",
            kernels: vec![ExecutionKernel::K3Debate, ExecutionKernel::K5Gate],
            max_fanout: 2,
            max_recursion_depth: 2,
            max_turns: 4,
            requires_independent_judge: true,
        },
        FormationSpec {
            id: 7,
            formation: LegionFormation::Tournament,
            muster_equivalent: "Contest: Tournament (K4 Bracket + Elo)",
            kernels: vec![ExecutionKernel::K4Bracket, ExecutionKernel::K5Gate],
            max_fanout: 6,
            max_recursion_depth: 2,
            max_turns: 2,
            requires_independent_judge: true,
        },
        FormationSpec {
            id: 8,
            formation: LegionFormation::Sieve,
            muster_equivalent: "Siege: Inquisitor + Fabri (K2 mutants -> K3 falsifiers -> K5)",
            kernels: vec![
                ExecutionKernel::K2Scatter,
                ExecutionKernel::K3Debate,
                ExecutionKernel::K5Gate,
            ],
            max_fanout: 8,
            max_recursion_depth: 2,
            max_turns: 3,
            requires_independent_judge: true,
        },
    ]
}

/// Fractal node: every unit OR composite formation implements the exact same RunSpec -> Receipt contract.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum FractalNode {
    Unit {
        unit_id: String,
        cost_minor_units: i64,
        passed: bool,
    },
    SubFormation {
        formation: LegionFormation,
        children: Vec<FractalNode>,
    },
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct StepReceipt {
    pub run_id: String,
    pub step_id: String,
    pub formation: LegionFormation,
    pub ok: bool,
    pub cost_minor_units: i64,
    pub prev_hash: String,
    pub hash: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum MusterError {
    RecursionDepthExceeded { depth: u8, max_depth: u8 },
    RunawayFanout { requested: usize, max_fanout: usize },
    BudgetExhausted { spent: i64, ceiling: i64 },
    StepReceiptFailed { step_id: String },
    ChainTampered { index: usize },
}

fn sha256_link(prev: &str, run_id: &str, step_id: &str, ok: bool, cost: i64) -> String {
    let mut h = Sha256::new();
    h.update(format!("{prev}|{run_id}|{step_id}|{ok}|{cost}").as_bytes());
    hex::encode(h.finalize())
}

/// Executes any formation fractally under P1 (receipt-gated), F4 (budget ceiling), and F6 (fan-out cap).
pub fn execute_formation_fractal(
    run_id: &str,
    spec: &FormationSpec,
    nodes: &[FractalNode],
    budget_ceiling_minor_units: i64,
    depth: u8,
) -> Result<Vec<StepReceipt>, MusterError> {
    if depth > spec.max_recursion_depth {
        return Err(MusterError::RecursionDepthExceeded {
            depth,
            max_depth: spec.max_recursion_depth,
        });
    }
    if nodes.len() > spec.max_fanout {
        return Err(MusterError::RunawayFanout {
            requested: nodes.len(),
            max_fanout: spec.max_fanout,
        });
    }

    let mut chain: Vec<StepReceipt> = Vec::new();
    let mut prev = "0".repeat(64);
    let mut spent: i64 = 0;

    for (idx, node) in nodes.iter().enumerate() {
        match node {
            FractalNode::Unit {
                unit_id,
                cost_minor_units,
                passed,
            } => {
                spent = spent.saturating_add(*cost_minor_units);
                if spent > budget_ceiling_minor_units {
                    return Err(MusterError::BudgetExhausted {
                        spent,
                        ceiling: budget_ceiling_minor_units,
                    });
                }
                let step_id = format!("d{depth}-s{idx}-{unit_id}");
                let hash = sha256_link(&prev, run_id, &step_id, *passed, *cost_minor_units);
                let rcpt = StepReceipt {
                    run_id: run_id.to_string(),
                    step_id: step_id.clone(),
                    formation: spec.formation,
                    ok: *passed,
                    cost_minor_units: *cost_minor_units,
                    prev_hash: prev,
                    hash: hash.clone(),
                };
                prev = hash;
                chain.push(rcpt);
                // K1 stops the chain on a red step; K5 is a gate, so no red unit may pass it either.
                if !passed
                    && (spec.kernels.contains(&ExecutionKernel::K1Chain)
                        || spec.kernels.contains(&ExecutionKernel::K5Gate))
                {
                    return Err(MusterError::StepReceiptFailed { step_id });
                }
            }
            FractalNode::SubFormation {
                formation,
                children,
            } => {
                let sub_spec = canonical_eight_formations()
                    .into_iter()
                    .find(|s| s.formation == *formation)
                    .unwrap_or_else(|| spec.clone());
                let sub_chain = execute_formation_fractal(
                    run_id,
                    &sub_spec,
                    children,
                    budget_ceiling_minor_units - spent,
                    depth + 1,
                )?;
                for r in sub_chain {
                    spent = spent.saturating_add(r.cost_minor_units);
                    let hash = sha256_link(&prev, run_id, &r.step_id, r.ok, r.cost_minor_units);
                    chain.push(StepReceipt {
                        prev_hash: prev,
                        hash: hash.clone(),
                        ..r
                    });
                    prev = hash;
                }
            }
        }
    }
    Ok(chain)
}

pub fn verify_receipt_chain(chain: &[StepReceipt]) -> Result<(), MusterError> {
    let mut prev = "0".repeat(64);
    for (i, r) in chain.iter().enumerate() {
        if r.prev_hash != prev {
            return Err(MusterError::ChainTampered { index: i });
        }
        let want = sha256_link(
            &r.prev_hash,
            &r.run_id,
            &r.step_id,
            r.ok,
            r.cost_minor_units,
        );
        if r.hash != want {
            return Err(MusterError::ChainTampered { index: i });
        }
        prev = r.hash.clone();
    }
    Ok(())
}

/// Deterministic Scorecard (from `legion/scorecard.py`): 30/20/20/15/15, >24h halves, <0.60 shadow.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct LegionScoreInput {
    pub legion: String,
    pub success_rate: f64,
    pub cost_efficiency: f64,
    pub latency_score: f64,
    pub audit_integrity: f64,
    pub uptime: f64,
    pub proof_age_hours: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct LegionScoreOutput {
    pub legion: String,
    pub composite: f64,
    pub proof_stale: bool,
    pub status: String, // "active" | "shadow"
}

pub fn score_legion(inp: &LegionScoreInput) -> LegionScoreOutput {
    let mut composite = inp.success_rate * 0.30
        + inp.cost_efficiency * 0.20
        + inp.latency_score * 0.20
        + inp.audit_integrity * 0.15
        + inp.uptime * 0.15;
    let stale = inp.proof_age_hours > 24.0;
    if stale {
        composite *= 0.5;
    }
    let rounded = (composite * 10_000.0).round() / 10_000.0;
    LegionScoreOutput {
        legion: inp.legion.clone(),
        composite: rounded,
        proof_stale: stale,
        status: if rounded < 0.60 { "shadow" } else { "active" }.to_string(),
    }
}
