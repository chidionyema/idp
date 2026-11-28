import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { BATCH, eventFor, metricsOf, parseMeasure, post, runMeasure, sweep, tally } from "../scripts/sweep-lib.mjs";

const M = (name, over = {}) => ({ name, measure: ["x", name], unit: "files", better: "lower", owner: "o", ...over });
const res = (over = {}) => ({ code: 0, stdout: "", stderr: "", timedOut: false, ms: 5, ...over });
const script = fileURLToPath(new URL("../scripts/sweep.mjs", import.meta.url));

test("parseMeasure takes exactly one optimus.<name>=<number> line, and a real 0 is 0", () => {
  assert.equal(parseMeasure("a.b", "optimus.a.b=3\n"), 3);
  assert.equal(parseMeasure("a.b", "noise\noptimus.a.b=0\nmore"), 0);
  assert.equal(parseMeasure("a.b", "optimus.a.b=-2.5"), -2.5);
  assert.equal(parseMeasure("a.b", "optimus.a.b=3\r\n"), 3);
  for (const bad of ["", "optimus.a.b=", "optimus.a.b=abc", "optimus.a.b=1\noptimus.a.b=2", "optimus.a.c=1", "xoptimus.a.b=1", "optimus.a.b=1x", " optimus.a.b=1", "optimus.aXb=1"]) {
    assert.equal(parseMeasure("a.b", bad), null, JSON.stringify(bad));
  }
});

test("eventFor: a number on a zero exit is DIRECT, anything else is BLIND with its reason, never 0", () => {
  const e = eventFor(M("m"), res({ stdout: "optimus.m=0\n" }), 1000, 3600);
  assert.deepEqual(e, { source: "optimus-sweep", kind: "optimus", subject: "m", ts: 1000, interval_s: 3600, status: "DIRECT", value: 0, evidence: { unit: "files", better: "lower", owner: "o", exit: 0, ms: 5 } });
  const cases = [
    [res({ code: 1, stderr: "BLIND: cannot join landing\nmore" }), "BLIND: cannot join landing"],
    [res({ code: 3 }), "exit 3"],
    [res({ code: 1, stdout: "\n  from stdout\n" }), "from stdout"],
    [res({ timedOut: true, code: 1 }), "timeout after 40s"],
    [res({ stdout: "nothing here" }), "no single optimus.m=<number> line on stdout"],
    [res({ stdout: "optimus.other=1" }), "no single optimus.m=<number> line on stdout"],
    [res({ code: 1, stdout: "optimus.m=5" }), "exit 1"],
  ];
  for (const [r, why] of cases) {
    const b = eventFor(M("m"), r, 1000, 60);
    assert.equal(b.status, "BLIND", why);
    assert.equal(b.reason, why);
    assert.equal("value" in b, false);
    assert.equal(b.interval_s, 60);
  }
  assert.equal(eventFor(M("m"), res({ code: 1, stderr: "x".repeat(500) }), 1, 1).reason.length, 200);
  assert.equal(eventFor(M("m"), res({ code: 1, stderr: "x".repeat(200) }), 1, 1).reason.length, 200, "200 is kept whole");
});

test("sweep keeps catalogue order, bounds concurrency, and a runner that throws is BLIND", async () => {
  const metrics = ["a", "b", "c", "d", "e"].map((n) => M(n));
  let live = 0;
  let peak = 0;
  const run = async (argv) => {
    live++;
    peak = Math.max(peak, live);
    await new Promise((r) => setTimeout(r, argv[1] === "a" ? 30 : 1));
    live--;
    if (argv[1] === "c") throw new Error("spawn ENOENT");
    return res({ stdout: `optimus.${argv[1]}=1\n` });
  };
  const ev = await sweep({ metrics, run, now: () => 7, concurrency: 2 });
  assert.deepEqual(ev.map((e) => e.subject), ["a", "b", "c", "d", "e"]);
  assert.ok(peak <= 2 && peak === 2, `peak ${peak}`);
  assert.equal(ev[2].status, "BLIND");
  assert.equal(ev[2].reason, "could not run: spawn ENOENT");
  assert.deepEqual(ev.filter((e) => e.status === "DIRECT").map((e) => e.subject), ["a", "b", "d", "e"]);
  assert.equal(tally(ev), "sweep  metrics=5  direct=4  blind=1");
  assert.equal((await sweep({ metrics: [M("z")], run: async () => res({ stdout: "optimus.z=2" }), now: () => 1 })).length, 1, "one metric still runs");
});

test("metricsOf refuses a catalogue it cannot trust, and reads the real one", () => {
  for (const bad of [null, {}, { metrics: [] }, { metrics: "x" }, { metrics: [{ name: "a" }] }, { metrics: [{ name: "a", measure: [] }] }, { metrics: [{ name: "a", measure: [1] }] }, { metrics: [{ measure: ["x"] }] }, { metrics: [M("a"), M("a")] }]) {
    assert.throws(() => metricsOf(bad), /catalogue|measure argv|twice/, JSON.stringify(bad));
  }
  assert.equal(metricsOf({ metrics: [M("a")] }).length, 1);
  const real = JSON.parse(readFileSync(new URL("../../../catalog/optimus-metrics.json", import.meta.url), "utf8"));
  assert.equal(metricsOf(real).length, real.metrics.length);
  assert.ok(real.metrics.length > 0);
});

