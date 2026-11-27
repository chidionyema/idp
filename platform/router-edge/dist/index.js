// context-governance/ts/context-budget-middleware/index.ts
var REASONING_RANK = {
  minimal: 0,
  low: 1,
  medium: 2,
  high: 3
};
function toHex(buf) {
  return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
}
async function sha256Hex(input) {
  const bytes = new TextEncoder().encode(input);
  const digest2 = await crypto.subtle.digest("SHA-256", bytes);
  return toHex(digest2);
}
function estimateTextTokens(text, mult) {
  if (!text) return 0;
  const utf8Bytes = new TextEncoder().encode(text).length;
  return Math.max(1, Math.ceil(utf8Bytes / 3.2 * mult));
}
function estimateRequestTokens(body, mult) {
  const messages = Array.isArray(body.messages) ? body.messages : [];
  const tools = Array.isArray(body.tools) ? body.tools : [];
  let total = tools.length > 0 ? estimateTextTokens(JSON.stringify(tools), mult) : 0;
  let imageCount = 0;
  for (const m of messages) {
    if (!m || typeof m !== "object") continue;
    total += 6;
    const content = m.content;
    if (typeof content === "string") {
      total += estimateTextTokens(content, mult);
    } else if (Array.isArray(content)) {
      for (const part of content) {
        if (!part || typeof part !== "object") continue;
        const p = part;
        if (p.type === "text") {
          total += estimateTextTokens(String(p.text || ""), mult);
        } else if (p.type === "image_url" || p.type === "image") {
          imageCount += 1;
          total += 2048;
        } else {
          total += estimateTextTokens(JSON.stringify(p), mult);
        }
      }
    }
  }
  return { total, toolCount: tools.length, imageCount };
}
async function gateRouterIngress(requestBody, headersIn, policy2, ledger) {
  const role = headersIn.get("x-meridian-role") || "role:ops-dispatch";
  const sessionId = headersIn.get("x-meridian-session-id") || "ephemeral";
  const missionId = headersIn.get("x-meridian-mission-id") || "unassigned";
  const csNonce = headersIn.get("x-meridian-critical-section");
  const isSubagent = headersIn.get("x-meridian-subagent") === "true";
  const rcfg = policy2.roles[role] || policy2.roles["role:ops-dispatch"];
  const phase = policy2.rollout_phase;
  const degradations = [];
  const violations = [];
  let session = null;
  let missionSpent = 0;
  let ledgerHealthy = true;
  try {
    session = await ledger.getSession(sessionId) || {
      turn_count: 0,
      initial_prefix_hash: "",
      soft_warnings_issued: 0,
      critical_section_turns_used: 0,
      calibration_ratio: 1
    };
    missionSpent = await ledger.getMissionTotal(missionId);
  } catch {
    ledgerHealthy = false;
    degradations.push("budget_ledger_unavailable_fail_open");
  }
  const clampedBody = { ...requestBody };
  if (phase === "SOFT_ROTATE" || phase === "ENFORCE") {
    const reqEffort = String(requestBody.reasoning_effort || "").toLowerCase();
    const clampEffort = rcfg.reasoning_effort_clamp;
    if (!reqEffort || (REASONING_RANK[reqEffort] ?? 99) > (REASONING_RANK[clampEffort] ?? 1)) {
      clampedBody.reasoning_effort = clampEffort;
      degradations.push(`reasoning_effort_clamped_to_${clampEffort}`);
    }
    const reqMax = Number(requestBody.max_tokens ?? requestBody.max_completion_tokens ?? 0);
    if (!reqMax || reqMax > rcfg.max_output_tokens_clamp) {
      clampedBody.max_tokens = rcfg.max_output_tokens_clamp;
      degradations.push(`max_tokens_clamped_to_${rcfg.max_output_tokens_clamp}`);
    }
  }
  const modelStr = String(requestBody.model || "").toLowerCase();
  let mult = policy2.tokenizer_safety_multipliers.default ?? 1.15;
  for (const [k, v] of Object.entries(policy2.tokenizer_safety_multipliers)) {
    if (k !== "default" && modelStr.includes(k)) {
      mult = v;
      break;
    }
  }
  const cal = session ? session.calibration_ratio : 1;
  const est = estimateRequestTokens(clampedBody, mult * cal);
  const messages = Array.isArray(clampedBody.messages) ? clampedBody.messages : [];
  const sysMsgs = messages.filter((m) => m?.role === "system");
  const tools = Array.isArray(clampedBody.tools) ? clampedBody.tools : [];
  const prefixHash = await sha256Hex(JSON.stringify({ system: sysMsgs, tools }));
  let kvState = "COLD_TURN_1";
  if (session) {
    session.turn_count += 1;
    if (session.turn_count === 1) {
      session.initial_prefix_hash = prefixHash;
      if (est.total > rcfg.turn_1_prefix_cap) violations.push("ERR_TURN1_PREFIX_CAP_EXCEEDED");
    } else if (prefixHash !== session.initial_prefix_hash) {
      kvState = "PREFIX_MUTATED_THRASH";
      violations.push("ERR_KV_PREFIX_THRASH");
    } else {
      kvState = "PREFIX_STABLE";
    }
  }
  if (est.toolCount > policy2.global_invariants.max_always_on_mcp_tools) {
    violations.push("ERR_MCP_TOOL_CEILING_EXCEEDED");
  }
  if (isSubagent && session && session.turn_count === 1 && est.total > policy2.global_invariants.subagent_max_brief_tokens) {
    violations.push("ERR_SUBAGENT_BRIEF_CAP_EXCEEDED");
  }
  if (missionSpent + est.total > rcfg.mission_aggregate_cap) {
    violations.push("ERR_MISSION_AGGREGATE_BUDGET_EXCEEDED");
  }
  let leaseActive = false;
  let effectiveHardCap = rcfg.hard_context_cap;
  if (csNonce) {
    if (!session || session.critical_section_turns_used < policy2.global_invariants.critical_section_max_turns) {
      if (session) session.critical_section_turns_used += 1;
      leaseActive = true;
      effectiveHardCap = Math.ceil(
        rcfg.hard_context_cap * (1 + policy2.global_invariants.critical_section_max_headroom_ratio)
      );
    } else {
      violations.push("ERR_CRITICAL_SECTION_LEASE_EXHAUSTED");
    }
  }
  let directive = "ALLOW";
  let allowed = true;
  let status = 200;
  if (est.total >= rcfg.soft_context_cap) {
    directive = "CHECKPOINT_AND_ROTATE";
    if (session) session.soft_warnings_issued += 1;
  }
  if (phase === "ENFORCE") {
    const graceExhausted = !session || session.soft_warnings_issued > rcfg.max_grace_turns_after_soft;
    if (violations.includes("ERR_MISSION_AGGREGATE_BUDGET_EXCEEDED") && !leaseActive) {
      allowed = false;
      status = 429;
      directive = "HARD_STOP_MISSION_BUDGET_EXHAUSTED";
    } else if (est.total > effectiveHardCap) {
      allowed = false;
      status = 429;
      directive = "HARD_STOP_CONTEXT_CAP_EXCEEDED";
    } else if (est.total >= rcfg.hard_context_cap && !leaseActive && graceExhausted) {
      allowed = false;
      status = 429;
      directive = "HARD_STOP_ROTATION_IGNORED";
    }
  }
  if (ledgerHealthy && session) {
    try {
      await ledger.putSession(sessionId, session);
    } catch {
      degradations.push("budget_ledger_write_failed_nonfatal");
    }
  }
  return {
    allowed,
    status,
    clampedBody,
    responseHeaders: {
      "X-Meridian-Context-Phase": phase,
      "X-Meridian-Context-Directive": phase === "SHADOW" ? "ALLOW" : directive,
      "X-Meridian-Context-Tokens": String(est.total),
      "X-Meridian-Context-Soft-Cap": String(rcfg.soft_context_cap),
      "X-Meridian-Context-Hard-Cap": String(effectiveHardCap),
      "X-Meridian-Prefix-Cache-State": kvState,
      "X-Meridian-Critical-Section-Lease": leaseActive ? "ACTIVE" : "NONE"
    },
    violations,
    degradations
  };
}

