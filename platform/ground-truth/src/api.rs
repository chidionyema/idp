use crate::crypto::{verify_github_webhook_hmac, AuthError};
use crate::store::GroundTruthEngine;
use crate::types::{
    CounterexampleUpsertRequest, CustodyUpsertRequest, PrerequisiteGateRequest,
    ProviderEventRequest, RoleAllocationUpdateRequest, VerifyFenceRequest,
};
use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Query, State,
    },
    http::{header, HeaderMap, HeaderValue, StatusCode},
    response::{
        sse::{Event, KeepAlive, Sse},
        IntoResponse,
    },
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use std::convert::Infallible;
use std::sync::Arc;
use std::time::Duration;
use tokio_stream::{wrappers::BroadcastStream, StreamExt};

#[derive(Debug, Deserialize)]
pub struct StreamQuery {
    pub since_seq: Option<i64>,
}

fn require_founder_signature(
    engine: &GroundTruthEngine,
    headers: &HeaderMap,
    method: &str,
    path: &str,
    raw_body: &str,
) -> Result<String, (StatusCode, Json<serde_json::Value>)> {
    let verifier = engine.founder_verifier.as_ref().ok_or_else(|| {
        (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(serde_json::json!({
                "ok": false,
                "error": AuthError::FounderPubkeyMissing.to_string()
            })),
        )
    })?;
    let sig = headers.get("x-genesis-signature").and_then(|v| v.to_str().ok());
    let ts = headers.get("x-genesis-timestamp").and_then(|v| v.to_str().ok());
    verifier
        .verify_signed_request(method, path, ts, sig, raw_body)
        .map_err(|e| {
            (
                StatusCode::UNAUTHORIZED,
                Json(serde_json::json!({ "ok": false, "error": e.to_string() })),
            )
        })?;
    Ok(sig.unwrap_or_default().to_string())
}

async fn health_handler(State(engine): State<Arc<GroundTruthEngine>>) -> impl IntoResponse {
    (
        StatusCode::OK,
        Json(serde_json::json!({
            "ok": true,
            "service": "genesis-ground-truth",
            "fencingToken": engine.current_fencing_token()
        })),
    )
}

async fn live_json_handler(State(engine): State<Arc<GroundTruthEngine>>) -> impl IntoResponse {
    match engine.read_live_projection() {
        Ok(proj) => {
            let mut headers = HeaderMap::new();
            let etag = format!("\"fence-{}-seq-{}\"", proj.fencing_token, proj.seq_id);
            if let Ok(v) = HeaderValue::from_str(&etag) {
                headers.insert(header::ETAG, v);
            }
            if let Ok(v) = HeaderValue::from_str(&proj.fencing_token.to_string()) {
                headers.insert("x-genesis-fence", v);
            }
            (StatusCode::OK, headers, Json(serde_json::json!({ "ok": true, "projection": proj }))).into_response()
        }
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "ok": false, "error": e.to_string() })),
        )
            .into_response(),
    }
}

