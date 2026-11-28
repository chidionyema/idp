// Exact-behaviour tests for the fold. Written against a mutation report (Stryker 8.7.1): every
// assertion here exists because a mutated copy of fold.mjs survived without it.
import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import {
  SCHEMA, STATUSES, DEFAULT_INTERVAL_S, STALE_FACTOR, FUTURE_SKEW_MS,
  eventProblem, keyOf, fold, canonical, snapshotHash, render, findCoercions, findStale, parity,
} from "../src/fold.mjs";

const NOW = 1_000_000_000;
const base = { source: "s", kind: "k", subject: "x", ts: 1000, status: "DIRECT", value: 1 };
const ev = (seq, over = {}) => ({ seq, ...base, ts: NOW - 1000, ...over });

test("constants are exactly the contract", () => {
  assert.equal(SCHEMA, "estate-live-state.v1");
  assert.deepEqual([...STATUSES], ["DIRECT", "ALLOCATED", "ESTIMATED", "BLIND"]);
  assert.ok(Object.isFrozen(STATUSES));
  assert.equal(DEFAULT_INTERVAL_S, 900);
  assert.equal(STALE_FACTOR, 2);
  assert.equal(FUTURE_SKEW_MS, 60_000);
  assert.equal(keyOf({ kind: "a", subject: "b" }), "a:b");
});

test("eventProblem: every guard fires alone, with its exact reason", () => {
  const cases = [
    [null, "not an object"], ["str", "not an object"], [5, "not an object"], [[], "not an object"], [undefined, "not an object"],
    [{ ...base, source: "" }, "source missing"], [{ ...base, source: 5 }, "source missing"], [{ ...base, source: undefined }, "source missing"],
    [{ ...base, kind: "" }, "kind missing"], [{ ...base, kind: 5 }, "kind missing"],
    [{ ...base, subject: "" }, "subject missing"], [{ ...base, subject: null }, "subject missing"],
    [{ ...base, ts: undefined }, "ts missing"], [{ ...base, ts: NaN }, "ts missing"], [{ ...base, ts: Infinity }, "ts missing"], [{ ...base, ts: "1" }, "ts missing"],
    [{ ...base, status: "NOPE" }, "status unknown"], [{ ...base, status: undefined }, "status unknown"],
    [{ ...base, interval_s: 0 }, "interval_s invalid"], [{ ...base, interval_s: -1 }, "interval_s invalid"], [{ ...base, interval_s: NaN }, "interval_s invalid"],
    [{ ...base, interval_s: Infinity }, "interval_s invalid"], [{ ...base, interval_s: "5" }, "interval_s invalid"], [{ ...base, interval_s: null }, "interval_s invalid"],
    [{ ...base, status: "BLIND", value: undefined }, "BLIND without a reason"], [{ ...base, status: "BLIND", value: undefined, reason: "" }, "BLIND without a reason"],
    [{ ...base, status: "BLIND", value: undefined, reason: 5 }, "BLIND without a reason"],
    [{ ...base, status: "BLIND", reason: "r", value: 0 }, "BLIND carries a value"], [{ ...base, status: "BLIND", reason: "r", value: false }, "BLIND carries a value"],
    [{ ...base, status: "BLIND", reason: "r", value: "" }, "BLIND carries a value"],
    [{ ...base, value: undefined }, "value missing"], [{ ...base, value: null }, "value missing"], [{ ...base, status: "ESTIMATED", value: null }, "value missing"],
    [{ ...base, value: NaN }, "value not finite"], [{ ...base, value: Infinity }, "value not finite"], [{ ...base, value: -Infinity }, "value not finite"],
  ];
  for (const [input, want] of cases) assert.equal(eventProblem(input), want, JSON.stringify(input));
});

test("eventProblem: valid events pass, and 0, false and '' are data", () => {
  for (const status of ["DIRECT", "ALLOCATED", "ESTIMATED"]) assert.equal(eventProblem({ ...base, status }), null, status);
  for (const value of [0, false, "", -1, 1.5, [], {}, "text"]) assert.equal(eventProblem({ ...base, value }), null, JSON.stringify(value));
  assert.equal(eventProblem({ ...base, interval_s: 1 }), null);
  assert.equal(eventProblem({ ...base, interval_s: 0.001 }), null);
  assert.equal(eventProblem({ ...base, status: "BLIND", value: undefined, reason: "r" }), null);
  assert.equal(eventProblem({ ...base, status: "BLIND", value: null, reason: "r" }), null);
});

