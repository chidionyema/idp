#!/usr/bin/env node
import assert from "node:assert/strict";
import worker, { BudgetLedgerDO, RoutingStateDO } from "../dist/index.js";

function createMemoryStorage() {
  const store = new Map();
  let transactionQueue = Promise.resolve();
  return {
    async get(key) {
      return store.has(key) ? structuredClone(store.get(key)) : undefined;
    },
    async put(key, val) {
      store.set(key, structuredClone(val));
    },
    async transaction(fn) {
      const job = transactionQueue.then(fn);
      transactionQueue = job.then(() => {}, () => {});
      return await job;
    },
  };
}

function makeNamespace(DOClass) {
  const instances = new Map();
  return {
    idFromName(name) {
      return name;
    },
    get(id) {
      if (!instances.has(id)) {
        instances.set(id, new DOClass({ storage: createMemoryStorage() }));
      }
      return {
        fetch(input, init) {
          return instances.get(id).fetch(new Request(input, init));
        },
      };
    },
  };
}

const env = {
  BUDGET_LEDGER: makeNamespace(BudgetLedgerDO),
  ROUTING_STATE: makeNamespace(RoutingStateDO),
  COMMIT_SHA: "test-sha-945078d",
  DEPLOYMENT_ZONE: "zone-b-cloudflare-edge",
  DEFAULT_OUTPUT_FLOOR: "2048",
  UPSTREAM_TIMEOUT_MS: "5000",
  RESERVATION_TTL_MS: "60000",
  MERIDIAN_CLIENT_KEY: "client-secret-test",
  MERIDIAN_ADMIN_KEY: "admin-secret-test",
  GROQ_API_KEY: "gsk-test",
  DEEPSEEK_API_KEY: "dsk-test",
};

const pending = [];
const ctx = { waitUntil: (p) => pending.push(p) };
async function drain() {
  await Promise.allSettled(pending.splice(0));
}

// Seed live Role pool via Admin API (zero static TOML)
const seedRes = await worker.fetch(
  new Request("https://llm.meridianlabs.cloud/admin/v1/roles", {
    method: "PUT",
    headers: { authorization: "Bearer admin-secret-test", "content-type": "application/json" },
    body: JSON.stringify({
      roles: {
        "role:coder": {
          role: "role:coder",
          minOutputFloor: 2048,
          candidates: [
            {
              id: "groq-gpt-oss-120b",
              vendor: "groq",
              lane: "edge-direct",
              baseUrl: "https://mock.groq.local/v1/chat/completions",
              apiKeySecretName: "GROQ_API_KEY",
              upstreamModel: "openai/gpt-oss-120b",
              maxContextTokens: 8192,
              maxOutputTokens: 4096,
              supportsTools: true,
              priority: 1,
              costPer1kInputUsd: 0.0002,
              costPer1kOutputUsd: 0.0006,
              enabled: true,
            },
            {
              id: "deepseek-wide-context",
              vendor: "deepseek",
              lane: "edge-direct",
              baseUrl: "https://mock.deepseek.local/v1/chat/completions",
              apiKeySecretName: "DEEPSEEK_API_KEY",
              upstreamModel: "deepseek-chat",
              maxContextTokens: 128000,
              maxOutputTokens: 8192,
              supportsTools: true,
              priority: 2,
              costPer1kInputUsd: 0.0005,
              costPer1kOutputUsd: 0.0015,
              enabled: true,
            },
          ],
        },
      },
    }),
  }),
  env,
  ctx
);
assert.equal(seedRes.status, 200);

// Mock upstream fetch
const calls = [];
globalThis.fetch = async (url, init) => {
  const parsed = JSON.parse(init.body);
  calls.push({ url: String(url), max_tokens: parsed.max_tokens, model: parsed.model, messages: parsed.messages });

  if (String(url).includes("mock.groq.local")) {
    return new Response(JSON.stringify({ error: "request too large" }), { status: 413 });
  }
  return new Response(
    JSON.stringify({
      id: "chatcmpl-test",
      choices: [{ message: { role: "assistant", content: "FAILOVER_OK" } }],
      usage: { prompt_tokens: 500, completion_tokens: 50 },
    }),
    { status: 200, headers: { "content-type": "application/json" } }
  );
};

