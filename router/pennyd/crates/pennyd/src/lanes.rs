use async_trait::async_trait;
use penny_core::{
    config::LaneClass,
    dialect::{for_name, Dialect},
    error::PennyError,
    providers::ModelEntry,
    router::{ByteStream, LlmLane},
};
use serde_json::Value;
use std::sync::Arc;
use std::time::Duration;

/// A lane bound to a registry entry: dialect translation + HTTP transport.
pub struct ProviderLane {
    entry: ModelEntry,
    canonical: String,
    dialect: &'static dyn Dialect,
    client: reqwest::Client,
    api_key: String,
    /// P1-2: inject provider cache headers only when THIS lane speaks anthropic
    inject_cc: bool,
}

impl ProviderLane {
    pub fn new(entry: ModelEntry, cache_control: bool) -> Result<Self, PennyError> {
        let dialect = for_name(&entry.provider.dialect)?;
        let api_key = match &entry.provider.auth {
            penny_core::providers::AuthKind::None => String::new(),
            other => {
                let env = match other {
                    penny_core::providers::AuthKind::Bearer { key_env } => key_env,
                    penny_core::providers::AuthKind::Header { key_env, .. } => key_env,
                    penny_core::providers::AuthKind::QueryParam { key_env, .. } => key_env,
                    penny_core::providers::AuthKind::None => unreachable!(),
                };
                std::env::var(env)
                    .map_err(|_| PennyError::Config(format!("env {env} not set for {}", entry.provider.id)))?
            }
        };
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(entry.provider.timeout_s))
            .build()
            .map_err(|e| PennyError::Config(e.to_string()))?;
        let canonical = entry.canonical_name();
        let inject_cc = cache_control && entry.provider.dialect == "anthropic";
        Ok(Self { entry, canonical, dialect, client, api_key, inject_cc })
    }

    fn prepare(&self, body: &Value) -> Value {
        if self.inject_cc {
            penny_core::shaping::inject_cache_control(body.clone(), true)
        } else {
            penny_core::shaping::strip_cache_control(body.clone())
        }
    }
}

#[async_trait]
impl LlmLane for ProviderLane {
    fn name(&self) -> &str {
        // canonical provider/model — cache keys and decision logs use this
        &self.canonical
    }
    fn class(&self) -> LaneClass {
        self.entry.model.class
    }
    fn price_in_per_mtok(&self) -> f64 {
        self.entry.model.price_in_per_mtok
    }
    fn price_out_per_mtok(&self) -> f64 {
        self.entry.model.price_out_per_mtok
    }
    fn supports_streaming(&self) -> bool {
        self.dialect.supports_streaming()
    }
    async fn complete_stream(&self, body: &Value) -> Result<ByteStream, PennyError> {
        let body = self.prepare(body);
        let t = self.dialect.translate_request(&self.entry.provider, &self.entry.model, &self.api_key, &body)?;
        let resp = self
            .client
            .post(&t.url)
            .headers((|| {
                let mut h = reqwest::header::HeaderMap::new();
                for (k, v) in &t.headers {
                    if let (Ok(n), Ok(val)) = (
                        reqwest::header::HeaderName::from_bytes(k.as_bytes()),
                        reqwest::header::HeaderValue::from_str(v),
                    ) {
                        h.insert(n, val);
                    }
                }
                h
            })())
            .json(&t.body)
            .send()
            .await
            .map_err(|e| PennyError::Upstream { lane: self.entry.canonical_name(), status: 0, body: e.to_string() })?;
        let status = resp.status().as_u16();
        if status == 429 {
            // P1-8: Retry-After applies to streaming too
            let retry_after_s = resp
                .headers()
                .get("retry-after")
                .and_then(|v| v.to_str().ok())
                .and_then(|s| s.parse::<u64>().ok());
            return Err(PennyError::RateLimited {
                lane: self.entry.canonical_name(),
                retry_after_s,
            });
        }
        if status != 200 {
            return Err(PennyError::Upstream {
                lane: self.entry.canonical_name(),
                status,
                body: "streaming upstream error".into(),
            });
        }
        use futures_util::StreamExt;
        Ok(Box::pin(resp.bytes_stream().map(|r| {
            r.map_err(|e| PennyError::Upstream { lane: "stream".into(), status: 0, body: e.to_string() })
        })))
    }
    async fn complete(&self, body: &Value) -> Result<Value, PennyError> {
        let body = self.prepare(body);
        let t = self.dialect.translate_request(&self.entry.provider, &self.entry.model, &self.api_key, &body)?;
        let mut req = self.client.post(&t.url);
        for (k, v) in &t.headers {
            req = req.header(k, v);
        }
        let resp = req
            .json(&t.body)
            .send()
            .await
            .map_err(|e| PennyError::Upstream { lane: self.entry.canonical_name(), status: 0, body: e.to_string() })?;
        let status = resp.status().as_u16();
        if status == 429 {
            let retry_after_s = resp
                .headers()
                .get("retry-after")
                .and_then(|v| v.to_str().ok())
                .and_then(|s| s.parse::<u64>().ok());
            return Err(PennyError::RateLimited {
                lane: self.entry.canonical_name(),
                retry_after_s,
            });
        }
        if status != 200 {
            let text = resp.text().await.unwrap_or_default();
            return Err(PennyError::Upstream {
                lane: self.entry.canonical_name(),
                status,
                body: text.chars().take(500).collect(),
            });
        }
        let v = resp
            .json::<Value>()
            .await
            .map_err(|e| PennyError::Upstream { lane: self.entry.canonical_name(), status: 0, body: e.to_string() })?;
        self.dialect.translate_response(&v)
    }
}

/// Build the cascade (already sorted by the registry) into lanes.
pub fn lanes_from_registry(
    reg: &penny_core::providers::Registry,
    cache_control: bool,
) -> Result<Vec<Arc<dyn LlmLane>>, PennyError> {
    reg.models
        .clone()
        .into_iter()
        .map(|e| ProviderLane::new(e, cache_control))
        .map(|r| r.map(|l| Arc::new(l) as Arc<dyn LlmLane>))
        .collect()
}
