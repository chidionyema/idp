import { BudgetLedgerDO } from "./ledger-do";
import { RoutingStateDO } from "./routing-do";
import { chatToResponse, modelsList, responseToSse, responsesToChat } from "./responses_adapter.mjs";
import type {
  BackendCandidate,
  ChatCompletionRequest,
  Env,
  PlanResponse,
  ReserveResponse,
} from "./types";

export { BudgetLedgerDO, RoutingStateDO };

// 401/402/403 are LANE state, not caller errors: a vendor key that was revoked or a wallet
// that ran dry must fail over like a 429 and never reach the caller. Measured 2026-11-25,
// run 45680655819: MiniMax answered 402 insufficient_balance_error and the router returned
// that 402 to probe 3 instead of walking to the next candidate, so one exhausted plan took
// the whole role down while two other lanes sat in the pool.
const FAILOVER_STATUS_CODES = new Set([401, 402, 403, 408, 413, 429, 500, 502, 503, 504, 520, 522, 524, 525, 530]);

async function timingSafeTokenEqual(provided: string, expected: string): Promise<boolean> {
  if (!provided || !expected) return false;
  const enc = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(provided)),
    crypto.subtle.digest("SHA-256", enc.encode(expected)),
  ]);
  const viewA = new Uint8Array(a);
  const viewB = new Uint8Array(b);
  let diff = 0;
  for (let i = 0; i < viewA.length; i++) {
    diff |= viewA[i] ^ viewB[i];
  }
  return diff === 0;
}

function extractBearer(request: Request): string {
  const header = request.headers.get("authorization") ?? "";
  if (!header.toLowerCase().startsWith("bearer ")) return "";
  return header.slice(7).trim();
}

export function estimateRequestInputTokens(req: ChatCompletionRequest): number {
  const encoder = new TextEncoder();
  const payloadBytes =
    encoder.encode(JSON.stringify(req.messages ?? [])).byteLength +
    (req.tools ? encoder.encode(JSON.stringify(req.tools)).byteLength : 0);
  // Conservative 3.2 bytes/token + fixed framing overhead
  return Math.ceil(payloadBytes / 3.2) + 128;
}

function estimateCostUsd(candidate: BackendCandidate, inputTokens: number, outputTokens: number): number {
  return (inputTokens / 1000) * candidate.costPer1kInputUsd + (outputTokens / 1000) * candidate.costPer1kOutputUsd;
}

function resolveRole(modelField: string | undefined): string {
  if (!modelField || !modelField.trim()) return "role:default";
  const normalized = modelField.trim();
  if (normalized.startsWith("role:")) return normalized;
  return `role:${normalized}`;
}

function getLedgerStub(env: Env): DurableObjectStub {
  return env.BUDGET_LEDGER.get(env.BUDGET_LEDGER.idFromName("global-ledger-v1"));
}

function getRoutingStub(env: Env): DurableObjectStub {
  return env.ROUTING_STATE.get(env.ROUTING_STATE.idFromName("global-routing-v1"));
}

async function recordOutcome(
  routingStub: DurableObjectStub,
  backendId: string,
  outcome: "success" | "payload_too_large" | "transient_failure",
  statusCode?: number,
  observedTokens?: number
): Promise<void> {
  await routingStub.fetch("https://routing.internal/record", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ backendId, outcome, statusCode, observedTokens }),
  });
}

async function releaseReservation(ledgerStub: DurableObjectStub, reservationId: string): Promise<void> {
  await ledgerStub.fetch("https://ledger.internal/release", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ reservationId }),
  });
}

async function settleReservation(
  ledgerStub: DurableObjectStub,
  reservationId: string,
  actualUsd: number
): Promise<void> {
  await ledgerStub.fetch("https://ledger.internal/settle", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ reservationId, actualUsd }),
  });
}

/**
 * Peeks the first non-empty SSE chunk before committing HTTP 200 to the client.
 * If upstream resets the socket (ECONNRESET) or emits an immediate JSON error frame
 * before any token arrives, returns { ok: false } so the router fails over cleanly.
 */
