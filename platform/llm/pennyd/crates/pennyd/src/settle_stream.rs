//! SettleStream: wraps an upstream SSE stream and reconciles the budget
//! reservation when the stream ends (normally or with an error). Without
//! this, streaming requests would hold reservations forever (P0-5 half).

use futures_core::Stream;
use penny_core::{budget::Budgets, error::PennyError, ledger::Ledger, router::ByteStream};
use serde_json::Value;
use std::pin::Pin;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::task::{Context, Poll};
use std::time::{Instant, SystemTime, UNIX_EPOCH};

use crate::trace::{TraceFinish, TraceStore};

pub struct SettleStream {
    inner: ByteStream,
    budgets: Budgets,
    key: String,
    reserved_usd: f64,
    price_in: f64,
    price_out: f64,
    parse_buf: Vec<u8>,
    input_tokens: u64,
    output_tokens: u64,
    cache_read_tokens: u64,
    cache_write_tokens: u64,
    estimated_input_tokens: u64,
    ledger: Arc<Ledger>,
    traces: Arc<TraceStore>,
    trace_req: String,
    key_fp: String,
    started: Instant,
    settled: Arc<AtomicBool>,
}

pub struct SettleContext {
    pub budgets: Budgets,
    pub key: String,
    pub reserved_usd: f64,
    pub price_in: f64,
    pub price_out: f64,
    pub estimated_input_tokens: u64,
    pub ledger: Arc<Ledger>,
    pub traces: Arc<TraceStore>,
    pub trace_req: String,
    pub key_fp: String,
    pub started: Instant,
}

impl SettleStream {
    pub fn new(inner: ByteStream, context: SettleContext) -> Self {
        Self {
            inner,
            budgets: context.budgets,
            key: context.key,
            reserved_usd: context.reserved_usd,
            price_in: context.price_in,
            price_out: context.price_out,
            parse_buf: Vec::new(),
            input_tokens: 0,
            output_tokens: 0,
            cache_read_tokens: 0,
            cache_write_tokens: 0,
            estimated_input_tokens: context.estimated_input_tokens,
            ledger: context.ledger,
            traces: context.traces,
            trace_req: context.trace_req,
            key_fp: context.key_fp,
            started: context.started,
            settled: Arc::new(AtomicBool::new(false)),
        }
    }

    fn observe_usage(&mut self, chunk: &[u8]) {
        // SSE event framing is small; retain only the tail if a provider sends
        // an unexpectedly large object so telemetry cannot itself grow without
        // bound.
        const KEEP: usize = 256 * 1024;
        self.parse_buf.extend_from_slice(chunk);
        while let Some((end, delim)) = sse_boundary(&self.parse_buf) {
            let event = self.parse_buf[..end].to_vec();
            self.parse_buf.drain(..end + delim);
            for line in String::from_utf8_lossy(&event).lines() {
                let Some(data) = line.strip_prefix("data:") else {
                    continue;
                };
                let Ok(value) = serde_json::from_str::<Value>(data.trim()) else {
                    continue;
                };
                let Some(usage) = value.get("usage").and_then(Value::as_object) else {
                    continue;
                };
                self.input_tokens = self
                    .input_tokens
                    .max(usage_u64(usage, &["prompt_tokens", "input_tokens"]));
                self.output_tokens = self
                    .output_tokens
                    .max(usage_u64(usage, &["completion_tokens", "output_tokens"]));
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
                        .get("prompt_tokens_details")
                        .and_then(|details| details.get("cached_tokens"))
                        .and_then(Value::as_u64)
                        .unwrap_or(0),
                );
                self.cache_read_tokens = self.cache_read_tokens.max(read);
                self.cache_write_tokens = self.cache_write_tokens.max(usage_u64(
                    usage,
                    &["cache_creation_input_tokens", "cache_write_tokens"],
                ));
            }
        }
        if self.parse_buf.len() > KEEP {
            let drop = self.parse_buf.len() - KEEP;
            self.parse_buf.drain(..drop);
        }
    }

    fn settle_once(&self, status: &str) {
        if !self.settled.swap(true, Ordering::SeqCst) {
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs())
                .unwrap_or(0);
            // Prefer the provider's final usage object. If the stream vanished
            // before it arrived, keep the pre-dispatch reservation as a
            // conservative charge rather than refunding unknown consumption.
            let observed = self.input_tokens > 0 || self.output_tokens > 0;
            let input = if observed {
                self.input_tokens
            } else {
                self.estimated_input_tokens
            };
            let output = if observed { self.output_tokens } else { 0 };
            let actual = if observed {
                input as f64 * self.price_in / 1e6 + output as f64 * self.price_out / 1e6
            } else {
                self.reserved_usd
            };
            let _ = self
                .budgets
                .settle(&self.key, self.reserved_usd, actual, now);
            self.ledger.charge(input, output, actual);
            self.traces.finish(
                &self.trace_req,
                TraceFinish {
                    status: status.into(),
                    in_tokens: input,
                    out_tokens: output,
                    cache_read_tokens: self.cache_read_tokens,
                    cache_write_tokens: self.cache_write_tokens,
                    estimated: !observed,
                    cost_usd: actual,
                    latency_ms: self.started.elapsed().as_millis() as u64,
                    key_fp: Some(self.key_fp.clone()),
                    error_kind: (status == "error").then(|| "upstream".into()),
                    ..TraceFinish::default()
                },
            );
        }
    }
}

