import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { watch } from "../scripts/watch-lib.mjs";
import { fold, snapshotHash } from "../src/fold.mjs";

const NOW = 1_800_000_000_000;
const ev = (seq, over = {}) => ({ seq, source: "sweep", kind: "optimus", subject: `m${seq}`, status: "DIRECT", value: seq, ts: NOW - 1000, ...over });

async function snapshotOf(events) {
  const snap = fold(events, NOW);
  return { ...snap, hash: await snapshotHash(snap) };
}
const ok = (body) => async () => ({ ok: true, status: 200, json: async () => body });
const run = (fetchImpl, ...rest) => watch({ base: "https://w.test", token: rest.length ? rest[0] : "t", fetchImpl, now: () => NOW });

test("a good snapshot prints one line per subject and the parity line, exit 0", async () => {
  const snap = await snapshotOf([ev(1), ev(2, { value: 0 })]);
  const r = await run(ok(snap));
  assert.equal(r.code, 0);
  assert.ok(r.out[0].startsWith("estate-live-state.v1 seq=2"));
  assert.ok(r.out.includes("optimus:m2  DIRECT  0"), "a real 0 is printed as 0");
  assert.equal(r.out.at(-1), `parity  seq=2  hash=${snap.hash}`);
  assert.deepEqual(r.err, []);
});

test("a BLIND subject prints the word BLIND and its reason, never a number", async () => {
  const snap = await snapshotOf([ev(1, { status: "BLIND", value: undefined, reason: "metric command missing" })]);
  const r = await run(ok(snap));
  assert.equal(r.code, 0);
  assert.ok(r.out.includes("optimus:m1  BLIND  (metric command missing)"));
  assert.ok(!r.out.some((l) => /optimus:m1\s+(DIRECT|0)/.test(l)));
});

test("a hash this reader cannot reproduce is a failure and prints no state", async () => {
  const snap = await snapshotOf([ev(1)]);
  const r = await run(ok({ ...snap, hash: "0".repeat(64) }));
  assert.equal(r.code, 1);
  assert.deepEqual(r.out, []);
  assert.match(r.err[0], /not what this reader computes/);
});

test("a tampered value fails the hash even when the server's hash is left alone", async () => {
  const snap = await snapshotOf([ev(1, { value: 7 })]);
  snap.subjects["optimus:m1"] = { ...snap.subjects["optimus:m1"], value: 8 };
  assert.equal((await run(ok(snap))).code, 1);
});

test("no token is BLIND (exit 2): nothing is fetched and no state is printed", async () => {
  let calls = 0;
  for (const token of [undefined, ""]) {
    const r = await run(async () => { calls++; return { ok: true }; }, token);
    assert.equal(r.code, 2);
    assert.ok(r.out[0].startsWith("BLIND"));
    assert.ok(!r.out.some((l) => l.startsWith("parity")));
  }
  assert.equal(calls, 0);
});

test("refusal, unreachable, and malformed answers are failures, and the token is never printed", async () => {
  const cases = [
    [async () => ({ ok: false, status: 401, json: async () => ({}) }), /HTTP 401/],
    [async () => { throw new Error("connect refused"); }, /unreachable: connect refused/],
    [async () => ({ ok: true, status: 200, json: async () => { throw new Error("bad"); } }), /not JSON/],
    [ok({ schema: "other" }), /not estate-live-state\.v1/],
    [ok(null), /not estate-live-state\.v1/],
    [ok({ schema: "estate-live-state.v1", hash: "h", subjects: {} }), /missing hash, subjects or blind/],
  ];
  for (const [c, why] of cases) {
    const r = await run(c, "SECRET-TOKEN");
    assert.equal(r.code, 1);
    assert.match(r.err[0], why);
    assert.ok(![...r.out, ...r.err].join("\n").includes("SECRET-TOKEN"));
  }
});

test("a snapshot that shows a silent producer as live is a failure", async () => {
  const snap = await snapshotOf([ev(1)]);
  snap.subjects["optimus:m1"].ts = NOW - 10 * 900 * 1000;
  snap.hash = await snapshotHash(snap);
  const r = await run(ok(snap));
  assert.equal(r.code, 1);
  assert.match(r.err[0], /silent past its interval/);
});

test("the CLI is BLIND with no token, exit 2, and says so", () => {
  const script = fileURLToPath(new URL("../scripts/watch.mjs", import.meta.url));
  const env = { PATH: process.env.PATH, LIVE_STATE_URL: "http://127.0.0.1:9" };
  const r = spawnSync(process.execPath, [script], { env, encoding: "utf8" });
  assert.equal(r.status, 2);
  assert.match(r.stdout, /^BLIND/);
});
