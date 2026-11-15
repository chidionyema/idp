//! SettleStream: wraps an upstream SSE stream and reconciles the budget
//! reservation when the stream ends (normally or with an error). Without
//! this, streaming requests would hold reservations forever (P0-5 half).

use futures_core::Stream;
use penny_core::{budget::Budgets, error::PennyError, router::ByteStream};
use std::pin::Pin;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::task::{Context, Poll};
use std::time::{SystemTime, UNIX_EPOCH};

pub struct SettleStream {
    inner: ByteStream,
    budgets: Budgets,
    key: String,
    est_usd: f64,
    settled: Arc<AtomicBool>,
}

impl SettleStream {
    pub fn new(inner: ByteStream, budgets: Budgets, key: String, est_usd: f64) -> Self {
        Self { inner, budgets, key, est_usd, settled: Arc::new(AtomicBool::new(false)) }
    }

    fn settle_once(&self) {
        if !self.settled.swap(true, Ordering::SeqCst) {
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs())
                .unwrap_or(0);
            // streamed usage is unknowable per-chunk: charge the estimate
            let _ = self.budgets.settle(&self.key, self.est_usd, self.est_usd, now);
        }
    }
}

impl Stream for SettleStream {
    type Item = Result<bytes::Bytes, PennyError>;

    fn poll_next(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        let this = self.get_mut();
        match this.inner.as_mut().poll_next(cx) {
            Poll::Ready(None) => {
                this.settle_once();
                Poll::Ready(None)
            }
            Poll::Ready(Some(Err(e))) => {
                this.settle_once();
                Poll::Ready(Some(Err(e)))
            }
            other => other,
        }
    }
}

impl Drop for SettleStream {
    fn drop(&mut self) {
        // client disconnect / task abort: release the reservation anyway
        self.settle_once();
    }
}
