//! Pipeline: auth (strict) -> resolve model -> ACL -> shape -> canonical
//! cache key -> reserve budget -> route (own lane + fit-checked fallbacks)
//! -> per-lane dialect shaping -> settle -> decision log (key FINGERPRINTS,
//! request_id, latency). P0-4/5/6 repairs integrated; see FAILURE_MODES.md.

use crate::metrics;
use crate::settle_stream::SettleStream;
use axum::{
    body::Body,
    extract::{DefaultBodyLimit, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use penny_core::{
    anthropic,
    budget::Budgets,
    cache::ExactCache,
    config::Config,
    decision_log::DecisionLog,
    error::PennyError,
    keys::{cache_key, fingerprint},
    ledger::Ledger,
    providers::{ModelEntry, Registry},
    router::{ByteStream, Router as LaneRouter},
    shaping,
};
use serde_json::{json, Value};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, RwLock};
use std::time::{Instant, SystemTime, UNIX_EPOCH};
use tokio::sync::Mutex;

static REQ_COUNTER: AtomicU64 = AtomicU64::new(0);

/// Which wire format the client spoke at the edge.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EdgeFormat {
    OpenAi,
    Anthropic,
}

pub struct App {
    pub cfg: Config,
    pub registry: RwLock<Arc<Registry>>,
    pub router: RwLock<Arc<LaneRouter>>,
    pub cache: ExactCache,
    pub budgets: Budgets,
    pub ledger: Ledger,
    pub log: Mutex<DecisionLog>,
    pub dropped_decisions: AtomicU64,
}

fn now_unix() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

fn request_id(now: u64) -> String {
    let n = REQ_COUNTER.fetch_add(1, Ordering::Relaxed);
    format!("{now:x}-{n:x}")
}

fn auth_key(app: &App, headers: &HeaderMap) -> Result<String, PennyError> {
    let key = headers
        .get("authorization")
        .and_then(|v| v.to_str().ok())
        .and_then(|h| h.strip_prefix("Bearer "))
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(String::from)
        .ok_or_else(|| PennyError::BadRequest("missing or malformed Authorization".into()))?;
    if !app.cfg.allow_unknown_keys && !app.cfg.keys.iter().any(|k| k.key == key) {
        return Err(PennyError::Unauthorized);
    }
    Ok(key)
}

fn daily_budget_for(cfg: &Config, key: &str) -> f64 {
    cfg.keys
        .iter()
        .find(|k| k.key == key)
        .map(|k| k.daily_budget_usd)
        .unwrap_or(cfg.budgets.default_daily_usd)
}

fn check_acl(cfg: &Config, key: &str, entry: &ModelEntry) -> Result<(), PennyError> {
    if let Some(kc) = cfg.keys.iter().find(|k| k.key == key) {
        let list = &kc.allowed_models;
        if !list.is_empty()
            && !list
                .iter()
                .any(|a| a == &entry.canonical_name() || entry.model.aliases.contains(a))
        {
            return Err(PennyError::ModelNotAllowed {
                key: fingerprint(key),
                model: entry.canonical_name(),
            });
        }
    }
    Ok(())
}

fn est_input_tokens(body: &Value) -> u64 {
    body.get("messages")
        .and_then(|m| m.as_array())
        .map(|a| a.iter().map(|m| m.to_string().len() / 4).sum::<usize>() as u64)
        .unwrap_or(0)
}

fn fits(entry: &ModelEntry, est_tokens: u64) -> bool {
    entry.model.context_window == 0 || (est_tokens as f64 * 1.3) < entry.model.context_window as f64
}

/// P1-3: context fit applies to the WHOLE chain, not just the primary.
fn resolve_chain(reg: &Registry, entry: &ModelEntry, est_tokens: u64) -> Result<Vec<String>, PennyError> {
    if !fits(entry, est_tokens) {
        return Err(PennyError::BadRequest(format!(
            "estimated {est_tokens} tokens exceeds context window of {}",
            entry.canonical_name()
        )));
    }
    let mut seen = std::collections::HashSet::new();
    let mut chain = Vec::new();
    for cand in std::iter::once(entry.canonical_name()).chain(
        entry
            .model
            .fallbacks
            .iter()
            .map(|f| match reg.resolve(f) {
                Some(e) => Ok(e.canonical_name()),
                None => Err(PennyError::BadRequest(format!(
                    "{} declares unknown fallback {f:?}",
                    entry.canonical_name()
                ))),
            }),
    ) {
        let name = cand?;
        if !seen.insert(name.clone()) {
            continue;
        }
        // P1-3: skip fallbacks that cannot hold the context
        let fit = reg
            .resolve(&name)
            .map(|e| fits(e, est_tokens))
            .unwrap_or(true);
        if fit {
            chain.push(name);
        }
    }
    Ok(chain)
}

