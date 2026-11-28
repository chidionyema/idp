// The probe is the thing that tells the estate the deployment works. It must be able to say no.
// The logic is tested in-process with an injected fetch; one test runs the real CLI end to end.
import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { execFile } from "node:child_process";
import { fileURLToPath } from "node:url";
import { probe } from "../scripts/probe-lib.mjs";

const PROBE = fileURLToPath(new URL("../scripts/probe.mjs", import.meta.url));
const HEALTH = { ok: true, schema: "estate-live-state.v1", zone: "zone-b-cloudflare-edge", commit_sha: "abc1234" };
const SNAP = { schema: "estate-live-state.v1", seq: 7, hash: "0123456789abcdef0123", subjects: { "k:a": {}, "k:b": {} }, blind: ["k:b"] };

// routes: path -> {status, body(req)} ; an absent path is a 404
function fakeFetch(routes) {
  return async (url, init = {}) => {
    const path = new URL(url).pathname;
    const r = routes[path];
    const status = r ? (r.status ?? 200) : 404;
    const body = r ? (typeof r.body === "function" ? r.body(init) : r.body) : {};
    return { ok: status >= 200 && status < 300, status, json: async () => body };
  };
}
// `arguments.length`, not a default parameter: run(routes, undefined) must mean "no token".
const run = (routes, ...rest) => probe({ base: "https://x", token: rest.length ? rest[0] : "tok", fetchImpl: fakeFetch(routes), ...(rest[1] ?? {}) });

test("a healthy deployment with a snapshot is code 0 and prints what it measured", async () => {
  const seen = [];
  const r = await run({ "/health": { body: HEALTH }, "/snapshot": { body: (init) => (seen.push(init.headers.authorization), init.headers.authorization === "Bearer tok" ? SNAP : { wrong: true }) } });
  assert.equal(r.code, 0, r.err.join());
  assert.deepEqual(r.err, []);
  assert.match(r.out[0], /^ok {2}\/health {2}commit_sha=abc1234 {2}zone=zone-b-cloudflare-edge {2}\d+ms$/);
  assert.match(r.out[1], /^ok {2}\/snapshot {2}seq=7 {2}hash=0123456789abcdef {2}subjects=2 {2}blind=1 {2}\d+ms$/);
  assert.deepEqual(seen, ["Bearer tok"]);
});

test("timings come from the injected clock", async () => {
  let t = 0;
  const r = await run({ "/health": { body: HEALTH }, "/snapshot": { body: SNAP } }, "tok", { now: () => (t += 10) });
  assert.match(r.out[0], /\s10ms$/);
  assert.match(r.out[1], /\s10ms$/);
});

test("no read token is BLIND, code 2 and never 0", async () => {
  for (const token of [undefined, ""]) {
    const r = await run({ "/health": { body: HEALTH } }, token);
    assert.equal(r.code, 2);
    assert.match(r.out[1], /^BLIND {2}\/snapshot/);
    assert.deepEqual(r.err, []);
  }
});

test("every way the deployment can be wrong is code 1 with a named reason", async () => {
  const cases = {
    "health 500": [{ "/health": { status: 500, body: {} } }, /\/health HTTP 500/],
    "health missing": [{}, /\/health HTTP 404/],
    "wrong schema": [{ "/health": { body: { ...HEALTH, schema: "other" } } }, /\/health schema "other"/],
    "dev-local sha": [{ "/health": { body: { ...HEALTH, commit_sha: "dev-local" } } }, /commit_sha "dev-local" is not a deployed sha/],
    "no sha": [{ "/health": { body: { ...HEALTH, commit_sha: null } } }, /commit_sha null is not a deployed sha/],
    "snapshot 401": [{ "/health": { body: HEALTH }, "/snapshot": { status: 401, body: {} } }, /\/snapshot HTTP 401/],
    "snapshot wrong schema": [{ "/health": { body: HEALTH }, "/snapshot": { body: { ...SNAP, schema: "x" } } }, /\/snapshot is not estate-live-state\.v1/],
    "snapshot no hash": [{ "/health": { body: HEALTH }, "/snapshot": { body: { ...SNAP, hash: undefined } } }, /\/snapshot is not estate-live-state\.v1/],
  };
  for (const [name, [routes, why]] of Object.entries(cases)) {
    const r = await run(routes);
    assert.equal(r.code, 1, name);
    assert.equal(r.err.length, 1, name);
    assert.match(r.err[0], /^PROBE FAIL {2}https:\/\/x {2}/, name);
    assert.match(r.err[0], why, name);
  }
});

test("an unreachable deployment is code 1, for /health and for /snapshot", async () => {
  const down = async () => { throw new Error("ECONNREFUSED"); };
  let r = await probe({ base: "https://x", token: "tok", fetchImpl: down });
  assert.equal(r.code, 1);
  assert.match(r.err[0], /\/health unreachable: ECONNREFUSED/);
  const half = async (url) => {
    if (new URL(url).pathname === "/health") return { ok: true, status: 200, json: async () => HEALTH };
    throw new Error("reset");
  };
  r = await probe({ base: "https://x", token: "tok", fetchImpl: half });
  assert.equal(r.code, 1);
  assert.match(r.err[0], /\/snapshot unreachable: reset/);
});

test("the CLI end to end: exit code and streams match the logic", async () => {
  const server = http.createServer((req, res) => {
    res.end(JSON.stringify(req.url === "/health" ? HEALTH : SNAP));
  });
  await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
  const url = `http://127.0.0.1:${server.address().port}`;
  const cli = (env) => new Promise((done) => {
    execFile(process.execPath, [PROBE], { env: { PATH: process.env.PATH, LIVE_STATE_URL: url, ...env }, timeout: 15_000 }, (err, stdout, stderr) => done({ code: err ? err.code : 0, stdout, stderr }));
  });
  try {
    const good = await cli({ LIVE_STATE_READ_TOKEN: "tok" });
    assert.equal(good.code, 0, good.stderr);
    assert.match(good.stdout, /ok {2}\/snapshot {2}seq=7/);
    const blind = await cli({});
    assert.equal(blind.code, 2);
    assert.match(blind.stdout, /BLIND/);
  } finally {
    server.close();
  }
});