// context-governance/governance/context-policy.v1.json
var context_policy_v1_default = {
  allowed_phases: [
    "SHADOW",
    "SOFT_ROTATE",
    "ENFORCE"
  ],
  gateway_base_url: "https://llm.meridianlabs.cloud/v1",
  global_invariants: {
    allowed_memory_authority_statuses: [
      "CURRENT"
    ],
    critical_section_max_headroom_ratio: 0.15,
    critical_section_max_turns: 2,
    critical_section_renewable: false,
    externalize_tool_result_bytes: 4096,
    forbidden_direct_provider_hosts: [
      "api.deepseek.com",
      "api.openai.com",
      "api.anthropic.com",
      "openrouter.ai",
      "api.z.ai"
    ],
    max_always_on_mcp_tools: 10,
    max_auto_injected_rules_tokens: 1500,
    min_kv_cache_hit_ratio_target: 0.75,
    quarantined_memory_namespaces: [
      "self-test",
      "probe",
      "healthcheck",
      "canary-probe"
    ],
    retain_recent_images_count: 1,
    subagent_max_brief_tokens: 4e3
  },
  roles: {
    "role:architecture-audit": {
      description: "Frontier architectural planning, formal specs, adversarial review",
      hard_context_cap: 64e3,
      max_grace_turns_after_soft: 2,
      max_output_tokens_clamp: 8192,
      mission_aggregate_cap: 2e5,
      reasoning_effort_clamp: "high",
      soft_context_cap: 48e3,
      turn_1_prefix_cap: 12e3
    },
    "role:ops-dispatch": {
      description: "Cline deploy dispatch, gh CLI, curl probes, incident triage",
      hard_context_cap: 24e3,
      max_grace_turns_after_soft: 1,
      max_output_tokens_clamp: 2048,
      mission_aggregate_cap: 48e3,
      reasoning_effort_clamp: "low",
      soft_context_cap: 16e3,
      turn_1_prefix_cap: 6e3
    },
    "role:sandbox-legion": {
      description: "Lane 3 agent-sandbox and Legion 8 sub-agent swarm",
      hard_context_cap: 48e3,
      max_grace_turns_after_soft: 1,
      max_output_tokens_clamp: 4096,
      mission_aggregate_cap: 16e4,
      reasoning_effort_clamp: "medium",
      soft_context_cap: 32e3,
      turn_1_prefix_cap: 8e3
    },
    "role:surgical-patch": {
      description: "Codex / OpenCode single-PR surgical code repair",
      hard_context_cap: 4e4,
      max_grace_turns_after_soft: 1,
      max_output_tokens_clamp: 4096,
      mission_aggregate_cap: 12e4,
      reasoning_effort_clamp: "medium",
      soft_context_cap: 28e3,
      turn_1_prefix_cap: 8e3
    }
  },
  rollout_phase: "SHADOW",
  schema: "urn:estate:context:policy:v1",
  tokenizer_safety_multipliers: {
    deepseek: 1.25,
    default: 1.15,
    gemini: 1.1,
    glm: 1.25,
    minimax: 1.25,
    nemotron: 1.2
  },
  version: "1.0.0"
};