async function probeFirstStreamChunk(
  upstreamBody: ReadableStream<Uint8Array>
): Promise<{ ok: true; stream: ReadableStream<Uint8Array> } | { ok: false; reason: string }> {
  const reader = upstreamBody.getReader();
  const decoder = new TextDecoder();
  const buffered: Uint8Array[] = [];

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        if (buffered.length === 0) {
          return { ok: false, reason: "empty_stream_before_first_chunk" };
        }
        break;
      }
      if (!value || value.byteLength === 0) continue;
      buffered.push(value);
      const text = decoder.decode(value, { stream: true }).trim();
      if (!text) continue;
      if (text.startsWith('{"error"') || text.includes('"error":')) {
        await reader.cancel("upstream_error_frame_in_stream");
        return { ok: false, reason: "upstream_error_frame" };
      }
      break;
    }
  } catch (err) {
    try {
      await reader.cancel();
    } catch {
      // ignore cancel errors on broken sockets
    }
    return { ok: false, reason: err instanceof Error ? err.message : "stream_read_error" };
  }

  const reassembled = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of buffered) {
        controller.enqueue(chunk);
      }
    },
    async pull(controller) {
      try {
        const { done, value } = await reader.read();
        if (done) {
          controller.close();
        } else if (value) {
          controller.enqueue(value);
        }
      } catch (err) {
        controller.error(err);
      }
    },
    async cancel(reason) {
      await reader.cancel(reason);
    },
  });

  return { ok: true, stream: reassembled };
}

