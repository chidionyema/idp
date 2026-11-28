import test from "node:test";
import assert from "node:assert/strict";
import vm from "node:vm";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import worker from "../src/index.mjs";
import { PAGE } from "../src/fleet-page.mjs";
import { buildPage, moduleSource, pageScript } from "../scripts/build-fleet.mjs";
import { fold, snapshotHash } from "../src/fold.mjs";
import { watch } from "../scripts/watch-lib.mjs";

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8");

test("the committed page is exactly what the builder makes from the sources the terminal runs", () => {
  const fresh = moduleSource(buildPage(read("../src/fold.mjs"), read("../scripts/watch-lib.mjs")));
  assert.equal(read("../src/fleet-page.mjs"), fresh, "run: node scripts/build-fleet.mjs");
});

test("the page carries the shared fold and read, and no second copy of their logic", () => {
  const script = pageScript(read("../src/fold.mjs"), read("../scripts/watch-lib.mjs"));
  assert.ok(script.includes("async function snapshotHash"));
  assert.ok(script.includes("async function watch"));
  assert.ok(!/^import /m.test(script) && !/^export /m.test(script));
  assert.equal(PAGE.split("</script").length, 2, "exactly one closing script tag");
});

test("/fleet serves the page with no secret, no store and a tight policy", async () => {
  const res = await worker.fetch(new Request("https://x/fleet"), {});
  assert.equal(res.status, 200);
  assert.equal(res.headers.get("content-type"), "text/html; charset=utf-8");
  assert.equal(res.headers.get("cache-control"), "no-store");
  assert.equal(
    res.headers.get("content-security-policy"),
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'",
    "the page may talk to its own origin and nothing else",
  );
  assert.equal(await res.text(), PAGE);
  const env = { LIVE_STATE: { idFromName: () => 1, get: () => ({ fetch: () => new Response("{}") }) } };
  assert.equal((await worker.fetch(new Request("https://x/fleet", { method: "POST" }), env)).status, 404, "GET only");
});

// Run the page's own script in a sandbox with a fake document and fetch.
async function runPage({ fetchImpl, token }) {
  const el = { textContent: "", className: "", listeners: {}, addEventListener(t, f) { this.listeners[t] = f; } };
  const store = new Map(token === undefined ? [] : [["t", token]]);
  const timers = [];
  const ctx = {
    document: { getElementById: () => el },
    sessionStorage: { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, v), removeItem: (k) => store.delete(k) },
    location: { origin: "https://live.test" },
    fetch: fetchImpl, AbortSignal, crypto, TextEncoder, JSON, Date, Object, Array, Math, String, Number, Error,
    setInterval: (f, ms) => timers.push(ms),
  };
  ctx.globalThis = ctx;
  const script = PAGE.match(/<script>\n([\s\S]*)\n<\/script>/)[1];
  vm.runInNewContext(script, ctx);
  await new Promise((r) => setTimeout(r, 50));
  return { el, timers, store };
}

test("a fresh snapshot renders identically in the page and the terminal", async () => {
  const now = Date.now();
  const snap = fold([{ seq: 1, source: "sweep", kind: "optimus", subject: "a", status: "DIRECT", value: 7, ts: now - 1000 }], now);
  snap.hash = await snapshotHash(snap);
  const fetchImpl = async () => ({ ok: true, status: 200, json: async () => snap });
  const terminal = await watch({ base: "https://live.test", token: "t", fetchImpl });
  assert.equal(terminal.code, 0);
  const { el, timers } = await runPage({ fetchImpl, token: "t" });
  assert.deepEqual(timers, [2000], "it re-reads every 2 seconds, inside the 5 second bound");
  assert.equal(el.className, "ok");
  assert.equal(el.textContent, terminal.out.join("\n"));
  assert.ok(el.textContent.endsWith(`parity  seq=1  hash=${snap.hash}`));
});

test("no token, or a feed that is down, shows BLIND and no numbers", async () => {
  const down = async () => { throw new Error("offline"); };
  for (const token of [undefined, "t"]) {
    const { el } = await runPage({ fetchImpl: down, token });
    assert.equal(el.className, "blind");
    assert.ok(el.textContent.startsWith("BLIND  estate-live-state"));
    assert.ok(!el.textContent.includes("parity"));
  }
  const { el } = await runPage({ fetchImpl: down, token: "t" });
  assert.ok(el.textContent.includes("unreachable: offline"), "the reason is on the card");
});

test("a good feed but no token is still BLIND: the page does not invent a token", async () => {
  const now = Date.now();
  const snap = fold([{ seq: 1, source: "sweep", kind: "optimus", subject: "a", status: "DIRECT", value: 7, ts: now - 1000 }], now);
  snap.hash = await snapshotHash(snap);
  const { el } = await runPage({ fetchImpl: async () => ({ ok: true, status: 200, json: async () => snap }), token: undefined });
  assert.equal(el.className, "blind");
  assert.ok(el.textContent.includes("LIVE_STATE_READ_TOKEN is not set"));
  assert.ok(!el.textContent.includes("optimus:a"));
});

test("typing a token keeps it for this tab, clears the field, and re-reads with it", async () => {
  const now = Date.now();
  const snap = fold([{ seq: 1, source: "sweep", kind: "optimus", subject: "a", status: "DIRECT", value: 7, ts: now - 1000 }], now);
  snap.hash = await snapshotHash(snap);
  const seen = [];
  const fetchImpl = async (url, init) => { seen.push(init.headers.authorization); return { ok: true, status: 200, json: async () => snap }; };
  const { el, store } = await runPage({ fetchImpl, token: undefined });
  const field = { value: "secret-1" };
  el.listeners.change({ target: field });
  await new Promise((r) => setTimeout(r, 50));
  assert.equal(store.get("t"), "secret-1");
  assert.equal(field.value, "", "the typed token is not left in the field");
  assert.deepEqual(seen, ["Bearer secret-1"]);
  assert.equal(el.className, "ok");
  el.listeners.change({ target: { value: "" } });
  assert.equal(store.has("t"), false, "an empty field forgets the token");
});
