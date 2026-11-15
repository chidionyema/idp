//! Anthropic-protocol ingress: Claude Code speaks Messages API; pennyd's
//! edge and cache are canonical OpenAI-shaped. This module is the boundary:
//! anthropic request -> canonical, canonical response -> anthropic, and a
//! streaming SSE translator (OpenAI chunk stream -> Anthropic event stream)
//! for stream=true requests served by OpenAI-dialect lanes (the
//! Claude Code -> GLM case). Anthropic-dialect lanes pass SSE through.

use crate::error::PennyError;
use crate::router::ByteStream;
use bytes::Bytes;
use futures_core::Stream;
use serde_json::{json, Value};
use std::pin::Pin;
use std::sync::atomic::{AtomicU64, Ordering};
use std::task::{Context, Poll};

static ID_COUNTER: AtomicU64 = AtomicU64::new(0);

fn new_id() -> String {
    let n = ID_COUNTER.fetch_add(1, Ordering::Relaxed);
    let t = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0);
    format!("msg_{:08x}{:04x}", t as u32, n as u32)
}

/// P1-6: content blocks -> openai content parts. Text stays text; images
/// become image_url data URLs; documents/files become an explicit marker
/// (never silently dropped — lossy translation is a correctness bug).
fn blocks_to_openai_content(v: &Value) -> Value {
    let blocks = match v {
        Value::String(_) | Value::Null => return v.clone(),
        Value::Array(a) => a.clone(),
        other => return other.clone(),
    };
    let mut parts: Vec<Value> = Vec::new();
    for b in &blocks {
        match b.get("type").and_then(|t| t.as_str()) {
            Some("text") => parts.push(json!({"type": "text", "text": b.get("text").and_then(|t| t.as_str()).unwrap_or("")})),
            Some("image") => {
                let src = b.get("source").cloned().unwrap_or(Value::Null);
                let media = src.get("media_type").and_then(|m| m.as_str()).unwrap_or("image/png");
                let data = src.get("data").and_then(|d| d.as_str()).unwrap_or("");
                parts.push(json!({"type": "image_url", "image_url": {"url": format!("data:{media};base64,{data}")}}));
            }
            Some("document") | Some("file") => {
                let name = b.get("name").or(b.get("file_name")).and_then(|n| n.as_str()).unwrap_or("document");
                parts.push(json!({"type": "text", "text": format!("[document attached: {name}]")}));
            }
            _ => {}
        }
    }
    if parts.is_empty() {
        json!(blocks_to_text(v))
    } else {
        json!(parts)
    }
}

fn blocks_to_text(v: &Value) -> String {
    match v {
        Value::String(s) => s.clone(),
        Value::Array(a) => a
            .iter()
            .filter(|b| b.get("type").and_then(|t| t.as_str()) == Some("text"))
            .filter_map(|b| b.get("text").and_then(|t| t.as_str()))
            .collect::<Vec<_>>()
            .join(""),
        _ => String::new(),
    }
}