async fn log_decision(app: &App, now: u64, req: &str, started: Instant, mut d: Value) {
    d["req"] = json!(req);
    d["ms"] = json!(started.elapsed().as_millis());
    if let Err(e) = app.log.lock().await.append(now, &d) {
        app.dropped_decisions.fetch_add(1, Ordering::Relaxed);
        tracing::error!("decision log write failed: {e}");
    }
}

/// P0-6/P1-1: the cache key covers the SEMANTIC request only. Volatile and
/// format-specific fields (max_tokens, stream flags, stream_options, the
/// requested alias) are excluded, so the same question via /v1/chat/completions
/// and /v1/messages lands on one canonical entry.
fn semantic_cache_key(canonical_model: &str, shaped: &Value) -> String {
    let key_body = json!({
        "messages": shaped.get("messages").cloned().unwrap_or(json!([])),
        "tools": shaped.get("tools").cloned().unwrap_or(json!([])),
        "tool_choice": shaped.get("tool_choice").cloned().unwrap_or(Value::Null),
        "temperature": shaped.get("temperature").cloned().unwrap_or(Value::Null),
        "response_format": shaped.get("response_format").cloned().unwrap_or(Value::Null),
    });
    cache_key(canonical_model, &key_body)
}

fn lane_dialect(reg: &Registry, lane_name: &str) -> String {
    reg.models
        .iter()
        .find(|e| e.canonical_name() == lane_name)
        .map(|e| e.provider.dialect.clone())
        .unwrap_or_else(|| "openai".into())
}

fn est_cost_usd(est_tokens: u64, entry: &ModelEntry, cfg: &Config) -> f64 {
    let out_cap = cfg.shaping.max_tokens_cap.max(1) as f64;
    est_tokens as f64 * entry.model.price_in_per_mtok / 1e6
        + out_cap * entry.model.price_out_per_mtok / 1e6
}

