//! Event-driven mirror sink (issue #8302, claim #8345).
//!
//! The mirror is driven by the envelope the engine already broadcasts when the
//! fencing token increments -- not by a timer, and not by a poll of the store.
//! It therefore cannot publish a projection that no fence bump produced.
use crate::store::GroundTruthEngine;
use std::sync::Arc;

#[derive(Debug, Clone)]
pub struct MirrorConfig {
    pub url: String,
    pub token_env: String,
}

impl MirrorConfig {
    pub fn from_env() -> Option<Self> {
        let url = std::env::var("ESTATE_GT_MIRROR_URL").ok()?;
        if url.trim().is_empty() {
            return None;
        }
        Some(Self {
            url,
            token_env: "ESTATE_GT_MIRROR_TOKEN".to_string(),
        })
    }
}

/// One publish attempt. Returns the fence that was published, or why nothing
/// was: a mirror that cannot publish says so instead of claiming success.
pub async fn publish_once(
    engine: &GroundTruthEngine,
    cfg: &MirrorConfig,
    fence: u64,
) -> Option<String> {
    let proj = engine.read_live_projection().ok()?;
    if proj.fencing_token != fence {
        return Some(format!("SKIP_STALE_FENCE:{}", proj.fencing_token));
    }
    let body = engine.render_compact_markdown(&proj);
    let token = std::env::var(&cfg.token_env).unwrap_or_default();
    let mut req = reqwest::Client::new().post(&cfg.url).body(body);
    if !token.is_empty() {
        req = req.bearer_auth(token);
    }
    match req.send().await {
        Ok(r) if r.status().is_success() => Some(format!("PUBLISHED:{fence}")),
        Ok(r) => Some(format!("REFUSED:{}", r.status().as_u16())),
        Err(e) => Some(format!("UNREACHABLE:{e}")),
    }
}

/// The worker: it awaits the envelope the engine emits on every fence bump, so
/// the mirror fires on the bump itself and on nothing else.
pub async fn run_mirror(engine: Arc<GroundTruthEngine>, cfg: MirrorConfig) {
    let mut rx = engine.tx.subscribe();
    let mut last = 0u64;
    while let Ok(env) = rx.recv().await {
        if env.fencing_token <= last {
            continue;
        }
        let _ = publish_once(&engine, &cfg, env.fencing_token).await;
        last = env.fencing_token;
    }
}