async fn live_markdown_handler(State(engine): State<Arc<GroundTruthEngine>>) -> impl IntoResponse {
    match engine.read_live_projection() {
        Ok(proj) => {
            let md = engine.render_compact_markdown(&proj);
            let mut headers = HeaderMap::new();
            headers.insert(
                header::CONTENT_TYPE,
                HeaderValue::from_static("text/markdown; charset=utf-8"),
            );
            if let Ok(v) = HeaderValue::from_str(&proj.fencing_token.to_string()) {
                headers.insert("x-genesis-fence", v);
            }
            if let Ok(v) = HeaderValue::from_str(&proj.seq_id.to_string()) {
                headers.insert("x-genesis-seq", v);
            }
            if let Ok(v) = HeaderValue::from_str(&proj.merkle_root) {
                headers.insert("x-genesis-merkle", v);
            }
            (StatusCode::OK, headers, md).into_response()
        }
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

async fn github_webhook_handler(
    headers: HeaderMap,
    State(engine): State<Arc<GroundTruthEngine>>,
    raw_body: String,
) -> impl IntoResponse {
    let sig_header = headers
        .get("x-hub-signature-256")
        .and_then(|v| v.to_str().ok());
    if let Err(err) = verify_github_webhook_hmac(
        engine.webhook_secret.as_deref(),
        sig_header,
        raw_body.as_bytes(),
    ) {
        return (
            StatusCode::UNAUTHORIZED,
            Json(serde_json::json!({ "ok": false, "error": err.to_string() })),
        );
    }

    let delivery_id = headers
        .get("x-github-delivery")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    let event_type = headers
        .get("x-github-event")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("unknown");

    if delivery_id.is_empty() {
        return (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({ "ok": false, "error": "MISSING_X_GITHUB_DELIVERY" })),
        );
    }

    let payload: serde_json::Value = match serde_json::from_str(&raw_body) {
        Ok(v) => v,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({ "ok": false, "error": format!("INVALID_JSON: {e}") })),
            )
        }
    };

    match engine.ingest_github_webhook(delivery_id, event_type, &payload) {
        Ok(Some(env)) => (
            StatusCode::OK,
            Json(serde_json::json!({ "ok": true, "deduplicated": false, "envelope": env })),
        ),
        Ok(None) => (
            StatusCode::OK,
            Json(serde_json::json!({ "ok": true, "deduplicated": true })),
        ),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "ok": false, "error": e.to_string() })),
        ),
    }
}

async fn provider_event_handler(
    headers: HeaderMap,
    State(engine): State<Arc<GroundTruthEngine>>,
    raw_body: String,
) -> impl IntoResponse {
    // Allow either Founder Ed25519 signature or shared webhook/internal HMAC
    let hmac_ok = verify_github_webhook_hmac(
        engine.webhook_secret.as_deref(),
        headers.get("x-hub-signature-256").and_then(|v| v.to_str().ok()),
        raw_body.as_bytes(),
    )
    .is_ok();
    if !hmac_ok {
        if let Err(err_resp) =
            require_founder_signature(&engine, &headers, "POST", "/api/truth/provider-event", &raw_body)
        {
            return err_resp;
        }
    }

    let req: ProviderEventRequest = match serde_json::from_str(&raw_body) {
        Ok(r) => r,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({ "ok": false, "error": e.to_string() })),
            )
        }
    };

    match engine.ingest_provider_signal(&req) {
        Ok(env) => (
            StatusCode::OK,
            Json(serde_json::json!({ "ok": true, "envelope": env })),
        ),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "ok": false, "error": e.to_string() })),
        ),
    }
}

async fn custody_upsert_handler(
    headers: HeaderMap,
    State(engine): State<Arc<GroundTruthEngine>>,
    raw_body: String,
) -> impl IntoResponse {
    if let Err(err_resp) =
        require_founder_signature(&engine, &headers, "POST", "/api/truth/custody", &raw_body)
    {
        return err_resp;
    }
    let req: CustodyUpsertRequest = match serde_json::from_str(&raw_body) {
        Ok(r) => r,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({ "ok": false, "error": e.to_string() })),
            )
        }
    };
    match engine.upsert_custody(&req) {
        Ok(env) => (
            StatusCode::OK,
            Json(serde_json::json!({ "ok": true, "envelope": env })),
        ),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "ok": false, "error": e.to_string() })),
        ),
    }
}

async fn counterexamples_upsert_handler(
    headers: HeaderMap,
    State(engine): State<Arc<GroundTruthEngine>>,
    raw_body: String,
) -> impl IntoResponse {
    let hmac_ok = verify_github_webhook_hmac(
        engine.webhook_secret.as_deref(),
        headers.get("x-hub-signature-256").and_then(|v| v.to_str().ok()),
        raw_body.as_bytes(),
    )
    .is_ok();
    if !hmac_ok {
        if let Err(err_resp) = require_founder_signature(
            &engine,
            &headers,
            "POST",
            "/api/truth/counterexamples",
            &raw_body,
        ) {
            return err_resp;
        }
    }
    let items: Vec<CounterexampleUpsertRequest> = match serde_json::from_str(&raw_body) {
        Ok(v) => v,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({ "ok": false, "error": e.to_string() })),
            )
        }
    };
    match engine.upsert_counterexamples(&items) {
        Ok(env) => (
            StatusCode::OK,
            Json(serde_json::json!({ "ok": true, "envelope": env })),
        ),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "ok": false, "error": e.to_string() })),
        ),
    }
}

