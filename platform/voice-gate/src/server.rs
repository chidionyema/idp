//! HTTP surface (spec §3): /v1/health, /v1/grade (single + batch, max 500).
//! Binds 127.0.0.1 only (R20); address and policy path come from the environment (LAW 46).

use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::Instant;

use crate::policy::VoicePolicy;
use crate::tier1::{Finding, Tier1};

pub struct AppState {
    pub policy: VoicePolicy,
    pub tier1: Tier1,
}

#[derive(Debug, Deserialize)]
pub struct GradeItem {
    pub lane: String,
    pub field: String,
    pub text: String,
    #[serde(default)]
    #[allow(dead_code)]
    pub context: Option<serde_json::Value>,
}

/// Accepts a single item or `{items: [...]}` (spec §3 batch mode).
#[derive(Debug, Deserialize)]
#[serde(untagged)]
pub enum GradeRequest {
    Batch { items: Vec<GradeItem> },
    Single(GradeItem),
}

#[derive(Debug, Serialize)]
pub struct ItemResult {
    pub verdict: &'static str,
    pub findings: Vec<Finding>,
}

#[derive(Debug, Serialize)]
pub struct GradeResponse {
    pub verdict: &'static str,
    pub results: Vec<ItemResult>,
    pub tier_reached: &'static str,
    pub latency_ms: u128,
    pub policy_version: u32,
}

#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub tier1: &'static str,
    pub tier2: &'static str,
    pub policy_version: u32,
}

pub const MAX_BATCH: usize = 500;

pub fn router(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/v1/health", get(handle_health))
        .route("/v1/grade", post(handle_grade))
        .with_state(state)
}

async fn handle_health(State(state): State<Arc<AppState>>) -> Json<HealthResponse> {
    Json(HealthResponse {
        tier1: "ok",
        tier2: "disabled",
        policy_version: state.policy.version,
    })
}

async fn handle_grade(
    State(state): State<Arc<AppState>>,
    body: Result<Json<GradeRequest>, axum::extract::rejection::JsonRejection>,
) -> Result<Json<GradeResponse>, (StatusCode, Json<serde_json::Value>)> {
    let started = Instant::now();
    let Json(req) = body.map_err(|e| {
        (StatusCode::BAD_REQUEST, Json(serde_json::json!({"error": "schema", "detail": e.to_string()})))
    })?;
    let items = match req {
        GradeRequest::Single(item) => vec![item],
        GradeRequest::Batch { items } => {
            if items.len() > MAX_BATCH {
                return Err((
                    StatusCode::BAD_REQUEST,
                    Json(serde_json::json!({"error": "schema", "detail": format!("batch exceeds {}", MAX_BATCH)})),
                ));
            }
            items
        }
    };

    let mut results = Vec::with_capacity(items.len());
    let mut overall = "PASS";
    for item in items {
        let lane = match state.policy.lane(&item.lane) {
            Some(l) => l,
            None => {
                return Err((
                    StatusCode::UNPROCESSABLE_ENTITY,
                    Json(serde_json::json!({"error": "unknown_lane", "lane": item.lane})),
                ))
            }
        };
        let findings = state.tier1.grade(&item.lane, lane, &item.field, &item.text);
        let verdict = if findings.is_empty() { "PASS" } else { "FAIL" };
        if verdict == "FAIL" {
            overall = "FAIL";
        }
        results.push(ItemResult { verdict, findings });
    }

    Ok(Json(GradeResponse {
        verdict: overall,
        results,
        tier_reached: "tier1",
        latency_ms: started.elapsed().as_millis(),
        policy_version: state.policy.version,
    }))
}
