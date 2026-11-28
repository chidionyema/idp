//! Engine 3b: Model-Agnostic Legion Dispatcher with Same-Billing-Class Failover.
//!
//! Solves the `NO_FIT_LANE` deadlock and eliminates vendor lock-in: selects the fastest
//! verified `FIT` lane in the mandated `BillingClass`, reserves atomic escrow before
//! inference, and automatically fails over to another `FIT` lane in the same class on fault.

use meridian_ledger::{BillingClass, BudgetLedger, LedgerError, RoutingState};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct MissionRequest {
    pub instruction_id: String,
    pub billing_class: BillingClass,
    pub max_cost_minor_units: i64,
    pub currency: String,
    pub nonce_prefix: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum WorkerExecResult {
    Success {
        patch_sha: String,
        actual_cost_minor_units: i64,
    },
    Fault {
        reason: String,
        drain_lane: bool,
    },
}

pub trait LaneExecutor {
    fn execute(&mut self, lane_id: &str, model: &str, req: &MissionRequest) -> WorkerExecResult;
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DispatchReceipt {
    pub instruction_id: String,
    pub winning_lane_id: String,
    pub winning_model: String,
    pub patch_sha: String,
    pub failed_over_from: Vec<String>,
    pub committed_minor_units: i64,
    pub new_fencing_token: u64,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum DispatchError {
    NoFitLane { billing_class: BillingClass, tried: Vec<String> },
    Ledger(LedgerError),
}

pub fn dispatch_with_failover(
    req: &MissionRequest,
    now_utc: u64,
    ledger: &mut BudgetLedger,
    routing: &mut RoutingState,
    executor: &mut dyn LaneExecutor,
) -> Result<DispatchReceipt, DispatchError> {
    let mut tried: HashSet<String> = HashSet::new();
    let mut failed_over_from: Vec<String> = Vec::new();
    let mut attempt: u32 = 0;

    loop {
        let lane = match routing.select_best_fit(req.billing_class, now_utc, &tried) {
            Some(rec) => rec.clone(),
            None => {
                return Err(DispatchError::NoFitLane {
                    billing_class: req.billing_class,
                    tried: failed_over_from,
                });
            }
        };

        attempt += 1;
        let res_id = format!("{}-att-{}", req.instruction_id, attempt);
        let nonce = format!("{}-{}", req.nonce_prefix, attempt);

        ledger
            .reserve(
                &res_id,
                &lane.lane_id,
                lane.billing_class,
                req.max_cost_minor_units,
                &req.currency,
                &nonce,
                ledger.revocation_epoch,
                ledger.fencing_token,
            )
            .map_err(DispatchError::Ledger)?;

        match executor.execute(&lane.lane_id, &lane.model, req) {
            WorkerExecResult::Success {
                patch_sha,
                actual_cost_minor_units,
            } => {
                let tok = ledger
                    .commit(&res_id, actual_cost_minor_units)
                    .map_err(DispatchError::Ledger)?;
                return Ok(DispatchReceipt {
                    instruction_id: req.instruction_id.clone(),
                    winning_lane_id: lane.lane_id,
                    winning_model: lane.model,
                    patch_sha,
                    failed_over_from,
                    committed_minor_units: actual_cost_minor_units,
                    new_fencing_token: tok,
                });
            }
            WorkerExecResult::Fault { reason, drain_lane } => {
                let _ = ledger.release(&res_id);
                if drain_lane {
                    routing.drain_lane(&lane.lane_id, &reason);
                }
                tried.insert(lane.lane_id.clone());
                failed_over_from.push(lane.lane_id);
            }
        }
    }
}
