//! Founder-visible spend ledger. All counters are atomic; integer nano-USD
//! (1 NUSD = 1e-9 USD) avoids float atomics and float drift. `savings` = input
//! tokens served from cache, priced at the cheapest paid lane (conservative
//! underestimate). One rounding happens when a USD rate card meets the ledger;
//! every addition after that is exact.

use std::sync::atomic::{AtomicU64, Ordering};

/// Integer nano-dollars per US dollar. The ledger never accumulates f64.
pub const NUSD_PER_USD: u64 = 1_000_000_000;

#[derive(Debug, Clone, Copy, Default)]
pub struct Snapshot {
    pub requests: u64,
    pub cache_eligible_requests: u64,
    pub cache_hits: u64,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub input_tokens_saved: u64,
    /// Exact accumulated spend in integer nano-USD.
    pub spend_nusd: u64,
    /// Exact accumulated avoided spend in integer nano-USD.
    pub saved_nusd: u64,
    pub spend_usd: f64,
    pub saved_usd: f64,
}

/// Whole nano-USD for one rate-card amount. The only rounding in the path.
pub fn nusd(usd: f64) -> u64 {
    (usd.max(0.0) * NUSD_PER_USD as f64).round() as u64
}

impl Snapshot {
    pub fn cache_hit_rate(&self) -> f64 {
        if self.cache_eligible_requests == 0 {
            0.0
        } else {
            self.cache_hits as f64 / self.cache_eligible_requests as f64
        }
    }
}

#[derive(Default)]
pub struct Ledger {
    requests: AtomicU64,
    cache_eligible_requests: AtomicU64,
    cache_hits: AtomicU64,
    input_tokens: AtomicU64,
    output_tokens: AtomicU64,
    input_tokens_saved: AtomicU64,
    spend_nusd: AtomicU64,
    saved_nusd: AtomicU64,
}

impl Ledger {
    pub fn mark_cache_eligible(&self) {
        self.cache_eligible_requests.fetch_add(1, Ordering::Relaxed);
    }

    pub fn charge(&self, in_tok: u64, out_tok: u64, usd: f64) {
        self.requests.fetch_add(1, Ordering::Relaxed);
        self.input_tokens.fetch_add(in_tok, Ordering::Relaxed);
        self.output_tokens.fetch_add(out_tok, Ordering::Relaxed);
        self.spend_nusd
            .fetch_add(nusd(usd), Ordering::Relaxed);
    }

    pub fn record_hit(&self, saved_in_tok: u64, saved_usd: f64) {
        self.requests.fetch_add(1, Ordering::Relaxed);
        self.cache_hits.fetch_add(1, Ordering::Relaxed);
        self.input_tokens_saved
            .fetch_add(saved_in_tok, Ordering::Relaxed);
        self.saved_nusd
            .fetch_add(nusd(saved_usd), Ordering::Relaxed);
    }

    pub fn cache_hit_rate(&self) -> f64 {
        let r = self.cache_eligible_requests.load(Ordering::Relaxed);
        if r == 0 {
            0.0
        } else {
            self.cache_hits.load(Ordering::Relaxed) as f64 / r as f64
        }
    }

    pub fn snapshot(&self) -> Snapshot {
        Snapshot {
            requests: self.requests.load(Ordering::Relaxed),
            cache_eligible_requests: self.cache_eligible_requests.load(Ordering::Relaxed),
            cache_hits: self.cache_hits.load(Ordering::Relaxed),
            input_tokens: self.input_tokens.load(Ordering::Relaxed),
            output_tokens: self.output_tokens.load(Ordering::Relaxed),
            input_tokens_saved: self.input_tokens_saved.load(Ordering::Relaxed),
            spend_nusd: self.spend_nusd.load(Ordering::Relaxed),
            saved_nusd: self.saved_nusd.load(Ordering::Relaxed),
            spend_usd: self.spend_nusd.load(Ordering::Relaxed) as f64 / NUSD_PER_USD as f64,
            saved_usd: self.saved_nusd.load(Ordering::Relaxed) as f64 / NUSD_PER_USD as f64,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn charge_and_hit_accounting() {
        let l = Ledger::default();
        l.mark_cache_eligible();
        l.charge(100, 20, 0.001);
        l.mark_cache_eligible();
        l.record_hit(100, 0.0005);
        let s = l.snapshot();
        assert_eq!(s.requests, 2);
        assert_eq!(s.cache_eligible_requests, 2);
        assert_eq!(s.cache_hits, 1);
        assert!((s.cache_hit_rate() - 0.5).abs() < 1e-9);
        assert_eq!(s.spend_nusd, 1_000_000);
        assert_eq!(s.saved_nusd, 500_000);
        assert!((s.spend_usd - 0.001).abs() < 1e-12);
    }

    #[test]
    fn sub_micro_charges_are_exact_and_never_lost() {
        let l = Ledger::default();
        for _ in 0..1000 {
            l.charge(1, 1, 0.000_000_001); // one nano-dollar
        }
        assert_eq!(l.snapshot().spend_nusd, 1000);
        assert!(l.snapshot().spend_usd > 0.0, "micro-USD truncation lost it");
    }

    #[test]
    fn the_conversion_rounds_once_and_not_toward_zero() {
        assert_eq!(nusd(0.000_000_0015), 2, "half a nano rounds up");
        assert_eq!(nusd(-1.0), 0, "a negative rate card cannot become spend");
    }
}
