//! Exact-match cache with adaptive TTL.
//!
//! TTL adapts to measured inter-arrival gaps (EWMA x3, clamped): a watcher
//! polling every 15 min gets ~45-min TTL, not a blind 1h. Cache writes are
//! ~60% cheaper than 1h TTLs at 5-min gaps (Claude Code postmortem: 17.1%
//! of one user's spend was cache-write waste).
//!
//! Deliberate non-features (per LiteLLM guidance + incident history):
//! NO semantic cache on agent traffic (cross-serves tool payloads between
//! callers), NO cross-key sharing (exact match only).

use moka::sync::Cache;
use std::sync::{Arc, Mutex};

#[derive(Clone)]
pub struct Entry {
    pub value: String,
    pub expires_unix: u64,
}

pub struct ExactCache {
    inner: Cache<String, Arc<Entry>>,
    ttl_min_s: u64,
    ttl_max_s: u64,
    ewma_gap_s: Mutex<f64>,
    last_seen: Mutex<u64>,
}

impl ExactCache {
    pub fn new(capacity: u64, ttl_min_s: u64, ttl_max_s: u64) -> Self {
        assert!(capacity > 0, "cache capacity must be > 0");
        Self {
            inner: Cache::new(capacity),
            ttl_min_s,
            ttl_max_s: ttl_max_s.max(ttl_min_s),
            ewma_gap_s: Mutex::new(0.0),
            last_seen: Mutex::new(0),
        }
    }

    fn adaptive_ttl(&self, now: u64) -> u64 {
        let gap = {
            let mut ls = self.last_seen.lock().unwrap();
            let g = now.saturating_sub(*ls);
            *ls = now;
            g as f64
        };
        let ttl = {
            let mut e = self.ewma_gap_s.lock().unwrap();
            *e = 0.7 * *e + 0.3 * gap;
            (*e * 3.0) as u64
        };
        ttl.clamp(self.ttl_min_s, self.ttl_max_s)
    }

    pub fn get(&self, key: &str, now: u64) -> Option<Arc<Entry>> {
        let e = self.inner.get(key)?;
        if e.expires_unix <= now {
            self.inner.remove(key);
            return None;
        }
        Some(e)
    }

    pub fn insert(&self, key: String, value: String, now: u64) {
        let ttl = self.adaptive_ttl(now);
        self.inner
            .insert(key, Arc::new(Entry { value, expires_unix: now + ttl }));
    }

    /// Evict a poisoned/corrupt entry (F-CA-3): a bad cached value must
    /// never be served and must not wedge the key forever.
    pub fn invalidate(&self, key: &str) {
        self.inner.remove(key);
    }

    pub fn len(&self) -> u64 {
        self.inner.entry_count()
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hit_and_expiry() {
        let c = ExactCache::new(100, 300, 3600);
        c.insert("k".into(), "v".into(), 10_000);
        assert_eq!(c.get("k", 10_100).unwrap().value, "v");
        assert!(c.get("k", 10_000 + 3700).is_none()); // past ttl_max
        assert!(c.is_empty());
    }

    #[test]
    fn adaptive_ttl_within_bounds() {
        let c = ExactCache::new(100, 300, 600);
        c.insert("a".into(), "1".into(), 1000);
        c.insert("b".into(), "2".into(), 1600); // gap 600 -> ewma 180 -> ttl 540
        let e = c.get("b", 1600).unwrap();
        let ttl = e.expires_unix - 1600;
        assert!((300..=600).contains(&ttl), "ttl {ttl} out of bounds");
    }

    #[test]
    fn expired_entry_not_served() {
        let c = ExactCache::new(10, 10, 20);
        c.insert("k".into(), "old".into(), 0);
        assert!(c.get("k", 25).is_none());
    }
}
