use serde::{Deserialize, Serialize};

/// Pack 4 (TP-CONTROL-CBF): Control Barrier Functions (forward invariance),
/// Lyapunov defect-potential convergence, and queueing stability (lambda < mu).

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HostBarrierState {
    pub disk_free_mb: f64,
    pub disk_delta_mb_per_min: f64,
    pub swap_used_mb: f64,
    pub swap_delta_mb_per_min: f64,
    pub load_1m: f64,
    pub active_heavy_sessions: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CbfConfig {
    pub disk_floor_mb: f64,
    pub swap_ceiling_mb: f64,
    pub load_ceiling: f64,
    pub max_heavy_sessions: u32,
    /// Barrier decay rate gamma > 0: requires h_dot + gamma * h >= 0
    pub gamma: f64,
}

impl Default for CbfConfig {
    fn default() -> Self {
        Self {
            disk_floor_mb: 1500.0,
            swap_ceiling_mb: 1500.0,
            load_ceiling: 8.0,
            max_heavy_sessions: 2,
            gamma: 0.5,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CbfVerdict {
    pub safe_for_local_heavy_work: bool,
    pub h_disk: f64,
    pub cbf_disk_margin: f64,
    pub h_swap: f64,
    pub cbf_swap_margin: f64,
    pub required_reflex: String,
}

/// Evaluates forward invariance h_dot(x, u) + gamma * h(x) >= 0 BEFORE the 1500MB cliff is hit.
pub fn evaluate_cbf(state: &HostBarrierState, cfg: &CbfConfig) -> CbfVerdict {
    let h_disk = state.disk_free_mb - cfg.disk_floor_mb;
    let cbf_disk_margin = state.disk_delta_mb_per_min + cfg.gamma * h_disk;

    let h_swap = cfg.swap_ceiling_mb - state.swap_used_mb;
    let h_swap_dot = -state.swap_delta_mb_per_min;
    let cbf_swap_margin = h_swap_dot + cfg.gamma * h_swap;

    let safe = h_disk > 0.0
        && cbf_disk_margin >= 0.0
        && h_swap > 0.0
        && cbf_swap_margin >= 0.0
        && state.load_1m <= cfg.load_ceiling
        && state.active_heavy_sessions <= cfg.max_heavy_sessions;

    let required_reflex = if safe {
        "NOMINAL_LOCAL_ALLOWED".to_string()
    } else if h_disk <= 0.0 || h_swap <= 0.0 {
        "BREACH_SHED_LOAD_RECLAIM_AND_OFFLOAD_CLOUD_CI".to_string()
    } else {
        "PREEMPTIVE_CBF_OFFLOAD_TO_CLOUD_CI".to_string()
    };

    CbfVerdict {
        safe_for_local_heavy_work: safe,
        h_disk,
        cbf_disk_margin,
        h_swap,
        cbf_swap_margin,
        required_reflex,
    }
}

/// Lyapunov progress gate: rejects retry loops when defect potential fails to strictly decrease.
pub fn verify_lyapunov_progress(prev_potential: f64, curr_potential: f64, min_drop: f64) -> Result<(), String> {
    let delta = curr_potential - prev_potential;
    if delta > -min_drop {
        return Err(format!(
            "ERR_LYAPUNOV_NON_CONVERGENT: defect potential delta={delta:.3} failed required drop <= -{min_drop:.3}; halt retry and switch strategy"
        ));
    }
    Ok(())
}

/// Queueing stability check: arrival_rate < service_rate (prevents unbounded not-operational divergence).
pub fn check_queue_stability(arrival_rate_per_hr: f64, certifier_service_rate_per_hr: f64) -> Result<f64, String> {
    if certifier_service_rate_per_hr <= 0.0 {
        return Err("ERR_QUEUE_CERTIFIER_STALLED: service rate mu <= 0; trip systemic admission backpressure".to_string());
    }
    let rho = arrival_rate_per_hr / certifier_service_rate_per_hr;
    if rho >= 1.0 {
        return Err(format!(
            "ERR_QUEUE_UNSTABLE_BACKPRESSURE: utilization rho={rho:.2} >= 1.0; park new feature lanes until certifier drains"
        ));
    }
    Ok(rho)
}