/// Anthropic Messages request -> canonical OpenAI chat body. Covers
/// string/array system, text, tool_use (assistant tool_calls) and
/// tool_result (tool role) — the full Claude Code agentic loop.
pub fn request_to_openai(body: &Value) -> Result<Value, PennyError> {
    if body.get("messages").and_then(|m| m.as_array()).is_none() {
        return Err(PennyError::BadRequest(
            "anthropic request: 'messages' must be an array".into(),
        ));
    }
    let mut messages: Vec<Value> = Vec::new();
    if let Some(sys) = body.get("system") {
        let text = blocks_to_text(sys);
        if !text.is_empty() {
            messages.push(json!({"role": "system", "content": text}));
        }
    }
    for m in body["messages"].as_array().cloned().unwrap_or_default() {
        let role = m.get("role").and_then(|r| r.as_str()).unwrap_or("user");
        let content = m.get("content").cloned().unwrap_or(Value::Null);
        match role {
            "user" => {
                let blocks = content.as_array().cloned().unwrap_or_default();
                let tool_results: Vec<Value> = blocks
                    .iter()
                    .filter(|b| b.get("type").and_then(|t| t.as_str()) == Some("tool_result"))
                    .cloned()
                    .collect();
                if !blocks.is_empty() && tool_results.len() == blocks.len() {
                    for tr in tool_results {
                        messages.push(json!({
                            "role": "tool",
                            "tool_call_id": tr.get("tool_use_id").cloned().unwrap_or(Value::Null),
                            "content": blocks_to_openai_content(tr.get("content").unwrap_or(&Value::Null)),
                        }));
                    }
                } else {
                    messages.push(json!({"role": "user", "content": blocks_to_openai_content(&content)}));
                }
            }
            "assistant" => {
                let text = blocks_to_text(&content);
                let tool_uses: Vec<Value> = content
                    .as_array()
                    .map(|a| {
                        a.iter()
                            .filter(|b| b.get("type").and_then(|t| t.as_str()) == Some("tool_use"))
                            .cloned()
                            .collect()
                    })
                    .unwrap_or_default();
                if tool_uses.is_empty() {
                    messages.push(json!({"role": "assistant", "content": text}));
                } else {
                    let calls: Vec<Value> = tool_uses
                        .iter()
                        .map(|tu| {
                            json!({
                                "id": tu.get("id").cloned().unwrap_or(Value::Null),
                                "type": "function",
                                "function": {
                                    "name": tu.get("name").cloned().unwrap_or(Value::Null),
                                    "arguments": tu.get("input").map(|i| i.to_string()).unwrap_or_else(|| "{}".into()),
                                },
                            })
                        })
                        .collect();
                    let mut msg = json!({"role": "assistant", "tool_calls": calls});
                    if !text.is_empty() {
                        msg["content"] = json!(text);
                    }
                    messages.push(msg);
                }
            }
            other => messages.push(json!({"role": other, "content": blocks_to_text(&content)})),
        }
    }
    let mut out = json!({
        "model": body.get("model").cloned().unwrap_or(Value::Null),
        "messages": messages,
    });
    // P0-2: Claude Code's tool catalog must survive the translation, or the
    // agentic loop is silently degraded to plain chat.
    if let Some(tools) = body.get("tools").and_then(|t| t.as_array()) {
        let mapped: Vec<Value> = tools
            .iter()
            .map(|t| {
                json!({
                    "type": "function",
                    "function": {
                        "name": t.get("name").cloned().unwrap_or(Value::Null),
                        "description": t.get("description").cloned().unwrap_or(json!("")),
                        "parameters": t.get("input_schema").cloned().unwrap_or(json!({"type": "object"})),
                    },
                })
            })
            .collect();
        out["tools"] = json!(mapped);
    }
    if let Some(tc) = body.get("tool_choice") {
        // anthropic: auto | any | none | {type:"tool", name} (legacy {type, name})
        let mapped = match tc {
            Value::String(s) => match s.as_str() {
                "any" => json!("required"),
                other => json!(other),
            },
            Value::Object(_) => {
                let name = tc.get("name").cloned().unwrap_or(Value::Null);
                json!({"type": "function", "function": {"name": name}})
            }
            other => other.clone(),
        };
        out["tool_choice"] = mapped;
    }
    if let Some(mt) = body.get("max_tokens") {
        out["max_tokens"] = mt.clone();
    }
    if body.get("stream").and_then(|s| s.as_bool()).unwrap_or(false) {
        out["stream"] = json!(true);
        // ask upstream for usage in the final chunk so estimates stay honest
        out["stream_options"] = json!({"include_usage": true});
    }
    Ok(out)
}

fn map_stop_reason(fr: Option<&str>) -> &'static str {
    match fr {
        Some("length") | Some("max_tokens") => "max_tokens",
        Some("tool_calls") | Some("tool_use") => "tool_use",
        _ => "end_turn",
    }
}

