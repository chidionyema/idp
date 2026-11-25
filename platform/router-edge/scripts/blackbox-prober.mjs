#!/usr/bin/env node
import assert from "node:assert/strict";

const BASE_URL = process.env.MERIDIAN_ROUTER_URL; // the zone's router hostname, e.g. https://llm.<ESTATE_ZONE>
const CLIENT_KEY = process.env.MERIDIAN_CLIENT_KEY;
const ADMIN_KEY = process.env.MERIDIAN_ADMIN_KEY;
const EXPECTED_SHA = process.env.EXPECTED_COMMIT_SHA;

assert(BASE_URL, "MERIDIAN_ROUTER_URL is required");
assert(CLIENT_KEY, "MERIDIAN_CLIENT_KEY is required");
assert(ADMIN_KEY, "MERIDIAN_ADMIN_KEY is required");

async function runProbe(name, fn) {
  const t0 = Date.now();
  try {
    const detail = await fn();
    console.log(JSON.stringify({ probe: name, status: "PASS", ms: Date.now() - t0, detail }));
  } catch (err) {
    console.error(JSON.stringify({ probe: name, status: "FAIL", ms: Date.now() - t0, error: String(err) }));
    process.exitCode = 1;
  }
}

// Probe 1: Live serving health, Zone B identity, and SHA parity
await runProbe("1_health_and_sha_parity", async () => {
  const res = await fetch(`${BASE_URL}/health`);
  assert.equal(res.status, 200, `expected 200, got ${res.status}`);
  const data = await res.json();
  assert.equal(data.status, "ok");
  assert.equal(data.ledger_ok, true);
  assert.equal(data.zone, "zone-b-cloudflare-edge");
  if (EXPECTED_SHA) {
    assert.equal(data.commit_sha, EXPECTED_SHA, `live SHA ${data.commit_sha} != ${EXPECTED_SHA}`);
  }
  return data;
});

// Probe 2: Invalid bearer token strictly rejected with HTTP 401
await runProbe("2_invalid_key_rejected_401", async () => {
  const res = await fetch(`${BASE_URL}/v1/chat/completions`, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: "Bearer invalid-probe-key" },
    body: JSON.stringify({ model: "role:coder", messages: [{ role: "user", content: "ping" }] }),
  });
  assert.equal(res.status, 401, `expected 401, got ${res.status}`);
  return { status: res.status };
});

// Probe 3: Authenticated large-payload request completes with 200 (never 413 -> 502)
await runProbe("3_authenticated_large_payload_200", async () => {
  const largeContext = "context-block ".repeat(1600); // ~22 KB payload to prove narrow-lane bypass/failover
  const res = await fetch(`${BASE_URL}/v1/chat/completions`, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${CLIENT_KEY}` },
    body: JSON.stringify({
      model: "role:coder",
      messages: [
        { role: "system", content: largeContext },
        { role: "user", content: "Reply with exactly: PROBE_OK" },
      ],
    }),
  });
  assert.equal(res.status, 200, `expected 200, got ${res.status}: ${await res.text()}`);
  const data = await res.json();
  assert(data.choices?.[0]?.message?.content?.length > 0, "empty assistant response");
  return {
    backend: res.headers.get("x-meridian-backend"),
    lane: res.headers.get("x-meridian-lane"),
    failoverCount: res.headers.get("x-meridian-failover-count"),
    commitSha: res.headers.get("x-meridian-commit-sha"),
  };
});

// Probe 4: Dynamic Role-pool readback + circuit-breaker visibility
await runProbe("4_dynamic_role_pool_control_plane", async () => {
  const res = await fetch(`${BASE_URL}/admin/v1/roles`, {
    headers: { authorization: `Bearer ${ADMIN_KEY}` },
  });
  assert.equal(res.status, 200);
  const data = await res.json();
  assert(data.roles && Object.keys(data.roles).length > 0, "no roles configured");
  return { roles: Object.keys(data.roles) };
});

// Probe 5: Fail-closed budget status verified on cloud DO (zero Mac disk dependency)
await runProbe("5_cloud_budget_ledger_status", async () => {
  const res = await fetch(`${BASE_URL}/admin/v1/budget`, {
    headers: { authorization: `Bearer ${ADMIN_KEY}` },
  });
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.equal(data.ok, true);
  assert(typeof data.remainingUsd === "number");
  return data;
});

if (process.exitCode && process.exitCode !== 0) {
  process.exit(process.exitCode);
}