async fn role_allocation_handler(
    headers: HeaderMap,
    State(engine): State<Arc<GroundTruthEngine>>,
    raw_body: String,
) -> impl IntoResponse {
    let sig = match require_founder_signature(
        &engine,
        &headers,
        "POST",
        "/api/truth/roles",
        &raw_body,
    ) {
        Ok(s) => s,
        Err(err_resp) => return err_resp,
    };

    let req: RoleAllocationUpdateRequest = match serde_json::from_str(&raw_body) {
        Ok(r) => r,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({ "ok": false, "error": e.to_string() })),
            )
        }
    };

    match engine.upsert_role_allocation(&req, &sig) {
        Ok(env) => (
            StatusCode::OK,
            Json(serde_json::json!({ "ok": true, "envelope": env })),
        ),
        Err(e) => (
            StatusCode::UNPROCESSABLE_ENTITY,
            Json(serde_json::json!({ "ok": false, "error": e.to_string() })),
        ),
    }
}

async fn admit_turn_handler(
    State(engine): State<Arc<GroundTruthEngine>>,
    Json(req): Json<PrerequisiteGateRequest>,
) -> impl IntoResponse {
    match engine.admit_agent_turn(&req) {
        Ok(verdict) if verdict.admitted => (StatusCode::OK, Json(verdict)),
        Ok(verdict) if verdict.reason.starts_with("STALE_FENCING_TOKEN") => {
            (StatusCode::CONFLICT, Json(verdict))
        }
        Ok(verdict) => (StatusCode::PRECONDITION_FAILED, Json(verdict)),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(crate::types::PrerequisiteGateVerdict {
                admitted: false,
                reason: e.to_string(),
                lease_id: None,
                bound_seq_id: 0,
                bound_fencing_token: engine.current_fencing_token(),
                scope_sha256: None,
                selected_provider_pool: vec![],
                expires_at_sec: None,
                live_markdown_brief: String::new(),
            }),
        ),
    }
}

async fn verify_fence_handler(
    State(engine): State<Arc<GroundTruthEngine>>,
    Json(req): Json<VerifyFenceRequest>,
) -> impl IntoResponse {
    match engine.verify_fence(&req) {
        Ok(v) if v.valid => (StatusCode::OK, Json(v)),
        Ok(v) if v.code == "STALE_FENCING_TOKEN" => (StatusCode::CONFLICT, Json(v)),
        Ok(v) => (StatusCode::FORBIDDEN, Json(v)),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(crate::types::VerifyFenceVerdict {
                valid: false,
                code: "INTERNAL_ERROR".into(),
                current_fencing_token: engine.current_fencing_token(),
                detail: e.to_string(),
            }),
        ),
    }
}

async fn ws_truth_handler(
    ws: WebSocketUpgrade,
    Query(query): Query<StreamQuery>,
    State(engine): State<Arc<GroundTruthEngine>>,
) -> impl IntoResponse {
    let since_seq = query.since_seq.unwrap_or(0);
    ws.on_upgrade(move |mut socket: WebSocket| async move {
        if let Ok(missed) = engine.fetch_replay_since(since_seq, 500) {
            for frame in missed {
                if let Ok(txt) = serde_json::to_string(&frame) {
                    if socket.send(Message::Text(txt)).await.is_err() {
                        return;
                    }
                }
            }
        }
        let mut rx = engine.tx.subscribe();
        let mut ping = tokio::time::interval(Duration::from_secs(5));
        loop {
            tokio::select! {
                Ok(env) = rx.recv() => {
                    if env.seq_id > since_seq {
                        if let Ok(txt) = serde_json::to_string(&env) {
                            if socket.send(Message::Text(txt)).await.is_err() {
                                break;
                            }
                        }
                    }
                }
                _ = ping.tick() => {
                    if socket.send(Message::Ping(Vec::new())).await.is_err() {
                        break;
                    }
                }
                Some(Ok(Message::Close(_))) = socket.recv() => break,
                else => break,
            }
        }
    })
}