test("eventProblem: the first failing guard names the problem", () => {
  const bad = { source: "", kind: "", subject: "", ts: NaN, status: "NOPE", interval_s: -1 };
  assert.equal(eventProblem(bad), "source missing");
  assert.equal(eventProblem({ ...bad, source: "s" }), "kind missing");
  assert.equal(eventProblem({ ...bad, source: "s", kind: "k" }), "subject missing");
  assert.equal(eventProblem({ ...bad, source: "s", kind: "k", subject: "x" }), "ts missing");
  assert.equal(eventProblem({ ...bad, source: "s", kind: "k", subject: "x", ts: 1 }), "status unknown");
  assert.equal(eventProblem({ ...bad, source: "s", kind: "k", subject: "x", ts: 1, status: "BLIND", value: 1 }), "interval_s invalid");
  assert.equal(eventProblem({ ...base, status: "BLIND", value: 1 }), "BLIND without a reason");
});

test("fold: a live event becomes exactly this subject", () => {
  const snap = fold([ev(1, { value: 5, evidence: { url: "u" } })], NOW);
  assert.deepEqual(snap, {
    schema: "estate-live-state.v1", seq: 1, as_of: NOW, blind: [], rejected: [],
    subjects: { "k:x": { status: "DIRECT", value: 5, source: "s", ts: NOW - 1000, seq: 1, interval_s: 900, evidence: { url: "u" } } },
  });
  const s = fold([ev(1, { interval_s: 60 })], NOW).subjects["k:x"];
  assert.equal(s.interval_s, 60);
  assert.equal(s.evidence, null);
});

test("fold: not a list folds to an empty snapshot at seq 0", () => {
  for (const input of [null, undefined, "x", 5, {}]) {
    assert.deepEqual(fold(input, NOW), { schema: "estate-live-state.v1", seq: 0, as_of: NOW, subjects: {}, blind: [], rejected: [] });
  }
});

test("fold: a bad seq is rejected by name and costs only that event", () => {
  const snap = fold([null, {}, { seq: 0 }, { seq: 1.5 }, { seq: "1" }, { seq: -1 }, ev(1)], NOW);
  assert.deepEqual(snap.rejected, [
    { seq: null, reason: "seq invalid" }, { seq: null, reason: "seq invalid" }, { seq: 0, reason: "seq invalid" },
    { seq: 1.5, reason: "seq invalid" }, { seq: "1", reason: "seq invalid" }, { seq: -1, reason: "seq invalid" },
  ]);
  assert.equal(snap.subjects["k:x"].status, "DIRECT");
  assert.equal(snap.seq, 1);
});

test("fold: an event that names no subject is rejected, and still moves the head", () => {
  const snap = fold([ev(1), { seq: 2, source: "s" }, { seq: 3, kind: "k" }, { seq: 4, kind: "", subject: "x" }, { seq: 5, kind: "k", subject: "" }], NOW);
  assert.deepEqual(snap.rejected, [2, 3, 4, 5].map((seq) => ({ seq, reason: "kind or subject missing" })));
  assert.equal(snap.seq, 5);
  assert.deepEqual(Object.keys(snap.subjects), ["k:x"]);
});

test("fold: a repeated seq is rejected once per repeat, first copy wins", () => {
  const snap = fold([ev(1, { value: 1 }), ev(1, { value: 2 }), ev(1, { value: 3 })], NOW);
  assert.deepEqual(snap.rejected, [{ seq: 1, reason: "seq repeated" }, { seq: 1, reason: "seq repeated" }]);
  assert.equal(snap.subjects["k:x"].value, 1);
});

test("fold: the highest seq wins per key whatever order the log arrives in", () => {
  const snap = fold([ev(3, { value: "c" }), ev(1, { value: "a" }), ev(2, { value: "b" }), ev(9, { subject: "y", value: "y" })], NOW);
  assert.equal(snap.subjects["k:x"].value, "c");
  assert.equal(snap.subjects["k:x"].seq, 3);
  assert.equal(snap.seq, 9);
});

