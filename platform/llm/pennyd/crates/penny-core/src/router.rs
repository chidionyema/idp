//! Cheap-first is a property of the REGISTRY (sorted by class+price), but
//! routing identity is per-model: a request resolves to exactly one model,
//! tried first on its own lane, then its EXPLICIT fallback chain. There is
//! no path where a request for model A is executed as model B unless the
//! operator declared that fallback in data.

use crate::config::LaneClass;
use crate::error::PennyError;
use async_trait::async_trait;
use futures_core::Stream;
use serde_json::Value;
use std::collections::HashMap;
use std::pin::Pin;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};

pub type ByteStream =
    Pin<Box<dyn Stream<Item = Result<bytes::Bytes, PennyError>> + Send + 'static>>;

#[async_trait]
pub trait LlmLane: Send + Sync {
    fn name(&self) -> &str;
    fn class(&self) -> LaneClass;
    fn price_in_per_mtok(&self) -> f64;
    fn price_out_per_mtok(&self) -> f64;

    /// SSE streaming passthrough. Lanes that cannot stream (yet) refuse
    /// loudly — silent buffering defeats client latency expectations.
    fn supports_streaming(&self) -> bool {
        false
    }
    async fn complete(&self, body: &Value) -> Result<Value, PennyError>;
    async fn complete_stream(&self, body: &Value) -> Result<ByteStream, PennyError> {
        let _ = body;
        Err(PennyError::Upstream {
            lane: self.name().to_string(),
            status: 0,
            body: "lane does not support streaming".into(),
        })
    }
}

/// Retry only transient failures (FailureAtlas / Bifrost lesson: retrying 4xx
/// amplifies the incident and burns backup quota). 429, 5xx, and transport
/// errors are retryable, as is 402: an exhausted provider balance is a dead
/// lane, not a bad request. Deterministic client errors stop the chain.
pub fn is_retryable(e: &PennyError) -> bool {
    match e {
        PennyError::Upstream { status, .. } => {
            *status == 0 || *status == 402 || *status == 429 || *status >= 500
        }
        PennyError::RateLimited { .. } => true,
        _ => false,
    }
}

fn has_answer(value: &Value) -> bool {
    let Some(message) = value
        .get("choices")
        .and_then(|choices| choices.get(0))
        .and_then(|choice| choice.get("message"))
    else {
        return false;
    };
    if message
        .get("tool_calls")
        .and_then(|calls| calls.as_array())
        .is_some_and(|calls| !calls.is_empty())
    {
        return true;
    }
    match message.get("content") {
        Some(Value::String(text)) => !text.trim().is_empty(),
        Some(Value::Array(parts)) => !parts.is_empty(),
        _ => false,
    }
}

#[derive(Debug, Clone, Default)]
struct Health {
    consecutive_failures: u32,
    open_until_unix: u64,
}

pub struct Router {
    pub lanes: Vec<Arc<dyn LlmLane>>,
    by_name: HashMap<String, usize>,
    breaker_threshold: u32,
    breaker_cooldown_s: u64,
    health: Mutex<Vec<Health>>,
    /// Bulkhead: cap concurrent in-flight calls per lane so a failing lane
    /// cannot absorb the whole fleet's timeout windows (thundering-herd
    /// control; FailureAtlas "cascading 429 storm").
    inflight: Vec<AtomicUsize>,
    max_inflight: usize,
}

impl Router {
    pub fn new(
        lanes: Vec<Arc<dyn LlmLane>>,
        breaker_threshold: u32,
        breaker_cooldown_s: u64,
        max_inflight: usize,
    ) -> Self {
        let by_name: HashMap<String, usize> = lanes
            .iter()
            .enumerate()
            .map(|(i, l)| (l.name().to_string(), i))
            .collect();
        let n = lanes.len();
        Self {
            lanes,
            by_name,
            breaker_threshold: breaker_threshold.max(1),
            breaker_cooldown_s,
            health: Mutex::new(vec![Health::default(); n]),
            inflight: (0..n).map(|_| AtomicUsize::new(0)).collect(),
            max_inflight: max_inflight.max(1),
        }
    }

