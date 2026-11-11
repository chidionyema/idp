//! Wire dialects: canonical OpenAI-shaped I/O in, provider-native format out.
//!
//! pennyd speaks OpenAI chat/completions at the edge (the lingua franca).
//! `Dialect` translates to/from the provider's native API. OpenAI-compatible
//! providers (DeepSeek, OpenRouter, Groq, Together, Mistral, ollama, vLLM,
//! llama.cpp server, ...) are covered by the passthrough dialect — pure data.
//! Anthropic native is translated structurally. A new dialect = one impl.

use crate::error::PennyError;
use crate::providers::{AuthKind, ModelDef, ProviderDef};
use serde_json::{json, Value};

pub struct TranslatedRequest {
    pub url: String,
    pub headers: Vec<(String, String)>,
    pub body: Value,
}

pub trait Dialect: Send + Sync {
    /// SSE passthrough supported. openai: yes (all OpenAI-compatible lanes).
    /// anthropic: not yet — buffering is refused loudly, never silently.
    fn supports_streaming(&self) -> bool {
        false
    }
    fn translate_request(
        &self,
        p: &ProviderDef,
        m: &ModelDef,
        key: &str,
        body: &Value,
    ) -> Result<TranslatedRequest, PennyError>;
    fn translate_response(&self, body: &Value) -> Result<Value, PennyError>;
}

/// Resolve a dialect name at registry load time. Loud on the unknown.
pub fn for_name(name: &str) -> Result<&'static dyn Dialect, PennyError> {
    match name {
        "openai" => Ok(&OpenAiDialect),
        "anthropic" => Ok(&AnthropicDialect),
        other => Err(unknown_dialect_err(other)),
    }
}

fn unknown_dialect_err(other: &str) -> PennyError {
    PennyError::Config(format!(
        "unknown dialect {other:?} (known: openai, anthropic)"
    ))
}

fn apply_auth(
    p: &ProviderDef,
    key: &str,
    url: String,
    headers: Vec<(String, String)>,
) -> (String, Vec<(String, String)>) {
    match &p.auth {
        AuthKind::None => (url, headers),
        AuthKind::Bearer { .. } => {
            let mut h = headers;
            h.push(("authorization".into(), format!("Bearer {key}")));
            (url, h)
        }
        AuthKind::Header { name, .. } => {
            let mut h = headers;
            h.push((name.clone(), key.to_string()));
            (url, h)
        }
        AuthKind::QueryParam { name, .. } => (format!("{url}?{name}={key}"), headers),
    }
}

fn base(p: &ProviderDef) -> String {
    p.base_url.trim_end_matches('/').to_string()
}

fn endpoint(p: &ProviderDef) -> String {
    format!("{}{}", base(p), p.request_path)
}

pub struct OpenAiDialect;

impl Dialect for OpenAiDialect {
    fn supports_streaming(&self) -> bool {
        true
    }
    fn translate_request(
        &self,
        p: &ProviderDef,
        m: &ModelDef,
        key: &str,
        body: &Value,
    ) -> Result<TranslatedRequest, PennyError> {
        let (url, headers) = apply_auth(p, key, endpoint(p), vec![]);
        let mut body = body.clone();
        body["model"] = json!(m.id);
        Ok(TranslatedRequest { url, headers, body })
    }

    fn translate_response(&self, body: &Value) -> Result<Value, PennyError> {
        Ok(body.clone()) // already canonical
    }
}

pub struct AnthropicDialect;

impl Dialect for AnthropicDialect {
    fn supports_streaming(&self) -> bool {
        // passthrough semantics: request translated to native Messages;
        // upstream SSE is ALREADY the anthropic event format, so bytes
        // stream through untranslated (ingress wraps only openai lanes).
        true
    }
    fn translate_request(
        &self,
        p: &ProviderDef,
        m: &ModelDef,
        key: &str,
        body: &Value,
    ) -> Result<TranslatedRequest, PennyError> {
        let url = endpoint(p);
        let headers = vec![
            ("content-type".into(), "application/json".into()),
            ("anthropic-version".into(), "2023-06-01".into()),
        ];
        let (url, mut headers) = apply_auth(p, key, url, headers);
        headers.push(("anthropic-beta".into(), "prompt-caching-2024-07-31".into()));

        let mut system_text: Vec<String> = Vec::new();
        let mut messages: Vec<Value> = Vec::new();
        for msg in body["messages"].as_array().cloned().unwrap_or_default() {
            match msg.get("role").and_then(|r| r.as_str()) {
                Some("system") => system_text.push(extract_text(msg.get("content"))),
                _ => messages.push(msg),
            }
        }
        let max_tokens = body
            .get("max_tokens")
            .and_then(|v| v.as_u64())
            .unwrap_or(1024);
        let out = json!({
            "model": m.id,
            "max_tokens": max_tokens,
            "messages": messages,
            "system": system_text.join("\n"),
        });
        Ok(TranslatedRequest {
            url,
            headers,
            body: out,
        })
    }