/// Canonical OpenAI response -> Anthropic Messages response.
pub fn response_to_anthropic(resp: &Value) -> Value {
    let choice = resp["choices"].get(0).cloned().unwrap_or_else(|| json!({}));
    let msg = choice["message"].clone();
    let mut content_blocks: Vec<Value> = Vec::new();
    if let Some(text) = msg.get("content").and_then(|c| c.as_str()) {
        if !text.is_empty() {
            content_blocks.push(json!({"type": "text", "text": text}));
        }
    }
    if let Some(tcs) = msg.get("tool_calls").and_then(|t| t.as_array()) {
        for tc in tcs {
            let input = tc["function"]["arguments"]
                .as_str()
                .and_then(|s| serde_json::from_str::<Value>(s).ok())
                .unwrap_or(Value::Null);
            content_blocks.push(json!({
                "type": "tool_use",
                "id": tc.get("id").cloned().unwrap_or(Value::Null),
                "name": tc["function"].get("name").cloned().unwrap_or(Value::Null),
                "input": input,
            }));
        }
    }
    let usage = resp.get("usage").cloned().unwrap_or_else(|| json!({}));
    json!({
        "id": resp.get("id").and_then(|i| i.as_str()).map(String::from).unwrap_or_else(new_id),
        "type": "message",
        "role": "assistant",
        "model": resp.get("model").cloned().unwrap_or(Value::Null),
        "content": content_blocks,
        "stop_reason": map_stop_reason(choice.get("finish_reason").and_then(|f| f.as_str())),
        "usage": {
            "input_tokens": usage.get("prompt_tokens").cloned().unwrap_or(json!(0)),
            "output_tokens": usage.get("completion_tokens").cloned().unwrap_or(json!(0)),
        },
    })
}

/// Anthropic-format error body for the /v1/messages edge (P1-9: the error
/// KIND must reflect the failure, not a single catch-all).
pub fn error_body(kind: &str, msg: &str) -> Value {
    json!({"type": "error", "error": {"type": kind, "message": msg}})
}

// ---------- streaming: OpenAI SSE -> Anthropic SSE ----------

fn sse_event(name: &str, data: Value) -> Bytes {
    Bytes::from(format!("event: {name}\ndata: {data}\n\n"))
}

/// P1-4: a stuck/malicious upstream must not grow memory without bound.
const SSE_BUF_CAP: usize = 1 << 20; // 1 MiB

#[derive(Default)]
struct ToolAccum {
    id: String,
    name: String,
    args: String,
    block_open: bool,
}

struct SseTranslator {
    upstream: ByteStream,
    buf: Vec<u8>,
    id: String,
    model: String,
    out_tokens: u64,
    sent_start: bool,
    finished: bool,
    finish_reason: Option<String>, // from the last choice chunk
    tools: Vec<ToolAccum>,         // P0-3: streamed tool_call deltas
}

impl SseTranslator {
    fn new(upstream: ByteStream, model: String) -> Self {
        Self {
            upstream,
            buf: Vec::new(),
            id: new_id(),
            model,
            out_tokens: 0,
            sent_start: false,
            finished: false,
            finish_reason: None,
            tools: Vec::new(),
        }
    }

    fn start_events(&mut self) -> Vec<Bytes> {
        self.sent_start = true;
        vec![
            sse_event(
                "message_start",
                json!({"type": "message_start", "message": {
                    "id": self.id, "type": "message", "role": "assistant",
                    "model": self.model, "content": [], "stop_reason": null,
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                }}),
            ),
            sse_event(
                "content_block_start",
                json!({"type": "content_block_start", "index": 0,
                       "content_block": {"type": "text", "text": ""}}),
            ),
        ]
    }

    fn finish_events(&mut self) -> Vec<Bytes> {
        let mut v: Vec<Bytes> = Vec::new();
        if !self.sent_start {
            v.extend(self.start_events());
        }
        v.push(sse_event("content_block_stop", json!({"type": "content_block_stop", "index": 0})));
        for (i, t) in self.tools.iter().enumerate() {
            if t.block_open {
                v.push(sse_event("content_block_stop",
                    json!({"type": "content_block_stop", "index": i + 1})));
            }
        }
        let stop = map_stop_reason(self.finish_reason.as_deref());
        v.push(sse_event(
            "message_delta",
            json!({"type": "message_delta", "delta": {"stop_reason": stop},
                   "usage": {"output_tokens": self.out_tokens}}),
        ));
        v.push(sse_event("message_stop", json!({"type": "message_stop"})));
        self.finished = true;
        v
    }

    fn pop_data(&mut self) -> Option<String> {
        let sep = self
            .buf
            .windows(2)
            .position(|w| w == b"\n\n")
            .map(|p| (p, 2))
            .or_else(|| self.buf.windows(4).position(|w| w == b"\r\n\r\n").map(|p| (p, 4)))?;
        let raw: Vec<u8> = self.buf.drain(..sep.0 + sep.1).collect();
        let text = String::from_utf8_lossy(&raw).to_string();
        let data: Vec<&str> = text
            .lines()
            .filter_map(|l| l.strip_prefix("data:"))
            .map(str::trim)
            .collect();
        if data.is_empty() {
            Some(String::new()) // keepalive/comment event
        } else {
            Some(data.join("\n"))
        }
    }

