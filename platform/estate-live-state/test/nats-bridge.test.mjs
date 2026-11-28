import test from "node:test";
import assert from "node:assert/strict";
import { natsMessageToLiveEvent, bridgeBatch } from "../scripts/nats-bridge-lib.mjs";
import { fold, findCoercions, snapshotHash } from "../src/fold.mjs";

const NOW = 1_795_880_000_000;

test("valid JetStream envelope bridges into a DIRECT estate-live-state.v1 event with provenance", () => {
  const ev = natsMessageToLiveEvent(
    {
      subject: "estate.fleet.presence.v1",
      seq: 119,
      data: JSON.stringify({
        id: "env-42",
        from: "carbon-antigravity",
        kind: "presence",
        subject: "carbon-antigravity",
        state: "working",
        spiffe_id: "spiffe://estate.internal/ns/agents/sa/carbon",
        ts: 1_795_879_990,
      }),
    },
    { now: () => NOW },
  );
  assert.equal(ev.status, "DIRECT");
  assert.equal(ev.source, "carbon-antigravity");
  assert.equal(ev.kind, "presence");
  assert.equal(ev.subject, "carbon-antigravity");
  assert.equal(ev.value, "working");
  assert.equal(ev.ts, 1_795_879_990_000);
  assert.equal(ev.evidence.transport, "nats-jetstream");
  assert.equal(ev.evidence.nats_seq, 119);
  assert.equal(ev.evidence.spiffe_id, "spiffe://estate.internal/ns/agents/sa/carbon");
});

test("falsifier: malformed or missing-value NATS payload becomes explicit BLIND, never 0", () => {
  const badJson = natsMessageToLiveEvent({ subject: "estate.fleet.x", seq: 7, data: "{not-json" }, { now: () => NOW });
  assert.equal(badJson.status, "BLIND");
  assert.match(badJson.reason, /not valid JSON/);
  assert.equal(badJson.value, undefined);

  const missingVal = natsMessageToLiveEvent(
    { subject: "estate.fleet.y", seq: 8, data: { from: "kimi", kind: "metric", subject: "yield" } },
    { now: () => NOW },
  );
  assert.equal(missingVal.status, "BLIND");
  assert.match(missingVal.reason, /value missing/);

  const snap = fold(
    [
      { ...badJson, seq: 1 },
      { ...missingVal, seq: 2 },
    ],
    NOW,
  );
  assert.deepEqual(findCoercions([{ ...badJson, seq: 1 }, { ...missingVal, seq: 2 }], snap), []);
  assert.equal(snap.blind.length, 2);
});

test("falsifier: unreachable NATS broker records BLIND event on target and exits 2 (never silent green)", async () => {
  let posted = null;
  const res = await bridgeBatch({
    brokerError: "127.0.0.1:4222: ECONNREFUSED",
    base: "https://live.meridianlabs.cloud",
    token: "secret-ingest",
    now: () => NOW,
    fetchImpl: async (url, init) => {
      posted = { url, body: JSON.parse(init.body) };
      return new Response(JSON.stringify({ accepted: 1, seq: 12 }), { status: 200 });
    },
  });
  assert.equal(res.code, 2);
  assert.equal(posted.url, "https://live.meridianlabs.cloud/append");
  assert.equal(posted.body.length, 1);
  assert.equal(posted.body[0].status, "BLIND");
  assert.match(posted.body[0].reason, /ECONNREFUSED/);
});

test("falsifier: missing ingest token returns BLIND code 2 without network call", async () => {
  let called = false;
  const res = await bridgeBatch({
    messages: [{ subject: "a", data: { value: 1 } }],
    base: "https://live.meridianlabs.cloud",
    token: "",
    fetchImpl: async () => {
      called = true;
      return new Response("{}", { status: 200 });
    },
  });
  assert.equal(res.code, 2);
  assert.equal(called, false);
  assert.match(res.out[0], /BLIND/);
});

test("falsifier: refusing target fails closed with code 1; accepted batch yields deterministic fold parity", async () => {
  const denied = await bridgeBatch({
    messages: [{ subject: "estate.fleet.ok", data: { value: "ready" } }],
    base: "https://live.meridianlabs.cloud",
    token: "wrong",
    now: () => NOW,
    fetchImpl: async () => new Response('{"error":"unauthorized"}', { status: 401 }),
  });
  assert.equal(denied.code, 1);
  assert.match(denied.err[0], /HTTP 401/);

  let forwarded = [];
  const ok = await bridgeBatch({
    messages: [
      { subject: "estate.fleet.ok", seq: 1, data: { from: "carbon", kind: "presence", subject: "carbon", value: "ready" } },
    ],
    base: "https://live.meridianlabs.cloud",
    token: "good",
    now: () => NOW,
    fetchImpl: async (_url, init) => {
      forwarded = JSON.parse(init.body);
      return new Response(JSON.stringify({ accepted: forwarded.length, seq: 5 }), { status: 200 });
    },
  });
  assert.equal(ok.code, 0);
  const snapA = fold([{ ...forwarded[0], seq: 5 }], NOW);
  const snapB = fold([{ ...forwarded[0], seq: 5 }], NOW);
  assert.equal(await snapshotHash(snapA), await snapshotHash(snapB));
});
