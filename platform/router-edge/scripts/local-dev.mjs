#!/usr/bin/env node
/**
 * Local dev server for meridian-router-edge.
 * Self-contained JavaScript (no TypeScript/esbuild needed).
 * Implements the same API as src/index.ts with in-memory DO stubs.
 *
 * Usage:
 *   MERIDIAN_CLIENT_KEY=xxx MERIDIAN_ADMIN_KEY=xxx node scripts/local-dev.mjs [PORT]
 */
import { createServer } from "node:http";
import { randomUUID } from "node:crypto";

const PORT = Number(process.argv[2] ?? process.env.PORT ?? 8787);
const COMMIT_SHA = process.env.COMMIT_SHA ?? "dev-local";
const ZONE = process.env.DEPLOYMENT_ZONE ?? "zone-b-cloudflare-edge";
const CLIENT_KEY = process.env.MERIDIAN_CLIENT_KEY ?? "dev-client-key";
const ADMIN_KEY = process.env.MERIDIAN_ADMIN_KEY ?? "dev-admin-key";

async function tse(a, b) {
  if (!a || !b || a.length !== b.length) return false;
  const e = new TextEncoder();
  const [ha, hb] = await Promise.all([
    crypto.subtle.digest("SHA-256", e.encode(a)),
    crypto.subtle.digest("SHA-256", e.encode(b)),
  ]);
  const A = new Uint8Array(ha), B = new Uint8Array(hb);
  let d = 0; for (let i = 0; i < A.length; i++) d |= A[i] ^ B[i];
  return d === 0;
}
function bearer(req) {
  const h = req.headers["authorization"] ?? "";
  return h.toLowerCase().startsWith("bearer ") ? h.slice(7).trim() : "";
}
const ledger = {
  day: new Date().toISOString().slice(0, 10),
  limit: 25.0, spent: 0, reservations: {},
};
const routing = { roles: {}, circuits: {} };
const FAILOVER = new Set([408,413,429,500,502,503,504,520,522,524,525,530]);
function sumRes() { let t = 0; for (const e of Object.values(ledger.reservations)) t += e.estimatedUsd; return t; }
function estIn(body) {
  const e = new TextEncoder();
  let b = e.encode(JSON.stringify(body.messages ?? [])).byteLength;
  if (body.tools) b += e.encode(JSON.stringify(body.tools)).byteLength;
  return Math.ceil(b / 3.2) + 128;
}
function estCost(c, i, o) { return (i / 1000) * c.costPer1kInputUsd + (o / 1000) * c.costPer1kOutputUsd; }
function roleOf(m) {
  if (!m || !m.trim()) return "role:default";
  const mm = m.trim(); return mm.startsWith("role:") ? mm : `role:${mm}`;
}
async function readBody(req) {
  const c = []; for await (const ch of req) c.push(ch);
  return Buffer.concat(c).toString();
}
function j(res, s, o) {
  const b = JSON.stringify(o);
  res.writeHead(s, { "content-type": "application/json; charset=utf-8", "content-length": String(Buffer.byteLength(b)) });
  res.end(b);
}

async function handleHealth(req, res) {
  j(res, 200, {
    status: "ok", commit_sha: COMMIT_SHA, zone: ZONE,
    ledger_ok: true,
    configured_roles: Object.keys(routing.roles).length,
    timestamp: new Date().toISOString(),
  });
}

async function handleAdmin(req, res, url) {
  const token = bearer(req);
  if (!(await tse(token, ADMIN_KEY))) {
    j(res, 401, { error: { type: "unauthorized", detail: "invalid_admin_key" } });
    return;
  }
  if (url.pathname === "/admin/v1/roles") {
    if (req.method === "PUT") {
      const body = JSON.parse(await readBody(req));
      if (!body || typeof body.roles !== "object") {
        j(res, 400, { error: "invalid_roles_payload" });
        return;
      }
      routing.roles = body.roles;
      j(res, 200, { ok: true, roleCount: Object.keys(body.roles).length });
    } else {
      j(res, 200, { roles: routing.roles });
    }
    return;
  }
  if (url.pathname === "/admin/v1/circuits" && req.method === "GET") {
    j(res, 200, { circuits: routing.circuits, nowMs: Date.now() });
    return;
  }
  if (url.pathname === "/admin/v1/budget") {
    if (req.method === "POST") {
      const body = JSON.parse(await readBody(req));
      if (typeof body.dailyLimitUsd !== "number" || body.dailyLimitUsd < 0) {
        j(res, 400, { error: "invalid_daily_limit" });
        return;
      }
      ledger.limit = body.dailyLimitUsd;
      if (body.resetSpend) { ledger.spent = 0; ledger.reservations = {}; }
      j(res, 200, { ok: true, dailyLimitUsd: ledger.limit, spentUsd: ledger.spent });
    } else {
      const resv = sumRes();
      j(res, 200, {
        ok: true, epochDay: ledger.day, dailyLimitUsd: ledger.limit,
        spentUsd: Number(ledger.spent.toFixed(6)),
        reservedUsd: Number(resv.toFixed(6)),
        remainingUsd: Number(Math.max(0, ledger.limit - ledger.spent - resv).toFixed(6)),
        activeReservations: Object.keys(ledger.reservations).length,
      });
    }
    return;
  }
  j(res, 404, { error: { type: "not_found" } });
}

