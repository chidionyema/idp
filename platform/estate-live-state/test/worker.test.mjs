// Falsifiers for the worker and the Durable Object, run against an in-memory storage double.
import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.mjs";
import { EstateLiveStateDO } from "../src/live-state-do.mjs";
import { fold, snapshotHash } from "../src/fold.mjs";

function memoryState() {
  const m = new Map();
  const storage = {
    async get(k) { return m.get(k); },
    async put(k, v) { m.set(k, structuredClone(v)); },
    async list({ prefix }) {
      return new Map([...m].filter(([k]) => k.startsWith(prefix)).sort(([a], [b]) => (a < b ? -1 : 1)));
    },
    async transaction(fn) {
      const snapshot = new Map(m);
      try {
        return await fn(storage);
      } catch (e) {
        m.clear();
        for (const [k, v] of snapshot) m.set(k, v);
        throw e;
      }
    },
    async getAlarm() { return null; },
    async setAlarm() {},
  };
  return { storage, getWebSockets: () => [], acceptWebSocket() {}, _m: m };
}

function rig(secrets = {}) {
  // `in`, not a default parameter: passing read: undefined must mean "not provisioned".
  const read = "read" in secrets ? secrets.read : "r-secret";
  const ingest = "ingest" in secrets ? secrets.ingest : "i-secret";
  const obj = new EstateLiveStateDO(memoryState(), {});
  const env = {
    LIVE_STATE: { idFromName: (n) => n, get: () => ({ fetch: (req) => obj.fetch(req) }) },
    LIVE_STATE_READ_TOKEN: read,
    LIVE_STATE_INGEST_TOKEN: ingest,
    COMMIT_SHA: "abc123",
  };
  const call = (path, { method = "GET", token, body } = {}) =>
    worker.fetch(
      new Request(`https://x${path}`, {
        method,
        headers: { ...(token ? { authorization: `Bearer ${token}` } : {}), "content-type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      }),
      env,
    );
  return { call, obj };
}

const good = (subject, over = {}) => ({ source: "sweep", kind: "optimus", subject, status: "DIRECT", value: 1, interval_s: 900, ...over });

test("/health needs no secret and reports the deployed sha", async () => {
  const { call } = rig();
  const r = await call("/health");
  assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), { ok: true, schema: "estate-live-state.v1", zone: null, commit_sha: "abc123" });
});

test("auth fails closed: wrong token 401, no token 401, unprovisioned secret 503, read token cannot write", async () => {
  const { call } = rig();
  assert.equal((await call("/snapshot")).status, 401);
  assert.equal((await call("/snapshot", { token: "nope" })).status, 401);
  assert.equal((await call("/append", { method: "POST", token: "r-secret", body: good("a") })).status, 401, "a read token must not write");
  assert.equal((await call("/snapshot", { token: "i-secret" })).status, 401, "an ingest token must not read");
  const open = rig({ read: undefined, ingest: "" });
  assert.equal((await open.call("/snapshot", { token: "" })).status, 503, "missing secret refuses everyone, empty token included");
  assert.equal((await open.call("/append", { method: "POST", body: good("a") })).status, 503);
});

test("append then snapshot: the served hash is the hash of the fold, and 0 stays 0", async () => {
  const { call, obj } = rig();
  const w = await call("/append", { method: "POST", token: "i-secret", body: [good("a", { value: 0 }), good("b", { status: "BLIND", value: null, reason: "no producer" })] });
  assert.equal(w.status, 200);
  assert.deepEqual(await w.json(), { accepted: 2, seq: 2 });
  const snap = await (await call("/snapshot", { token: "r-secret" })).json();
  assert.equal(snap.subjects["optimus:a"].value, 0);
  assert.equal(snap.subjects["optimus:b"].status, "BLIND");
  const stored = [...(await obj.state.storage.list({ prefix: "k:" })).values()];
  assert.equal(snap.hash, await snapshotHash(fold(stored, Date.parse(snap.as_of) || Date.now())));
});

test("a batch with one bad event lands nothing", async () => {
  const { call } = rig();
  const r = await call("/append", { method: "POST", token: "i-secret", body: [good("a"), good("b", { value: undefined })] });
  assert.equal(r.status, 422);
  assert.deepEqual((await r.json()).refused.map((x) => x.i), [1]);
  const snap = await (await call("/snapshot", { token: "r-secret" })).json();
  assert.deepEqual(Object.keys(snap.subjects), [], "good event in a refused batch must not land");
});

test("producer silence flips to BLIND on the next read", async () => {
  const { call } = rig();
  await call("/append", { method: "POST", token: "i-secret", body: good("old", { ts: Date.now() - 10_000, interval_s: 1 }) });
  const snap = await (await call("/snapshot", { token: "r-secret" })).json();
  assert.equal(snap.subjects["optimus:old"].status, "BLIND");
  assert.match(snap.subjects["optimus:old"].reason, /^stale:/);
});

test("bad JSON and oversize batches are 400, unknown paths 404", async () => {
  const { call } = rig();
  const bad = await worker.fetch(new Request("https://x/append", { method: "POST", headers: { authorization: "Bearer i-secret" }, body: "{" }), {
    LIVE_STATE: { idFromName: () => "e", get: () => ({ fetch: (req) => new EstateLiveStateDO(memoryState(), {}).fetch(req) }) },
    LIVE_STATE_INGEST_TOKEN: "i-secret",
  });
  assert.equal(bad.status, 400);
  const big = await call("/append", { method: "POST", token: "i-secret", body: Array.from({ length: 101 }, (_, i) => good(`s${i}`)) });
  assert.equal(big.status, 400);
  assert.equal((await call("/nope")).status, 404);
});
