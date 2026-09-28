//! Voice Gate — semantic egress gateway (spec: prospector specs/voice-gate-2026-09-06.md).
//! Tier 1 deterministic core. Tier 2 (local SLM) and Tier 3 (bounded rewrite) land in
//! phases 2–3 behind the same API; `/v1/health` advertises tier2 "disabled" until then,
//! and lanes are fail-closed per policy when it is required.

use std::sync::Arc;
use tracing::info;
use voice_gate::policy::VoicePolicy;
use voice_gate::server::AppState;
use voice_gate::tier1::Tier1;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .json()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let policy_path = std::env::var("VOICE_GATE_POLICY").unwrap_or_else(|_| "voice-policy.yaml".to_string());
    let bind = std::env::var("VOICE_GATE_BIND").unwrap_or_else(|_| "127.0.0.1:8420".to_string());
    if !bind.starts_with("127.0.0.1") && !bind.starts_with("[::1]") {
        // R20: only the gateway binds a non-loopback address; everything else is loopback or nothing.
        return Err(format!("VOICE_GATE_BIND must be loopback, got {bind}").into());
    }

    let policy = VoicePolicy::load(std::path::Path::new(&policy_path))?;
    info!(version = policy.version, lanes = policy.lanes.len(), "policy loaded");
    let tier1 = Tier1::new(&policy)?;
    let state = Arc::new(AppState { policy, tier1 });

    let listener = tokio::net::TcpListener::bind(&bind).await?;
    info!(%bind, "voice-gate listening");
    axum::serve(listener, voice_gate::server::router(state)).await?;
    Ok(())
}
