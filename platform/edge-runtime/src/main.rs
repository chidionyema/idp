//! Edge Runtime: loads one artifact directory (model.gguf, model-card.yaml, tokenizer.json,
//! pulled by an `oras` init container) and answers `/v1/infer` on loopback (R20).
//! Config by environment only (LAW 46): EDGE_ARTIFACT_DIR, EDGE_BIND.
use std::collections::VecDeque;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

mod engine;
mod server;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt().json().with_env_filter(tracing_subscriber::EnvFilter::from_default_env()).init();
    let dir = PathBuf::from(std::env::var("EDGE_ARTIFACT_DIR").unwrap_or_else(|_| "artifact".into()));
    let bind = std::env::var("EDGE_BIND").unwrap_or_else(|_| "127.0.0.1:8421".into());
    if !bind.starts_with("127.0.0.1:") {
        anyhow::bail!("EDGE_BIND must be loopback (R20), got {bind}");
    }
    let engine = engine::Engine::load(&dir)?;
    tracing::info!(task = engine.card.task, dir = %dir.display(), "artifact loaded");
    let state = Arc::new(server::AppState {
        engine: Mutex::new(engine),
        latencies: Mutex::new(VecDeque::with_capacity(1000)),
        calls: Mutex::new((0, 0)),
    });
    let listener = tokio::net::TcpListener::bind(&bind).await?;
    tracing::info!(%bind, "listening");
    axum::serve(listener, server::app(state)).await?;
    Ok(())
}