fn usage_u64(usage: &serde_json::Map<String, Value>, names: &[&str]) -> u64 {
    names
        .iter()
        .find_map(|name| usage.get(*name).and_then(Value::as_u64))
        .unwrap_or(0)
}

fn sse_boundary(buf: &[u8]) -> Option<(usize, usize)> {
    buf.windows(2)
        .position(|w| w == b"\n\n")
        .map(|p| (p, 2))
        .or_else(|| {
            buf.windows(4)
                .position(|w| w == b"\r\n\r\n")
                .map(|p| (p, 4))
        })
}

impl Stream for SettleStream {
    type Item = Result<bytes::Bytes, PennyError>;

    fn poll_next(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        let this = self.get_mut();
        match this.inner.as_mut().poll_next(cx) {
            Poll::Ready(None) => {
                this.settle_once("ok");
                Poll::Ready(None)
            }
            Poll::Ready(Some(Ok(chunk))) => {
                this.observe_usage(&chunk);
                Poll::Ready(Some(Ok(chunk)))
            }
            Poll::Ready(Some(Err(e))) => {
                this.settle_once("error");
                Poll::Ready(Some(Err(e)))
            }
            other => other,
        }
    }
}

impl Drop for SettleStream {
    fn drop(&mut self) {
        // client disconnect / task abort: release the reservation anyway
        self.settle_once("cancelled");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use futures_util::StreamExt;

    fn now() -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs()
    }

    fn wrap(
        chunks: Vec<Result<bytes::Bytes, PennyError>>,
        estimated_input_tokens: u64,
    ) -> (SettleStream, Arc<Ledger>, Arc<TraceStore>) {
        let budgets = Budgets::new();
        budgets.reserve("edge-key", 0.01, now()).unwrap();
        let ledger = Arc::new(Ledger::default());
        let traces = Arc::new(TraceStore::default());
        traces.begin("req-1", now(), "test", "openai", "glm", true);
        let stream: ByteStream = Box::pin(futures_util::stream::iter(chunks));
        (
            SettleStream::new(
                stream,
                SettleContext {
                    budgets,
                    key: "edge-key".into(),
                    reserved_usd: 0.01,
                    price_in: 1.0,
                    price_out: 2.0,
                    estimated_input_tokens,
                    ledger: ledger.clone(),
                    traces: traces.clone(),
                    trace_req: "req-1".into(),
                    key_fp: "key-fp".into(),
                    started: Instant::now(),
                },
            ),
            ledger,
            traces,
        )
    }

    #[tokio::test]
    async fn midstream_failure_settles_error_trace() {
        let (mut stream, ledger, traces) = wrap(
            vec![
                Ok(bytes::Bytes::from_static(
                    b"data: {\"choices\":[{\"delta\":{\"content\":\"partial\"}}]}\n\n",
                )),
                Err(PennyError::Upstream {
                    lane: "mock".into(),
                    status: 0,
                    body: "disconnected".into(),
                }),
            ],
            25,
        );
        while let Some(item) = stream.next().await {
            if item.is_err() {
                break;
            }
        }
        drop(stream);

        let row = &traces.snapshot(1)[0];
        assert_eq!(row["status"], "error");
        assert_eq!(row["estimated"], true);
        assert_eq!(row["error_kind"], "upstream");
        assert_eq!(ledger.snapshot().requests, 1);
    }

    #[tokio::test]
    async fn stream_without_usage_is_marked_estimate() {
        let (mut stream, ledger, traces) = wrap(
            vec![Ok(bytes::Bytes::from_static(
                b"data: {\"choices\":[{\"delta\":{\"content\":\"ok\"}}]}\n\ndata: [DONE]\n\n",
            ))],
            25,
        );
        while stream.next().await.is_some() {}

        let row = &traces.snapshot(1)[0];
        assert_eq!(row["status"], "ok");
        assert_eq!(row["estimated"], true);
        assert_eq!(row["in_tokens"], 25);
        assert_eq!(row["out_tokens"], 0);
        assert_eq!(ledger.snapshot().requests, 1);
        assert_eq!(row["cost_usd"].as_f64().unwrap(), 0.01);
    }
}
