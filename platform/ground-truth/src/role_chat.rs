//! Truth-injecting inference hook (issue #8302, claim #8345).
//!
//! A model call made for a role is not allowed to render anything the live
//! ground truth did not authorise: the call is admitted at the ingress door,
//! the current brief is injected as the system message, and an answer whose
//! fence moved underneath it is refused rather than returned.
use crate::ingress::{IngressDecision, IngressRefusal, IngressTicket};
use crate::store::GroundTruthEngine;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct RoleChatRequest {
    pub session_id: String,
    pub ticket: String,
    pub nonce: String,
    pub fencing_token: u64,
    pub role_id: String,
    pub messages: Vec<ChatMessage>,
}

#[derive(Debug, Clone, Serialize)]
pub struct RoleChatAnswer {
    pub ok: bool,
    pub fencing_token: u64,
    pub scope_sha256: String,
    pub content: String,
}

/// The system message a role call is bound to: live ground truth first, the
/// role second, and the rule that binds them.
pub fn system_message(role_id: &str, brief: &str) -> String {
    format!("GROUND TRUTH (live, authoritative):\n{brief}\n\nROLE: {role_id}\nAn answer that contradicts the ground truth above is refused, not returned.")
}

#[derive(Debug, Clone)]
pub struct ChatConfig {
    pub url: String,
    pub token_env: String,
}

impl ChatConfig {
    /// `ESTATE_GT_CHAT_URL` names the model endpoint; the key is carried by an
    /// env var NAME, never a literal in this file.
    pub fn from_env() -> Option<Self> {
        let url = std::env::var("ESTATE_GT_CHAT_URL").ok()?;
        if url.trim().is_empty() {
            return None;
        }
        Some(Self {
            url,
            token_env: "ESTATE_GT_CHAT_TOKEN".to_string(),
        })
    }
}

#[derive(Debug, Clone)]
pub enum ChatOutcome {
    Answer(RoleChatAnswer),
    Refused(IngressRefusal),
    FenceMoved { seen: u64, live: u64 },
    BadRequest(String),
}

/// Admit, inject, call, then refuse an answer whose fence moved underneath it.
pub async fn handle(
    engine: &GroundTruthEngine,
    cfg: &ChatConfig,
    req: &RoleChatRequest,
) -> anyhow::Result<ChatOutcome> {
    let t = IngressTicket {
        session_id: req.session_id.clone(),
        ticket: req.ticket.clone(),
        nonce: req.nonce.clone(),
        fencing_token: req.fencing_token,
    };
    match engine.check_ingress(&t)? {
        IngressDecision::Open => {}
        IngressDecision::Shut(r) => return Ok(ChatOutcome::Refused(r)),
    }
    let proj = engine.read_live_projection()?;
    let brief = engine.render_compact_markdown(&proj);
    let system = system_message(&req.role_id, &brief);
    let mut messages = Vec::with_capacity(req.messages.len() + 1);
    messages.push(ChatMessage { role: "system".into(), content: system });
    messages.extend(req.messages.iter().cloned());
    let token = std::env::var(&cfg.token_env).unwrap_or_default();
    let mut call = reqwest::Client::new()
        .post(&cfg.url)
        .json(&serde_json::json!({ "model": req.role_id, "messages": messages }));
    if !token.is_empty() {
        call = call.bearer_auth(token);
    }
    let resp = match call.send().await {
        Ok(r) => r,
        Err(e) => return Ok(ChatOutcome::BadRequest(format!("UPSTREAM_UNREACHABLE: {e}"))),
    };
    if !resp.status().is_success() {
        return Ok(ChatOutcome::BadRequest(format!("UPSTREAM_{}", resp.status().as_u16())));
    }
    let body: serde_json::Value = match resp.json().await {
        Ok(v) => v,
        Err(e) => return Ok(ChatOutcome::BadRequest(format!("UPSTREAM_BAD_JSON: {e}"))),
    };
    let content = body
        .pointer("/choices/0/message/content")
        .and_then(|v| v.as_str())
        .unwrap_or_default()
        .to_string();
    let live = engine.current_fencing_token();
    if live != proj.fencing_token {
        return Ok(ChatOutcome::FenceMoved { seen: proj.fencing_token, live });
    }
    let scope = crate::ingress::sha256_hex(&format!("{}:{}:{}", req.role_id, req.session_id, live));
    Ok(ChatOutcome::Answer(RoleChatAnswer {
        ok: true,
        fencing_token: live,
        scope_sha256: scope,
        content,
    }))
}