// src/context-shadow.ts
var KEY = "context_shadow_v1";
var MAX_SESSIONS = 128;
var policy = { ...context_policy_v1_default, rollout_phase: "SHADOW" };
var empty = () => ({ observations: 0, estimatedTokens: 0, warnings: 0, sessions: {} });
async function digest(value) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(bytes), (b) => b.toString(16).padStart(2, "0")).join("");
}
async function observeContext(stub, request, body, role, clientToken, sourceSha) {
  const serialized = JSON.stringify(body);
  if (serialized.length > 1048576) return;
  const session = request.headers.get("x-meridian-session-id")?.slice(0, 128) || crypto.randomUUID();
  const mission = request.headers.get("x-meridian-mission-id")?.slice(0, 128) || "unattributed";
  const scope = await digest(JSON.stringify([await digest(clientToken), session, mission, role]));
  const contextRole = role === "role:coder" ? "role:surgical-patch" : role === "role:architect" ? "role:architecture-audit" : "role:ops-dispatch";
  const response = await stub.fetch("https://ledger.internal/context/observe", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ scope, role: contextRole, request: body, sourceSha })
  });
  if (!response.ok) throw new Error("context_observer_unavailable");
}
async function contextSnapshot(storage) {
  const snapshot = await storage.get(KEY) || empty();
  return Response.json({
    schema: "urn:estate:context:shadow-observation:v1",
    phase: "SHADOW",
    observations: snapshot.observations,
    estimatedTokens: snapshot.estimatedTokens,
    warnings: snapshot.warnings,
    retainedSessions: Object.keys(snapshot.sessions).length,
    lastObservation: snapshot.lastObservation ?? null,
    measurement: "estimate",
    providerUsageCoverage: null,
    cacheHitRatio: null,
    enforcementEnabled: false
  });
}
async function recordContext(state, input) {
  const data = input;
  if (!data || !/^[a-f0-9]{64}$/.test(data.scope) || !Object.hasOwn(policy.roles, data.role) || !data.request || typeof data.sourceSha !== "string") {
    return Response.json({ error: "invalid_context_observation" }, { status: 400 });
  }
  return state.storage.transaction(async () => {
    const snapshot = await state.storage.get(KEY) || empty();
    const now = Date.now();
    const ledger = {
      getSession: async () => snapshot.sessions[data.scope]?.record ?? null,
      putSession: async (_id, record) => {
        snapshot.sessions[data.scope] = { record, observedAt: now };
      },
      // Mission enforcement is deliberately not inferred from this observation-only counter.
      getMissionTotal: async () => 0
    };
    const result = await gateRouterIngress(data.request, new Headers({
      "x-meridian-role": data.role,
      "x-meridian-session-id": data.scope
    }), policy, ledger);
    const tokens = Number(result.responseHeaders["X-Meridian-Context-Tokens"]);
    snapshot.observations += 1;
    snapshot.estimatedTokens += tokens;
    snapshot.warnings += result.violations.length;
    snapshot.lastObservation = {
      sourceSha: data.sourceSha.slice(0, 64),
      observedAt: now,
      role: data.role,
      estimatedTokens: tokens,
      violations: result.violations
    };
    const ordered = Object.keys(snapshot.sessions).sort((a, b) => snapshot.sessions[b].observedAt - snapshot.sessions[a].observedAt);
    for (const key of ordered.slice(MAX_SESSIONS)) delete snapshot.sessions[key];
    await state.storage.put(KEY, snapshot);
    return Response.json({ observed: true, phase: "SHADOW" });
  });
}