// Test 1: Upstream 413 fails over transparently to deepseek-wide-context -> HTTP 200 (never 502) + output floor >= 2048
const res1 = await worker.fetch(
  new Request("https://llm.meridianlabs.cloud/v1/chat/completions", {
    method: "POST",
    headers: { authorization: "Bearer client-secret-test", "content-type": "application/json" },
    body: JSON.stringify({ model: "role:coder", messages: [{ role: "user", content: "x".repeat(4000) }] }),
  }),
  env,
  ctx
);
await drain();
assert.equal(res1.status, 200);
assert.equal(res1.headers.get("x-meridian-backend"), "deepseek-wide-context");
assert.equal(res1.headers.get("x-meridian-failover-count"), "1");
assert.equal(calls.length, 2);
assert(calls[1].max_tokens >= 2048, "output floor not enforced");

// Test 2: Second identically sized request skips groq PRE-DISPATCH (learned 413 cap -> 0 wasted Groq calls)
calls.length = 0;
const res2 = await worker.fetch(
  new Request("https://llm.meridianlabs.cloud/v1/chat/completions", {
    method: "POST",
    headers: { authorization: "Bearer client-secret-test", "content-type": "application/json" },
    body: JSON.stringify({ model: "role:coder", messages: [{ role: "user", content: "x".repeat(4000) }] }),
  }),
  env,
  ctx
);
await drain();
assert.equal(res2.status, 200);
assert.equal(res2.headers.get("x-meridian-failover-count"), "0");
assert.equal(calls.length, 1, "should have bypassed groq pre-dispatch");

// Test 3: Exhausted budget fails closed with HTTP 429 BEFORE any upstream call fires
await worker.fetch(
  new Request("https://llm.meridianlabs.cloud/admin/v1/budget", {
    method: "POST",
    headers: { authorization: "Bearer admin-secret-test", "content-type": "application/json" },
    body: JSON.stringify({ dailyLimitUsd: 0.00001, resetSpend: true }),
  }),
  env,
  ctx
);
calls.length = 0;
const res3 = await worker.fetch(
  new Request("https://llm.meridianlabs.cloud/v1/chat/completions", {
    method: "POST",
    headers: { authorization: "Bearer client-secret-test", "content-type": "application/json" },
    body: JSON.stringify({ model: "role:coder", messages: [{ role: "user", content: "hello" }] }),
  }),
  env,
  ctx
);
assert.equal(res3.status, 429);
assert.equal(calls.length, 0, "must not spend upstream calls when budget is exhausted");

// Test 4: Invalid key strictly returns 401
const res4 = await worker.fetch(
  new Request("https://llm.meridianlabs.cloud/v1/chat/completions", {
    method: "POST",
    headers: { authorization: "Bearer wrong-key", "content-type": "application/json" },
    body: JSON.stringify({ model: "role:coder", messages: [{ role: "user", content: "hello" }] }),
  }),
  env,
  ctx
);
assert.equal(res4.status, 401);

// Context governance observes authenticated ingress through the real Worker and ledger classes.
// Financial refusals remain independent of observer health.
await drain();
const contextStatusRequest = (key = "admin-secret-test") => new Request(
  "https://llm.meridianlabs.cloud/admin/v1/context", { headers: { authorization: `Bearer ${key}` } }
);
const contextRes = await worker.fetch(contextStatusRequest(), env, ctx);
assert.equal(contextRes.status, 200, "context governance is not wired into the existing ledger");
const context = await contextRes.json();
assert.equal(context.phase, "SHADOW");
assert.equal(context.observations, 3, "wrong-key request must not enter context telemetry");
assert(context.estimatedTokens > 0);
assert(!JSON.stringify(context).includes("x".repeat(100)), "raw prompts must not be persisted or exposed");
assert.equal((await worker.fetch(contextStatusRequest("wrong-key"), env, ctx)).status, 401);

