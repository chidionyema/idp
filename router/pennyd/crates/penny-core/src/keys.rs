//! Canonical cache keys: identical requests must hash identically regardless
//! of JSON key order or whitespace. serde_json's default Map is BTreeMap
//! (sorted keys), so a sorted recursive canonicalisation is deterministic.

use serde_json::Value;
use sha2::{Digest, Sha256};

pub fn canonicalize(v: &Value) -> Value {
    match v {
        Value::Object(m) => {
            let mut out = serde_json::Map::new();
            for k in m.keys() {
                out.insert(k.clone(), canonicalize(&m[k]));
            }
            Value::Object(out)
        }
        Value::Array(a) => Value::Array(a.iter().map(canonicalize).collect()),
        other => other.clone(),
    }
}

/// One-way identifier for a bearer key: safe for logs, metrics and receipts.
/// P0-4: the raw key must never appear in the decision log.
pub fn fingerprint(secret: &str) -> String {
    let mut h = Sha256::new();
    h.update(secret.as_bytes());
    hex::encode(h.finalize())[..12].to_string()
}

pub fn cache_key(model: &str, body: &Value) -> String {
    let canon = canonicalize(&serde_json::json!({ "model": model, "body": body }));
    let mut h = Sha256::new();
    h.update(canon.to_string().as_bytes());
    hex::encode(h.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn key_order_irrelevant() {
        let a = json!({"messages": [{"role": "user", "content": "hi"}], "temperature": 0});
        let b = json!({"temperature": 0, "messages": [{"content": "hi", "role": "user"}]});
        assert_eq!(cache_key("m", &a), cache_key("m", &b));
    }

    #[test]
    fn model_participates() {
        let a = json!({"messages": []});
        assert_ne!(cache_key("cheap", &a), cache_key("dear", &a));
    }

    #[test]
    fn whitespace_irrelevant() {
        let a: Value = serde_json::from_str(r#"{"x": 1}"#).unwrap();
        let b: Value = serde_json::from_str("{ "x" : 1 }").unwrap();
        assert_eq!(cache_key("m", &a), cache_key("m", &b));
    }
}
