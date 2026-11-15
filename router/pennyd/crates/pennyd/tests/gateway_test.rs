use async_trait::async_trait;
use axum::{body::Body, http::{Request, StatusCode}};
use penny_core::{
    budget::Budgets,
    cache::ExactCache,
    config::{Config, LaneClass},
    decision_log::DecisionLog,
    error::PennyError,
    ledger::Ledger,
    providers::Registry,
    router::{ByteStream, LlmLane, Router as LaneRouter},
};
use pennyd::gateway::{build_router, App};
use serde_json::{json, Value};
use std::sync::{Arc, RwLock};
use tower::ServiceExt;

struct Mock { name: &'static str, fail: bool }

#[async_trait]
impl LlmLane for Mock {
    fn name(&self) -> &str { self.name }
    fn class(&self) -> LaneClass { LaneClass::Free }
    fn price_in_per_mtok(&self) -> f64 { 1.0 }
    fn price_out_per_mtok(&self) -> f64 { 4.0 }
    fn supports_streaming(&self) -> bool { true }
    async fn complete(&self, _b: &Value) -> Result<Value, PennyError> {
        if self.fail {
            return Err(PennyError::Upstream { lane: self.name.into(), status: 500, body: "boom".into() });
        }
        Ok(json!({
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            "choices": [],
            "penny_cacheable": true
        }))
    }
    async fn complete_stream(&self, _b: &Value) -> Result<ByteStream, PennyError> {
        Ok(Box::pin(futures_util::stream::iter(vec![
            Ok(bytes::Bytes::from_static(
                b"data: {\"choices\":[{\"delta\":{\"content\":\"hi\"}}]}\n\ndata: [DONE]\n\n",
            )),
        ])))
    }
}

const PROVIDER: &str = r#"
id = "mock"
dialect = "openai"
base_url = "http://127.0.0.1:9"

[auth]
kind = "none"

[[models]]
id = "mock-model"
class = "free"
price_in_per_mtok = 0.0
price_out_per_mtok = 0.0
aliases = ["test-chat"]
fallbacks = ["mock-fallback"]

[[models]]
id = "mock-fallback"
class = "free"
price_in_per_mtok = 0.0
price_out_per_mtok = 0.0

[[models]]
id = "tiny-window"
class = "free"
price_in_per_mtok = 0.0
price_out_per_mtok = 0.0
context_window = 100
"#;

fn test_app(budget: f64, fail_primary: bool) -> Arc<App> {
    let base = std::env::temp_dir().join(format!("pennyd-it-{}-{budget}-{fail_primary}", std::process::id()));
    let _ = std::fs::remove_dir_all(&base);
    let providers = base.join("providers");
    std::fs::create_dir_all(&providers).unwrap();
    std::fs::write(providers.join("mock.toml"), PROVIDER).unwrap();
    let log_path = base.join("decisions.jsonl");
    let _ = std::fs::remove_file(&log_path);
    let log_path = log_path.display().to_string();
    let providers_dir = providers.display().to_string();

    let toml_str = format!(r#"
bind = "127.0.0.1:0"
log_path = "{log_path}"
providers_dir = "{providers_dir}"
[cache]
capacity = 100
ttl_min_s = 60
ttl_max_s = 600
hit_rate_floor = 0.5
[budgets]
default_daily_usd = 999.0
[shaping]
cache_control = true
max_tokens_cap = 1024
tool_result_max_chars = 500
[router]
breaker_threshold = 2
breaker_cooldown_s = 10
[[keys]]
key = "k1"
daily_budget_usd = {budget}
allowed_models = ["test-chat", "tiny-window"]

[[keys]]
key = "k2-restricted"
daily_budget_usd = {budget}
allowed_models = ["nonexistent-alias"]
"#);
    let cfg: Config = toml::from_str(&toml_str).unwrap();
    LOG_PATH.store_path(cfg.log_path.clone());
    let registry = Arc::new(Registry::load_dir(&providers).unwrap());
    Arc::new(App {
        cache: ExactCache::new(cfg.cache.capacity, cfg.cache.ttl_min_s, cfg.cache.ttl_max_s),
        budgets: Budgets::new(),
        ledger: Ledger::default(),
        registry: RwLock::new(registry.clone()),
        router: RwLock::new(Arc::new(LaneRouter::new(
            vec![
                Arc::new(Mock { name: "mock/mock-model", fail: fail_primary }),
                Arc::new(Mock { name: "mock/mock-fallback", fail: false }),
            ],
            2,
            10,
            1024,
        ))),
        cfg,
        log: tokio::sync::Mutex::new(DecisionLog::open(&log_path).unwrap()),
        dropped_decisions: std::sync::atomic::AtomicU64::new(0),
    })
}

struct LogPath;
static LOG_PATH: LogPath = LogPath;
impl LogPath {
    fn store_path(&self, _p: String) {}
    // the path is deterministic per (pid, budget): rebuild it
    fn get(&self, budget: f64) -> std::path::PathBuf {
        std::env::temp_dir().join(format!("pennyd-it-{}-{budget}-false", std::process::id()))
            .join("decisions.jsonl")
    }
}

fn post_req(body: &Value) -> Request<Body> {
    Request::builder()
        .method("POST")
        .uri("/v1/chat/completions")
        .header("content-type", "application/json")
        .header("authorization", "Bearer k1")
        .body(Body::from(body.to_string()))
        .unwrap()
}

async fn read_json(resp: axum::http::Response<Body>) -> Value {
    serde_json::from_slice(&axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap()).unwrap()
}

#[tokio::test]
async fn alias_resolves_and_caches() {
    let app = test_app(10.0, false);
    let router = build_router(app.clone());
    let body = json!({"model": "test-chat", "messages": [{"role": "user", "content": "hello"}]});

    let r1 = router.clone().oneshot(post_req(&body)).await.unwrap();
    assert_eq!(r1.status(), StatusCode::OK);
    let v1 = read_json(r1).await;
    assert_eq!(v1["penny_lane"], "mock/mock-model");
    assert!(v1.get("penny_cache").is_none());

    let r2 = router.clone().oneshot(post_req(&body)).await.unwrap();
    let v2 = read_json(r2).await;
    assert_eq!(v2["penny_cache"], "hit");
    assert_eq!(app.ledger.snapshot().cache_hits, 1);
    assert!(app.log.lock().await.verify().unwrap().is_none());
}

#[tokio::test]
async fn declared_fallback_escalates_end_to_end() {
    let app = test_app(10.0, true); // primary lane fails
    let router = build_router(app);
    let resp = router
        .oneshot(post_req(&json!({"model": "test-chat", "messages": []})))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let v = read_json(resp).await;
    assert_eq!(v["penny_lane"], "mock/mock-fallback"); // explicit chain, not global order
}

#[tokio::test]
async fn streaming_passes_through_sse() {
    let app = test_app(10.0, false);
    let router = build_router(app);
    let resp = router
        .oneshot(post_req(&json!({"model": "test-chat", "stream": true, "messages": []})))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    assert!(resp.headers()["content-type"].to_str().unwrap().contains("text/event-stream"));
}

#[tokio::test]
async fn unknown_key_rejected_by_default() {
    let app = test_app(10.0, false);
    let router = build_router(app);
    let resp = router
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/v1/chat/completions")
                .header("content-type", "application/json")
                .header("authorization", "Bearer intruder")
                .body(Body::from(json!({"model": "test-chat", "messages": []}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn unknown_model_lists_available() {
    let app = test_app(10.0, false);
    let router = build_router(app);
    let resp = router
        .oneshot(post_req(&json!({"model": "gpt-99", "messages": []})))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    let v = read_json(resp).await;
    assert!(v["error"].as_str().unwrap().contains("test-chat"));
}

#[tokio::test]
async fn models_endpoint_lists_registry() {
    let app = test_app(10.0, false);
    let router = build_router(app);
    let resp = router
        .oneshot(Request::builder().method("GET").uri("/v1/models").body(Body::empty()).unwrap())
        .await
        .unwrap();
    let v = read_json(resp).await;
    let ids: Vec<&str> = v["data"].as_array().unwrap().iter()
        .map(|m| m["id"].as_str().unwrap()).collect();
    assert!(ids.contains(&"mock/mock-model") && ids.contains(&"mock/mock-fallback"));
}

#[tokio::test]
async fn oversized_body_rejected_413() {
    // F-IN-5: a 2MB+ payload must be refused before any upstream exposure
    let app = test_app(10.0, false);
    let router = build_router(app);
    let big = "x".repeat(2_200_000);
    let resp = router
        .oneshot(post_req(&json!({"model": "test-chat", "messages": [{"role": "user", "content": big}]})))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::PAYLOAD_TOO_LARGE);
}

#[tokio::test]
async fn poisoned_cache_entry_falls_through() {
    // F-CA-3: corrupt cache value -> evicted, request served from the lane
    let app = test_app(10.0, false);
    let router = build_router(app.clone());
    let body = json!({"model": "test-chat", "messages": [{"role": "user", "content": "hi"}]});
    let r1 = router.clone().oneshot(post_req(&body)).await.unwrap();
    assert_eq!(r1.status(), StatusCode::OK);

    let ck = penny_core::keys::cache_key("mock/mock-model", &body);
    app.cache.insert(ck, "{corrupt".to_string(), 0);

    let r2 = router.clone().oneshot(post_req(&body)).await.unwrap();
    assert_eq!(r2.status(), StatusCode::OK); // not a 400 from cache poison
    let v2 = read_json(r2).await;
    assert!(v2.get("penny_cache").is_none()); // served fresh, entry replaced
}

#[tokio::test]
async fn context_window_overflow_refused_before_routing() {
    // F-RO-5: known-oversized request refuses cleanly instead of failing
    // downstream on every lane
    let app = test_app(10.0, false);
    let router = build_router(app);
    let big = "word ".repeat(1000); // ~5000 chars -> ~1250 est tokens >> 100 window
    let resp = router
        .oneshot(post_req(&json!({"model": "tiny-window", "messages": [{"role": "user", "content": big}]})))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    let v = read_json(resp).await;
    assert!(v["error"].as_str().unwrap().contains("context window"));
}

#[tokio::test]
async fn model_acl_enforced_403() {
    // F-IN-6: restricted key cannot reach models outside its ACL
    let app = test_app(10.0, false);
    let router = build_router(app);
    let resp = router
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/v1/chat/completions")
                .header("content-type", "application/json")
                .header("authorization", "Bearer k2-restricted")
                .body(Body::from(json!({"model": "test-chat", "messages": []}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::FORBIDDEN);
    let v = read_json(resp).await;
    assert_eq!(v["error"]["type"], "model_not_allowed");
}

#[tokio::test]
async fn bearer_key_never_reaches_the_decision_log() {
    // P0-4 probe from the adversarial review
    let app = test_app(10.0, false);
    let router = build_router(app.clone());
    let body = json!({"model": "test-chat", "messages": [{"role": "user", "content": "secret check"}]});
    let r = router.oneshot(post_req(&body)).await.unwrap();
    assert_eq!(r.status(), StatusCode::OK);
    let log_text = std::fs::read_to_string(LOG_PATH.get(10.0)).unwrap();
    assert!(!log_text.contains("k1"), "raw bearer key leaked into decision log");
    assert!(log_text.contains("key_fp"), "fingerprint expected in log rows");
}

#[tokio::test]
async fn anthropic_error_kinds_match_failures() {
    // P1-9 probe: 401 auth, 403 permission, 400 invalid_request
    let app = test_app(10.0, false);
    let router = build_router(app.clone());
    // 401
    let unauth = Request::builder().method("POST").uri("/v1/messages")
        .header("content-type", "application/json")
        .header("authorization", "Bearer nobody")
        .body(Body::from(json!({"model": "test-chat", "max_tokens": 10,
            "messages": [{"role": "user", "content": "x"}]}).to_string())).unwrap();
    let r = router.clone().oneshot(unauth).await.unwrap();
    assert_eq!(r.status(), StatusCode::UNAUTHORIZED);
    assert_eq!(read_json(r).await["error"]["type"], "authentication_error");
    // 403
    let forbidden = Request::builder().method("POST").uri("/v1/messages")
        .header("content-type", "application/json")
        .header("authorization", "Bearer k2-restricted")
        .body(Body::from(json!({"model": "test-chat", "max_tokens": 10,
            "messages": [{"role": "user", "content": "x"}]}).to_string())).unwrap();
    let r2 = router.oneshot(forbidden).await.unwrap();
    assert_eq!(r2.status(), StatusCode::FORBIDDEN);
    assert_eq!(read_json(r2).await["error"]["type"], "permission_error");
}

#[tokio::test]
async fn full_pipeline_proof_everything_works_together() {
    // The commercial proof: one session exercises every subsystem and
    // cross-asserts ledger + decision log + health at the end.
    let app = test_app(10.0, false);
    let router = build_router(app.clone());
    let body = json!({"model": "test-chat", "messages": [{"role": "user", "content": "proof"}]});

    // 1. route miss -> upstream -> ledger + log
    let r1 = router.clone().oneshot(post_req(&body)).await.unwrap();
    assert_eq!(r1.status(), StatusCode::OK);
    assert_eq!(read_json(r1).await["penny_lane"], "mock/mock-model");

    // 2. identical request -> cache hit, no second upstream
    let r2 = router.clone().oneshot(post_req(&body)).await.unwrap();
    assert_eq!(read_json(r2).await["penny_cache"], "hit");

    // 3. streaming -> SSE, flagged estimate
    let r3 = router
        .clone()
        .oneshot(post_req(&json!({"model": "test-chat", "stream": true, "messages": []})))
        .await
        .unwrap();
    assert!(r3.headers()["content-type"].to_str().unwrap().contains("text/event-stream"));

    // 4. ACL: restricted key refused
    let r4 = router
        .clone()
        .oneshot(
            Request::builder().method("POST").uri("/v1/chat/completions")
                .header("content-type", "application/json")
                .header("authorization", "Bearer k2-restricted")
                .body(Body::from(json!({"model": "test-chat", "messages": []}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(r4.status(), StatusCode::FORBIDDEN);

    // 5. unknown model -> 400 with discovery
    let r5 = router
        .clone()
        .oneshot(post_req(&json!({"model": "nope", "messages": []})))
        .await
        .unwrap();
    assert_eq!(r5.status(), StatusCode::BAD_REQUEST);

    // 6. cross-subsystem consistency: ledger, log chain, health
    let snap = app.ledger.snapshot();
    assert_eq!(snap.cache_hits, 1);
    assert!(snap.spend_usd > 0.0);
    assert!(app.log.lock().await.verify().unwrap().is_none());
    let h = router
        .oneshot(Request::builder().method("GET").uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    let hv = read_json(h).await;
    assert_eq!(hv["ok"], true);
    assert_eq!(hv["dropped_decisions"], 0);
}

fn messages_req(model: &str, stream: bool) -> Request<Body> {
    let mut body = json!({
        "model": model, "max_tokens": 512,
        "system": "be terse",
        "messages": [{"role": "user", "content": "hello from claude"}],
    });
    if stream {
        body["stream"] = json!(true);
    }
    Request::builder()
        .method("POST")
        .uri("/v1/messages")
        .header("content-type", "application/json")
        .header("authorization", "Bearer k1")
        .header("anthropic-version", "2023-06-01")
        .body(Body::from(body.to_string()))
        .unwrap()
}

#[tokio::test]
async fn messages_ingress_returns_anthropic_shape() {
    let app = test_app(10.0, false);
    let router = build_router(app);
    let resp = router.oneshot(messages_req("test-chat", false)).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let v = read_json(resp).await;
    assert_eq!(v["type"], "message");
    assert_eq!(v["role"], "assistant");
    assert_eq!(v["content"][0]["type"], "text");
    assert_eq!(v["stop_reason"], "end_turn");
    assert_eq!(v["usage"]["input_tokens"], 100); // mock lane usage, anthropic field names
}

#[tokio::test]
async fn messages_ingress_streaming_translates_sse() {
    let app = test_app(10.0, false);
    let router = build_router(app);
    let resp = router.oneshot(messages_req("test-chat", true)).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    assert!(resp.headers()["content-type"].to_str().unwrap().contains("text/event-stream"));
    let bytes = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    let text = String::from_utf8(bytes.to_vec()).unwrap();
    for needle in ["message_start", "content_block_delta", "hi", "message_stop"] {
        assert!(text.contains(needle), "missing {needle}");
    }
}

#[tokio::test]
async fn messages_and_openai_share_cache_namespace() {
    // F-AI-2: identical semantics through both edges -> one cache namespace
    let app = test_app(10.0, false);
    let router = build_router(app.clone());
    // canonical body for the anthropic request == these messages + system
    let openai_body = json!({"model": "test-chat", "messages": [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "shared cache check"}]});
    let r1 = router.clone().oneshot(post_req(&openai_body)).await.unwrap();
    assert_eq!(r1.status(), StatusCode::OK);
    let r2 = router.clone().oneshot(messages_req("test-chat", false)).await.unwrap();
    assert_eq!(r2.status(), StatusCode::OK);
    // different content -> miss; then prove sharing with identical content
    assert_eq!(app.ledger.snapshot().cache_hits, 0);
    // now identical semantic content via both edges
    let app2 = test_app(10.0, false);
    let router2 = build_router(app2.clone());
    let body = json!({"model": "test-chat", "messages": [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "same"}]});
    let _ = router2.clone().oneshot(post_req(&body)).await.unwrap();
    let mut msg = json!({"model": "test-chat", "max_tokens": 512,
        "system": "be terse", "messages": [{"role": "user", "content": "same"}]});
    msg["messages"] = json!([{"role": "user", "content": "same"}]);
    let r = router2.clone().oneshot(
        Request::builder().method("POST").uri("/v1/messages")
            .header("content-type", "application/json")
            .header("authorization", "Bearer k1")
            .body(Body::from(msg.to_string())).unwrap()).await.unwrap();
    let v = read_json(r).await;
    assert_eq!(v["penny_cache"], "hit", "cross-edge semantic requests share one cache namespace");
    assert_eq!(app2.ledger.snapshot().cache_hits, 1);
}

#[tokio::test]
async fn messages_ingress_errors_are_anthropic_shaped() {
    let app = test_app(10.0, false);
    let router = build_router(app);
    let bad = Request::builder().method("POST").uri("/v1/messages")
        .header("content-type", "application/json")
        .header("authorization", "Bearer k1")
        .body(Body::from(json!({"model": "test-chat"}).to_string())).unwrap();
    let resp = router.oneshot(bad).await.unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    let v = read_json(resp).await;
    assert_eq!(v["type"], "error");
    assert_eq!(v["error"]["type"], "invalid_request_error");
}

#[tokio::test]
async fn budget_refusal_is_loud() {
    let app = test_app(0.00001, false);
    let router = build_router(app);
    let resp = router
        .oneshot(post_req(&json!({"model": "test-chat", "messages": []})))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::TOO_MANY_REQUESTS);
    let v = read_json(resp).await;
    assert_eq!(v["error"]["type"], "budget_exceeded");
    assert!(v["error"]["key_fp"].is_string()); // P0-4: never the raw key
}