// src/ledger-do.ts
var DEFAULT_DAILY_LIMIT_USD = 25;
var STORAGE_KEY = "ledger_state_v1";
function utcDay(nowMs) {
  return new Date(nowMs).toISOString().slice(0, 10);
}
var BudgetLedgerDO = class {
  state;
  constructor(state) {
    this.state = state;
  }
  async load(nowMs) {
    const today = utcDay(nowMs);
    const stored = await this.state.storage.get(STORAGE_KEY);
    if (!stored || stored.epochDay !== today) {
      const fresh = {
        epochDay: today,
        dailyLimitUsd: stored?.dailyLimitUsd ?? DEFAULT_DAILY_LIMIT_USD,
        spentUsd: 0,
        reservations: {}
      };
      await this.state.storage.put(STORAGE_KEY, fresh);
      return fresh;
    }
    let mutated = false;
    for (const [id, entry] of Object.entries(stored.reservations)) {
      if (entry.expiresAtMs <= nowMs) {
        delete stored.reservations[id];
        mutated = true;
      }
    }
    if (mutated) {
      await this.state.storage.put(STORAGE_KEY, stored);
    }
    return stored;
  }
  sumReserved(snap) {
    let total = 0;
    for (const entry of Object.values(snap.reservations)) {
      total += entry.estimatedUsd;
    }
    return total;
  }
  async fetch(request) {
    const url = new URL(request.url);
    const nowMs = Date.now();
    try {
      if (request.method === "GET" && url.pathname === "/context/status") return contextSnapshot(this.state.storage);
      if (request.method === "POST" && url.pathname === "/context/observe") return recordContext(this.state, await request.json());
      if (request.method === "GET" && url.pathname === "/status") {
        const snap = await this.load(nowMs);
        const reservedUsd = this.sumReserved(snap);
        return Response.json({
          ok: true,
          epochDay: snap.epochDay,
          dailyLimitUsd: snap.dailyLimitUsd,
          spentUsd: Number(snap.spentUsd.toFixed(6)),
          reservedUsd: Number(reservedUsd.toFixed(6)),
          remainingUsd: Number(Math.max(0, snap.dailyLimitUsd - snap.spentUsd - reservedUsd).toFixed(6)),
          activeReservations: Object.keys(snap.reservations).length
        });
      }
      if (request.method === "POST" && url.pathname === "/configure") {
        const body = await request.json();
        if (typeof body.dailyLimitUsd !== "number" || body.dailyLimitUsd < 0 || !Number.isFinite(body.dailyLimitUsd)) {
          return Response.json({ error: "invalid_daily_limit" }, { status: 400 });
        }
        const snap = await this.load(nowMs);
        snap.dailyLimitUsd = body.dailyLimitUsd;
        if (body.resetSpend) {
          snap.spentUsd = 0;
          snap.reservations = {};
        }
        await this.state.storage.put(STORAGE_KEY, snap);
        return Response.json({ ok: true, dailyLimitUsd: snap.dailyLimitUsd, spentUsd: snap.spentUsd });
      }
      if (request.method === "POST" && url.pathname === "/reserve") {
        const body = await request.json();
        if (!body.reservationId || body.estimatedUsd < 0 || !Number.isFinite(body.estimatedUsd)) {
          return Response.json({ error: "invalid_reserve_request" }, { status: 400 });
        }
        const result = await this.state.storage.transaction(async () => {
          const snap = await this.load(nowMs);
          const reservedUsd = this.sumReserved(snap);
          const remaining = snap.dailyLimitUsd - snap.spentUsd - reservedUsd;
          if (body.estimatedUsd > remaining + 1e-9) {
            const denied = {
              ok: false,
              code: "BUDGET_EXHAUSTED",
              remainingUsd: Number(Math.max(0, remaining).toFixed(6)),
              dailyLimitUsd: snap.dailyLimitUsd,
              spentUsd: Number(snap.spentUsd.toFixed(6)),
              reservedUsd: Number(reservedUsd.toFixed(6))
            };
            return denied;
          }
          snap.reservations[body.reservationId] = {
            estimatedUsd: body.estimatedUsd,
            expiresAtMs: nowMs + Math.max(5e3, body.ttlMs || 12e4),
            role: body.role
          };
          await this.state.storage.put(STORAGE_KEY, snap);
          const nextReserved = reservedUsd + body.estimatedUsd;
          const approved = {
            ok: true,
            code: "RESERVED",
            remainingUsd: Number(Math.max(0, snap.dailyLimitUsd - snap.spentUsd - nextReserved).toFixed(6)),
            dailyLimitUsd: snap.dailyLimitUsd,
            spentUsd: Number(snap.spentUsd.toFixed(6)),
            reservedUsd: Number(nextReserved.toFixed(6))
          };
          return approved;
        });
        return Response.json(result, { status: result.ok ? 200 : 429 });
      }
      if (request.method === "POST" && url.pathname === "/settle") {
        const body = await request.json();
        await this.state.storage.transaction(async () => {
          const snap = await this.load(nowMs);
          delete snap.reservations[body.reservationId];
          if (typeof body.actualUsd === "number" && body.actualUsd > 0 && Number.isFinite(body.actualUsd)) {
            snap.spentUsd += body.actualUsd;
          }
          await this.state.storage.put(STORAGE_KEY, snap);
        });
        return Response.json({ ok: true });
      }
      if (request.method === "POST" && url.pathname === "/release") {
        const body = await request.json();
        await this.state.storage.transaction(async () => {
          const snap = await this.load(nowMs);
          delete snap.reservations[body.reservationId];
          await this.state.storage.put(STORAGE_KEY, snap);
        });
        return Response.json({ ok: true });
      }
      return Response.json({ error: "not_found" }, { status: 404 });
    } catch (err) {
      return Response.json(
        { error: { type: "ledger_unavailable", detail: err instanceof Error ? err.message : String(err) } },
        { status: 503 }
      );
    }
  }
};

