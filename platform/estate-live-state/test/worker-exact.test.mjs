// Exact-behaviour tests for the worker and the Durable Object. Each assertion exists because a
// mutated copy of the source (Stryker 8.7.1) survived without it.
import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.mjs";
import { EstateLiveStateDO } from "../src/live-state-do.mjs";

function makeState({ alarm = null } = {}) {
  const m = new Map();
  const s = { sockets: [], alarm, alarmSets: [], _m: m };
  s.storage = {
    async get(k) { return m.get(k); },
    async put(k, v) { m.set(k, structuredClone(v)); },
    async list({ prefix }) { return new Map([...m].filter(([k]) => k.startsWith(prefix))); },
    async transaction(fn) { return fn(s.storage); },
    async getAlarm() { return s.alarm; },
    async setAlarm(t) { s.alarm = t; s.alarmSets.push(t); },
  };
  s.getWebSockets = () => s.sockets;
  s.acceptWebSocket = (ws) => s.sockets.push(ws);
  return s;
}
const fakeSocket = ({ throwOnSend = false, throwOnClose = false } = {}) => ({
  sent: [], closed: 0,
  send(msg) { if (throwOnSend) throw new Error("dead"); this.sent.push(msg); },
  close() { this.closed++; if (throwOnClose) throw new Error("already closed"); },
});
const good = (subject, over = {}) => ({ source: "sweep", kind: "optimus", subject, status: "DIRECT", value: 1, ...over });
const post = (body, path = "/append") => new Request(`https://x${path}`, { method: "POST", body: typeof body === "string" ? body : JSON.stringify(body) });
const get = (path, headers = {}) => new Request(`https://x${path}`, { headers });

test("DO routes by method and path, and answers JSON", async () => {
  const obj = new EstateLiveStateDO(makeState(), {});
  for (const req of [get("/append"), post({}, "/snapshot"), get("/nope"), post({}, "/")]) {
    const r = await obj.fetch(req);
    assert.equal(r.status, 404, req.url);
    assert.equal(r.headers.get("content-type"), "application/json");
    assert.deepEqual(await r.json(), { error: "not found" });
  }
  assert.equal((await obj.fetch(post({ ...good("a") }))).status, 200);
  assert.equal((await obj.fetch(get("/snapshot"))).status, 200);
  assert.equal((await obj.fetch(get("/ws"))).status, 426, "/ws reaches upgrade");
  assert.equal((await obj.fetch(post({}, "/ws"))).status, 426, "/ws routes by path alone");
});

test("append: refuses bad JSON, empty and oversize batches, with exact bodies", async () => {
  const obj = new EstateLiveStateDO(makeState(), {});
  let r = await obj.fetch(post("{"));
  assert.equal(r.status, 400);
  assert.deepEqual(await r.json(), { error: "body is not JSON" });
  r = await obj.fetch(post([]));
  assert.equal(r.status, 400);
  assert.deepEqual(await r.json(), { error: "send 1 to 100 events" });
  r = await obj.fetch(post(Array.from({ length: 101 }, (_, i) => good(`s${i}`))));
  assert.equal(r.status, 400);
  r = await obj.fetch(post(Array.from({ length: 100 }, (_, i) => good(`s${i}`))));
  assert.equal(r.status, 200, "exactly 100 is allowed");
  assert.deepEqual(await r.json(), { accepted: 100, seq: 100 });
});

test("append: a single object works, seq is the server's, head is stored, ts defaults to now", async () => {
  const state = makeState();
  const obj = new EstateLiveStateDO(state, {});
  const before = Date.now();
  const r = await obj.fetch(post({ ...good("a"), seq: 999 }));
  assert.deepEqual(await r.json(), { accepted: 1, seq: 1 });
  assert.equal(state._m.get("head"), 1);
  const stored = state._m.get("k:optimus:a");
  assert.equal(stored.seq, 1, "a client cannot choose its own seq");
  assert.ok(stored.ts >= before && stored.ts <= Date.now(), "ts defaulted to now");
  await obj.fetch(post([good("b"), good("c", { ts: 0 })]));
  assert.equal(state._m.get("head"), 3);
  assert.equal(state._m.get("k:optimus:c").ts, 0, "a producer-supplied ts of 0 is kept, not replaced");
  assert.equal(state._m.get("k:optimus:b").seq, 2);
});