test("runMeasure runs a real child, strips the live-state tokens, and reports a timeout", async () => {
  const ok = await runMeasure([process.execPath, "-e", "console.log('optimus.t=' + (process.env.LIVE_STATE_INGEST_TOKEN === undefined ? 1 : 0))"], { env: { ...process.env, LIVE_STATE_INGEST_TOKEN: "SECRET", LIVE_STATE_READ_TOKEN: "SECRET2" } });
  assert.equal(ok.code, 0);
  assert.equal(parseMeasure("t", ok.stdout), 1, "the child never saw the ingest token");
  const failed = await runMeasure([process.execPath, "-e", "console.error('BLIND: nope'); process.exit(4)"], {});
  assert.equal(failed.code, 4);
  assert.match(failed.stderr, /BLIND: nope/);
  assert.equal(failed.timedOut, false);
  const slow = await runMeasure([process.execPath, "-e", "setInterval(() => {}, 1000)"], { timeoutMs: 300 });
  assert.equal(slow.timedOut, true);
  assert.notEqual(slow.code, 0);
  const missing = await runMeasure(["/no/such/binary"], {});
  assert.notEqual(missing.code, 0);
  assert.equal(missing.timedOut, false);
});

const evs = (n) => Array.from({ length: n }, (_, i) => eventFor(M(`m${i}`), res({ stdout: `optimus.m${i}=${i}` }), 1, 60));

test("post sends batches of 100 with the bearer token, and stops at the first refusal", async () => {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init, n: JSON.parse(init.body).length });
    return { ok: true, status: 200, json: async () => ({ accepted: JSON.parse(init.body).length, seq: calls.length * 100 }) };
  };
  const r = await post({ base: "https://w.test", token: "T", events: evs(250), fetchImpl });
  assert.equal(BATCH, 100);
  assert.deepEqual(calls.map((c) => c.n), [100, 100, 50]);
  assert.ok(calls.every((c) => c.url === "https://w.test/append" && c.init.method === "POST" && c.init.headers.authorization === "Bearer T"));
  assert.equal(r.code, 0);
  assert.equal(r.out.at(-1), "ok  /append  accepted=250/250  seq=300");
  assert.equal((await post({ base: "b", token: "T", events: evs(100), fetchImpl })).out.length, 1, "exactly 100 is one batch");

  let n = 0;
  const refuseSecond = async () => (++n === 2 ? { ok: false, status: 422 } : { ok: true, status: 200, json: async () => ({ accepted: 100, seq: 1 }) });
  const stopped = await post({ base: "b", token: "T", events: evs(250), fetchImpl: refuseSecond });
  assert.equal(stopped.code, 1);
  assert.equal(n, 2, "nothing is sent after a refusal");
  assert.match(stopped.err[0], /HTTP 422 after 100 of 250/);
});

test("post fails on a short accept, an unreadable body or an unreachable worker, and never prints the token", async () => {
  const cases = [
    [async () => ({ ok: true, status: 200, json: async () => ({ accepted: 3 }) }), /accepted 3 of 5/],
    [async () => ({ ok: true, status: 200, json: async () => { throw new Error("x"); } }), /accepted \? of 5/],
    [async () => { throw new Error("refused"); }, /unreachable: refused/],
  ];
  for (const [fetchImpl, why] of cases) {
    const r = await post({ base: "b", token: "SECRET-TOKEN", events: evs(5), fetchImpl });
    assert.equal(r.code, 1);
    assert.match(r.err[0], why);
    assert.ok(![...r.out, ...r.err].join("\n").includes("SECRET-TOKEN"));
  }
});

test("post with no ingest token is BLIND (exit 2) and sends nothing", async () => {
  let calls = 0;
  for (const token of [undefined, ""]) {
    const r = await post({ base: "b", token, events: evs(3), fetchImpl: async () => { calls++; } });
    assert.equal(r.code, 2);
    assert.match(r.out[0], /^BLIND {2}not posted .* 3 events were measured and sent nowhere$/);
  }
  assert.equal(calls, 0);
});

test("the CLI: --dry-run measures and prints, a bad catalogue exits 1, no token exits 2", () => {
  const dir = mkdtempSync(join(tmpdir(), "sweep-"));
  const cat = join(dir, "c.json");
  const good = { metrics: [{ name: "t.seven", measure: [process.execPath, "-e", "console.log('optimus.t.seven=7')"], unit: "n", better: "lower", owner: "o" }, { name: "t.broken", measure: [process.execPath, "-e", "console.error('BLIND: no data'); process.exit(1)"], unit: "n", better: "lower", owner: "o" }] };
  writeFileSync(cat, JSON.stringify(good));
  const env = { PATH: process.env.PATH, LIVE_STATE_URL: "http://127.0.0.1:9" };
  const run = (...a) => spawnSync(process.execPath, [script, ...a], { env, encoding: "utf8", cwd: dir });
  const dry = run("--dry-run", "--catalog", cat);
  assert.equal(dry.status, 0);
  assert.match(dry.stdout, /^sweep {2}metrics=2 {2}direct=1 {2}blind=1$/m);
  assert.match(dry.stdout, /^t\.seven {2}DIRECT {2}7$/m);
  assert.match(dry.stdout, /^t\.broken {2}BLIND {2}\(BLIND: no data\)$/m);
  const noToken = run("--catalog", cat);
  assert.equal(noToken.status, 2);
  assert.match(noToken.stdout, /^BLIND {2}not posted/m);
  writeFileSync(cat, "{");
  const bad = run("--catalog", cat);
  assert.equal(bad.status, 1);
  assert.match(bad.stderr, /^SWEEP FAIL/);
  assert.equal(run("--catalog", join(dir, "missing.json")).status, 1);
});
