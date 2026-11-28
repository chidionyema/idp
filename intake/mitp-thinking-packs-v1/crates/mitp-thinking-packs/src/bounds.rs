use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BoundingEnvelope {
    /// S_max: maximum reasoning / tool steps
    pub max_steps: u32,
    /// T_max: maximum wall-clock seconds per stage
    pub max_wall_sec: u64,
    /// C_max: maximum monetary cost in USD micro-units (1_000_000 = $1.00)
    pub max_cost_micro_usd: u64,
    /// D_max: maximum search / recursion depth
    pub max_depth: u32,
    /// Delta I_min: minimum net VOI - lambda*cost required to keep probing
    pub min_net_voi: f64,
    /// K_max: maximum remediation attempts (DROP-2026-1059: <= 3)
    pub max_attempts: u32,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct ExecutionConsumption {
    pub steps_used: u32,
    pub wall_sec_elapsed: u64,
    pub cost_micro_usd_used: u64,
    pub current_depth: u32,
    pub attempts_used: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LyapunovMeasure {
    pub remaining_attempts: u32,
    pub remaining_budget_quanta: u64,
    pub remaining_steps: u32,
}

impl BoundingEnvelope {
    /// Well-founded lexicographic termination measure Phi(t) in N^3.
    pub fn lyapunov_measure(&self, used: &ExecutionConsumption, cost_quantum_micro: u64) -> LyapunovMeasure {
        let q = cost_quantum_micro.max(1);
        LyapunovMeasure {
            remaining_attempts: self.max_attempts.saturating_sub(used.attempts_used),
            remaining_budget_quanta: self.max_cost_micro_usd.saturating_sub(used.cost_micro_usd_used) / q,
            remaining_steps: self.max_steps.saturating_sub(used.steps_used),
        }
    }

    pub fn check_admissible(
        &self,
        used: &ExecutionConsumption,
        next_cost_micro_usd: u64,
    ) -> Result<(), String> {
        if used.attempts_used >= self.max_attempts {
            return Err(format!(
                "ERR_ATTEMPT_CEILING_EXCEEDED: attempts {} >= K_max {}",
                used.attempts_used, self.max_attempts
            ));
        }
        if used.steps_used >= self.max_steps {
            return Err(format!(
                "ERR_STEP_BUDGET_EXCEEDED: steps {} >= S_max {}",
                used.steps_used, self.max_steps
            ));
        }
        if used.wall_sec_elapsed >= self.max_wall_sec {
            return Err(format!(
                "ERR_WALL_CLOCK_GUILLOTINE: elapsed {}s >= T_max {}s",
                used.wall_sec_elapsed, self.max_wall_sec
            ));
        }
        let projected_cost = used.cost_micro_usd_used.saturating_add(next_cost_micro_usd);
        if projected_cost > self.max_cost_micro_usd {
            return Err(format!(
                "ERR_ESCROW_COST_CAP_EXCEEDED: projected {} > C_max {} micro-USD",
                projected_cost, self.max_cost_micro_usd
            ));
        }
        if used.current_depth > self.max_depth {
            return Err(format!(
                "ERR_RECURSION_DEPTH_EXCEEDED: depth {} > D_max {}",
                used.current_depth, self.max_depth
            ));
        }
        Ok(())
    }
}
