// Falsifiers for the live-state fold. Each gate here ships with a known-bad fixture it must reject
// and a known-good it must accept (AGENTS.md section 9 P1): a checker that cannot fail is not a gate.
import test from "node:test";
import assert from "node:assert/strict";
import { fold, snapshotHash, render, findCoercions, findStale, parity, eventProblem } from "../src/fold.mjs";

const NOW = 1_800_000_000_000;
const ev = (seq, over = {}) => ({
  seq,
  source: "sweep",
  kind: "optimus",
  subject: `m${seq}`,
  ts: NOW - 1000,
  status: "DIRECT",
  value: 1,
  interval_s: 900,
  ...over,
});

// ---- known-bad folds: what a careless implementation does. The checkers must catch every one.
const foldCoercing = (events, now) => {
  const snap = fold(events, now);
  for (const s of Object.values(snap.subjects)) {
    if (s.status === "BLIND") {
      s.status = "DIRECT";
      s.value = 0; // BLIND coerced to zero: the founder reads a green number that was never measured
    }
  }
  return snap;
};
const foldCorrupt = (events, now) => {
  const snap = fold(events, now);
  const k = Object.keys(snap.subjects)[0];
  snap.subjects[k] = { ...snap.subjects[k], value: 999 };
  return snap;
};

test("falsifier 1: a missing value is BLIND, never 0", async () => {
  const log = [ev(1, { value: undefined }), ev(2, { value: 0 }), ev(3, { status: "BLIND", value: null, reason: "producer cannot measure" })];
  const good = fold(log, NOW);
  assert.deepEqual(findCoercions(log, good), [], "known-good must pass");
  assert.equal(good.subjects["optimus:m1"].status, "BLIND");
  assert.equal(good.subjects["optimus:m1"].value, null);
  assert.match(render(good, await snapshotHash(good)), /optimus:m1  BLIND  \(malformed: value missing\)/);
  assert.equal(good.subjects["optimus:m2"].status, "DIRECT", "0 is data, not absence");
  assert.equal(good.subjects["optimus:m2"].value, 0);
  const bad = findCoercions(log, foldCoercing(log, NOW));
  assert.ok(bad.length >= 2, `known-bad must be rejected, got ${JSON.stringify(bad)}`);
});

test("falsifier 2: two readers of one log agree on seq and hash", async () => {
  const log = [ev(1), ev(2), ev(3, { value: false })];
  const a = fold(log, NOW);
  const b = fold([...log].reverse(), NOW + 5000); // different order, later clock: same state
  const ra = { name: "terminal", seq: a.seq, hash: await snapshotHash(a) };
  const rb = { name: "telegram", seq: b.seq, hash: await snapshotHash(b) };
  assert.deepEqual(parity([ra, rb]), [], "known-good must pass");
  const c = foldCorrupt(log, NOW);
  const rc = { name: "web", seq: c.seq, hash: await snapshotHash(c) };
  assert.ok(parity([ra, rc]).length >= 1, "known-bad must be rejected");
});

test("falsifier 3: a silent producer flips to BLIND with its age", () => {
  const log = [ev(1, { ts: NOW - 200_000, interval_s: 60 }), ev(2, { ts: NOW - 10_000, interval_s: 60 })];
  const good = fold(log, NOW);
  assert.deepEqual(findStale(good, NOW), [], "known-good must pass");
  assert.equal(good.subjects["optimus:m1"].status, "BLIND");
  assert.match(good.subjects["optimus:m1"].reason, /^stale: 200s old, interval 60s$/);
  assert.equal(good.subjects["optimus:m2"].status, "DIRECT");
  const bad = findStale(fold(log, NOW - 190_000), NOW); // a fold that believes it is earlier than it is
  assert.ok(bad.length >= 1, "known-bad must be rejected");
});

test("a future timestamp is BLIND, not fresh", () => {
  const snap = fold([ev(1, { ts: NOW + 3_600_000 })], NOW);
  assert.equal(snap.subjects["optimus:m1"].reason, "future-ts");
});

test("replay is idempotent and a repeated seq is rejected and counted", async () => {
  const log = [ev(1), ev(2)];
  const once = fold(log, NOW);
  const twice = fold([...log, ...log], NOW);
  assert.equal(await snapshotHash(once), await snapshotHash(twice));
  assert.equal(twice.rejected.length, 2);
  assert.ok(twice.rejected.every((r) => r.reason === "seq repeated"));
});

test("keeping only the latest event per key equals folding the whole log", async () => {
  const log = [ev(1, { subject: "a", value: 1 }), ev(2, { subject: "b", value: 2 }), ev(3, { subject: "a", value: 3 }), ev(4, { subject: "b", status: "BLIND", value: null, reason: "down" })];
  const latest = [log[2], log[3]];
  assert.equal(await snapshotHash(fold(log, NOW)), await snapshotHash(fold(latest, NOW)));
});

test("a BLIND event with a value, or without a reason, is itself malformed", () => {
  assert.equal(eventProblem(ev(1, { status: "BLIND", value: 0, reason: "x" })), "BLIND carries a value");
  assert.equal(eventProblem(ev(1, { status: "BLIND", value: null })), "BLIND without a reason");
  assert.equal(eventProblem(ev(1, { value: NaN })), "value not finite");
});