async fn handle_chat(
    app: &App,
    headers: &HeaderMap,
    body: Value,
    format: EdgeFormat,
) -> Result<Response, PennyError> {
    let started = Instant::now();
    let now = now_unix();
    let req = request_id(now);

    let key = auth_key(app, headers)?;
    let kfp = fingerprint(&key);
    app.budgets.ensure(&key, daily_budget_for(&app.cfg, &key));
    if app.budgets.is_exhausted(&key, now) {
        return Err(PennyError::BudgetExceeded { key: kfp });
    }

    let requested = body
        .get("model")
        .and_then(|m| m.as_str())
        .unwrap_or("default")
        .to_string();
    let wants_stream = body
        .get("stream")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);

    let reg = app.registry.read().unwrap().clone();
    let entry = reg.resolve(&requested).ok_or_else(|| {
        PennyError::BadRequest(format!(
            "unknown model '{requested}'. Available: {}",
            reg.alias_list()
        ))
    })?;
    check_acl(&app.cfg, &key, &entry)?;
    let canonical_model = entry.canonical_name();

    // dialect-agnostic shaping FIRST: the cache key is computed on this body
    let (mut shaped, _) = shaping::truncate_tool_results(body.clone(), app.cfg.shaping.tool_result_max_chars);
    shaped = shaping::cap_max_tokens(shaped, app.cfg.shaping.max_tokens_cap);

    let ck = semantic_cache_key(&canonical_model, &shaped);
    let est_tokens = est_input_tokens(&shaped);

    if !wants_stream {
        if let Some(hit) = app.cache.get(&ck, now) {
            match serde_json::from_str::<Value>(&hit.value) {
                Ok(mut v) => {
                    let in_tok = est_tokens;
                    let saved_usd = in_tok as f64 * entry.model.price_in_per_mtok / 1e6;
                    app.ledger.record_hit(in_tok, saved_usd);
                    v["penny_cache"] = json!("hit");
                    log_decision(
                        app, now, &req, started,
                        json!({"decision": "cache_hit", "key_fp": kfp, "model": canonical_model,
                               "in_tokens": in_tok}),
                    )
                    .await;
                    let v = if format == EdgeFormat::Anthropic {
                        let mut a = anthropic::response_to_anthropic(&v);
                        a["penny_cache"] = json!("hit");
                        a
                    } else {
                        v
                    };
                    return Ok((StatusCode::OK, Json(v)).into_response());
                }
                Err(_) => {
                    app.cache.invalidate(&ck);
                }
            }
        }
    }

    let chain = resolve_chain(&reg, &entry, est_tokens)?;
    let est_usd = est_cost_usd(est_tokens, &entry, &app.cfg);
    // P0-5: reserve BEFORE dispatch; refusal happens pre-spend
    app.budgets.reserve(&key, est_usd, now)?;

    let router = app.router.read().unwrap().clone();

    if wants_stream {
        match router.route_chain_stream(&chain, &shaped, now).await {
            Ok((lane_idx, stream)) => {
                let lane = router.lanes[lane_idx].clone();
                let usd_est = est_tokens as f64 * lane.price_in_per_mtok() / 1e6;
                app.ledger.charge(est_tokens, 0, usd_est);
                log_decision(
                    app, now, &req, started,
                    json!({"decision": "route_stream", "key_fp": kfp, "model": canonical_model,
                           "lane": lane.name(), "in_tokens_est": est_tokens,
                           "usd_est": usd_est, "est": true}),
                )
                .await;
                // settle the reservation when the stream completes/ errors
                let guarded = SettleStream::new(stream, app.budgets.clone(), key.clone(), usd_est);
                let mut stream: ByteStream = Box::pin(guarded);
                if format == EdgeFormat::Anthropic && lane_dialect(&reg, lane.name()) == "openai" {
                    stream = anthropic::openai_sse_to_anthropic(stream, canonical_model.clone());
                }
                return Response::builder()
                    .status(StatusCode::OK)
                    .header("content-type", "text/event-stream")
                    .header("cache-control", "no-cache")
                    .body(Body::from_stream(stream))
                    .map_err(|e| PennyError::BadRequest(e.to_string()));
            }
            Err(e) => {
                let _ = app.budgets.settle(&key, est_usd, 0.0, now);
                return Err(e);
            }
        }
    }

    match router.route_chain(&chain, &shaped, now).await {
        Ok((lane_idx, mut resp)) => {
            let lane = router.lanes[lane_idx].clone();
            let usage = resp.get("usage").cloned().unwrap_or_else(|| json!({}));
            let in_tok = usage.get("prompt_tokens").and_then(|v| v.as_u64()).unwrap_or(0);
            let out_tok = usage.get("completion_tokens").and_then(|v| v.as_u64()).unwrap_or(0);
            let actual_usd = in_tok as f64 * lane.price_in_per_mtok() / 1e6
                + out_tok as f64 * lane.price_out_per_mtok() / 1e6;
            app.budgets.settle(&key, est_usd, actual_usd, now)?;
            app.ledger.charge(in_tok, out_tok, actual_usd);

            resp["penny_lane"] = json!(lane.name());
            let cacheable = resp
                .get("penny_cacheable")
                .and_then(|v| v.as_bool())
                .unwrap_or(true);
            if cacheable {
                app.cache
                    .insert(ck.clone(), serde_json::to_string(&resp).unwrap_or_default(), now);
            }
            log_decision(
                app, now, &req, started,
                json!({
                    "decision": "route", "key_fp": kfp, "model": canonical_model,
                    "lane": lane.name(), "class": format!("{:?}", lane.class()),
                    "in_tokens": in_tok, "out_tokens": out_tok, "usd": actual_usd,
                }),
            )
            .await;
            let resp = if format == EdgeFormat::Anthropic {
                anthropic::response_to_anthropic(&resp)
            } else {
                resp
            };
            Ok((StatusCode::OK, Json(resp)).into_response())
        }
        Err(e) => {
            let _ = app.budgets.settle(&key, est_usd, 0.0, now);
            Err(e)
        }
    }
}

fn anthropic_err(kind: &str, status: StatusCode, msg: &str) -> Response {
    (status, Json(anthropic::error_body(kind, msg))).into_response()
}