async fn sse_truth_handler(
    Query(query): Query<StreamQuery>,
    State(engine): State<Arc<GroundTruthEngine>>,
) -> Sse<impl tokio_stream::Stream<Item = Result<Event, Infallible>>> {
    let since_seq = query.since_seq.unwrap_or(0);
    let replay = engine.fetch_replay_since(since_seq, 500).unwrap_or_default();
    let replay_stream = tokio_stream::iter(
        replay
            .into_iter()
            .filter_map(|env| serde_json::to_string(&env).ok())
            .map(|json| Ok(Event::default().data(json))),
    );
    let live_stream = BroadcastStream::new(engine.tx.subscribe()).filter_map(move |res| match res {
        Ok(env) if env.seq_id > since_seq => serde_json::to_string(&env)
            .ok()
            .map(|json| Ok(Event::default().data(json))),
        _ => None,
    });
    Sse::new(replay_stream.chain(live_stream)).keep_alive(
        KeepAlive::new()
            .interval(Duration::from_secs(5))
            .text("heartbeat"),
    )
}

pub fn ground_truth_router(engine: Arc<GroundTruthEngine>) -> Router {
    Router::new()
        .route("/health/liveliness", get(health_handler))
        .route("/api/truth/live", get(live_json_handler))
        .route("/api/truth/live.md", get(live_markdown_handler))
        .route("/api/truth/admit", post(admit_turn_handler))
        .route("/api/truth/ingress", post(ingress_handler))
        .route("/v1/role/chat", post(role_chat_handler))
        .route("/api/truth/verify-fence", post(verify_fence_handler))
        .route("/api/truth/provider-event", post(provider_event_handler))
        .route("/api/truth/custody", post(custody_upsert_handler))
        .route("/api/truth/counterexamples", post(counterexamples_upsert_handler))
        .route("/api/truth/roles", post(role_allocation_handler))
        .route("/api/webhooks/github", post(github_webhook_handler))
        .route("/api/realtime/ws", get(ws_truth_handler))
        .route("/api/realtime/sse", get(sse_truth_handler))
        .with_state(engine)
}

async fn ingress_handler(
    State(engine): State<Arc<GroundTruthEngine>>,
    Json(t): Json<crate::ingress::IngressTicket>,
) -> impl IntoResponse {
    match engine.check_ingress(&t) {
        Ok(crate::ingress::IngressDecision::Open) => (
            StatusCode::OK,
            Json(serde_json::json!({ "ok": true, "door": "open" })),
        )
            .into_response(),
        Ok(crate::ingress::IngressDecision::Shut(r)) => (
            r.status(),
            Json(serde_json::json!({ "ok": false, "error": r.code() })),
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "ok": false, "error": e.to_string() })),
        )
            .into_response(),
    }
}

async fn role_chat_handler(
    State(engine): State<Arc<GroundTruthEngine>>,
    Json(req): Json<crate::role_chat::RoleChatRequest>,
) -> impl IntoResponse {
    let Some(cfg) = crate::role_chat::ChatConfig::from_env() else {
        return (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(serde_json::json!({ "ok": false, "error": "CHAT_ENDPOINT_NOT_CONFIGURED" })),
        )
            .into_response();
    };
    match crate::role_chat::handle(&engine, &cfg, &req).await {
        Ok(crate::role_chat::ChatOutcome::Answer(a)) => (StatusCode::OK, Json(a)).into_response(),
        Ok(crate::role_chat::ChatOutcome::Refused(r)) => (
            r.status(),
            Json(serde_json::json!({ "ok": false, "error": r.code() })),
        )
            .into_response(),
        Ok(crate::role_chat::ChatOutcome::FenceMoved { seen, live }) => (
            StatusCode::CONFLICT,
            Json(serde_json::json!({ "ok": false, "error": "FENCE_MOVED", "seen": seen, "live": live })),
        )
            .into_response(),
        Ok(crate::role_chat::ChatOutcome::BadRequest(m)) => (
            StatusCode::BAD_GATEWAY,
            Json(serde_json::json!({ "ok": false, "error": m })),
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "ok": false, "error": e.to_string() })),
        )
            .into_response(),
    }
}