async function handleChat(req, res) {
  const token = bearer(req);
  if (!(await tse(token, CLIENT_KEY))) {
    j(res, 401, { error: { type: "unauthorized", detail: "invalid_api_key" } });
    return;
  }
  let body;
  try { body = JSON.parse(await readBody(req)); } catch {
    j(res, 400, { error: { type: "invalid_request", detail: "malformed_json" } });
    return;
  }
  if (!Array.isArray(body.messages) || body.messages.length === 0) {
    j(res, 400, { error: { type: "invalid_request", detail: "messages_required" } });
    return;
  }
  const role = roleOf(body.model);
  const defaultFloor = 2048;
  const requestedOutput = body.max_completion_tokens ?? body.max_tokens ?? defaultFloor;
  const estimatedInput = estIn(body);
  const requiresTools = Array.isArray(body.tools) && body.tools.length > 0;

  const pool = routing.roles[role] ?? routing.roles["role:default"];
  if (!pool) {
    j(res, 503, { error: { type: "no_eligible_backend", role, rejected: [] } });
    return;
  }
  const nowMs = Date.now();
  const effectiveOutput = Math.max(requestedOutput, pool.minOutputFloor || 2048);
  const requiredTotal = estimatedInput + effectiveOutput;

  const eligible = [], rejected = [];
  const sorted = [...pool.candidates].sort((a, b) => a.priority - b.priority);
  for (const c of sorted) {
    if (!c.enabled) { rejected.push({ id: c.id, reason: "disabled" }); continue; }
    if (requiresTools && !c.supportsTools) { rejected.push({ id: c.id, reason: "tools_unsupported" }); continue; }
    const circuit = routing.circuits[c.id];
    if (circuit && circuit.openUntilMs > nowMs) {
      rejected.push({ id: c.id, reason: "circuit_open" });
      continue;
    }
    const learnedCap = circuit?.learnedMaxContextTokens && (circuit.learnedMaxExpiresMs ?? 0) > nowMs
      ? circuit.learnedMaxContextTokens : Infinity;
    const effMaxCtx = Math.min(c.maxContextTokens, learnedCap);
    if (requiredTotal > effMaxCtx) {
      rejected.push({ id: c.id, reason: `payload_exceeds_context:${requiredTotal}>${effMaxCtx}` });
      continue;
    }
    eligible.push(c);
  }
  if (eligible.length === 0) {
    j(res, 503, {
      error: { type: "no_eligible_backend", role,
        estimated_input_tokens: estimatedInput,
        effective_output_tokens: effectiveOutput,
        rejected },
    });
    return;
  }

  const worstCaseUsd = Math.max(...eligible.map(c => estCost(c, estimatedInput, effectiveOutput)));
  const reservationId = randomUUID();
  const resv = sumRes();
  const remaining = ledger.limit - ledger.spent - resv;
  if (worstCaseUsd > remaining + 1e-9) {
    j(res, 429, {
      error: { type: "budget_exhausted", code: "BUDGET_EXHAUSTED",
        remainingUsd: Number(Math.max(0, remaining).toFixed(6)),
        dailyLimitUsd: ledger.limit, spentUsd: Number(ledger.spent.toFixed(6)),
        reservedUsd: Number(resv.toFixed(6)) },
    });
    return;
  }
  ledger.reservations[reservationId] = { estimatedUsd: worstCaseUsd, expiresAtMs: nowMs + 120000, role };

  const attemptErrors = [];
  const timeoutMs = 5000;

  for (let i = 0; i < eligible.length; i++) {
    const c = eligible[i];
    const upstreamKey = process.env[c.apiKeySecretName] ?? "";
    if (!upstreamKey) {
      attemptErrors.push({ backendId: c.id, status: 500, detail: `missing_secret_${c.apiKeySecretName}` });
      continue;
    }
    const boundedOutput = Math.min(effectiveOutput, c.maxOutputTokens);
    const upstreamPayload = { ...body, model: c.upstreamModel, max_tokens: boundedOutput };
    delete upstreamPayload.max_completion_tokens;

    try {
      const ctrl = new AbortController();
      const tmo = setTimeout(() => ctrl.abort(), timeoutMs);
      const resp = await fetch(c.baseUrl, {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${upstreamKey}` },
        body: JSON.stringify(upstreamPayload),
        signal: ctrl.signal,
      }).finally(() => clearTimeout(tmo));
      const ub = await resp.text();

      if (resp.status === 413) {
        attemptErrors.push({ backendId: c.id, status: 413, detail: "payload_too_large" });
        const prev = routing.circuits[c.id] ?? { failures: 0, openUntilMs: 0 };
        const safeCap = Math.max(512, Math.floor((estimatedInput + boundedOutput) * 0.85));
        routing.circuits[c.id] = {
          ...prev,
          learnedMaxContextTokens: prev.learnedMaxContextTokens
            ? Math.min(prev.learnedMaxContextTokens, safeCap) : safeCap,
          learnedMaxExpiresMs: nowMs + 600000,
          lastErrorCode: 413, lastErrorAtMs: nowMs,
        };
        continue;
      }
      if (FAILOVER.has(resp.status)) {
        attemptErrors.push({ backendId: c.id, status: resp.status, detail: ub.slice(0, 200) });
        const prev = routing.circuits[c.id] ?? { failures: 0, openUntilMs: 0 };
        const cd = Math.min(300000, 15000 * Math.pow(2, Math.min(prev.failures, 5)));
        routing.circuits[c.id] = {
          ...prev, failures: prev.failures + 1, openUntilMs: nowMs + cd,
          lastErrorCode: resp.status, lastErrorAtMs: nowMs,
        };
        continue;
      }
      if (!resp.ok) {
        delete ledger.reservations[reservationId];
        res.writeHead(resp.status, { "content-type": "application/json" });
        res.end(ub);
        return;
      }

      delete ledger.reservations[reservationId];
      ledger.spent += estCost(c, estimatedInput, boundedOutput);
      routing.circuits[c.id] = { failures: 0, openUntilMs: 0 };

      res.writeHead(200, {
        "content-type": "application/json; charset=utf-8",
        "x-meridian-role": role, "x-meridian-backend": c.id,
        "x-meridian-lane": c.lane, "x-meridian-failover-count": String(i),
        "x-meridian-commit-sha": COMMIT_SHA,
        "x-meridian-reservation-id": reservationId,
      });
      res.end(JSON.stringify({
        id: "chatcmpl-local",
        choices: [{ message: { role: "assistant", content: "LOCAL_DEV_OK" } }],
        usage: { prompt_tokens: estimatedInput, completion_tokens: boundedOutput },
      }));
      return;
    } catch (err) {
      attemptErrors.push({ backendId: c.id, status: 503, detail: err instanceof Error ? err.message : "network_error" });
      const prev = routing.circuits[c.id] ?? { failures: 0, openUntilMs: 0 };
      const cd = Math.min(300000, 15000 * Math.pow(2, Math.min(prev.failures, 5)));
      routing.circuits[c.id] = {
        ...prev, failures: prev.failures + 1, openUntilMs: nowMs + cd,
        lastErrorCode: 503, lastErrorAtMs: nowMs,
      };
      continue;
    }
  }

  delete ledger.reservations[reservationId];
  j(res, 503, {
    error: {
      type: "all_pool_backends_failed", role,
      attempts: attemptErrors,
      pre_filtered_rejected: rejected,
    },
  });
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  try {
    if (req.method === "GET" && (url.pathname === "/health" || url.pathname === "/health/liveliness")) {
      await handleHealth(req, res);
    } else if (url.pathname.startsWith("/admin/v1/")) {
      await handleAdmin(req, res, url);
    } else if (req.method === "POST" && url.pathname === "/v1/chat/completions") {
      await handleChat(req, res);
    } else {
      j(res, 404, { error: { type: "not_found" } });
    }
  } catch (err) {
    console.error("error:", err);
    j(res, 500, { error: { type: "internal_error", detail: String(err) } });
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(JSON.stringify({
    service: "meridian-router-edge (local dev)",
    port: PORT,
    url: `http://127.0.0.1:${PORT}`,
    commit_sha: COMMIT_SHA,
    zone: ZONE,
    note: "In-memory Durable Object stubs. Upstream calls mocked unless real vendor keys are set.",
    env_example: "MERIDIAN_CLIENT_KEY=xxx MERIDIAN_ADMIN_KEY=xxx GROQ_API_KEY=sk-... node scripts/local-dev.mjs",
  }));
});

process.on("SIGINT", () => { server.close(); process.exit(0); });
process.on("SIGTERM", () => { server.close(); process.exit(0); });