pub async fn chat(
    State(app): State<Arc<App>>,
    headers: HeaderMap,
    Json(body): Json<Value>,
) -> Response {
    match handle_chat(&app, &headers, body, EdgeFormat::OpenAi).await {
        Ok(r) => r,
        Err(PennyError::BudgetExceeded { key }) => (
            StatusCode::TOO_MANY_REQUESTS,
            Json(json!({
                "error": {"type": "budget_exceeded", "key_fp": key,
                          "action": "raise daily_budget_usd or wait for day rollover"}
            })),
        )
            .into_response(),
        Err(PennyError::Unauthorized) => (
            StatusCode::UNAUTHORIZED,
            Json(json!({"error": {"type": "unauthorized", "detail": "unknown API key"}})),
        )
            .into_response(),
        Err(PennyError::ModelNotAllowed { key, model }) => (
            StatusCode::FORBIDDEN,
            Json(json!({"error": {"type": "model_not_allowed", "key_fp": key, "model": model}})),
        )
            .into_response(),
        Err(PennyError::BadRequest(m)) => {
            (StatusCode::BAD_REQUEST, Json(json!({"error": m}))).into_response()
        }
        Err(e) => (
            StatusCode::BAD_GATEWAY,
            Json(json!({"error": {"type": "upstream", "detail": e.to_string()}})),
        )
            .into_response(),
    }
}

/// Anthropic Messages ingress.
pub async fn messages(
    State(app): State<Arc<App>>,
    headers: HeaderMap,
    Json(body): Json<Value>,
) -> Response {
    let canonical = match anthropic::request_to_openai(&body) {
        Ok(c) => c,
        Err(e) => return anthropic_err("invalid_request_error", StatusCode::BAD_REQUEST, &e.to_string()),
    };
    match handle_chat(&app, &headers, canonical, EdgeFormat::Anthropic).await {
        Ok(r) => r,
        // P1-9: the error kind must match the failure
        Err(PennyError::BudgetExceeded { key }) => {
            anthropic_err("rate_limit_error", StatusCode::TOO_MANY_REQUESTS,
                          &format!("budget exceeded for key {key}"))
        }
        Err(PennyError::Unauthorized) => {
            anthropic_err("authentication_error", StatusCode::UNAUTHORIZED, "unknown API key")
        }
        Err(PennyError::ModelNotAllowed { key, model }) => {
            anthropic_err("permission_error", StatusCode::FORBIDDEN,
                          &format!("key {key} is not allowed to use model {model}"))
        }
        Err(PennyError::BadRequest(m)) => {
            anthropic_err("invalid_request_error", StatusCode::BAD_REQUEST, &m)
        }
        Err(PennyError::RateLimited { lane, retry_after_s }) => {
            let msg = match retry_after_s {
                Some(s) => format!("lane {lane} rate limited; retry after {s}s"),
                None => format!("lane {lane} rate limited"),
            };
            anthropic_err("rate_limit_error", StatusCode::TOO_MANY_REQUESTS, &msg)
        }
        Err(e) => anthropic_err("api_error", StatusCode::BAD_GATEWAY, &e.to_string()),
    }
}

pub async fn list_models(State(app): State<Arc<App>>) -> Response {
    let reg = app.registry.read().unwrap().clone();
    Json(reg.list_models()).into_response()
}

pub async fn health(State(app): State<Arc<App>>) -> Response {
    let guard = app.log.lock().await;
    let broken = guard.verify().unwrap_or(Some(u64::MAX));
    Json(json!({
        "ok": broken.is_none() && guard.tampered_at.is_none(),
        "chain_break_at": broken,
        "tampered_at": guard.tampered_at,
        "head_seq": guard.seq,
        "version": env!("CARGO_PKG_VERSION"),
        "git_sha": env!("GIT_SHA"),
        "dropped_decisions": app.dropped_decisions.load(Ordering::Relaxed),
    }))
    .into_response()
}

pub async fn metrics_route(State(app): State<Arc<App>>) -> Response {
    (
        [("content-type", "text/plain; version=0.0.4")],
        metrics::render_metrics(&app.ledger),
    )
        .into_response()
}

pub async fn dash(State(app): State<Arc<App>>) -> Response {
    (
        [("content-type", "text/html; charset=utf-8")],
        metrics::dashboard_html(&app.ledger, app.cfg.cache.hit_rate_floor),
    )
        .into_response()
}

pub fn build_router(app: Arc<App>) -> Router {
    Router::new()
        .route("/v1/chat/completions", post(chat))
        .route("/v1/messages", post(messages))
        .route("/v1/models", get(list_models))
        .route("/health", get(health))
        .route("/metrics", get(metrics_route))
        .route("/dash", get(dash))
        .layer(DefaultBodyLimit::max(app.cfg.max_body_bytes))
        .with_state(app)
}