// Only the observer fails here. Inference and the financial ledger must still work.
await worker.fetch(new Request("https://llm.meridianlabs.cloud/admin/v1/budget", {
  method: "POST", headers: { authorization: "Bearer admin-secret-test", "content-type": "application/json" },
  body: JSON.stringify({ dailyLimitUsd: 25, resetSpend: true }),
}), env, ctx);
const originalLedger = env.BUDGET_LEDGER;
env.BUDGET_LEDGER = {
  ...originalLedger,
  get(id) {
    const stub = originalLedger.get(id);
    return { fetch(input, init) {
      if (String(input).includes("/context/observe")) return Promise.reject(new Error("observer unavailable"));
      return stub.fetch(input, init);
    } };
  },
};
const observerFailureResponse = await worker.fetch(new Request("https://llm.meridianlabs.cloud/v1/chat/completions", {
  method: "POST", headers: { authorization: "Bearer client-secret-test", "content-type": "application/json" },
  body: JSON.stringify({ model: "role:coder", messages: [{ role: "user", content: "OBSERVER_FAILURE_CANARY" }] }),
}), env, ctx);
await drain();
assert.equal(observerFailureResponse.status, 200, "SHADOW outage must not interrupt inference");
env.BUDGET_LEDGER = originalLedger;

const largeMessages = [{ role: "user", content: "x".repeat(120000) }];
const largeResponse = await worker.fetch(new Request("https://llm.meridianlabs.cloud/v1/chat/completions", {
  method: "POST", headers: { authorization: "Bearer client-secret-test", "content-type": "application/json" },
  body: JSON.stringify({ model: "role:coder", messages: largeMessages }),
}), env, ctx);
await drain();
assert.equal(largeResponse.status, 200, "SHADOW must not interrupt a valid over-cap request");
assert.deepEqual(calls.at(-1).messages, largeMessages, "context observer must not compact or mutate requests");
const largeSnapshot = await (await worker.fetch(contextStatusRequest(), env, ctx)).json();
assert.equal(largeSnapshot.observations, 4);
assert.equal(largeSnapshot.lastObservation.role, "role:surgical-patch");
assert(largeSnapshot.lastObservation.estimatedTokens > 28000);
assert.equal(largeSnapshot.cacheHitRatio, null, "unmeasured cache coverage must stay UNKNOWN");

const persistentStorage = createMemoryStorage();
const contextLedger = new BudgetLedgerDO({ storage: persistentStorage });
const directObservation = i => contextLedger.fetch(new Request("https://ledger.internal/context/observe", {
  method: "POST", headers: { "content-type": "application/json" },
  body: JSON.stringify({ scope: i.toString(16).padStart(64, "0"), role: "role:ops-dispatch", sourceSha: env.COMMIT_SHA,
    request: { model: "test", messages: [{ role: "user", content: "PRIVATE_CONTEXT_SENTINEL" }] } }),
}));
for (let i = 0; i < 130; i++) assert.equal((await directObservation(i)).status, 200);
await Promise.all(Array.from({ length: 10 }, (_, i) => directObservation(200 + i)));
const restartedLedger = new BudgetLedgerDO({ storage: persistentStorage });
const persisted = await (await restartedLedger.fetch(new Request("https://ledger.internal/context/status"))).json();
assert.equal(persisted.observations, 140, "concurrent observations must persist across object restart");
assert.equal(persisted.retainedSessions, 128, "observer storage must be bounded");
assert.equal(await persistentStorage.get("ledger_state_v1"), undefined, "observer must not initialise/reset financial state");
assert(!JSON.stringify(persisted).includes("PRIVATE_CONTEXT_SENTINEL"));

console.log("ALL 4 FALSIFIER PROOFS PASSED (413->200 failover, pre-dispatch learned cap, fail-closed 429, 401 auth)");
console.log("CONTEXT SHADOW INTEGRATION PASSED (real ingress, admin auth, privacy, observer outage isolation)");