test("append: non-object events are refused by name, nothing lands", async () => {
  const state = makeState();
  const obj = new EstateLiveStateDO(state, {});
  const r = await obj.fetch(post([good("a"), null, "x", 5]));
  assert.equal(r.status, 422);
  assert.deepEqual(await r.json(), {
    error: "events refused",
    refused: [{ i: 1, problem: "not an object" }, { i: 2, problem: "not an object" }, { i: 3, problem: "not an object" }],
  });
  assert.equal(state._m.size, 0);
});

test("upgrade: needs the websocket header, then registers the socket, greets with a snapshot and arms the alarm", async () => {
  const state = makeState();
  const obj = new EstateLiveStateDO(state, {});
  const real = { Response: globalThis.Response, Pair: globalThis.WebSocketPair };
  const server = fakeSocket();
  const client = { client: true };
  globalThis.WebSocketPair = class { constructor() { this[0] = client; this[1] = server; } };
  globalThis.Response = class { constructor(body, init) { this.body = body; this.status = init?.status; this.webSocket = init?.webSocket; } };
  try {
    const refused = await obj.upgrade(new Request("https://x/ws", { headers: { Upgrade: "h2c" } }));
    assert.equal(refused.status, 426);
    assert.equal(state.sockets.length, 0);
    const t0 = Date.now();
    const ok = await obj.upgrade(new Request("https://x/ws", { headers: { Upgrade: "websocket" } }));
    assert.equal(ok.status, 101);
    assert.equal(ok.webSocket, client);
    assert.equal(ok.body, null);
    assert.deepEqual(state.sockets, [server]);
    const hello = JSON.parse(server.sent[0]);
    assert.equal(hello.type, "snapshot");
    assert.equal(hello.snapshot.schema, "estate-live-state.v1");
    assert.ok(state.alarm >= t0 + 30_000 && state.alarm <= Date.now() + 30_000, "alarm is 30s ahead, not behind");
    await obj.upgrade(new Request("https://x/ws", { headers: { Upgrade: "websocket" } }));
    assert.equal(state.alarmSets.length, 1, "an alarm already set is not set again");
  } finally {
    globalThis.Response = real.Response;
    globalThis.WebSocketPair = real.Pair;
  }
});

test("arm: no sockets, no alarm", async () => {
  const state = makeState();
  await new EstateLiveStateDO(state, {}).arm();
  assert.equal(state.alarmSets.length, 0);
});

test("append broadcasts event to every socket, a dead socket does not stop the rest", async () => {
  const state = makeState();
  const dead = fakeSocket({ throwOnSend: true });
  const live = fakeSocket();
  state.sockets.push(dead, live);
  const obj = new EstateLiveStateDO(state, {});
  await obj.fetch(post(good("a", { value: 0 })));
  assert.equal(live.sent.length, 1);
  const msg = JSON.parse(live.sent[0]);
  assert.equal(msg.type, "event");
  assert.equal(msg.snapshot.subjects["optimus:a"].value, 0);
  assert.ok(state.alarm !== null, "broadcast re-arms the alarm while sockets are connected");
});

test("alarm broadcasts a tick and re-arms", async () => {
  const state = makeState();
  const ws = fakeSocket();
  state.sockets.push(ws);
  const obj = new EstateLiveStateDO(state, {});
  await obj.alarm();
  assert.equal(JSON.parse(ws.sent[0]).type, "tick");
  assert.equal(state.alarmSets.length, 1);
});

test("websocket messages: ping gets pong, anything else gets nothing; close never throws", async () => {
  const obj = new EstateLiveStateDO(makeState(), {});
  const ws = fakeSocket();
  await obj.webSocketMessage(ws, "ping");
  assert.deepEqual(ws.sent, ["pong"]);
  await obj.webSocketMessage(ws, "hello");
  await obj.webSocketMessage(ws, "");
  assert.deepEqual(ws.sent, ["pong"]);
  const open = fakeSocket();
  await obj.webSocketClose(open);
  assert.equal(open.closed, 1);
  await obj.webSocketClose(fakeSocket({ throwOnClose: true }));
});

