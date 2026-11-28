import assert from "node:assert/strict";
import { test } from "node:test";
import { chatToResponse, modelsList, responseToSse, responsesToChat } from "../src/responses_adapter.mjs";
import { probeCodexSurface, releasePool } from "../scripts/role-pool.mjs";

// Codex 0.169 refuses wire_api "chat", so these pin the translation it depends on. Each
// refusal below is a known-bad input the adapter must reject; each pass is a known-good.

test("string input becomes one user turn; instructions become the system turn", () => {
  const r = responsesToChat({ model: "deepseek-flash", instructions: "be brief", input: "hi", max_output_tokens: 64 });
  assert.equal(r.ok, true);
  assert.deepEqual(r.chat.messages, [{ role: "system", content: "be brief" }, { role: "user", content: "hi" }]);
  assert.equal(r.chat.max_tokens, 64);
  assert.equal(r.chat.model, "deepseek-flash");
  assert.equal(r.chat.stream, false, "the router answers whole; streaming is applied on the way out");
});

test("typed message items map roles, developer becomes system, reasoning items are skipped", () => {
  const r = responsesToChat({
    model: "coder",
    input: [
      { type: "message", role: "developer", content: [{ type: "input_text", text: "rules" }] },
      { type: "reasoning", summary: [] },
      { type: "message", role: "user", content: [{ type: "input_text", text: "a" }, { type: "input_text", text: "b" }] },
      { type: "message", role: "assistant", content: [{ type: "output_text", text: "c" }] },
    ],
  });
  assert.equal(r.ok, true);
  assert.deepEqual(r.chat.messages.map((m) => [m.role, m.content]), [["system", "rules"], ["user", "ab"], ["assistant", "c"]]);
});

test("input it cannot represent is refused, never silently dropped", () => {
  for (const [label, body] of [
    ["tool output item", { input: [{ type: "function_call_output", call_id: "x", output: "y" }] }],
    ["function call item", { input: [{ type: "function_call", name: "sh", arguments: "{}" }] }],
    ["image part", { input: [{ type: "message", role: "user", content: [{ type: "input_image", image_url: "u" }] }] }],
    ["unknown role", { input: [{ type: "message", role: "tool", content: "x" }] }],
    ["no input", { model: "m" }],
    ["only a system turn", { instructions: "x", input: [] }],
    ["not an object", null],
  ]) {
    const r = responsesToChat(body);
    assert.equal(r.ok, false, label + " must be refused");
    assert.ok(r.detail, label + " names why");
  }
});

test("tools are reported dropped, not forwarded to lanes that cannot run them", () => {
  const r = responsesToChat({ model: "m", input: "x", tools: [{ type: "function", name: "shell" }] });
  assert.equal(r.ok, true);
  assert.equal(r.toolsDropped, true);
  assert.equal("tools" in r.chat, false);
  assert.equal(responsesToChat({ model: "m", input: "x" }).toolsDropped, false);
});

test("a chat answer becomes a Responses object carrying its text and usage", () => {
  const out = chatToResponse(
    { id: "c1", choices: [{ message: { role: "assistant", content: "OK" } }], usage: { prompt_tokens: 3, completion_tokens: 2 } },
    "deepseek-flash",
    1700000000000
  );
  assert.equal(out.object, "response");
  assert.equal(out.status, "completed");
  assert.equal(out.output[0].content[0].text, "OK");
  assert.deepEqual(out.usage, { input_tokens: 3, output_tokens: 2, total_tokens: 5 });
});

test("SSE carries every delta in order and always ends in response.completed", () => {
  const long = "x".repeat(600);
  const resp = chatToResponse({ id: "c2", choices: [{ message: { content: long } }] }, "m", 1);
  const sse = responseToSse(resp);
  const events = sse.trim().split("\n\n").map((b) => ({
    type: b.match(/^event: (.+)$/m)[1],
    data: JSON.parse(b.match(/^data: (.+)$/m)[1]),
  }));
  assert.equal(events[0].type, "response.created");
  assert.equal(events.at(-1).type, "response.completed");
  assert.equal(events.at(-1).data.response.output[0].content[0].text, long);
  const deltas = events.filter((e) => e.type === "response.output_text.delta").map((e) => e.data.delta);
  assert.ok(deltas.length >= 3 && deltas.join("") === long, "chunks reassemble to the whole answer");
  assert.deepEqual(events.map((e) => e.data.sequence_number), events.map((_, i) => i), "sequence numbers are gapless");
  assert.equal(events.filter((e) => e.type === "response.completed").length, 1);
});

test("an empty answer still terminates the stream", () => {
  const sse = responseToSse(chatToResponse({ choices: [{ message: { content: "" } }] }, "m", 1));
  assert.match(sse, /event: response\.completed/);
});

test("/v1/models lists every role that routes, by the name a client sends", () => {
  const { roles } = releasePool();
  const ids = modelsList(roles).data.map((m) => m.id);
  for (const lane of ["minimax-m3", "deepseek-flash", "deepseek-v4-pro", "gemini-3.5-flash", "coder"]) {
    assert.ok(ids.includes(lane), lane + " is listed");
  }
  assert.ok(ids.every((id) => !id.startsWith("role:")));
});

// The release proof for Codex: it must fail on each way the surface can be broken.
test("the release probe passes a working surface and names every way it can break", async () => {
  const pool = releasePool();
  const ids = Object.keys(pool.roles).map((n) => n.slice(5));
  const resp = chatToResponse({ choices: [{ message: { content: "OK" } }] }, "m", 1);
  const surface = ({ models = ids, status = 200, body = resp, sse = responseToSse(resp) } = {}) => async (url, init) => {
    if (url.endsWith("/v1/models")) return Response.json({ data: models.map((id) => ({ id })) });
    const stream = JSON.parse(init.body).stream;
    return new Response(stream ? sse : JSON.stringify(body), { status });
  };
  assert.equal((await probeCodexSurface("https://r", "k", "minimax-m3", pool, surface())).ok, true);
  const broken = [
    ["a lane missing from /v1/models", surface({ models: ids.slice(1) })],
    ["responses 502", surface({ status: 502 })],
    ["responses with no text", surface({ body: chatToResponse({ choices: [{ message: { content: "" } }] }, "m", 1) })],
    ["a stream that never completes", surface({ sse: "event: response.created\ndata: {}\n\n" })],
    ["a transport failure", async () => { throw new Error("socket hang up"); }],
  ];
  for (const [label, fetchImpl] of broken) {
    const out = await probeCodexSurface("https://r", "k", "minimax-m3", pool, fetchImpl);
    assert.equal(out.ok, false, label + " must not pass");
  }
  const gap = await probeCodexSurface("https://r", "k", "minimax-m3", pool, surface({ models: ids.slice(1) }));
  assert.deepEqual(gap.models_missing, [ids[0]], "the missing model is named");
});
