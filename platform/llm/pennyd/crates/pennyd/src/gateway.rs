//! Pipeline: auth (strict) -> resolve model -> ACL -> shape -> canonical
//! cache key -> reserve budget -> route (own lane + fit-checked fallbacks)
//! -> per-lane dialect shaping -> settle -> decision log (key FINGERPRINTS,
//! request_id, latency). P0-4/5/6 repairs integrated; see FAILURE_MODES.md.

use crate::settle_stream::{SettleContext, SettleStream};
use crate::{
    catalog, metrics,
    trace::{TraceFinish, TraceStore},
};
use axum::{
    body::Body,
    extract::{DefaultBodyLimit, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
    routing::{get, post, put},
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

struct RequestContext {
    started: Instant,
    now: u64,
    req: String,
    requested_model: String,
}

pub struct App {
    pub cfg: Config,
    pub registry: RwLock<Arc<Registry>>,
    pub router: RwLock<Arc<LaneRouter>>,
    pub cache: ExactCache,
    pub budgets: Budgets,
    pub ledger: Arc<Ledger>,
    pub traces: Arc<TraceStore>,
    pub log: Mutex<DecisionLog>,
    pub catalog_lock: Mutex<()>,
    pub dropped_decisions: AtomicU64,
}

pub(crate) fn registry_snapshot(app: &App) -> Arc<Registry> {
    app.registry
        .read()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
        .clone()
}

pub(crate) fn router_snapshot(app: &App) -> Arc<LaneRouter> {
    app.router
        .read()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
        .clone()
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

fn clean_surface(value: &str) -> Option<String> {
    let value = value.trim();
    if value.is_empty() || value.len() > 64 {
        return None;
    }
    value
        .chars()
        .all(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.' | ':'))
        .then(|| value.to_string())
}

fn surface_name(headers: &HeaderMap, format: EdgeFormat) -> String {
    if let Some(surface) = headers
        .get("x-estate-surface")
        .and_then(|value| value.to_str().ok())
        .and_then(clean_surface)
    {
        return surface;
    }
    let user_agent = headers
        .get("user-agent")
        .and_then(|value| value.to_str().ok())
        .unwrap_or("")
        .to_ascii_lowercase();
    for (needle, name) in [
        ("claude-code", "claude-code"),
        ("claude-cli", "claude-code"),
        ("claude desktop", "claude-desktop"),
        ("claude-desktop", "claude-desktop"),
        ("opencode", "opencode"),
        ("dsh", "dsh"),
        ("codex", "codex"),
        ("kimi", "kimi"),
        ("pi", "pi"),
    ] {
        if user_agent.contains(needle) {
            return name.into();
        }
    }
    match format {
        EdgeFormat::Anthropic => "anthropic".into(),
        EdgeFormat::OpenAi => "openai".into(),
    }
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
fn resolve_chain(
    reg: &Registry,
    entry: &ModelEntry,
    est_tokens: u64,
) -> Result<Vec<String>, PennyError> {
    if !fits(entry, est_tokens) {
        return Err(PennyError::BadRequest(format!(
            "estimated {est_tokens} tokens exceeds context window of {}",
            entry.canonical_name()
        )));
    }
    let mut seen = std::collections::HashSet::new();
    let mut chain = Vec::new();
    let mut candidates = vec![Ok(entry.canonical_name())];
    candidates.extend(entry.model.fallbacks.iter().map(|f| match reg.resolve(f) {
        Some(e) => Ok(e.canonical_name()),
        None => Err(PennyError::BadRequest(format!(
            "{} declares unknown fallback {f:?}",
            entry.canonical_name()
        ))),
    }));
    for cand in candidates {
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
    let mut key_body = shaped.clone();
    if let Some(object) = key_body.as_object_mut() {
        // The canonical model is added separately. These fields do not change a
        // completed answer; every other generation control does.
        object.remove("model");
        object.remove("stream");
        object.remove("stream_options");
        object.remove("penny_lane");
    }
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

fn error_fields(e: &PennyError) -> Value {
    match e {
        PennyError::BudgetExceeded { key } => {
            json!({"kind": "budget_exceeded", "key_fp": key})
        }
        PennyError::Unauthorized => json!({"kind": "unauthorized"}),
        PennyError::ModelNotAllowed { key, model } => {
            json!({"kind": "model_not_allowed", "key_fp": key, "model": model})
        }
        PennyError::AllLanesFailed => json!({"kind": "all_lanes_failed"}),
        PennyError::RateLimited {
            lane,
            retry_after_s,
        } => json!({
            "kind": "rate_limited", "lane": lane, "retry_after_s": retry_after_s
        }),
        PennyError::Upstream { lane, status, body } => json!({
            "kind": "upstream", "lane": lane, "upstream_status": status,
            "detail": body.chars().take(240).collect::<String>()
        }),
        PennyError::BadRequest(message) => {
            json!({"kind": "bad_request", "detail": message})
        }
        PennyError::Config(message) => json!({"kind": "config", "detail": message}),
    }
}

fn error_kind(e: &PennyError) -> &'static str {
    match e {
        PennyError::BudgetExceeded { .. } => "budget_exceeded",
        PennyError::Unauthorized => "unauthorized",
        PennyError::ModelNotAllowed { .. } => "model_not_allowed",
        PennyError::AllLanesFailed => "all_lanes_failed",
        PennyError::RateLimited { .. } => "rate_limited",
        PennyError::Upstream { .. } => "upstream",
        PennyError::BadRequest(_) => "bad_request",
        PennyError::Config(_) => "config",
    }
}

fn usage_u64(usage: &Value, names: &[&str]) -> u64 {
    names
        .iter()
        .find_map(|name| usage.get(*name).and_then(Value::as_u64))
        .unwrap_or(0)
}

fn cache_usage(usage: &Value) -> (u64, u64) {
    let read = usage_u64(
        usage,
        &[
            "cache_read_input_tokens",
            "cache_read_tokens",
            "cached_tokens",
        ],
    )
    .max(
        usage
            .pointer("/prompt_tokens_details/cached_tokens")
            .and_then(Value::as_u64)
            .unwrap_or(0),
    );
    let write = usage_u64(
        usage,
        &["cache_creation_input_tokens", "cache_write_tokens"],
    );
    (read, write)
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
    let requested_model = body
        .get("model")
        .and_then(Value::as_str)
        .unwrap_or("default")
        .to_string();
    let wants_stream = body.get("stream").and_then(Value::as_bool).unwrap_or(false);
    let surface = surface_name(headers, format);
    app.traces.begin(
        &req,
        now,
        &surface,
        match format {
            EdgeFormat::OpenAi => "openai",
            EdgeFormat::Anthropic => "anthropic",
        },
        &requested_model,
        wants_stream,
    );
    let ctx = RequestContext {
        started,
        now,
        req,
        requested_model,
    };
    match handle_chat_inner(app, headers, body, format, &ctx).await {
        Ok(response) => Ok(response),
        Err(error) => {
            let key_fp = headers
                .get("authorization")
                .and_then(|value| value.to_str().ok())
                .and_then(|value| value.strip_prefix("Bearer "))
                .map(fingerprint);
            log_decision(
                app,
                ctx.now,
                &ctx.req,
                ctx.started,
                json!({
                    "decision": "error",
                    "key_fp": key_fp.clone(),
                    "requested_model": ctx.requested_model,
                    "error": error_fields(&error),
                }),
            )
            .await;
            app.traces.finish(
                &ctx.req,
                TraceFinish {
                    status: "error".into(),
                    latency_ms: ctx.started.elapsed().as_millis() as u64,
                    key_fp,
                    error_kind: Some(error_kind(&error).into()),
                    ..TraceFinish::default()
                },
            );
            Err(error)
        }
    }
}

async fn handle_chat_inner(
    app: &App,
    headers: &HeaderMap,
    body: Value,
    format: EdgeFormat,
    ctx: &RequestContext,
) -> Result<Response, PennyError> {
    let started = ctx.started;
    let now = ctx.now;
    let req = ctx.req.clone();

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

    let reg = registry_snapshot(app);
    let entry = reg.resolve(&requested).ok_or_else(|| {
        PennyError::BadRequest(format!(
            "unknown model '{requested}'. Available: {}",
            reg.alias_list()
        ))
    })?;
    check_acl(&app.cfg, &key, entry)?;
    let canonical_model = entry.canonical_name();
    app.traces.route(&req, &canonical_model, None);
    if !wants_stream {
        app.ledger.mark_cache_eligible();
    }

    // dialect-agnostic shaping FIRST: the cache key is computed on this body
    let (mut shaped, _) =
        shaping::truncate_tool_results(body.clone(), app.cfg.shaping.tool_result_max_chars);
    shaped = shaping::floor_max_tokens(shaped, entry.model.min_output_tokens);
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
                    app.traces.finish(
                        &req,
                        TraceFinish {
                            lane: Some(canonical_model.clone()),
                            status: "cache_hit".into(),
                            in_tokens: in_tok,
                            exact_cache_hit: true,
                            latency_ms: started.elapsed().as_millis() as u64,
                            key_fp: Some(kfp.clone()),
                            ..TraceFinish::default()
                        },
                    );
                    v["penny_cache"] = json!("hit");
                    log_decision(
                        app,
                        now,
                        &req,
                        started,
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

    let chain = resolve_chain(&reg, entry, est_tokens)?;
    // Streaming is byte-passed for a same-dialect edge. Anthropic ingress can
    // translate OpenAI lanes, but OpenAI ingress has no Anthropic-stream
    // translator yet; skip those lanes rather than return the wrong wire
    // format. A non-streaming fallback remains available.
    let chain = if wants_stream && format == EdgeFormat::OpenAi {
        let openai_only: Vec<String> = chain
            .into_iter()
            .filter(|name| lane_dialect(&reg, name) != "anthropic")
            .collect();
        if openai_only.is_empty() {
            return Err(PennyError::BadRequest(
                "no OpenAI-dialect lane can serve this streaming request".into(),
            ));
        }
        openai_only
    } else {
        chain
    };
    let est_usd = est_cost_usd(est_tokens, entry, &app.cfg);
    // P0-5: reserve BEFORE dispatch; refusal happens pre-spend
    app.budgets.reserve(&key, est_usd, now)?;

    let router = router_snapshot(app);

    if wants_stream {
        match router.route_chain_stream(&chain, &shaped, now).await {
            Ok((lane_idx, stream)) => {
                let lane = router.lanes[lane_idx].clone();
                app.traces.route(&req, &canonical_model, Some(lane.name()));
                log_decision(
                    app,
                    now,
                    &req,
                    started,
                    json!({"decision": "route_stream", "key_fp": kfp.clone(), "model": canonical_model,
                           "lane": lane.name(), "in_tokens_est": est_tokens,
                           "usd_est": est_usd, "est": true}),
                )
                .await;
                // settle the reservation when the stream completes/ errors
                let guarded = SettleStream::new(
                    stream,
                    SettleContext {
                        budgets: app.budgets.clone(),
                        key: key.clone(),
                        reserved_usd: est_usd,
                        price_in: lane.price_in_per_mtok(),
                        price_out: lane.price_out_per_mtok(),
                        estimated_input_tokens: est_tokens,
                        ledger: app.ledger.clone(),
                        traces: app.traces.clone(),
                        trace_req: req.clone(),
                        key_fp: kfp,
                        started,
                    },
                );
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
            let in_tok = usage
                .get("prompt_tokens")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            let out_tok = usage
                .get("completion_tokens")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            let actual_usd = in_tok as f64 * lane.price_in_per_mtok() / 1e6
                + out_tok as f64 * lane.price_out_per_mtok() / 1e6;
            let (cache_read, cache_write) = cache_usage(&usage);
            app.budgets.settle(&key, est_usd, actual_usd, now)?;
            app.ledger.charge(in_tok, out_tok, actual_usd);
            app.traces.finish(
                &req,
                TraceFinish {
                    lane: Some(lane.name().to_string()),
                    status: "ok".into(),
                    in_tokens: in_tok,
                    out_tokens: out_tok,
                    cache_read_tokens: cache_read,
                    cache_write_tokens: cache_write,
                    cost_usd: actual_usd,
                    latency_ms: started.elapsed().as_millis() as u64,
                    key_fp: Some(kfp.clone()),
                    ..TraceFinish::default()
                },
            );

            resp["penny_lane"] = json!(lane.name());
            let cacheable = resp
                .get("penny_cacheable")
                .and_then(|v| v.as_bool())
                .unwrap_or(true);
            if cacheable {
                app.cache.insert(
                    ck.clone(),
                    serde_json::to_string(&resp).unwrap_or_default(),
                    now,
                );
            }
            log_decision(
                app,
                now,
                &req,
                started,
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
        Err(e) => {
            return anthropic_err(
                "invalid_request_error",
                StatusCode::BAD_REQUEST,
                &e.to_string(),
            )
        }
    };
    match handle_chat(&app, &headers, canonical, EdgeFormat::Anthropic).await {
        Ok(r) => r,
        // P1-9: the error kind must match the failure
        Err(PennyError::BudgetExceeded { key }) => anthropic_err(
            "rate_limit_error",
            StatusCode::TOO_MANY_REQUESTS,
            &format!("budget exceeded for key {key}"),
        ),
        Err(PennyError::Unauthorized) => anthropic_err(
            "authentication_error",
            StatusCode::UNAUTHORIZED,
            "unknown API key",
        ),
        Err(PennyError::ModelNotAllowed { key, model }) => anthropic_err(
            "permission_error",
            StatusCode::FORBIDDEN,
            &format!("key {key} is not allowed to use model {model}"),
        ),
        Err(PennyError::BadRequest(m)) => {
            anthropic_err("invalid_request_error", StatusCode::BAD_REQUEST, &m)
        }
        Err(PennyError::RateLimited {
            lane,
            retry_after_s,
        }) => {
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
    let reg = registry_snapshot(&app);
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

pub async fn requests_route(State(app): State<Arc<App>>) -> Response {
    (
        [("content-type", "application/json")],
        Json(json!({"requests": app.traces.snapshot(500)})),
    )
        .into_response()
}

pub async fn dash(State(app): State<Arc<App>>) -> Response {
    let registry = registry_snapshot(&app);
    let traces = app.traces.snapshot(200);
    (
        [("content-type", "text/html; charset=utf-8")],
        metrics::dashboard_html_with_traces(
            &app.ledger,
            app.cfg.cache.hit_rate_floor,
            &registry,
            &traces,
        ),
    )
        .into_response()
}

pub fn build_router(app: Arc<App>) -> Router {
    Router::new()
        .route("/v1/chat/completions", post(chat))
        .route("/v1/messages", post(messages))
        .route("/v1/models", get(list_models))
        .route("/admin/models", get(catalog::list))
        .route(
            "/admin/models/{provider}/{model}",
            put(catalog::upsert).delete(catalog::remove),
        )
        .route("/health", get(health))
        .route("/health/liveliness", get(health))
        .route("/healthz", get(health))
        .route("/metrics", get(metrics_route))
        .route("/api/requests", get(requests_route))
        .route("/dash", get(dash))
        .layer(DefaultBodyLimit::max(app.cfg.max_body_bytes))
        .with_state(app)
}
