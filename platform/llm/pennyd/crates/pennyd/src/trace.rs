//! Bounded, per-request accounting shared by the dashboard and JSON API.
//!
//! This is deliberately separate from the aggregate spend ledger: "we spent
//! $13" is not useful to a founder who has to explain which surface, model,
//! lane, cache state and token counts produced it.

use serde_json::{json, Value};
use std::collections::VecDeque;
use std::sync::Mutex;

const DEFAULT_CAPACITY: usize = 4096;

#[derive(Debug, Clone)]
pub struct RequestTrace {
    pub req: String,
    pub started_unix: u64,
    pub surface: String,
    pub edge: String,
    pub requested_model: String,
    pub canonical_model: Option<String>,
    pub lane: Option<String>,
    pub stream: bool,
    pub status: String,
    pub in_tokens: u64,
    pub out_tokens: u64,
    pub cache_read_tokens: u64,
    pub cache_write_tokens: u64,
    pub exact_cache_hit: bool,
    pub estimated: bool,
    pub cost_usd: f64,
    pub latency_ms: u64,
    pub key_fp: Option<String>,
    pub error_kind: Option<String>,
}

#[derive(Debug, Default)]
pub struct TraceFinish {
    pub lane: Option<String>,
    pub status: String,
    pub in_tokens: u64,
    pub out_tokens: u64,
    pub cache_read_tokens: u64,
    pub cache_write_tokens: u64,
    pub exact_cache_hit: bool,
    pub estimated: bool,
    pub cost_usd: f64,
    pub latency_ms: u64,
    pub key_fp: Option<String>,
    pub error_kind: Option<String>,
}

pub struct TraceStore {
    rows: Mutex<VecDeque<RequestTrace>>,
    capacity: usize,
}

impl Default for TraceStore {
    fn default() -> Self {
        Self::new(DEFAULT_CAPACITY)
    }
}

impl TraceStore {
    pub fn new(capacity: usize) -> Self {
        Self {
            rows: Mutex::new(VecDeque::with_capacity(capacity.max(1))),
            capacity: capacity.max(1),
        }
    }

    pub fn begin(
        &self,
        req: &str,
        started_unix: u64,
        surface: &str,
        edge: &str,
        requested_model: &str,
        stream: bool,
    ) {
        let mut rows = self.rows.lock().unwrap();
        rows.push_back(RequestTrace {
            req: req.to_string(),
            started_unix,
            surface: surface.to_string(),
            edge: edge.to_string(),
            requested_model: requested_model.to_string(),
            canonical_model: None,
            lane: None,
            stream,
            status: "pending".into(),
            in_tokens: 0,
            out_tokens: 0,
            cache_read_tokens: 0,
            cache_write_tokens: 0,
            exact_cache_hit: false,
            estimated: false,
            cost_usd: 0.0,
            latency_ms: 0,
            key_fp: None,
            error_kind: None,
        });
        while rows.len() > self.capacity {
            rows.pop_front();
        }
    }

    pub fn route(&self, req: &str, canonical_model: &str, lane: Option<&str>) {
        let mut rows = self.rows.lock().unwrap();
        if let Some(row) = rows.iter_mut().find(|row| row.req == req) {
            row.canonical_model = Some(canonical_model.to_string());
            if let Some(lane) = lane {
                row.lane = Some(lane.to_string());
            }
        }
    }

    pub fn finish(&self, req: &str, finish: TraceFinish) {
        let mut rows = self.rows.lock().unwrap();
        if let Some(row) = rows.iter_mut().find(|row| row.req == req) {
            row.status = finish.status;
            row.in_tokens = finish.in_tokens;
            row.out_tokens = finish.out_tokens;
            row.cache_read_tokens = finish.cache_read_tokens;
            row.cache_write_tokens = finish.cache_write_tokens;
            row.exact_cache_hit = finish.exact_cache_hit;
            row.estimated = finish.estimated;
            row.cost_usd = finish.cost_usd.max(0.0);
            row.latency_ms = finish.latency_ms;
            row.key_fp = finish.key_fp;
            row.error_kind = finish.error_kind;
            if finish.lane.is_some() {
                row.lane = finish.lane;
            }
        }
    }

    pub fn snapshot(&self, limit: usize) -> Vec<Value> {
        let rows = self.rows.lock().unwrap();
        rows.iter()
            .rev()
            .take(limit.min(self.capacity))
            .map(|row| {
                json!({
                    "req": row.req,
                    "started_unix": row.started_unix,
                    "surface": row.surface,
                    "edge": row.edge,
                    "requested_model": row.requested_model,
                    "canonical_model": row.canonical_model,
                    "lane": row.lane,
                    "stream": row.stream,
                    "status": row.status,
                    "in_tokens": row.in_tokens,
                    "out_tokens": row.out_tokens,
                    "cache_read_tokens": row.cache_read_tokens,
                    "cache_write_tokens": row.cache_write_tokens,
                    "exact_cache_hit": row.exact_cache_hit,
                    "estimated": row.estimated,
                    "cost_usd": row.cost_usd,
                    "latency_ms": row.latency_ms,
                    "key_fp": row.key_fp,
                    "error_kind": row.error_kind,
                })
            })
            .collect()
    }
}