// ---- the worker in front

function rig(secrets = {}) {
  const state = makeState();
  const obj = new EstateLiveStateDO(state, {});
  const names = [];
  const env = {
    LIVE_STATE: { idFromName: (n) => { names.push(n); return n; }, get: () => ({ fetch: (r) => obj.fetch(r) }) },
    LIVE_STATE_READ_TOKEN: "read" in secrets ? secrets.read : "r-secret",
    LIVE_STATE_INGEST_TOKEN: "ingest" in secrets ? secrets.ingest : "i-secret",
  };
  return { env, names, state, call: (req) => worker.fetch(req, env) };
}
const bearer = (t) => ({ authorization: `Bearer ${t}` });

test("worker: every answer is JSON, /health is GET only and has the exact shape", async () => {
  const { call, env } = rig();
  const h = await call(get("/health"));
  assert.equal(h.headers.get("content-type"), "application/json");
  assert.deepEqual(await h.json(), { ok: true, schema: "estate-live-state.v1", zone: null, commit_sha: null });
  env.DEPLOYMENT_ZONE = "z";
  env.COMMIT_SHA = "sha";
  assert.deepEqual(await (await call(get("/health"))).json(), { ok: true, schema: "estate-live-state.v1", zone: "z", commit_sha: "sha" });
  const post404 = await call(post({}, "/health"));
  assert.equal(post404.status, 404);
  const nf = await call(get("/nope"));
  assert.equal(nf.headers.get("content-type"), "application/json");
  assert.deepEqual(await nf.json(), { error: "not found" });
});

test("worker: routes need the right method and the right token, and the DO is named estate", async () => {
  const { call, names } = rig();
  assert.equal((await call(get("/append", bearer("i-secret")))).status, 404, "GET /append");
  assert.equal((await call(new Request("https://x/snapshot", { method: "POST", headers: bearer("r-secret") }))).status, 404, "POST /snapshot");
  assert.equal((await call(get("/ws"))).status, 401, "/ws needs a token");
  assert.equal((await call(get("/ws", bearer("i-secret")))).status, 401, "/ws wants the read token");
  assert.equal((await call(get("/ws", bearer("r-secret")))).status, 426, "/ws with the read token reaches the DO");
  const w = await call(new Request("https://x/append", { method: "POST", headers: bearer("i-secret"), body: JSON.stringify(good("a")) }));
  assert.deepEqual(await w.json(), { accepted: 1, seq: 1 });
  assert.ok(names.length > 0 && names.every((n) => n === "estate"));
});

test("worker: auth refusals carry exact bodies and JSON content-type", async () => {
  const { call } = rig();
  const no = await call(get("/snapshot"));
  assert.equal(no.status, 401);
  assert.equal(no.headers.get("content-type"), "application/json");
  assert.deepEqual(await no.json(), { error: "unauthorized" });
  const unprovisioned = await rig({ read: undefined }).call(get("/snapshot", bearer("x")));
  assert.equal(unprovisioned.status, 503);
  assert.equal(unprovisioned.headers.get("content-type"), "application/json");
  assert.deepEqual(await unprovisioned.json(), { error: "secret not provisioned" });
  const ingestOff = await rig({ ingest: "" }).call(new Request("https://x/append", { method: "POST", headers: bearer(""), body: "{}" }));
  assert.equal(ingestOff.status, 503);
  assert.equal((await rig({ read: 12345 }).call(get("/snapshot", bearer("12345")))).status, 503, "a non-string secret is not provisioned");
});

test("worker: only an exact Bearer token passes", async () => {
  const { call } = rig();
  const status = async (authorization) => (await call(get("/snapshot", authorization === undefined ? {} : { authorization }))).status;
  assert.equal(await status("Bearer r-secret"), 200);
  for (const bad of [undefined, "", "Bearer ", "Bearer", "bearer r-secret", "Basic r-secret", "r-secret", "Bearer  r-secret", "Bearer r-secre", "Bearer r-secret-x", "Bearer r-secreT", "Bearer R-secret"]) {
    assert.equal(await status(bad), 401, JSON.stringify(bad));
  }
});