    fn translate_response(&self, body: &Value) -> Result<Value, PennyError> {
        let usage = body.get("usage").cloned().unwrap_or_else(|| json!({}));
        let text: String = body["content"]
            .as_array()
            .map(|blocks| {
                blocks
                    .iter()
                    .filter(|b| b["type"] == "text")
                    .map(|b| extract_text(b.get("text")))
                    .collect::<Vec<_>>()
                    .join("")
            })
            .unwrap_or_default();
        Ok(json!({
            "id": body.get("id").cloned().unwrap_or(Value::Null),
            "model": body.get("model").cloned().unwrap_or(Value::Null),
            "usage": {
                "prompt_tokens": usage.get("input_tokens").cloned().unwrap_or(json!(0)),
                "completion_tokens": usage.get("output_tokens").cloned().unwrap_or(json!(0)),
            },
            "choices": [{
                "index": 0,
                "message": { "role": "assistant", "content": text },
                "finish_reason": "stop",
            }],
        }))
    }
}

fn extract_text(v: Option<&Value>) -> String {
    match v {
        Some(Value::String(s)) => s.clone(),
        Some(Value::Array(a)) => a
            .iter()
            .map(|b| b.get("text").and_then(|t| t.as_str()).unwrap_or(""))
            .collect::<Vec<_>>()
            .join(""),
        _ => String::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::providers::{AuthKind, LaneClass, ModelDef, ProviderDef};

    fn provider(dialect: &str, auth: AuthKind) -> ProviderDef {
        ProviderDef {
            id: "p".into(),
            dialect: dialect.into(),
            base_url: "https://example.com".into(),
            request_path: if dialect == "anthropic" {
                "/v1/messages".into()
            } else {
                "/v1/chat/completions".into()
            },
            auth,
            api_key_file: None,
            timeout_s: 60,
        }
    }

    fn model(id: &str) -> ModelDef {
        ModelDef {
            id: id.into(),
            class: LaneClass::Paid,
            price_in_per_mtok: 1.0,
            price_out_per_mtok: 4.0,
            context_window: 0,
            min_output_tokens: 0,
            aliases: vec![],
            fallbacks: vec![],
        }
    }

    #[test]
    fn openai_passthrough_with_model_swap() {
        let p = provider(
            "openai",
            AuthKind::Bearer {
                key_env: "K".into(),
            },
        );
        let m = model("deepseek-chat");
        let body = json!({"model": "alias-x", "messages": [{"role": "user", "content": "hi"}]});
        let t = OpenAiDialect
            .translate_request(&p, &m, "SECRET", &body)
            .unwrap();
        assert_eq!(t.url, "https://example.com/v1/chat/completions");
        assert!(t
            .headers
            .iter()
            .any(|(k, v)| k == "authorization" && v == "Bearer SECRET"));
        assert_eq!(t.body["model"], "deepseek-chat");
    }

    #[test]
    fn explicit_versioned_path_is_not_rewritten() {
        let mut p = provider("openai", AuthKind::None);
        p.base_url = "https://api.z.ai/api/coding/paas/v4".into();
        p.request_path = "/chat/completions".into();
        let t = OpenAiDialect
            .translate_request(&p, &model("glm-5.3"), "", &json!({}))
            .unwrap();
        assert_eq!(
            t.url,
            "https://api.z.ai/api/coding/paas/v4/chat/completions"
        );
    }

    #[test]
    fn anthropic_extracts_system_and_maps_usage() {
        let p = provider(
            "anthropic",
            AuthKind::Header {
                name: "x-api-key".into(),
                key_env: "K".into(),
            },
        );
        let m = model("claude-haiku");
        let body = json!({
            "model": "alias",
            "max_tokens": 512,
            "messages": [
                {"role": "system", "content": "be terse"},
                {"role": "user", "content": "hello"},
            ],
        });
        let t = AnthropicDialect
            .translate_request(&p, &m, "KEY", &body)
            .unwrap();
        assert_eq!(t.url, "https://example.com/v1/messages");
        assert!(t
            .headers
            .iter()
            .any(|(k, v)| k == "x-api-key" && v == "KEY"));
        assert_eq!(t.body["system"], "be terse");
        assert_eq!(t.body["max_tokens"], 512);
        assert_eq!(t.body["messages"].as_array().unwrap().len(), 1);

        let native = json!({
            "id": "msg_1", "model": "claude-haiku",
            "usage": {"input_tokens": 10, "output_tokens": 4},
            "content": [{"type": "text", "text": "world"}],
        });
        let canon = AnthropicDialect.translate_response(&native).unwrap();
        assert_eq!(canon["usage"]["prompt_tokens"], 10);
        assert_eq!(canon["usage"]["completion_tokens"], 4);
        assert_eq!(canon["choices"][0]["message"]["content"], "world");
    }

    #[test]
    fn unknown_dialect_is_loud() {
        assert!(for_name("gemini-native").is_err());
    }
}