test("fold: a malformed event with a subject becomes BLIND with every field it could keep", () => {
  assert.deepEqual(fold([{ seq: 1, kind: "k", subject: "x" }], NOW).subjects["k:x"], {
    status: "BLIND", value: null, reason: "malformed: source missing", source: null, ts: null, seq: 1, interval_s: 900, evidence: null,
  });
  assert.deepEqual(fold([{ seq: 2, kind: "k", subject: "x", source: "s", ts: 5, interval_s: 30, evidence: { a: 1 }, status: "DIRECT" }], NOW).subjects["k:x"], {
    status: "BLIND", value: null, reason: "malformed: value missing", source: "s", ts: 5, seq: 2, interval_s: 30, evidence: { a: 1 },
  });
  for (const interval_s of [0, -5, "x", undefined]) {
    assert.equal(fold([{ seq: 1, kind: "k", subject: "x", interval_s }], NOW).subjects["k:x"].interval_s, 900, String(interval_s));
  }
  for (const ts of [NaN, Infinity, "5", undefined]) {
    assert.equal(fold([{ seq: 1, kind: "k", subject: "x", ts }], NOW).subjects["k:x"].ts, null, String(ts));
  }
  assert.equal(fold([{ seq: 1, kind: "k", subject: "x", source: "" }], NOW).subjects["k:x"].source, null);
});

test("fold: a declared BLIND keeps its reason, and blind keys come back sorted", () => {
  const snap = fold([ev(1, { subject: "b", status: "BLIND", value: undefined, reason: "down" }), ev(2, { subject: "a", status: "BLIND", value: null, reason: "gone" }), ev(3, { subject: "c" })], NOW);
  assert.equal(snap.subjects["k:b"].reason, "down");
  assert.equal(snap.subjects["k:a"].value, null);
  assert.deepEqual(snap.blind, ["k:a", "k:b"]);
});

test("fold: stale at exactly twice the interval is live, one millisecond more is BLIND", () => {
  const edge = fold([ev(1, { ts: NOW - 120_000, interval_s: 60 })], NOW).subjects["k:x"];
  assert.equal(edge.status, "DIRECT");
  const past = fold([ev(1, { ts: NOW - 120_001, interval_s: 60, value: 7 })], NOW).subjects["k:x"];
  assert.deepEqual(past, {
    status: "BLIND", value: null, source: "s", ts: NOW - 120_001, seq: 1, interval_s: 60, evidence: null,
    last_seen_ts: NOW - 120_001, reason: "stale: 120s old, interval 60s",
  });
});

test("fold: a timestamp more than 60s ahead is BLIND future-ts, 60s exactly is live", () => {
  assert.equal(fold([ev(1, { ts: NOW + 60_000 })], NOW).subjects["k:x"].status, "DIRECT");
  const future = fold([ev(1, { ts: NOW + 60_001 })], NOW).subjects["k:x"];
  assert.equal(future.status, "BLIND");
  assert.equal(future.reason, "future-ts");
  assert.equal(future.value, null);
  assert.equal(future.last_seen_ts, NOW + 60_001);
});

test("fold: the default interval decides staleness when none is declared", () => {
  assert.equal(fold([ev(1, { ts: NOW - 1_800_000 })], NOW).subjects["k:x"].status, "DIRECT");
  assert.equal(fold([ev(1, { ts: NOW - 1_800_001 })], NOW).subjects["k:x"].status, "BLIND");
});

test("canonical: sorted keys at every depth, undefined is null", () => {
  assert.equal(canonical(null), "null");
  assert.equal(canonical(undefined), "null");
  assert.equal(canonical(true), "true");
  assert.equal(canonical(1), "1");
  assert.equal(canonical("a"), '"a"');
  assert.equal(canonical([1, "a", null]), '[1,"a",null]');
  assert.equal(canonical({ b: 1, a: { d: 2, c: [3, { z: 1, y: 2 }] } }), '{"a":{"c":[3,{"y":2,"z":1}],"d":2},"b":1}');
  assert.equal(canonical({ a: undefined }), '{"a":null}');
  assert.equal(canonical({}), "{}");
  assert.equal(canonical([]), "[]");
});

test("snapshotHash matches an independent sha256 and ignores as_of and rejected", async () => {
  for (let seq = 0; seq < 40; seq++) {
    const snap = { schema: SCHEMA, seq, subjects: { "k:x": { v: seq } }, as_of: seq * 7, rejected: [{ seq }] };
    const want = createHash("sha256").update(`{"schema":"estate-live-state.v1","seq":${seq},"subjects":{"k:x":{"v":${seq}}}}`).digest("hex");
    assert.equal(await snapshotHash(snap), want);
  }
  const a = fold([ev(1)], NOW);
  const b = { ...fold([ev(1)], NOW + 5), as_of: 0, rejected: [{ seq: 9, reason: "x" }] };
  assert.equal(await snapshotHash(a), await snapshotHash(b));
  assert.notEqual(await snapshotHash(a), await snapshotHash(fold([ev(1, { value: 2 })], NOW)));
  assert.notEqual(await snapshotHash(a), await snapshotHash({ ...a, seq: 2 }));
});

