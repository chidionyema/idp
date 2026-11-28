import test from "node:test";
import assert from "node:assert/strict";
import { board, TELEGRAM_LIMIT } from "../scripts/board-lib.mjs";
import { fold, snapshotHash, render } from "../src/fold.mjs";

const NOW = 1_800_000_000_000;
const ev = (seq, over = {}) => ({ seq, source: "sweep", kind: "optimus", subject: `m${seq}`, status: "DIRECT", value: seq, ts: NOW - 1000, ...over });
async function snapshotOf(events) {
  const snap = fold(events, NOW);
  return { ...snap, hash: await snapshotHash(snap) };
}
const ok = (body) => async () => ({ ok: true, status: 200, json: async () => body });
const run = (fetchImpl, token = "t") => board({ base: "https://w.test", token, fetchImpl, now: () => NOW });

test("a good read is the terminal's lines, whole, ending in the parity line", async () => {
  const snap = await snapshotOf([ev(1), ev(2, { value: 0 })]);
  const r = await run(ok(snap));
  assert.equal(r.code, 0);
  const lines = r.text.split("\n");
  assert.ok(lines[0].startsWith("estate-live-state.v1 seq=2"));
  assert.ok(lines.includes("optimus:m2  DIRECT  0"), "a real 0 stays 0");
  assert.equal(lines.at(-1), `parity  seq=2  hash=${snap.hash}`);
  assert.equal(r.cut, 0);
  assert.ok(!r.text.includes("TRUNCATED"));
});

test("a BLIND subject is the word BLIND on the card", async () => {
  const snap = await snapshotOf([ev(1, { status: "BLIND", value: undefined, reason: "no producer" })]);
  const r = await run(ok(snap));
  assert.ok(r.text.includes("optimus:m1  BLIND  (no producer)"));
});

test("an unreachable feed edits the card to BLIND, it does not keep the last good numbers", async () => {
  const r = await run(async () => { throw new Error("down"); });
  assert.equal(r.code, 1);
  assert.ok(r.text.startsWith("BLIND  estate-live-state\n"));
  assert.ok(r.text.includes("unreachable: down"));
  assert.ok(!r.text.includes("parity"), "no parity line is printed for a read that did not happen");
  assert.deepEqual([r.lines, r.cut], [0, 0]);
});

test("no read token is BLIND with code 2", async () => {
  const r = await run(ok({}), "");
  assert.equal(r.code, 2);
  assert.ok(r.text.startsWith("BLIND  estate-live-state\n"));
  assert.ok(r.text.includes("LIVE_STATE_READ_TOKEN is not set"));
});

test("a hash the reader cannot reproduce is BLIND, never a card of unverified numbers", async () => {
  const snap = await snapshotOf([ev(1)]);
  const r = await run(ok({ ...snap, hash: "0".repeat(64) }));
  assert.equal(r.code, 1);
  assert.ok(r.text.startsWith("BLIND  estate-live-state\n"));
  assert.ok(!r.text.includes("optimus:m1"));
});

test("too many subjects: the card fits Telegram, says how many it cut, and keeps the parity line", async () => {
  const events = Array.from({ length: 400 }, (_, i) => ev(i + 1, { subject: `metric-with-a-long-name-${i}` }));
  const snap = await snapshotOf(events);
  const r = await run(ok(snap));
  assert.equal(r.code, 0);
  assert.equal(TELEGRAM_LIMIT, 4096, "Telegram's own cap, not a number this file may drift on");
  assert.ok(r.text.length <= TELEGRAM_LIMIT, `${r.text.length} chars`);
  assert.ok(r.cut > 0 && r.lines + r.cut === 400, "every subject is shown or counted");
  // independent oracle: the card with one more subject must not fit, so nothing was cut early
  const all = render(snap, snap.hash).split("\n");
  const withMore = (n) => [all[0], ...all.slice(1, 1 + n), `TRUNCATED  ${400 - n} more subject(s) not shown; the parity line below is complete`, `parity  seq=400  hash=${snap.hash}`].join("\n");
  assert.ok(withMore(r.lines).length <= TELEGRAM_LIMIT && withMore(r.lines + 1).length > TELEGRAM_LIMIT, "cut exactly where the next subject would overflow");
  const lines = r.text.split("\n");
  assert.equal(lines.at(-1), `parity  seq=400  hash=${snap.hash}`);
  assert.equal(lines.at(-2), `TRUNCATED  ${r.cut} more subject(s) not shown; the parity line below is complete`);
});

test("the card is cut at the limit's edge, not before it", async () => {
  const snap = await snapshotOf(Array.from({ length: 60 }, (_, i) => ev(i + 1, { subject: `s${i}` })));
  const full = await run(ok(snap));
  assert.equal(full.cut, 0, "60 short subjects fit whole");
  assert.ok(full.text.length < TELEGRAM_LIMIT);
});

test("a huge error message still fits the card", async () => {
  const r = await run(async () => { throw new Error("x".repeat(10_000)); });
  assert.equal(r.code, 1);
  assert.equal(r.text.length, TELEGRAM_LIMIT, "cut at the limit, exactly");
});

// The boundary, measured: build a full card of exactly 4095, 4096 and 4097 characters.
async function cardOfLength(target) {
  const mk = (pad) => Array.from({ length: 40 }, (_, i) => ev(i + 1, { subject: `s${i}`, value: i === 39 ? "x".repeat(pad) : "v" }));
  const base = await run(ok(await snapshotOf(mk(0))));
  assert.equal(base.cut, 0);
  const pad = target - base.text.length;
  assert.ok(pad > 0, "the base card is shorter than the target");
  const snap = await snapshotOf(mk(pad));
  return { snap, r: await run(ok(snap)) };
}

test("a card of exactly the limit is shown whole; one character over is cut, one under is whole", async () => {
  const under = await cardOfLength(TELEGRAM_LIMIT - 1);
  assert.equal(under.r.text.length, TELEGRAM_LIMIT - 1);
  assert.equal(under.r.cut, 0);
  const exact = await cardOfLength(TELEGRAM_LIMIT);
  assert.equal(exact.r.text.length, TELEGRAM_LIMIT);
  assert.equal(exact.r.cut, 0, "4096 characters fit Telegram's 4096");
  const over = await cardOfLength(TELEGRAM_LIMIT + 1);
  assert.ok(over.r.cut >= 1, "4097 does not fit");
  assert.ok(over.r.text.length <= TELEGRAM_LIMIT);
});