const worker = {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const commitSha = env.COMMIT_SHA || "unknown";
    const zone = env.DEPLOYMENT_ZONE || "zone-b-cloudflare-edge";

    // 1. Public Blackbox Health Endpoint (zero secret exposure)
    if (request.method === "GET" && (url.pathname === "/health" || url.pathname === "/health/liveliness")) {
      const [ledgerRes, rolesRes] = await Promise.all([
        getLedgerStub(env)
          .fetch("https://ledger.internal/status")
          .then((r) => r.ok)
          .catch(() => false),
        getRoutingStub(env)
          .fetch("https://routing.internal/roles")
          .then(async (r) => (r.ok ? Object.keys(((await r.json()) as { roles: Record<string, unknown> }).roles).length : -1))
          .catch(() => -1),
      ]);

      const healthy = ledgerRes && rolesRes >= 0;
      return Response.json(
        {
          status: healthy ? "ok" : "degraded",
          commit_sha: commitSha,
          zone,
          ledger_ok: ledgerRes,
          configured_roles: rolesRes,
          timestamp: new Date().toISOString(),
        },
        { status: healthy ? 200 : 503 }
      );
    }

    // 2. Admin Control Plane (dynamic Role-to-pool & budget updates — zero Git PR required)
    if (url.pathname.startsWith("/admin/v1/")) {
      const token = extractBearer(request);
      const isAdmin = await timingSafeTokenEqual(token, env.MERIDIAN_ADMIN_KEY);
      if (!isAdmin) {
        return Response.json({ error: { type: "unauthorized", detail: "invalid_admin_key" } }, { status: 401 });
      }

      if (url.pathname === "/admin/v1/roles") {
        return getRoutingStub(env).fetch("https://routing.internal/roles", {
          method: request.method,
          headers: { "content-type": "application/json" },
          body: request.method === "PUT" ? await request.text() : undefined,
        });
      }

      if (url.pathname === "/admin/v1/circuits" && request.method === "GET") {
        return getRoutingStub(env).fetch("https://routing.internal/circuits");
      }

      if (url.pathname === "/admin/v1/budget") {
        const targetPath = request.method === "POST" ? "/configure" : "/status";
        return getLedgerStub(env).fetch(`https://ledger.internal${targetPath}`, {
          method: request.method,
          headers: { "content-type": "application/json" },
          body: request.method === "POST" ? await request.text() : undefined,
        });
      }

      return Response.json({ error: { type: "not_found" } }, { status: 404 });
    }

    // 2b. OpenAI-compatible discovery and Responses API (what Codex speaks). Both reuse the
    // one chat path below, so admission, budget reservation and failover are never duplicated.
    if (request.method === "GET" && url.pathname === "/v1/models") {
      if (!(await timingSafeTokenEqual(extractBearer(request), env.MERIDIAN_CLIENT_KEY))) {
        return Response.json({ error: { type: "unauthorized", detail: "invalid_api_key" } }, { status: 401 });
      }
      const rolesRes = await getRoutingStub(env).fetch("https://routing.internal/roles");
      if (!rolesRes.ok) {
        return Response.json({ error: { type: "roles_unavailable" } }, { status: 503 });
      }
      const { roles } = (await rolesRes.json()) as { roles: Record<string, unknown> };
      return Response.json(modelsList(roles));
    }

    if (request.method === "POST" && url.pathname === "/v1/responses") {
      if (!(await timingSafeTokenEqual(extractBearer(request), env.MERIDIAN_CLIENT_KEY))) {
        return Response.json({ error: { type: "unauthorized", detail: "invalid_api_key" } }, { status: 401 });
      }
      let raw: unknown;
      try {
        raw = await request.json();
      } catch {
        return Response.json({ error: { type: "invalid_request", detail: "malformed_json" } }, { status: 400 });
      }
      const conv = responsesToChat(raw);
      if (!conv.ok) {
        return Response.json({ error: { type: "invalid_request", detail: conv.detail } }, { status: 400 });
      }
      const inner = await worker.fetch(
        new Request(`${url.origin}/v1/chat/completions`, {
          method: "POST",
          headers: { "content-type": "application/json", authorization: request.headers.get("authorization") ?? "" },
          body: JSON.stringify(conv.chat),
        }),
        env,
        ctx
      );
      if (!inner.ok) return inner;
      let chatJson: unknown;
      try {
        chatJson = await inner.json();
      } catch {
        return Response.json({ error: { type: "bad_upstream_body" } }, { status: 502 });
      }
      const resp = chatToResponse(chatJson, conv.chat.model ?? "default");
      const headers: Record<string, string> = {
        "x-meridian-backend": inner.headers.get("x-meridian-backend") ?? "",
        "x-meridian-commit-sha": commitSha,
        "x-meridian-tools": conv.toolsDropped ? "dropped" : "none",
      };
      if (conv.wantsStream) {
        return new Response(responseToSse(resp), {
          headers: { ...headers, "content-type": "text/event-stream", "cache-control": "no-cache" },
        });
      }
      return Response.json(resp, { headers });
    }

    // 3. Authenticated Inference Data Plane (/v1/chat/completions)
    if (request.method === "POST" && url.pathname === "/v1/chat/completions") {
      const clientToken = extractBearer(request);
      const isAuthorized = await timingSafeTokenEqual(clientToken, env.MERIDIAN_CLIENT_KEY);
      if (!isAuthorized) {
        return Response.json({ error: { type: "unauthorized", detail: "invalid_api_key" } }, { status: 401 });
      }

      let body: ChatCompletionRequest;
      try {
        body = (await request.json()) as ChatCompletionRequest;
      } catch {
        return Response.json({ error: { type: "invalid_request", detail: "malformed_json" } }, { status: 400 });
      }

      if (!Array.isArray(body.messages) || body.messages.length === 0) {
        return Response.json({ error: { type: "invalid_request", detail: "messages_required" } }, { status: 400 });
      }

      const role = resolveRole(body.model);
      const defaultFloor = Number(env.DEFAULT_OUTPUT_FLOOR || "2048");
      const requestedOutput = body.max_completion_tokens ?? body.max_tokens ?? defaultFloor;
      const estimatedInputTokens = estimateRequestInputTokens(body);
      const requiresTools = Array.isArray(body.tools) && body.tools.length > 0;

      const routingStub = getRoutingStub(env);
      const ledgerStub = getLedgerStub(env);

      // Step A: Capability-aware Battalion Admission Plan
      const planRes = await routingStub.fetch("https://routing.internal/plan", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          role,
          estimatedInputTokens,
          requestedOutputTokens: requestedOutput,
          requiresTools,
        }),
      });

      if (!planRes.ok) {
        return Response.json(
          { error: { type: "admission_refused", detail: await planRes.text() } },
          { status: planRes.status }
        );
      }

      const plan = (await planRes.json()) as PlanResponse;
      if (plan.eligible.length === 0) {
        return Response.json(
          {
            error: {
              type: "no_eligible_backend",
              role: plan.role,
              estimated_input_tokens: estimatedInputTokens,
              effective_output_tokens: plan.effectiveOutputTokens,
              rejected: plan.rejected,
            },
          },
          { status: 503 }
        );
      }

      // Step B: Atomic Fail-Closed Budget Reservation (worst-case across eligible pool)
      const worstCaseUsd = Math.max(...plan.eligible.map((c) => estimateCostUsd(c, estimatedInputTokens, plan.effectiveOutputTokens)));
      const reservationId = crypto.randomUUID();
      const ttlMs = Number(env.RESERVATION_TTL_MS || "120000");

      let reserveRes: Response;
      try {
        reserveRes = await ledgerStub.fetch("https://ledger.internal/reserve", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            reservationId,
            role: plan.role,
            estimatedUsd: worstCaseUsd,
            ttlMs,
          }),
        });
      } catch (err) {
        return Response.json(
          {
            error: {
              type: "ledger_unavailable",
              detail: err instanceof Error ? err.message : "ledger_unreachable",
            },
          },
          { status: 503 }
        );
      }

      if (reserveRes.status === 429) {
        const detail = (await reserveRes.json()) as ReserveResponse;
        return Response.json({ error: { type: "budget_exhausted", ...detail } }, { status: 429 });
      }

      if (!reserveRes.ok) {
        return Response.json(
          { error: { type: "ledger_unavailable", detail: await reserveRes.text() } },
          { status: 503 }
        );
      }

      // Step C: Execute with Automatic Failover Across Eligible Pool
      const attemptErrors: Array<{ backendId: string; status: number; detail: string }> = [];
      const timeoutMs = Number(env.UPSTREAM_TIMEOUT_MS || "45000");

      for (let i = 0; i < plan.eligible.length; i++) {
        const candidate = plan.eligible[i];
        const upstreamKey = env[candidate.apiKeySecretName];
        if (typeof upstreamKey !== "string" || !upstreamKey) {
          attemptErrors.push({ backendId: candidate.id, status: 500, detail: `missing_secret_${candidate.apiKeySecretName}` });
          continue;
        }

        const boundedOutput = Math.min(plan.effectiveOutputTokens, candidate.maxOutputTokens);
        const upstreamPayload: ChatCompletionRequest = {
          ...body,
          model: candidate.upstreamModel,
          max_tokens: boundedOutput,
        };
        delete upstreamPayload.max_completion_tokens;

        let upstreamRes: Response;
        try {
          upstreamRes = await fetch(candidate.baseUrl, {
            method: "POST",
            headers: {
              "content-type": "application/json",
              authorization: `Bearer ${upstreamKey}`,
            },
            body: JSON.stringify(upstreamPayload),
            signal: AbortSignal.timeout(timeoutMs),
          });
        } catch (err) {
          const msg = err instanceof Error ? err.message : "network_error";
          attemptErrors.push({ backendId: candidate.id, status: 503, detail: msg });
          ctx.waitUntil(recordOutcome(routingStub, candidate.id, "transient_failure", 503));
          continue;
        }

        if (upstreamRes.status === 413) {
          const errText = await upstreamRes.text().catch(() => "payload_too_large");
          attemptErrors.push({ backendId: candidate.id, status: 413, detail: errText.slice(0, 200) });
          ctx.waitUntil(
            recordOutcome(routingStub, candidate.id, "payload_too_large", 413, estimatedInputTokens + boundedOutput)
          );
          continue;
        }

        if (FAILOVER_STATUS_CODES.has(upstreamRes.status)) {
          const errText = await upstreamRes.text().catch(() => "upstream_error");
          attemptErrors.push({
            backendId: candidate.id,
            status: upstreamRes.status,
            detail: errText.slice(0, 200),
          });
          ctx.waitUntil(recordOutcome(routingStub, candidate.id, "transient_failure", upstreamRes.status));
          continue;
        }

        if (!upstreamRes.ok) {
        // Non-retriable 4xx (e.g., 400 malformed prompt) -> release budget and return client error
        const errBody = await upstreamRes.text().catch(() => "");
        ctx.waitUntil(releaseReservation(ledgerStub, reservationId));
        return new Response(errBody, {
          status: upstreamRes.status,
          headers: {
            "content-type": upstreamRes.headers.get("content-type") ?? "application/json",
            "x-meridian-backend": candidate.id,
            "x-meridian-commit-sha": commitSha,
          },
        });
      }

      // Success path: Streaming
      if (body.stream && upstreamRes.body) {
        const probed = await probeFirstStreamChunk(upstreamRes.body);
        if (!probed.ok) {
          attemptErrors.push({ backendId: candidate.id, status: 502, detail: probed.reason });
          ctx.waitUntil(recordOutcome(routingStub, candidate.id, "transient_failure", 502));
          continue;
        }

        ctx.waitUntil(recordOutcome(routingStub, candidate.id, "success", 200));

        // Settle conservative streaming cost when stream finishes
        const { readable, writable } = new TransformStream<Uint8Array, Uint8Array>();
        const streamCost = estimateCostUsd(candidate, estimatedInputTokens, boundedOutput);
        ctx.waitUntil(
          probed.stream
            .pipeTo(writable)
            .catch(() => {})
            .finally(() => settleReservation(ledgerStub, reservationId, streamCost))
        );

        return new Response(readable, {
          status: 200,
          headers: {
            "content-type": "text/event-stream; charset=utf-8",
            "cache-control": "no-cache",
            "x-meridian-role": plan.role,
            "x-meridian-backend": candidate.id,
            "x-meridian-lane": candidate.lane,
            "x-meridian-failover-count": String(i),
            "x-meridian-commit-sha": commitSha,
            "x-meridian-reservation-id": reservationId,
          },
        });
      }

      // Success path: Non-streaming JSON
      const rawText = await upstreamRes.text();
      let actualUsd = estimateCostUsd(candidate, estimatedInputTokens, boundedOutput);
      try {
        const parsed = JSON.parse(rawText) as {
          usage?: { prompt_tokens?: number; completion_tokens?: number };
        };
        if (parsed.usage?.prompt_tokens != null && parsed.usage?.completion_tokens != null) {
          actualUsd = estimateCostUsd(candidate, parsed.usage.prompt_tokens, parsed.usage.completion_tokens);
        }
      } catch {
        // Retain conservative cost if upstream omitted usage
      }

      ctx.waitUntil(
        Promise.all([
          recordOutcome(routingStub, candidate.id, "success", 200),
          settleReservation(ledgerStub, reservationId, actualUsd),
        ])
      );

      return new Response(rawText, {
        status: 200,
        headers: {
          "content-type": "application/json; charset=utf-8",
          "x-meridian-role": plan.role,
          "x-meridian-backend": candidate.id,
          "x-meridian-lane": candidate.lane,
          "x-meridian-failover-count": String(i),
          "x-meridian-commit-sha": commitSha,
          "x-meridian-reservation-id": reservationId,
        },
      });
    }

    // All eligible backends exhausted -> release budget and return explicit pool-exhaustion error
    ctx.waitUntil(releaseReservation(ledgerStub, reservationId));
    return Response.json(
      {
        error: {
          type: "all_pool_backends_failed",
          role: plan.role,
          attempts: attemptErrors,
          pre_filtered_rejected: plan.rejected,
        },
      },
      { status: 503 }
    );
  }

  return Response.json({ error: { type: "not_found" } }, { status: 404 });
  },
};

export default worker;
