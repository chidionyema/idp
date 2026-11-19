use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const TRACKED_REPOS: [&str; 5] = [
    "chidionyema/idp",
    "chidionyema/argon",
    "chidionyema/argon-sync",
    "chidionyema/gemini-sync",
    "chidionyema/geaistudio",
];

pub const MAX_FILES_PER_CHANGE: usize = 5;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RealtimeEnvelope {
    pub seq_id: i64,
    pub ts_ns: u64,
    pub fencing_token: u64,
    pub topic: String,
    pub source_node: String,
    pub prev_merkle_root: String,
    pub merkle_root: String,
    pub payload: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RepoHeadSummary {
    pub repo_full_name: String,
    pub default_branch: String,
    pub head_sha: String,
    pub branch_count: i64,
    pub stranded_branch_count: i64,
    pub unique_blobs_off_main: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FleetKpis {
    pub argon_ci_fail_pct: f64,
    pub argon_runs_sampled: i64,
    pub gemini_sync_fail_pct: f64,
    pub gemini_sync_runs_sampled: i64,
    pub open_prs_red: i64,
    pub open_prs_total: i64,
    pub argon_stranded_branches: i64,
    pub argon_total_branches: i64,
    pub argon_unique_blobs_off_main: i64,
    pub repos: Vec<RepoHeadSummary>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ReadinessVerdict {
    Ready,
    NotReady,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderHealth {
    pub provider_id: String,
    pub status: String,
    pub last_http_status: i64,
    pub circuit_open_until_ns: u64,
    pub detail: String,
    pub updated_at_ns: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkerReadiness {
    pub verdict: ReadinessVerdict,
    pub agent_sandbox_success_lifetime: i64,
    pub agent_sandbox_failure_lifetime: i64,
    pub agent_sandbox_success_last_7d: i64,
    pub provider_capacity_ok: bool,
    pub scope_bound_before_inference: bool,
    pub founder_seal_boolean_eliminated: bool,
    pub blockers: Vec<String>,
    pub providers: Vec<ProviderHealth>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CustodyEntry {
    pub artifact_id: String,
    pub surface: String,
    pub artifact_name: String,
    pub status: String,
    pub location: String,
    pub evidence: String,
    pub updated_at_ns: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FailureClassSummary {
    pub failure_class: String,
    pub repo_full_name: String,
    pub workflow_name: String,
    pub failed_runs: i64,
    pub total_runs: i64,
    pub failed_on_main: i64,
    pub failing_step: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpenPrSummary {
    pub repo_full_name: String,
    pub pr_number: i64,
    pub title: String,
    pub head_branch: String,
    pub head_sha: String,
    pub checks_verdict: String,
    pub failing_checks: Vec<String>,
    pub opened_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StrandedBranchSummary {
    pub repo_full_name: String,
    pub branch_name: String,
    pub head_sha: String,
    pub code_files_not_on_main: i64,
    pub last_author: String,
    pub last_commit_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CounterexampleEntry {
    pub check_id: String,
    pub claim: String,
    pub verdict: String,
    pub repo_full_name: String,
    pub head_sha: String,
    pub evidence: String,
    pub checked_at_ns: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoleAllocation {
    pub role_id: String,
    pub ordered_pool: Vec<String>,
    pub weights: BTreeMap<String, f64>,
    pub budget_cap_usd: f64,
    pub max_tokens_cap: i64,
    pub circuit_breaker_policy: String,
    pub config_version: i64,
    pub founder_sig: String,
    pub updated_at_ns: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GroundTruthProjection {
    pub schema_version: String,
    pub seq_id: i64,
    pub fencing_token: u64,
    pub merkle_root: String,
    pub generated_at_ns: u64,
    pub block1_fleet_kpis: FleetKpis,
    pub block2_worker_readiness: WorkerReadiness,
    pub block3_custody_ledger: Vec<CustodyEntry>,
    pub block4_failure_taxonomy: Vec<FailureClassSummary>,
    pub block5_open_prs: Vec<OpenPrSummary>,
    pub block5_top_stranded_branches: Vec<StrandedBranchSummary>,
    pub block6_counterexamples: Vec<CounterexampleEntry>,
    pub block6_open_obligation_count: i64,
    pub block6_role_allocations: Vec<RoleAllocation>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderEventRequest {
    pub provider_id: String,
    pub http_status: i64,
    pub circuit_open_seconds: Option<u64>,
    pub detail: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CustodyUpsertRequest {
    pub artifact_id: String,
    pub surface: String,
    pub artifact_name: String,
    pub status: String,
    pub location: String,
    pub evidence: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CounterexampleUpsertRequest {
    pub check_id: String,
    pub claim: String,
    pub verdict: String,
    pub repo_full_name: String,
    pub head_sha: String,
    pub evidence: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoleAllocationUpdateRequest {
    pub role_id: String,
    pub ordered_pool: Vec<String>,
    #[serde(default)]
    pub weights: BTreeMap<String, f64>,
    pub budget_cap_usd: f64,
    pub max_tokens_cap: i64,
    pub circuit_breaker_policy: Option<String>,
    #[serde(default)]
    pub founder_override_single_vendor: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrerequisiteGateRequest {
    pub agent_surface: String,
    pub role_id: String,
    pub repo_full_name: String,
    pub seen_fencing_token: u64,
    pub planned_paths: Vec<String>,
    #[serde(default)]
    pub is_atomic_ic_bundle: bool,
    #[serde(default)]
    pub read_only_recon: bool,
    pub ttl_seconds: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrerequisiteGateVerdict {
    pub admitted: bool,
    pub reason: String,
    pub lease_id: Option<String>,
    pub bound_seq_id: i64,
    pub bound_fencing_token: u64,
    pub scope_sha256: Option<String>,
    pub selected_provider_pool: Vec<String>,
    pub expires_at_sec: Option<i64>,
    pub live_markdown_brief: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerifyFenceRequest {
    pub lease_id: String,
    pub presented_fencing_token: u64,
    pub touched_paths: Vec<String>,
    pub presented_scope_sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerifyFenceVerdict {
    pub valid: bool,
    pub code: String,
    pub current_fencing_token: u64,
    pub detail: String,
}
