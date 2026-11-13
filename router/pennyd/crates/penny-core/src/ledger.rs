//! Founder-visible spend ledger. All counters are atomic; micro-USD avoids
//! float atomics. `savings` = input tokens served from cache, priced at the
//! cheapest paid lane (conservative underestimate).

use std::sync::atomic::{AtomicU64, Ordering};

#[derive(Debug, Clone, Copy, Default)]
pub struct Snapshot {
    pub requests: u64,
    pub cache_hits: u64,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub input_tokens_saved: u64,
    pub spend_usd: f64,
    pub saved_usd: f64,
}

#[derive(Default)]
pub struct Ledger {
    requests: AtomicU64,
    cache_hits: AtomicU64,
    input_tokens: AtomicU64,
    output_tokens: AtomicU64,
    input_tokens_saved: AtomicU64,
    spend_micros: AtomicU64,
    saved_micros: AtomicU64,
}

impl Ledger {
    pub fn charge(&self, in_tok: u64, out_tok: u64, usd: f64) {
        self.requests.fetch_add(1, Ordering::Relaxed);
        self.input_tokens.fetch_add(in_tok, Ordering::Relaxed);
        self.output_tokens.fetch_add(out_tok, Ordering::Relaxed);
        self.spend_micros
            .fetch_add((usd.max(0.0) * 1_000_000.0) as u64, Ordering::Relaxed);
    }

    pub fn record_hit(&self, saved_in_tok: u64, saved_usd: f64) {
        self.requests.fetch_add(1, Ordering::Relaxed);
        self.cache_hits.fetch_add(1, Ordering::Relaxed);
        self.input_tokens_saved
            .fetch_add(saved_in_tok, Ordering::Relaxed);
        self.saved_micros
            .fetch_add((saved_usd.max(0.0) * 1_000_000.0) as u64, Ordering::Relaxed);
    }

    pub fn cache_hit_rate(&self) -> f64 {
        let r = self.requests.load(Ordering::Relaxed);
        if r == 0 {
            0.0
        } else {
            self.cache_hits.load(Ordering::Relaxed) as f64 / r as f64
        }
    }

    pub fn snapshot(&self) -> Snapshot {
        Snapshot {
            requests: self.requests.load(Ordering::Relaxed),
            cache_hits: self.cache_hits.load(Ordering::Relaxed),
            input_tokens: self.input_tokens.load(Ordering::Relaxed),
            output_tokens: self.output_tokens.load(Ordering::Relaxed),
            input_tokens_saved: self.input_tokens_saved.load(Ordering::Relaxed),
            spend_usd: self.spend_micros.load(Ordering::Relaxed) as f64 / 1_000_000.0,
            saved_usd: self.saved_micros.load(Ordering::Relaxed) as f64 / 1_000_000.0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn charge_and_hit_accounting() {
        let l = Ledger::default();
        l.charge(100, 20, 0.001);
        l.record_hit(100, 0.0005);
        let s = l.snapshot();
        assert_eq!(s.requests, 2);
        assert_eq!(s.cache_hits, 1);
        assert!((s.cache_hit_rate() - 0.5).abs() < 1e-9);
        assert!(s.spend_usd >= 0.001);
        assert!(s.saved_usd >= 0.0005);
    }
}