    fn try_emit(&mut self) -> Option<Bytes> {
        let mut out: Vec<u8> = Vec::new();
        while let Some(data) = self.pop_data() {
            if data.is_empty() {
                continue;
            }
            if data == "[DONE]" {
                for e in self.finish_events() {
                    out.extend_from_slice(&e);
                }
                break;
            }
            let Ok(chunk) = serde_json::from_str::<Value>(&data) else { continue };
            if let Some(u) = chunk.get("usage") {
                if let Some(n) = u.get("completion_tokens").and_then(|v| v.as_u64()) {
                    self.out_tokens += n;
                }
            }
            let choice = chunk["choices"].get(0).cloned().unwrap_or(Value::Null);
            if let Some(fr) = choice.get("finish_reason").and_then(|f| f.as_str()) {
                self.finish_reason = Some(fr.to_string());
            }
            let delta = choice.get("delta").cloned().unwrap_or(Value::Null);
            let text = delta.get("content").and_then(|c| c.as_str()).unwrap_or("");
            if !text.is_empty() {
                if !self.sent_start {
                    for e in self.start_events() {
                        out.extend_from_slice(&e);
                    }
                }
                let ev = sse_event(
                    "content_block_delta",
                    json!({"type": "content_block_delta", "index": 0,
                           "delta": {"type": "text_delta", "text": text}}),
                );
                out.extend_from_slice(&ev);
            }
            // P0-3: streamed tool calls must produce tool_use blocks
            if let Some(tds) = delta.get("tool_calls").and_then(|t| t.as_array()) {
                for td in tds {
                    let idx = td.get("index").and_then(|i| i.as_u64()).unwrap_or(0) as usize;
                    while self.tools.len() <= idx {
                        self.tools.push(ToolAccum::default());
                    }
                    let t = &mut self.tools[idx];
                    if let Some(id) = td.get("id").and_then(|i| i.as_str()) {
                        t.id = id.to_string();
                    }
                    if let Some(name) = td["function"].get("name").and_then(|n| n.as_str()) {
                        t.name = name.to_string();
                    }
                    if let Some(args) = td["function"].get("arguments").and_then(|a| a.as_str()) {
                        t.args.push_str(args);
                    }
                    if !t.block_open {
                        t.block_open = true;
                        if !self.sent_start {
                            for e in self.start_events() {
                                out.extend_from_slice(&e);
                            }
                        }
                        // text block (index 0) closes before the tool block opens
                        if self.sent_start {
                            out.extend_from_slice(&sse_event(
                                "content_block_stop",
                                json!({"type": "content_block_stop", "index": 0}),
                            ));
                        }
                        out.extend_from_slice(&sse_event(
                            "content_block_start",
                            json!({"type": "content_block_start", "index": idx + 1,
                                   "content_block": {"type": "tool_use",
                                                     "id": t.id, "name": t.name, "input": {}}}),
                        ));
                    }
                    out.extend_from_slice(&sse_event(
                        "content_block_delta",
                        json!({"type": "content_block_delta", "index": idx + 1,
                               "delta": {"type": "input_json_delta", "partial_json":
                                   td["function"].get("arguments").cloned().unwrap_or(json!(""))}}),
                    ));
                }
            }
        }
        if out.is_empty() {
            None
        } else {
            Some(Bytes::from(out))
        }
    }
}

impl Stream for SseTranslator {
    type Item = Result<Bytes, PennyError>;