test("render: exact lines, BLIND never prints a number", () => {
  const snap = fold([ev(1, { subject: "b", value: "ok" }), ev(2, { subject: "a", value: 0 }), ev(3, { subject: "c", status: "BLIND", value: null, reason: "down" }), ev(4, { subject: "d", status: "ESTIMATED", value: { n: 1 } })], NOW);
  assert.equal(render(snap, "abcdef0123456789ZZZ"), [
    "estate-live-state.v1 seq=4 hash=abcdef0123456789 blind=1",
    "k:a  DIRECT  0", "k:b  DIRECT  ok", "k:c  BLIND  (down)", 'k:d  ESTIMATED  {"n":1}',
  ].join("\n"));
  assert.match(render(snap, undefined), /hash=undefined /);
});

test("findCoercions: each violation is reported by name, clean is empty", () => {
  const live = { status: "DIRECT", value: 1 };
  const blindEv = ev(1, { status: "BLIND", value: undefined, reason: "r" });
  assert.deepEqual(findCoercions([ev(1)], { subjects: { "k:x": live } }), []);
  assert.deepEqual(findCoercions([ev(1)], { subjects: {} }), ["k:x: present in the log, absent from the snapshot"]);
  assert.deepEqual(findCoercions([ev(1, { value: undefined })], { subjects: { "k:x": live } }), ["k:x: malformed event shown as DIRECT"]);
  assert.deepEqual(findCoercions([blindEv], { subjects: { "k:x": live } }), ["k:x: BLIND event shown as DIRECT"]);
  assert.deepEqual(findCoercions([blindEv], { subjects: { "k:x": { status: "BLIND", value: 0 } } }), ["k:x: BLIND carries value 0"]);
  assert.deepEqual(findCoercions([blindEv], { subjects: { "k:x": { status: "BLIND", value: null } } }), []);
  assert.deepEqual(findCoercions([], { subjects: { "k:x": { status: "ESTIMATED", value: null } } }), ["k:x: ESTIMATED with no value"]);
  assert.deepEqual(findCoercions([], { subjects: { "k:x": { status: "DIRECT" } } }), ["k:x: DIRECT with no value"]);
  assert.deepEqual(findCoercions([], { subjects: { "k:x": { status: "DIRECT", value: 0 } } }), []);
  assert.deepEqual(findCoercions([], { subjects: { "k:x": { status: "BLIND", value: null } } }), []);
});

test("findCoercions: judges the latest event per key, whatever the order", () => {
  const good = ev(2);
  const bad = ev(1, { value: undefined });
  const snap = { subjects: { "k:x": { status: "DIRECT", value: 1 } } };
  assert.deepEqual(findCoercions([good, bad], snap), []);
  assert.deepEqual(findCoercions([bad, good], snap), []);
  assert.deepEqual(findCoercions([ev(3, { value: undefined }), ev(2)], snap), ["k:x: malformed event shown as DIRECT"]);
  assert.deepEqual(findCoercions([{ kind: "k" }, { seq: "1", kind: "k", subject: "z" }, null, 5], { subjects: {} }), []);
});

test("findStale: boundary and exact message", () => {
  const at = (age, extra = {}) => ({ subjects: { "k:x": { status: "DIRECT", ts: NOW - age, interval_s: 60, ...extra } } });
  assert.deepEqual(findStale(at(120_000), NOW), []);
  assert.deepEqual(findStale(at(120_001), NOW), ["k:x: DIRECT but 120s old, interval 60s"]);
  assert.deepEqual(findStale(at(500_000, { status: "BLIND" }), NOW), []);
  assert.deepEqual(findStale({ subjects: {} }, NOW), []);
});

test("parity: exact messages, one per disagreement", () => {
  const a = { name: "a", seq: 1, hash: "aaaaaaaaaaaaXXXX" };
  assert.deepEqual(parity([a, { ...a, name: "b" }]), []);
  assert.deepEqual(parity([a]), []);
  assert.deepEqual(parity([a, { name: "b", seq: 2, hash: "bbbbbbbbbbbbYYYY" }]), ["b: seq 2 != a seq 1", "b: hash bbbbbbbbbbbb != a hash aaaaaaaaaaaa"]);
  assert.deepEqual(parity([a, { ...a, name: "b", seq: 2 }]), ["b: seq 2 != a seq 1"]);
  assert.deepEqual(parity([a, { ...a, name: "b", hash: "cccccccccccc" }]), ["b: hash cccccccccccc != a hash aaaaaaaaaaaa"]);
  assert.equal(parity([a, { ...a, name: "b", seq: 2 }, { ...a, name: "c", hash: "z" }]).length, 2);
});
