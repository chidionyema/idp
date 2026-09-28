use crate::engine::{Engine, Verdict};
use axum::{extract::State, http::StatusCode, routing::{get, post}, Json, Router};
use serde::Deserialize;
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};

const WINDOW: usize = 1000;

pub struct AppState {
    pub engine: Mutex<Engine>,
    pub latencies: Mutex<VecDeque<u64>>,
    pub calls: Mutex<(u64, u64)>, // (answered, abstained)
}

#[derive(Deserialize)]
pub struct InferRequest {
    pub task: String,
    pub input: String,
}

pub fn app(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/v1/infer", post(infer))
        .route("/v1/health", get(health))
        .with_state(state)
}

async fn infer(State(state): State<Arc<AppState>>, Json(req): Json<InferRequest>) -> Result<Json<Verdict>, (StatusCode, String)> {
    let task = state.engine.lock().map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?.card.task.clone();
    if req.task != task {
        return Err((StatusCode::NOT_FOUND, format!("task {} not loaded (have {task})", req.task)));
    }
    let st = state.clone();
    let verdict = tokio::task::spawn_blocking(move || -> anyhow::Result<Verdict> {
        let mut engine = st.engine.lock().map_err(|e| anyhow::anyhow!("{e}"))?;
        engine.classify(&req.input)
    })
    .await
    .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?
    .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    if let Ok(mut l) = state.latencies.lock() {
        if l.len() == WINDOW {
            l.pop_front();
        }
        l.push_back(verdict.latency_ms);
    }
    if let Ok(mut c) = state.calls.lock() {
        if verdict.abstain { c.1 += 1 } else { c.0 += 1 }
    }
    tracing::info!(task, abstain = verdict.abstain, margin = verdict.margin, latency_ms = verdict.latency_ms, "infer");
    Ok(Json(verdict))
}

fn percentile(sorted: &[u64], pct: f64) -> Option<u64> {
    if sorted.is_empty() {
        return None;
    }
    let idx = ((sorted.len() - 1) as f64 * pct).round() as usize;
    sorted.get(idx).copied()
}

async fn health(State(state): State<Arc<AppState>>) -> Json<serde_json::Value> {
    let card = state.engine.lock().map(|e| e.card.clone()).ok();
    let mut sorted: Vec<u64> = state.latencies.lock().map(|l| l.iter().copied().collect()).unwrap_or_default();
    sorted.sort_unstable();
    let (answered, abstained) = state.calls.lock().map(|c| *c).unwrap_or((0, 0));
    Json(serde_json::json!({
        "loaded": card.as_ref().map(|c| serde_json::json!({"task": c.task, "base": c.base, "abstain_below": c.abstain_below})),
        "window": sorted.len(),
        "p50_ms": percentile(&sorted, 0.5),
        "p95_ms": percentile(&sorted, 0.95),
        "answered": answered,
        "abstained": abstained,
    }))
}