// src/routing-do.ts
var ROLES_KEY = "roles_v1";
var CIRCUITS_KEY = "circuits_v1";
var LEARNED_413_TTL_MS = 10 * 60 * 1e3;
var BASE_COOLDOWN_MS = 15e3;
var MAX_COOLDOWN_MS = 3e5;
var RoutingStateDO = class {
  state;
  constructor(state) {
    this.state = state;
  }
  async getRoles() {
    return await this.state.storage.get(ROLES_KEY) ?? {};
  }
  async getCircuits() {
    return await this.state.storage.get(CIRCUITS_KEY) ?? {};
  }
  async fetch(request) {
    const url = new URL(request.url);
    const nowMs = Date.now();
    if (request.method === "GET" && url.pathname === "/roles") {
      const roles = await this.getRoles();
      return Response.json({ roles });
    }
    if (request.method === "PUT" && url.pathname === "/roles") {
      const body = await request.json();
      if (!body || typeof body.roles !== "object") {
        return Response.json({ error: "invalid_roles_payload" }, { status: 400 });
      }
      for (const [roleName, pool] of Object.entries(body.roles)) {
        if (!Array.isArray(pool.candidates) || pool.candidates.length === 0) {
          return Response.json({ error: `role_${roleName}_requires_candidates` }, { status: 400 });
        }
        for (const c of pool.candidates) {
          if (!c.id || !c.baseUrl || !c.apiKeySecretName || !c.upstreamModel || c.maxContextTokens <= 0) {
            return Response.json({ error: `invalid_candidate_${c.id || "unknown"}` }, { status: 400 });
          }
        }
      }
      await this.state.storage.put(ROLES_KEY, body.roles);
      return Response.json({ ok: true, roleCount: Object.keys(body.roles).length });
    }
    if (request.method === "GET" && url.pathname === "/circuits") {
      const circuits = await this.getCircuits();
      return Response.json({ circuits, nowMs });
    }
    if (request.method === "POST" && url.pathname === "/plan") {
      const req = await request.json();
      const roles = await this.getRoles();
      const pool = roles[req.role] ?? roles["role:default"];
      if (!pool) {
        return Response.json({ error: "unknown_role", role: req.role }, { status: 404 });
      }
      const circuits = await this.getCircuits();
      const excluded = new Set(req.excludeBackendIds ?? []);
      const effectiveOutputTokens = Math.max(req.requestedOutputTokens, pool.minOutputFloor || 2048);
      const requiredTotalTokens = req.estimatedInputTokens + effectiveOutputTokens;
      const eligible = [];
      const rejected = [];
      const sorted = [...pool.candidates].sort((a, b) => a.priority - b.priority);
      for (const candidate of sorted) {
        if (!candidate.enabled) {
          rejected.push({ id: candidate.id, reason: "disabled" });
          continue;
        }
        if (excluded.has(candidate.id)) {
          rejected.push({ id: candidate.id, reason: "excluded_by_caller" });
          continue;
        }
        if (req.requiresTools && !candidate.supportsTools) {
          rejected.push({ id: candidate.id, reason: "tools_unsupported" });
          continue;
        }
        const circuit = circuits[candidate.id];
        if (circuit && circuit.openUntilMs > nowMs) {
          rejected.push({
            id: candidate.id,
            reason: `circuit_open_until_${circuit.openUntilMs}_code_${circuit.lastErrorCode ?? 0}`
          });
          continue;
        }
        const learnedCap = circuit?.learnedMaxContextTokens && (circuit.learnedMaxExpiresMs ?? 0) > nowMs ? circuit.learnedMaxContextTokens : Infinity;
        const effectiveMaxContext = Math.min(candidate.maxContextTokens, learnedCap);
        if (requiredTotalTokens > effectiveMaxContext) {
          rejected.push({
            id: candidate.id,
            reason: `payload_exceeds_context:${requiredTotalTokens}>${effectiveMaxContext}`
          });
          continue;
        }
        eligible.push(candidate);
      }
      const response = {
        role: pool.role,
        effectiveOutputTokens,
        eligible,
        rejected
      };
      return Response.json(response);
    }
    if (request.method === "POST" && url.pathname === "/record") {
      const body = await request.json();
      const circuits = await this.getCircuits();
      const prev = circuits[body.backendId] ?? { failures: 0, openUntilMs: 0 };
      if (body.outcome === "success") {
        circuits[body.backendId] = {
          failures: 0,
          openUntilMs: 0,
          learnedMaxContextTokens: prev.learnedMaxContextTokens,
          learnedMaxExpiresMs: prev.learnedMaxExpiresMs
        };
      } else if (body.outcome === "payload_too_large") {
        const safeCap = Math.max(512, Math.floor((body.observedTokens ?? 4096) * 0.85));
        circuits[body.backendId] = {
          ...prev,
          learnedMaxContextTokens: prev.learnedMaxContextTokens ? Math.min(prev.learnedMaxContextTokens, safeCap) : safeCap,
          learnedMaxExpiresMs: nowMs + LEARNED_413_TTL_MS,
          lastErrorCode: 413,
          lastErrorAtMs: nowMs
        };
      } else {
        const failures = prev.failures + 1;
        const cooldown = Math.min(MAX_COOLDOWN_MS, BASE_COOLDOWN_MS * Math.pow(2, Math.min(failures - 1, 5)));
        circuits[body.backendId] = {
          ...prev,
          failures,
          openUntilMs: nowMs + cooldown,
          lastErrorCode: body.statusCode ?? 503,
          lastErrorAtMs: nowMs
        };
      }
      await this.state.storage.put(CIRCUITS_KEY, circuits);
      return Response.json({ ok: true, circuit: circuits[body.backendId] });
    }
    return Response.json({ error: "not_found" }, { status: 404 });
  }
};