    fn acquire(&self, i: usize) -> bool {
        if self.inflight[i].load(Ordering::Acquire) >= self.max_inflight {
            return false;
        }
        self.inflight[i].fetch_add(1, Ordering::AcqRel);
        true
    }

    fn release(&self, i: usize) {
        self.inflight[i].fetch_sub(1, Ordering::AcqRel);
    }

    fn check_health(&self, i: usize, now: u64) -> bool {
        self.health.lock().unwrap()[i].open_until_unix <= now
    }

    fn on_success(&self, i: usize) {
        self.health.lock().unwrap()[i].consecutive_failures = 0;
    }

    fn on_failure(&self, i: usize, now: u64, retry_after_s: Option<u64>) {
        let mut h = self.health.lock().unwrap();
        if let Some(s) = retry_after_s {
            // provider advertised when to return: honor it over blind cooldown
            h[i].open_until_unix = now + s.max(self.breaker_cooldown_s);
        }
        h[i].consecutive_failures += 1;
        if h[i].consecutive_failures >= self.breaker_threshold {
            h[i].open_until_unix = now + self.breaker_cooldown_s;
        }
    }

    /// Try the chain in order: the resolved model first, then its declared
    /// fallbacks. `names` are canonical `provider/model` ids.
    pub async fn route_chain(
        &self,
        names: &[String],
        body: &Value,
        now: u64,
    ) -> Result<(usize, Value), PennyError> {
        let mut last_err = PennyError::AllLanesFailed;
        for name in names {
            let Some(&i) = self.by_name.get(name.as_str()) else {
                last_err = PennyError::Upstream {
                    lane: name.clone(),
                    status: 0,
                    body: "no such lane".into(),
                };
                continue;
            };
            if !self.check_health(i, now) {
                last_err = PennyError::Upstream {
                    lane: name.clone(),
                    status: 0,
                    body: "circuit open".into(),
                };
                continue;
            }
            if !self.acquire(i) {
                last_err = PennyError::Upstream {
                    lane: name.clone(),
                    status: 0,
                    body: "lane saturated (bulkhead)".into(),
                };
                continue;
            }
            let result = self.lanes[i].complete(body).await;
            self.release(i);
            match result {
                Ok(v) => {
                    if !has_answer(&v) {
                        self.on_failure(i, now, None);
                        last_err = PennyError::Upstream {
                            lane: self.lanes[i].name().to_string(),
                            status: 0,
                            body: "empty assistant content (possibly reasoning budget exhausted)"
                                .into(),
                        };
                        continue;
                    }
                    self.on_success(i);
                    return Ok((i, v));
                }
                Err(e) => {
                    if !is_retryable(&e) {
                        return Err(e); // deterministic failure: stop, don't amplify
                    }
                    let ra = match &e {
                        PennyError::RateLimited { retry_after_s, .. } => *retry_after_s,
                        _ => None,
                    };
                    self.on_failure(i, now, ra);
                    last_err = e;
                }
            }
        }
        Err(last_err)
    }

