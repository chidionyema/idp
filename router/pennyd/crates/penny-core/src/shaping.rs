//! Request shaping — the zero-quality-loss tier of savings:
//!   * provider-side cache headers on the system message (Anthropic bills
//!     cached input at 0.1x; cache-friendly layouts cut 41-80% of API cost)
//!   * max_tokens caps (output costs 4-5x input on every current Claude model)
//!   * tool-result truncation (an oversized tool result is re-billed on
//!     EVERY later turn of an agent loop)

use serde_json::{json, Value};

pub fn inject_cache_control(mut body: Value, enabled: bool) -> Value {
    if !enabled {
        return body;
    }
    if let Some(messages) = body.get_mut("messages").and_then(|m| m.as_array_mut()) {
        for m in messages.iter_mut() {
            if m.get("role").and_then(|r| r.as_str()) == Some("system") {
                let cc = json!({ "type": "ephemeral" });
                match m.get_mut("content") {
                    Some(c) if c.is_string() => {
                        let text = c.take();
                        *c = json!([{ "type": "text", "text": text, "cache_control": cc }]);
                    }
                    Some(c) => {
                        if let Some(arr) = c.as_array_mut() {
                            if let Some(first) = arr.first_mut() {
                                first["cache_control"] = cc;
                            }
                        }
                    }
                    None => {}
                }
                break; // first system message only — deterministic cache breakpoints
            }
        }
    }
    body
}

pub fn cap_max_tokens(mut body: Value, cap: u64) -> Value {
    let over = body
        .get("max_tokens")
        .and_then(|v| v.as_u64())
        .map(|mt| mt > cap)
        .unwrap_or(true);
    if over {
        body["max_tokens"] = json!(cap);
    }
    body
}

/// P1-2: remove cache_control markers before sending to an OpenAI-dialect
/// lane (defensive — they are not part of that wire format).
pub fn strip_cache_control(mut body: Value) -> Value {
    if let Some(messages) = body.get_mut("messages").and_then(|m| m.as_array_mut()) {
        for m in messages.iter_mut() {
            if let Some(content) = m.get_mut("content").and_then(|c| c.as_array_mut()) {
                for b in content.iter_mut() {
                    b.as_object_mut().map(|o| o.remove("cache_control"));
                }
            }
        }
    }
    body
}

/// Truncates tool-role message contents. Returns (shaped_body, n_truncated).
/// UTF-8 safe: cuts on char boundaries.
pub fn truncate_tool_results(mut body: Value, max_chars: usize) -> (Value, usize) {
    let mut truncated = 0usize;
    if let Some(messages) = body.get_mut("messages").and_then(|m| m.as_array_mut()) {
        for m in messages.iter_mut() {
            if m.get("role").and_then(|r| r.as_str()) != Some("tool") {
                continue;
            }
            if let Some(c) = m.get_mut("content").and_then(|c| c.as_str()) {
                if c.chars().count() > max_chars {
                    let cut: String = c.chars().take(max_chars).collect();
                    let dropped = c.chars().count() - max_chars;
                    *c = format!("{cut}
[pennyd: truncated {dropped} chars]");
                    truncated += 1;
                }
            }
        }
    }
    (body, truncated)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn cache_control_on_string_system() {
        let body = json!({"messages": [{"role": "system", "content": "You are terse."}]});
        let out = inject_cache_control(body, true);
        let c = &out["messages"][0]["content"];
        assert_eq!(c[0]["cache_control"]["type"], "ephemeral");
        assert_eq!(c[0]["text"], "You are terse.");
    }

    #[test]
    fn cache_control_on_block_system() {
        let body = json!({"messages": [{"role": "system", "content": [{"type": "text", "text": "x"}]}]});
        let out = inject_cache_control(body, true);
        assert_eq!(out["messages"][0]["content"][0]["cache_control"]["type"], "ephemeral");
    }

    #[test]
    fn disabled_is_identity() {
        let body = json!({"messages": [{"role": "system", "content": "x"}]});
        let out = inject_cache_control(body, false);
        assert!(out["messages"][0]["content"].is_string());
    }

    #[test]
    fn cap_applied_and_respected() {
        assert_eq!(cap_max_tokens(json!({"max_tokens": 4096}), 1024)["max_tokens"], 1024);
        assert_eq!(cap_max_tokens(json!({"max_tokens": 500}), 1024)["max_tokens"], 500);
        assert_eq!(cap_max_tokens(json!({}), 1024)["max_tokens"], 1024);
    }

    #[test]
    fn truncation_is_utf8_safe() {
        let s = "é".repeat(600); // 2-byte chars; byte-slicing would panic
        let body = json!({"messages": [{"role": "tool", "content": s}]});
        let (out, n) = truncate_tool_results(body, 100);
        assert_eq!(n, 1);
        let c = out["messages"][0]["content"].as_str().unwrap();
        assert!(c.chars().count() < 160);
        assert!(c.contains("truncated"));
    }

    #[test]
    fn non_tool_messages_untouched() {
        let body = json!({"messages": [{"role": "user", "content": "y".repeat(10000)}]});
        let (out, n) = truncate_tool_results(body, 10);
        assert_eq!(n, 0);
        assert_eq!(out["messages"][0]["content"].as_str().unwrap().len(), 10000);
    }
}