// src/index.ts
var FAILOVER_STATUS_CODES = /* @__PURE__ */ new Set([408, 413, 429, 500, 502, 503, 504, 520, 522, 524, 525, 530]);
async function timingSafeTokenEqual(provided, expected) {
  if (!provided || !expected) return false;
  const enc = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(provided)),
    crypto.subtle.digest("SHA-256", enc.encode(expected))
  ]);
  const viewA = new Uint8Array(a);
  const viewB = new Uint8Array(b);
  let diff = 0;
  for (let i = 0; i < viewA.length; i++) {
    diff |= viewA[i] ^ viewB[i];
  }
  return diff === 0;
}
function extractBearer(request) {
  const header = request.headers.get("authorization") ?? "";
  if (!header.toLowerCase().startsWith("bearer ")) return "";
  return header.slice(7).trim();
}
function estimateRequestInputTokens(req) {
  const encoder = new TextEncoder();
  const payloadBytes = encoder.encode(JSON.stringify(req.messages ?? [])).byteLength + (req.tools ? encoder.encode(JSON.stringify(req.tools)).byteLength : 0);
  return Math.ceil(payloadBytes / 3.2) + 128;
}
function estimateCostUsd(candidate, inputTokens, outputTokens) {
  return inputTokens / 1e3 * candidate.costPer1kInputUsd + outputTokens / 1e3 * candidate.costPer1kOutputUsd;
}
function resolveRole(modelField) {
  if (!modelField || !modelField.trim()) return "role:default";
  const normalized = modelField.trim();
  if (normalized.startsWith("role:")) return normalized;
  return `role:${normalized}`;
}
function getLedgerStub(env) {
  return env.BUDGET_LEDGER.get(env.BUDGET_LEDGER.idFromName("global-ledger-v1"));
}
function getRoutingStub(env) {
  return env.ROUTING_STATE.get(env.ROUTING_STATE.idFromName("global-routing-v1"));
}
async function recordOutcome(routingStub, backendId, outcome, statusCode, observedTokens) {
  await routingStub.fetch("https://routing.internal/record", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ backendId, outcome, statusCode, observedTokens })
  });
}
async function releaseReservation(ledgerStub, reservationId) {
  await ledgerStub.fetch("https://ledger.internal/release", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ reservationId })
  });
}
async function settleReservation(ledgerStub, reservationId, actualUsd) {
  await ledgerStub.fetch("https://ledger.internal/settle", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ reservationId, actualUsd })
  });
}
async function probeFirstStreamChunk(upstreamBody) {
  const reader = upstreamBody.getReader();
  const decoder = new TextDecoder();
  const buffered = [];
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
    }
    return { ok: false, reason: err instanceof Error ? err.message : "stream_read_error" };
  }
  const reassembled = new ReadableStream({
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
    }
  });
  return { ok: true, stream: reassembled };
}
var index_default = {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const commitSha = env.COMMIT_SHA || "unknown";
    const zone = env.DEPLOYMENT_ZONE || "zone-b-cloudflare-edge";
    if (request.method === "GET" && (url.pathname === "/health" || url.pathname === "/health/liveliness")) {
      const [ledgerRes, rolesRes] = await Promise.all([
        getLedgerStub(env).fetch("https://ledger.internal/status").then((r) => r.ok).catch(() => false),
        getRoutingStub(env).fetch("https://routing.internal/roles").then(async (r) => r.ok ? Object.keys((await r.json()).roles).length : -1).catch(() => -1)
      ]);
      const healthy = ledgerRes && rolesRes >= 0;
      return Response.json(
        {
          status: healthy ? "ok" : "degraded",
          commit_sha: commitSha,
          zone,
          ledger_ok: ledgerRes,
          configured_roles: rolesRes,
          timestamp: (/* @__PURE__ */ new Date()).toISOString()
        },
        { status: healthy ? 200 : 503 }
      );
    }
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
          body: request.method === "PUT" ? await request.text() : void 0
        });
      }
      if (url.pathname === "/admin/v1/circuits" && request.method === "GET") {
        return getRoutingStub(env).fetch("https://routing.internal/circuits");
      }
      if (url.pathname === "/admin/v1/context" && request.method === "GET") {
        return getLedgerStub(env).fetch("https://ledger.internal/context/status");
      }
      if (url.pathname === "/admin/v1/budget") {
        const targetPath = request.method === "POST" ? "/configure" : "/status";
        return getLedgerStub(env).fetch(`https://ledger.internal${targetPath}`, {
          method: request.method,
          headers: { "content-type": "application/json" },
          body: request.method === "POST" ? await request.text() : void 0
        });
      }
      return Response.json({ error: { type: "not_found" } }, { status: 404 });
    }
    if (request.method === "POST" && url.pathname === "/v1/chat/completions") {
      const clientToken = extractBearer(request);
      const isAuthorized = await timingSafeTokenEqual(clientToken, env.MERIDIAN_CLIENT_KEY);
      if (!isAuthorized) {
        return Response.json({ error: { type: "unauthorized", detail: "invalid_api_key" } }, { status: 401 });
      }
      let body;
      try {
        body = await request.json();
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
      ctx.waitUntil(observeContext(ledgerStub, request, body, role, clientToken, commitSha).catch(() => {
      }));
      const planRes = await routingStub.fetch("https://routing.internal/plan", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          role,
          estimatedInputTokens,
          requestedOutputTokens: requestedOutput,
          requiresTools
        })
      });
      if (!planRes.ok) {
        return Response.json(
          { error: { type: "admission_refused", detail: await planRes.text() } },
          { status: planRes.status }
        );
      }
      const plan = await planRes.json();
      if (plan.eligible.length === 0) {
        return Response.json(
          {
            error: {
              type: "no_eligible_backend",
              role: plan.role,
              estimated_input_tokens: estimatedInputTokens,
              effective_output_tokens: plan.effectiveOutputTokens,
              rejected: plan.rejected
            }
          },
          { status: 503 }
        );
      }
      const worstCaseUsd = Math.max(...plan.eligible.map((c) => estimateCostUsd(c, estimatedInputTokens, plan.effectiveOutputTokens)));
      const reservationId = crypto.randomUUID();
      const ttlMs = Number(env.RESERVATION_TTL_MS || "120000");
      let reserveRes;
      try {
        reserveRes = await ledgerStub.fetch("https://ledger.internal/reserve", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            reservationId,
            role: plan.role,
            estimatedUsd: worstCaseUsd,
            ttlMs
          })
        });
      } catch (err) {
        return Response.json(
          {
            error: {
              type: "ledger_unavailable",
              detail: err instanceof Error ? err.message : "ledger_unreachable"
            }
          },
          { status: 503 }
        );
      }
      if (reserveRes.status === 429) {
        const detail = await reserveRes.json();
        return Response.json({ error: { type: "budget_exhausted", ...detail } }, { status: 429 });
      }
      if (!reserveRes.ok) {
        return Response.json(
          { error: { type: "ledger_unavailable", detail: await reserveRes.text() } },
          { status: 503 }
        );
      }
      const attemptErrors = [];
      const timeoutMs = Number(env.UPSTREAM_TIMEOUT_MS || "45000");
      for (let i = 0; i < plan.eligible.length; i++) {
        const candidate = plan.eligible[i];
        const upstreamKey = env[candidate.apiKeySecretName];
        if (typeof upstreamKey !== "string" || !upstreamKey) {
          attemptErrors.push({ backendId: candidate.id, status: 500, detail: `missing_secret_${candidate.apiKeySecretName}` });
          continue;
        }
        const boundedOutput = Math.min(plan.effectiveOutputTokens, candidate.maxOutputTokens);
        const upstreamPayload = {
          ...body,
          model: candidate.upstreamModel,
          max_tokens: boundedOutput
        };
        delete upstreamPayload.max_completion_tokens;
        let upstreamRes;
        try {
          upstreamRes = await fetch(candidate.baseUrl, {
            method: "POST",
            headers: {
              "content-type": "application/json",
              authorization: `Bearer ${upstreamKey}`
            },
            body: JSON.stringify(upstreamPayload),
            signal: AbortSignal.timeout(timeoutMs)
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
            detail: errText.slice(0, 200)
          });
          ctx.waitUntil(recordOutcome(routingStub, candidate.id, "transient_failure", upstreamRes.status));
          continue;
        }
        if (!upstreamRes.ok) {
          const errBody = await upstreamRes.text().catch(() => "");
          ctx.waitUntil(releaseReservation(ledgerStub, reservationId));
          return new Response(errBody, {
            status: upstreamRes.status,
            headers: {
              "content-type": upstreamRes.headers.get("content-type") ?? "application/json",
              "x-meridian-backend": candidate.id,
              "x-meridian-commit-sha": commitSha
            }
          });
        }
        if (body.stream && upstreamRes.body) {
          const probed = await probeFirstStreamChunk(upstreamRes.body);
          if (!probed.ok) {
            attemptErrors.push({ backendId: candidate.id, status: 502, detail: probed.reason });
            ctx.waitUntil(recordOutcome(routingStub, candidate.id, "transient_failure", 502));
            continue;
          }
          ctx.waitUntil(recordOutcome(routingStub, candidate.id, "success", 200));
          const { readable, writable } = new TransformStream();
          const streamCost = estimateCostUsd(candidate, estimatedInputTokens, boundedOutput);
          ctx.waitUntil(
            probed.stream.pipeTo(writable).catch(() => {
            }).finally(() => settleReservation(ledgerStub, reservationId, streamCost))
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
              "x-meridian-reservation-id": reservationId
            }
          });
        }
        const rawText = await upstreamRes.text();
        let actualUsd = estimateCostUsd(candidate, estimatedInputTokens, boundedOutput);
        try {
          const parsed = JSON.parse(rawText);
          if (parsed.usage?.prompt_tokens != null && parsed.usage?.completion_tokens != null) {
            actualUsd = estimateCostUsd(candidate, parsed.usage.prompt_tokens, parsed.usage.completion_tokens);
          }
        } catch {
        }
        ctx.waitUntil(
          Promise.all([
            recordOutcome(routingStub, candidate.id, "success", 200),
            settleReservation(ledgerStub, reservationId, actualUsd)
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
            "x-meridian-reservation-id": reservationId
          }
        });
      }
      ctx.waitUntil(releaseReservation(ledgerStub, reservationId));
      return Response.json(
        {
          error: {
            type: "all_pool_backends_failed",
            role: plan.role,
            attempts: attemptErrors,
            pre_filtered_rejected: plan.rejected
          }
        },
        { status: 503 }
      );
    }
    return Response.json({ error: { type: "not_found" } }, { status: 404 });
  }
};
export {
  BudgetLedgerDO,
  RoutingStateDO,
  index_default as default,
  estimateRequestInputTokens
};