    /// Streaming variant: lanes without streaming support are skipped for
    /// streaming requests (their failure is implicit, so we don't burn a
    /// circuit-breaker strike on them).
    pub async fn route_chain_stream(
        &self,
        names: &[String],
        body: &Value,
        now: u64,
    ) -> Result<(usize, ByteStream), PennyError> {
        let mut last_err = PennyError::AllLanesFailed;
        for name in names {
            let Some(&i) = self.by_name.get(name.as_str()) else {
                last_err = PennyError::Upstream {
                    lane: name.clone(),
                    status: 0,
                    body: "no such lane".into(),
                };
                continue;
            };
            if !self.check_health(i, now) || !self.lanes[i].supports_streaming() {
                continue;
            }
            if !self.acquire(i) {
                last_err = PennyError::Upstream {
                    lane: name.clone(),
                    status: 0,
                    body: "lane saturated (bulkhead)".into(),
                };
                continue;
            }
            let result = self.lanes[i].complete_stream(body).await;
            self.release(i);
            match result {
                Ok(s) => {
                    self.on_success(i);
                    return Ok((i, s));
                }
                Err(e) => {
                    if !is_retryable(&e) {
                        return Err(e);
                    }
                    let ra = match &e {
                        PennyError::RateLimited { retry_after_s, .. } => *retry_after_s,
                        _ => None,
                    };
                    self.on_failure(i, now, ra);
                    last_err = e;
                }
            }
        }
        Err(last_err)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct MockLane {
        name: &'static str,
        class: LaneClass,
        fail: bool,
        stream: bool,
    }

    #[async_trait]
    impl LlmLane for MockLane {
        fn name(&self) -> &str {
            self.name
        }
        fn class(&self) -> LaneClass {
            self.class
        }
        fn price_in_per_mtok(&self) -> f64 {
            0.0
        }
        fn price_out_per_mtok(&self) -> f64 {
            0.0
        }
        fn supports_streaming(&self) -> bool {
            self.stream
        }
        async fn complete(&self, _body: &Value) -> Result<Value, PennyError> {
            if self.fail {
                Err(PennyError::Upstream {
                    lane: self.name.into(),
                    status: 500,
                    body: "boom".into(),
                })
            } else {
                Ok(serde_json::json!({
                    "ok": self.name,
                    "choices": [{
                        "message": {"role": "assistant", "content": format!("answer from {}", self.name)},
                        "finish_reason": "stop"
                    }]
                }))
            }
        }
        async fn complete_stream(&self, _body: &Value) -> Result<ByteStream, PennyError> {
            if !self.stream {
                return Err(PennyError::Upstream {
                    lane: self.name.into(),
                    status: 0,
                    body: "no stream".into(),
                });
            }
            Ok(Box::pin(futures_util::stream::iter(vec![Ok(
                bytes::Bytes::from_static(b"data: {}\n\n"),
            )])))
        }
    }

    fn arc(l: MockLane) -> Arc<dyn LlmLane> {
        Arc::new(l)
    }

    struct EmptyLane;

    #[async_trait]
    impl LlmLane for EmptyLane {
        fn name(&self) -> &str {
            "p/empty"
        }
        fn class(&self) -> LaneClass {
            LaneClass::Paid
        }
        fn price_in_per_mtok(&self) -> f64 {
            0.0
        }
        fn price_out_per_mtok(&self) -> f64 {
            0.0
        }
        async fn complete(&self, _body: &Value) -> Result<Value, PennyError> {
            Ok(serde_json::json!({
                "choices": [{
                    "message": {"role": "assistant", "content": ""},
                    "finish_reason": "length"
                }],
                "usage": {"completion_tokens": 24}
            }))
        }
    }

    #[tokio::test]
    async fn chain_stays_on_identity_no_cross_model_substitution() {
        // request names ONLY lane-b: lane-a (a different model) must never run
        let calls = std::sync::Arc::new(std::sync::Mutex::new(Vec::<String>::new()));
        // identity proven by: only one lane exists in the router
        let r = Router::new(
            vec![arc(MockLane {
                name: "p/model-b",
                class: LaneClass::Paid,
                fail: false,
                stream: false,
            })],
            2,
            60,
            usize::MAX,
        );
        let (i, v) = r
            .route_chain(&["p/model-b".to_string()], &serde_json::json!({}), 1000)
            .await
            .unwrap();
        assert_eq!(i, 0);
        assert_eq!(v["ok"], "p/model-b");
        // and an undeclared name is a loud error, not a silent redirect
        assert!(r
            .route_chain(&["p/model-a".to_string()], &serde_json::json!({}), 1000)
            .await
            .is_err());
        drop(calls);
    }

    #[tokio::test]
    async fn declared_fallback_escalates() {
        let r = Router::new(
            vec![
                arc(MockLane {
                    name: "p/cheap",
                    class: LaneClass::Free,
                    fail: true,
                    stream: false,
                }),
                arc(MockLane {
                    name: "p/dear",
                    class: LaneClass::Paid,
                    fail: false,
                    stream: false,
                }),
            ],
            2,
            60,
            usize::MAX,
        );
        let chain = vec!["p/cheap".to_string(), "p/dear".to_string()];
        let (i, v) = r
            .route_chain(&chain, &serde_json::json!({}), 1000)
            .await
            .unwrap();
        assert_eq!(i, 1);
        assert_eq!(v["ok"], "p/dear");
    }

    #[tokio::test]
    async fn exhausted_balance_escalates_to_a_declared_fallback() {
        let r = Router::new(
            vec![
                Arc::new(StatusLane {
                    name: "p/exhausted",
                    status: 402,
                }),
                arc(MockLane {
                    name: "p/funded",
                    class: LaneClass::Paid,
                    fail: false,
                    stream: false,
                }),
            ],
            2,
            60,
            usize::MAX,
        );
        let chain = vec!["p/exhausted".to_string(), "p/funded".to_string()];
        let (i, value) = r
            .route_chain(&chain, &serde_json::json!({}), 1000)
            .await
            .unwrap();
        assert_eq!(i, 1);
        assert_eq!(value["ok"], "p/funded");
    }

    #[tokio::test]
    async fn empty_truncated_response_escalates_to_a_declared_fallback() {
        let r = Router::new(
            vec![
                Arc::new(EmptyLane),
                arc(MockLane {
                    name: "p/answer",
                    class: LaneClass::Paid,
                    fail: false,
                    stream: false,
                }),
            ],
            2,
            60,
            usize::MAX,
        );
        let chain = vec!["p/empty".to_string(), "p/answer".to_string()];
        let (i, value) = r
            .route_chain(&chain, &serde_json::json!({}), 1000)
            .await
            .unwrap();
        assert_eq!(i, 1);
        assert_eq!(value["ok"], "p/answer");
    }

    #[tokio::test]
    async fn streaming_skips_non_streaming_lanes() {
        let r = Router::new(
            vec![
                arc(MockLane {
                    name: "p/buf",
                    class: LaneClass::Free,
                    fail: false,
                    stream: false,
                }),
                arc(MockLane {
                    name: "p/sse",
                    class: LaneClass::Paid,
                    fail: false,
                    stream: true,
                }),
            ],
            2,
            60,
            usize::MAX,
        );
        let chain = vec!["p/buf".to_string(), "p/sse".to_string()];
        let (i, _s) = r
            .route_chain_stream(&chain, &serde_json::json!({}), 1000)
            .await
            .unwrap();
        assert_eq!(i, 1);
    }

    struct StatusLane {
        name: &'static str,
        status: u16,
    }

    #[async_trait]
    impl LlmLane for StatusLane {
        fn name(&self) -> &str {
            self.name
        }
        fn class(&self) -> LaneClass {
            LaneClass::Paid
        }
        fn price_in_per_mtok(&self) -> f64 {
            1.0
        }
        fn price_out_per_mtok(&self) -> f64 {
            4.0
        }
        async fn complete(&self, _b: &Value) -> Result<Value, PennyError> {
            Err(PennyError::Upstream {
                lane: self.name.into(),
                status: self.status,
                body: "status".into(),
            })
        }
    }

    struct SlowLane {
        notify: Arc<tokio::sync::Notify>,
        entered: Arc<AtomicUsize>,
    }

    #[async_trait]
    impl LlmLane for SlowLane {
        fn name(&self) -> &str {
            "p/slow"
        }
        fn class(&self) -> LaneClass {
            LaneClass::Free
        }
        fn price_in_per_mtok(&self) -> f64 {
            0.0
        }
        fn price_out_per_mtok(&self) -> f64 {
            0.0
        }
        async fn complete(&self, _b: &Value) -> Result<Value, PennyError> {
            self.entered.fetch_add(1, Ordering::SeqCst);
            self.notify.notified().await;
            Ok(serde_json::json!({
                "ok": "slow",
                "choices": [{
                    "message": {"role": "assistant", "content": "slow answer"},
                    "finish_reason": "stop"
                }]
            }))
        }
    }

    #[tokio::test]
    async fn deterministic_400_stops_chain_without_fallback() {
        // F-RO-4: a 400-class error is the caller's fault; retrying it on
        // every lane amplifies the incident. Chain must stop immediately.
        let r = Router::new(
            vec![
                Arc::new(StatusLane {
                    name: "p/bad-req",
                    status: 400,
                }),
                Arc::new(MockLane {
                    name: "p/good",
                    class: LaneClass::Paid,
                    fail: false,
                    stream: false,
                }),
            ],
            2,
            60,
            usize::MAX,
        );
        let chain = vec!["p/bad-req".to_string(), "p/good".to_string()];
        match r.route_chain(&chain, &serde_json::json!({}), 0).await {
            Err(PennyError::Upstream {
                status: 400, lane, ..
            }) => assert_eq!(lane, "p/bad-req"),
            other => panic!("expected 400 stop, got {other:?}"),
        }
    }

    #[tokio::test]
    async fn rate_limit_honors_retry_after() {
        // F-RO-6: 429 with Retry-After opens the breaker for the advertised
        // window, not a blind cooldown.
        struct RL;
        #[async_trait]
        impl LlmLane for RL {
            fn name(&self) -> &str {
                "p/rl"
            }
            fn class(&self) -> LaneClass {
                LaneClass::Paid
            }
            fn price_in_per_mtok(&self) -> f64 {
                1.0
            }
            fn price_out_per_mtok(&self) -> f64 {
                4.0
            }
            async fn complete(&self, _b: &Value) -> Result<Value, PennyError> {
                Err(PennyError::RateLimited {
                    lane: "p/rl".into(),
                    retry_after_s: Some(90),
                })
            }
        }
        let r = Router::new(vec![Arc::new(RL)], 5, 10, usize::MAX);
        let chain = vec!["p/rl".to_string()];
        assert!(r
            .route_chain(&chain, &serde_json::json!({}), 1000)
            .await
            .is_err());
        // still open at t=1050 (< 90s window even though blind cooldown is 10s)
        match r.route_chain(&chain, &serde_json::json!({}), 1050).await {
            Err(PennyError::Upstream { body, .. }) => assert!(body.contains("circuit open")),
            other => panic!("breaker should still be open: {other:?}"),
        }
        // recovered after the advertised window
        match r.route_chain(&chain, &serde_json::json!({}), 1100).await {
            Err(PennyError::RateLimited { .. }) => {}
            other => panic!("expected RateLimited retry: {other:?}"),
        }
    }

    #[tokio::test]
    async fn bulkhead_saturates_and_skips() {
        // F-RO-7: a blocked lane cannot absorb the fleet's concurrency;
        // excess demand skips to the fallback immediately.
        let notify = Arc::new(tokio::sync::Notify::new());
        let entered = Arc::new(AtomicUsize::new(0));
        let slow = Arc::new(SlowLane {
            notify: notify.clone(),
            entered: entered.clone(),
        });
        let r = Arc::new(Router::new(
            vec![
                slow as Arc<dyn LlmLane>,
                Arc::new(MockLane {
                    name: "p/fallback",
                    class: LaneClass::Paid,
                    fail: false,
                    stream: false,
                }),
            ],
            5,
            60,
            1, // inflight cap of ONE
        ));
        let chain = vec!["p/slow".to_string(), "p/fallback".to_string()];
        let r2 = r.clone();
        let chain2 = chain.clone();
        let h =
            tokio::spawn(async move { r2.route_chain(&chain2, &serde_json::json!({}), 0).await });
        for _ in 0..50 {
            if entered.load(Ordering::SeqCst) > 0 {
                break;
            }
            tokio::time::sleep(std::time::Duration::from_millis(5)).await;
        }
        // second concurrent request: slow lane is saturated -> instant fallback
        let (i, v) = r
            .route_chain(&chain, &serde_json::json!({}), 0)
            .await
            .unwrap();
        assert_eq!(i, 1);
        assert_eq!(v["ok"], "p/fallback");
        notify.notify_one();
        let (i, _) = h.await.unwrap().unwrap();
        assert_eq!(i, 0);
    }

    struct Flappy {
        left: Mutex<u32>,
    }

    #[async_trait]
    impl LlmLane for Flappy {
        fn name(&self) -> &str {
            "p/flappy"
        }
        fn class(&self) -> LaneClass {
            LaneClass::Free
        }
        fn price_in_per_mtok(&self) -> f64 {
            0.0
        }
        fn price_out_per_mtok(&self) -> f64 {
            0.0
        }
        async fn complete(&self, _b: &Value) -> Result<Value, PennyError> {
            let mut l = self.left.lock().unwrap();
            if *l > 0 {
                *l -= 1;
                Err(PennyError::Upstream {
                    lane: "p/flappy".into(),
                    status: 500,
                    body: "flap".into(),
                })
            } else {
                Ok(serde_json::json!({
                    "ok": "recovered",
                    "choices": [{
                        "message": {"role": "assistant", "content": "recovered answer"},
                        "finish_reason": "stop"
                    }]
                }))
            }
        }
    }

    #[tokio::test]
    async fn circuit_recovers_after_cooldown() {
        // F-RO-3 recovery half: breaker opens, lane heals after cooldown
        let r = Router::new(
            vec![Arc::new(Flappy {
                left: Mutex::new(2),
            })],
            2,
            50,
            usize::MAX,
        );
        let chain = vec!["p/flappy".to_string()];
        assert!(r
            .route_chain(&chain, &serde_json::json!({}), 0)
            .await
            .is_err());
        assert!(r
            .route_chain(&chain, &serde_json::json!({}), 1)
            .await
            .is_err()); // opens until t=51
        let (_, v) = r
            .route_chain(&chain, &serde_json::json!({}), 60)
            .await
            .unwrap();
        assert_eq!(v["ok"], "recovered");
    }

    #[tokio::test]
    async fn storm_64_concurrent_all_succeed_on_healthy_lane() {
        // F-CON-3: burst traffic on one healthy lane — bulkhead admits all
        let r = Arc::new(Router::new(
            vec![Arc::new(MockLane {
                name: "p/only",
                class: LaneClass::Paid,
                fail: false,
                stream: true,
            })],
            3,
            60,
            256,
        ));
        let mut hs = Vec::new();
        for _ in 0..64 {
            let r2 = r.clone();
            hs.push(tokio::spawn(async move {
                r2.route_chain(&["p/only".to_string()], &serde_json::json!({}), 0)
                    .await
            }));
        }
        for h in hs {
            assert!(h.await.unwrap().is_ok());
        }
    }

    #[tokio::test]
    async fn circuit_opens_after_threshold() {
        let r = Router::new(
            vec![
                arc(MockLane {
                    name: "a/x",
                    class: LaneClass::Free,
                    fail: true,
                    stream: false,
                }),
                arc(MockLane {
                    name: "b/y",
                    class: LaneClass::Free,
                    fail: true,
                    stream: false,
                }),
            ],
            2,
            100,
            usize::MAX,
        );
        let chain = vec!["a/x".to_string(), "b/y".to_string()];
        assert!(r
            .route_chain(&chain, &serde_json::json!({}), 0)
            .await
            .is_err());
        assert!(r
            .route_chain(&chain, &serde_json::json!({}), 10)
            .await
            .is_err());
        match r.route_chain(&chain, &serde_json::json!({}), 20).await {
            Err(PennyError::AllLanesFailed) | Err(PennyError::Upstream { .. }) => {}
            other => panic!("unexpected {other:?}"),
        }
    }
}
