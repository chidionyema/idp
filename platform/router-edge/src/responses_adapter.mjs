// OpenAI Responses API <-> the router's one execution path (/v1/chat/completions).
//
// Why this exists: Codex 0.169 refuses `wire_api = "chat"` ("`wire_api = \"chat\"` is no
// longer supported", measured in the shipped binary), so a provider that only speaks chat
// completions is unreachable from Codex desktop. This module is pure translation. The
// Worker routes /v1/responses through the SAME admission, budget reservation and failover
// as chat, so there is no second path to meter, secure or let drift.
//
// Scope, stated so nobody has to guess:
//   * Text in, text out. Lanes carry supportsTools=false (raising that is a measurement), so
//     `tools` are NOT forwarded and the response says so in `x-meridian-tools: dropped`.
//   * Items it cannot represent are refused with 400, never silently dropped, except
//     `reasoning` items, which carry no user content and are skipped by definition.
//   * stream:true is answered as protocol-correct SSE built from the completed answer and
//     always ends in response.completed. A failure happens before any byte streams, so it is
//     returned as the real HTTP error (402/429/503...), which a client can classify and retry.

const TEXT_PART_TYPES = new Set(["input_text", "output_text", "text"]);

function partsToText(content) {
  if (typeof content === "string") return { ok: true, text: content };
  if (!Array.isArray(content)) return { ok: false, detail: "content_must_be_string_or_parts" };
  let text = "";
  for (const part of content) {
    if (!part || !TEXT_PART_TYPES.has(part.type) || typeof part.text !== "string") {
      return { ok: false, detail: `unsupported_content_part:${part && part.type}` };
    }
    text += part.text;
  }
  return { ok: true, text };
}

const ROLE_MAP = { user: "user", assistant: "assistant", system: "system", developer: "system" };

export function responsesToChat(body) {
  if (!body || typeof body !== "object") return { ok: false, detail: "body_must_be_object" };
  const messages = [];
  if (typeof body.instructions === "string" && body.instructions.trim()) {
    messages.push({ role: "system", content: body.instructions });
  }
  const input = body.input;
  if (typeof input === "string") {
    messages.push({ role: "user", content: input });
  } else if (Array.isArray(input)) {
    for (const item of input) {
      if (!item || typeof item !== "object") return { ok: false, detail: "input_item_must_be_object" };
      if (item.type === "reasoning") continue;
      if (item.type !== undefined && item.type !== "message") {
        return { ok: false, detail: `unsupported_input_item:${item.type}` };
      }
      const role = ROLE_MAP[item.role];
      if (!role) return { ok: false, detail: `unsupported_role:${item.role}` };
      const t = partsToText(item.content);
      if (!t.ok) return t;
      messages.push({ role, content: t.text });
    }
  } else {
    return { ok: false, detail: "input_required" };
  }
  if (!messages.some((m) => m.role !== "system")) return { ok: false, detail: "no_user_content" };

  const chat = { model: body.model, messages, stream: false };
  if (Number.isFinite(body.max_output_tokens)) chat.max_tokens = body.max_output_tokens;
  if (Number.isFinite(body.temperature)) chat.temperature = body.temperature;
  if (Number.isFinite(body.top_p)) chat.top_p = body.top_p;
  const toolsDropped = Array.isArray(body.tools) && body.tools.length > 0;
  return { ok: true, chat, toolsDropped, wantsStream: body.stream === true };
}

export function chatToResponse(chatJson, model, now = Date.now()) {
  const choice = chatJson && Array.isArray(chatJson.choices) ? chatJson.choices[0] : undefined;
  const text = choice && choice.message && typeof choice.message.content === "string" ? choice.message.content : "";
  const u = (chatJson && chatJson.usage) || {};
  const input = Number(u.prompt_tokens) || 0;
  const output = Number(u.completion_tokens) || 0;
  const rid = `resp_${(chatJson && chatJson.id) || now}`;
  return {
    id: rid,
    object: "response",
    created_at: Math.floor(now / 1000),
    status: "completed",
    model,
    output: [
      {
        type: "message",
        id: `msg_${rid.slice(5)}`,
        status: "completed",
        role: "assistant",
        content: [{ type: "output_text", text, annotations: [] }],
      },
    ],
    usage: { input_tokens: input, output_tokens: output, total_tokens: Number(u.total_tokens) || input + output },
  };
}

function sse(events) {
  return events.map((e) => `event: ${e.type}\ndata: ${JSON.stringify(e)}\n\n`).join("");
}

export function responseToSse(resp) {
  const item = resp.output[0];
  const part = item.content[0];
  const inProgress = { ...resp, status: "in_progress", output: [], usage: null };
  const emptyItem = { ...item, status: "in_progress", content: [] };
  const emptyPart = { ...part, text: "" };
  const events = [
    { type: "response.created", response: inProgress },
    { type: "response.in_progress", response: inProgress },
    { type: "response.output_item.added", output_index: 0, item: emptyItem },
    { type: "response.content_part.added", item_id: item.id, output_index: 0, content_index: 0, part: emptyPart },
  ];
  const CHUNK = 256;
  for (let i = 0; i < part.text.length; i += CHUNK) {
    events.push({
      type: "response.output_text.delta",
      item_id: item.id,
      output_index: 0,
      content_index: 0,
      delta: part.text.slice(i, i + CHUNK),
    });
  }
  events.push(
    { type: "response.output_text.done", item_id: item.id, output_index: 0, content_index: 0, text: part.text },
    { type: "response.content_part.done", item_id: item.id, output_index: 0, content_index: 0, part },
    { type: "response.output_item.done", output_index: 0, item },
    { type: "response.completed", response: resp }
  );
  return sse(events.map((e, i) => ({ ...e, sequence_number: i })));
}

// `roles` is the routing table's role map; every role that routes is a model a client may name.
export function modelsList(roles, now = Date.now()) {
  const created = Math.floor(now / 1000);
  const ids = Object.keys(roles || {})
    .map((r) => (r.startsWith("role:") ? r.slice(5) : r))
    .sort();
  return {
    object: "list",
    data: ids.map((id) => ({ id, object: "model", created, owned_by: "meridian-router" })),
  };
}