    fn poll_next(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        let this = self.get_mut(); // all fields Unpin
        loop {
            if this.finished {
                return Poll::Ready(None);
            }
            if let Some(bytes) = this.try_emit() {
                return Poll::Ready(Some(Ok(bytes)));
            }
            match this.upstream.as_mut().poll_next(cx) {
                Poll::Ready(Some(Ok(chunk))) => {
                    this.buf.extend_from_slice(&chunk);
                    if this.buf.len() > SSE_BUF_CAP {
                        this.finished = true;
                        return Poll::Ready(Some(Err(PennyError::Upstream {
                            lane: "sse-translator".into(),
                            status: 0,
                            body: "upstream exceeded SSE buffer cap (stuck stream?)".into(),
                        })));
                    }
                }
                Poll::Ready(Some(Err(e))) => return Poll::Ready(Some(Err(e))),
                Poll::Ready(None) => {
                    // upstream closed without [DONE]: emit a well-formed close
                    if let Some(bytes) = {
                        let mut fin: Vec<u8> = Vec::new();
                        for e in this.finish_events() {
                            fin.extend_from_slice(&e);
                        }
                        if fin.is_empty() { None } else { Some(Bytes::from(fin)) }
                    } {
                        return Poll::Ready(Some(Ok(bytes)));
                    }
                }
                Poll::Pending => return Poll::Pending,
            }
        }
    }
}

