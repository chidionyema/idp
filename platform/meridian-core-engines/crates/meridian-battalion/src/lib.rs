//! Engine 3a: Model-Agnostic Battalion Capacity Qualifier.
//!
//! Replaces the read-only `PR #8677` census with a real two-phase offline golden mission
//! qualifier (`PRE_EDIT_RED -> FIX_GREEN`) that writes signed `estate.lane-fitness.v1`
//! leases directly into `RoutingStateDO` and `--fitness-dir`.

use ed25519_dalek::SigningKey;
use meridian_ledger::{BillingClass, LaneFitnessRecord, LaneStatus, RoutingState};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct CandidateLaneSpec {
    pub lane_id: String,
    pub provider: String,
    pub model: String,
    pub secret_env: String,
    pub billing_class: BillingClass,
    pub ttl_secs: u64,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ProbeOutcome {
    /// Auth succeeded (HTTP 200), pre-edit golden test failed RED, candidate patch turned it GREEN.
    GoldenPass { p99_ms: u32 },
    /// Candidate answered chat OK but produced an empty/invalid patch (exit 2 — the #3525 defect).
    EmptyOrFailedPatch { p99_ms: u32, detail: String },
    /// Missing env var or HTTP 401/403 — names the exact `SEED_*` secret variable.
    SecretBoundary { http_status: u16 },
    /// Transient transport/5xx/429 failure.
    ProviderDegraded { http_status: u16 },
}

pub trait GoldenMissionProber {
    fn probe_lane(&self, lane: &CandidateLaneSpec) -> ProbeOutcome;
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct QualificationReport {
    pub fit_lanes: Vec<String>,
    pub unfit_lanes: Vec<String>,
    pub secret_escalations: Vec<String>,
}

impl QualificationReport {
    /// Single-line machine escalation naming exact `SEED_*` secret variables (never generic lane names).
    pub fn escalation_line(&self) -> Option<String> {
        if self.secret_escalations.is_empty() {
            None
        } else {
            Some(format!(
                "ESCALATE/1 founder secret boundary: missing_or_refused={}",
                self.secret_escalations.join(",")
            ))
        }
    }
}

pub fn qualify_pool(
    candidates: &[CandidateLaneSpec],
    prober: &dyn GoldenMissionProber,
    signer: &SigningKey,
    now_utc: u64,
    routing: &mut RoutingState,
    export_dir: Option<&Path>,
) -> Result<QualificationReport, String> {
    if let Some(dir) = export_dir {
        fs::create_dir_all(dir).map_err(|e| format!("create_dir_all: {e}"))?;
    }

    let mut report = QualificationReport {
        fit_lanes: Vec::new(),
        unfit_lanes: Vec::new(),
        secret_escalations: Vec::new(),
    };

    for lane in candidates {
        let (status, golden_pass, p99_ms, reason) = match prober.probe_lane(lane) {
            ProbeOutcome::GoldenPass { p99_ms } => {
                report.fit_lanes.push(lane.lane_id.clone());
                (LaneStatus::Fit, true, p99_ms, "PRE_EDIT_RED->FIX_GREEN".to_string())
            }
            ProbeOutcome::EmptyOrFailedPatch { p99_ms, detail } => {
                report.unfit_lanes.push(lane.lane_id.clone());
                (LaneStatus::Unfit, false, p99_ms, format!("EMPTY_OR_FAILED_PATCH:{detail}"))
            }
            ProbeOutcome::SecretBoundary { http_status } => {
                report.unfit_lanes.push(lane.lane_id.clone());
                report.secret_escalations.push(lane.secret_env.clone());
                (LaneStatus::Drained, false, 0, format!("SECRET_BOUNDARY_HTTP_{http_status}:{}", lane.secret_env))
            }
            ProbeOutcome::ProviderDegraded { http_status } => {
                report.unfit_lanes.push(lane.lane_id.clone());
                (LaneStatus::Drained, false, 0, format!("PROVIDER_DEGRADED_HTTP_{http_status}"))
            }
        };

        let mut rec = LaneFitnessRecord {
            schema: LaneFitnessRecord::SCHEMA_V1.to_string(),
            lane_id: lane.lane_id.clone(),
            provider: lane.provider.clone(),
            model: lane.model.clone(),
            secret_env: lane.secret_env.clone(),
            billing_class: lane.billing_class,
            status,
            checked_at_utc: now_utc,
            expires_at_utc: now_utc.saturating_add(lane.ttl_secs),
            p99_ms,
            golden_pass,
            reason,
            signer_pubkey_hex: String::new(),
            signature_hex: String::new(),
        };
        rec.sign(signer);

        routing
            .upsert_signed(rec.clone())
            .map_err(|e| format!("routing upsert {}: {:?}", lane.lane_id, e))?;

        if let Some(dir) = export_dir {
            let out_path = dir.join(format!("{}.json", lane.lane_id));
            let body = serde_json::to_string_pretty(&rec).map_err(|e| format!("json: {e}"))?;
            fs::write(&out_path, body).map_err(|e| format!("write {:?}: {e}", out_path))?;
        }
    }

    Ok(report)
}