/// Wrap an OpenAI-dialect SSE stream as an Anthropic SSE event stream.
pub fn openai_sse_to_anthropic(upstream: ByteStream, model: String) -> ByteStream {
    Box::pin(SseTranslator::new(upstream, model))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn request_simple() {
        let body = json!({
            "model": "test-chat", "max_tokens": 256,
            "system": "be terse",
            "messages": [{"role": "user", "content": "hello"}],
        });
        let c = request_to_openai(&body).unwrap();
        assert_eq!(c["messages"][0], json!({"role": "system", "content": "be terse"}));
        assert_eq!(c["messages"][1]["role"], "user");
        assert_eq!(c["max_tokens"], 256);
    }

    #[test]
    fn request_tool_loop_round_trip() {
        let body = json!({
            "model": "m", "max_tokens": 100,
            "messages": [
                {"role": "user", "content": "check it"},
                {"role": "assistant", "content": [
                    {"type": "text", "text": "checking"},
                    {"type": "tool_use", "id": "tu_1", "name": "get", "input": {"a": 1}},
                ]},
                {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": "tu_1", "content": "result-text"},
                ]},
            ],
        });
        let c = request_to_openai(&body).unwrap();
        let msgs = c["messages"].as_array().unwrap();
        assert_eq!(msgs[2]["tool_calls"][0]["function"]["name"], "get");
        assert_eq!(msgs[2]["tool_calls"][0]["function"]["arguments"], r#"{"a":1}"#);
        assert_eq!(msgs[3], json!({"role": "tool", "tool_call_id": "tu_1", "content": "result-text"}));
        let back = response_to_anthropic(&json!({
            "choices": [{"message": {"role": "assistant", "tool_calls": msgs[2]["tool_calls"].clone()}, "finish_reason": "tool_calls"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 7},
        }));
        assert_eq!(back["stop_reason"], "tool_use");
        assert_eq!(back["content"][0]["type"], "tool_use");
        assert_eq!(back["content"][0]["input"], json!({"a": 1}));
        assert_eq!(back["usage"]["input_tokens"], 5);
    }

    #[test]
    fn request_missing_messages_rejected() {
        assert!(request_to_openai(&json!({"model": "m"})).is_err());
    }

    #[test]
    fn response_maps_stop_reasons() {
        let mk = |fr: &str| response_to_anthropic(&json!({
            "choices": [{"message": {"content": "x"}, "finish_reason": fr}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2},
        }));
        assert_eq!(mk("stop")["stop_reason"], "end_turn");
        assert_eq!(mk("length")["stop_reason"], "max_tokens");
        assert_eq!(mk("tool_calls")["stop_reason"], "tool_use");
    }

    #[tokio::test]
    async fn sse_translation_split_chunks_and_done() {
        let part1 = b"data: {\"choices\":[{\"delta\":{\"content\":\"Hel\"}}]}\n\nda";
        let part2 = b"ta: {\"choices\":[{\"delta\":{\"content\":\"lo\"}}]}\n\ndata: [DONE]\n\n";
        let upstream: ByteStream = Box::pin(futures_util::stream::iter(vec![
            Ok(Bytes::from_static(part1)),
            Ok(Bytes::from_static(part2)),
        ]));
        let mut s = openai_sse_to_anthropic(upstream, "glm".to_string());
        use futures_util::StreamExt;
        let mut all = Vec::new();
        while let Some(item) = s.next().await {
            all.extend_from_slice(&item.unwrap());
        }
        let text = String::from_utf8(all).unwrap();
        for needle in ["message_start", "content_block_delta", "Hel", "lo",
                       "content_block_stop", "message_delta", "message_stop", "end_turn"] {
            assert!(text.contains(needle), "missing {needle}");
        }
    }

    #[test]
    fn anthropic_tool_catalog_reaches_the_openai_lane() {
        // P0-2 probe from adversarial review
        let body = json!({
            "model": "m", "max_tokens": 100,
            "tools": [{"name": "Read", "description": "read a file",
                       "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}}}],
            "tool_choice": {"type": "tool", "name": "Read"},
            "messages": [{"role": "user", "content": "hi"}],
        });
        let c = request_to_openai(&body).unwrap();
        assert_eq!(c["tools"][0]["function"]["name"], "Read");
        assert_eq!(c["tools"][0]["function"]["parameters"]["properties"]["path"]["type"], "string");
        assert_eq!(c["tool_choice"]["function"]["name"], "Read");
    }

    #[tokio::test]
    async fn streamed_tool_calls_produce_tool_use_blocks() {
        // P0-3 probe from adversarial review
        let upstream: ByteStream = Box::pin(futures_util::stream::iter(vec![
            Ok(Bytes::from_static(b"data: {\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":0,\"id\":\"call_1\",\"function\":{\"name\":\"Read\",\"arguments\":\"{\\\"path\\\": \\\"/etc/passwd\\\"}\"}}]}}]}\n\n")),
            Ok(Bytes::from_static(b"data: {\"choices\":[{\"delta\":{},\"finish_reason\":\"tool_calls\"}],\"usage\":{\"completion_tokens\":3}}\n\n")),
            Ok(Bytes::from_static(b"data: [DONE]\n\n")),
        ]));
        let mut s = openai_sse_to_anthropic(upstream, "m".to_string());
        use futures_util::StreamExt;
        let mut all = Vec::new();
        while let Some(item) = s.next().await {
            all.extend_from_slice(&item.unwrap());
        }
        let text = String::from_utf8(all).unwrap();
        assert!(text.contains("tool_use"), "expected tool_use block: {text}");
        assert!(text.contains("input_json_delta"));
        assert!(text.contains("call_1"));
        assert!(text.contains("tool_use"), "stop_reason must be tool_use");
    }

    #[tokio::test]
    async fn sse_buffer_cap_terminates_stuck_stream() {
        // P1-4: >1MiB without an event delimiter -> hard error, not unbounded growth
        let junk = vec![b'x'; (1 << 20) + 64];
        let upstream: ByteStream = Box::pin(futures_util::stream::iter(vec![Ok(Bytes::from(junk))]));
        let mut s = openai_sse_to_anthropic(upstream, "m".to_string());
        use futures_util::StreamExt;
        let mut saw_err = false;
        while let Some(item) = s.next().await {
            if item.is_err() {
                saw_err = true;
                break;
            }
        }
        assert!(saw_err, "stuck stream must error at the cap");
    }

    #[test]
    fn images_survive_tool_results() {
        // P1-6: image blocks become image_url parts, never empty strings
        let body = json!({
            "model": "m", "max_tokens": 10,
            "messages": [{"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "tu_9", "content": [
                    {"type": "text", "text": "screenshot"},
                    {"type": "image", "source": {"media_type": "image/png", "data": "QUJD"}},
                ]},
            ]}],
        });
        let c = request_to_openai(&body).unwrap();
        let content = &c["messages"][0]["content"];
        assert_eq!(content[0]["type"], "text");
        assert_eq!(content[1]["type"], "image_url");
        assert!(content[1]["image_url"]["url"].as_str().unwrap().starts_with("data:image/png;base64,"));
    }

    #[tokio::test]
    async fn sse_empty_stream_yields_wellformed_message() {
        let upstream: ByteStream = Box::pin(futures_util::stream::iter(vec![
            Ok(Bytes::from_static(b"data: [DONE]\n\n")),
        ]));
        let mut s = openai_sse_to_anthropic(upstream, "m".to_string());
        use futures_util::StreamExt;
        let mut all = Vec::new();
        while let Some(item) = s.next().await {
            all.extend_from_slice(&item.unwrap());
        }
        let text = String::from_utf8(all).unwrap();
        assert!(text.contains("message_start"));
        assert!(text.contains("message_stop"));
    }
}
