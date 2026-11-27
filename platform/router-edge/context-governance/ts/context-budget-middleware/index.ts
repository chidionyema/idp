/**
 * Meridian Context Budget & Role-Clamping Middleware for Lane 1 Cloudflare Workers
 * (`meridian-router-edge` + `BudgetLedgerDO`).
 *
 * Zero external dependencies (Web Crypto API only).
 * Enforces:
 *  - Streaming-safe ingress gating (never cuts mid-SSE chunk)
 *  - Transparent reasoning_effort & max_tokens clamping per role
 *  - KV-cache prefix_sha256 immutability tracking (zero dynamic injection into prefix)
 *  - Bounded non-renewable Critical-Section Lease (+15% headroom, max 2 turns)
 *  - Degraded fail-open on BudgetLedgerDO transient timeout
 */

export type RolloutPhase = "SHADOW" | "SOFT_ROTATE" | "ENFORCE";

export interface RolePolicy {
  reasoning_effort_clamp: "minimal" | "low" | "medium" | "high";
  max_output_tokens_clamp: number;
  turn_1_prefix_cap: number;
  soft_context_cap: number;
  hard_context_cap: number;
  mission_aggregate_cap: number;
  max_grace_turns_after_soft: number;
}

export interface ContextPolicyManifest {
  rollout_phase: RolloutPhase;
  global_invariants: {
    max_always_on_mcp_tools: number;
    critical_section_max_headroom_ratio: number;
    critical_section_max_turns: number;
    subagent_max_brief_tokens: number;
  };
  tokenizer_safety_multipliers: Record<string, number>;
  roles: Record<string, RolePolicy>;
}

export interface SessionBudgetRecord {
  turn_count: number;
  initial_prefix_hash: string;
  soft_warnings_issued: number;
  critical_section_turns_used: number;
  calibration_ratio: number;
}

export interface LedgerStore {
  getSession(sessionId: string): Promise<SessionBudgetRecord | null>;
  putSession(sessionId: string, rec: SessionBudgetRecord): Promise<void>;
  getMissionTotal(missionId: string): Promise<number>;
}

const REASONING_RANK: Record<string, number> = {
  minimal: 0,
  low: 1,
  medium: 2,
  high: 3,
};

function toHex(buf: ArrayBuffer): string {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function sha256Hex(input: string): Promise<string> {
  const bytes = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return toHex(digest);
}

function estimateTextTokens(text: string, mult: number): number {
  if (!text) return 0;
  const utf8Bytes = new TextEncoder().encode(text).length;
  return Math.max(1, Math.ceil((utf8Bytes / 3.2) * mult));
}

export function estimateRequestTokens(
  body: Record<string, unknown>,
  mult: number
): { total: number; toolCount: number; imageCount: number } {
  const messages = Array.isArray(body.messages) ? body.messages : [];
  const tools = Array.isArray(body.tools) ? body.tools : [];
  let total = tools.length > 0 ? estimateTextTokens(JSON.stringify(tools), mult) : 0;
  let imageCount = 0;

  for (const m of messages) {
    if (!m || typeof m !== "object") continue;
    total += 6;
    const content = (m as Record<string, unknown>).content;
    if (typeof content === "string") {
      total += estimateTextTokens(content, mult);
    } else if (Array.isArray(content)) {
      for (const part of content) {
        if (!part || typeof part !== "object") continue;
        const p = part as Record<string, unknown>;
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

export async function gateRouterIngress(
  requestBody: Record<string, unknown>,
  headersIn: Headers,
  policy: ContextPolicyManifest,
  ledger: LedgerStore
): Promise<{
  allowed: boolean;
  status: number;
  clampedBody: Record<string, unknown>;
  responseHeaders: Record<string, string>;
  violations: string[];
  degradations: string[];
}> {
  const role = headersIn.get("x-meridian-role") || "role:ops-dispatch";
  const sessionId = headersIn.get("x-meridian-session-id") || "ephemeral";
  const missionId = headersIn.get("x-meridian-mission-id") || "unassigned";
  const csNonce = headersIn.get("x-meridian-critical-section");
  const isSubagent = headersIn.get("x-meridian-subagent") === "true";

  const rcfg = policy.roles[role] || policy.roles["role:ops-dispatch"];
  const phase = policy.rollout_phase;
  const degradations: string[] = [];
  const violations: string[] = [];

  let session: SessionBudgetRecord | null = null;
  let missionSpent = 0;
  let ledgerHealthy = true;

  try {
    session = (await ledger.getSession(sessionId)) || {
      turn_count: 0,
      initial_prefix_hash: "",
      soft_warnings_issued: 0,
      critical_section_turns_used: 0,
      calibration_ratio: 1.0,
    };
    missionSpent = await ledger.getMissionTotal(missionId);
  } catch {
    ledgerHealthy = false;
    degradations.push("budget_ledger_unavailable_fail_open");
  }

  // Transparent role clamping (prevents high-reasoning token burn on ops-dispatch)
  const clampedBody: Record<string, unknown> = { ...requestBody };
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
  let mult = policy.tokenizer_safety_multipliers.default ?? 1.15;
  for (const [k, v] of Object.entries(policy.tokenizer_safety_multipliers)) {
    if (k !== "default" && modelStr.includes(k)) {
      mult = v;
      break;
    }
  }
  const cal = session ? session.calibration_ratio : 1.0;
  const est = estimateRequestTokens(clampedBody, mult * cal);

  // Prefix immutability hash (system messages + tools only)
  const messages = Array.isArray(clampedBody.messages) ? clampedBody.messages : [];
  const sysMsgs = messages.filter((m) => (m as Record<string, unknown>)?.role === "system");
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

  if (est.toolCount > policy.global_invariants.max_always_on_mcp_tools) {
    violations.push("ERR_MCP_TOOL_CEILING_EXCEEDED");
  }
  if (isSubagent && session && session.turn_count === 1 && est.total > policy.global_invariants.subagent_max_brief_tokens) {
    violations.push("ERR_SUBAGENT_BRIEF_CAP_EXCEEDED");
  }
  if (missionSpent + est.total > rcfg.mission_aggregate_cap) {
    violations.push("ERR_MISSION_AGGREGATE_BUDGET_EXCEEDED");
  }

  let leaseActive = false;
  let effectiveHardCap = rcfg.hard_context_cap;
  if (csNonce) {
    if (!session || session.critical_section_turns_used < policy.global_invariants.critical_section_max_turns) {
      if (session) session.critical_section_turns_used += 1;
      leaseActive = true;
      effectiveHardCap = Math.ceil(
        rcfg.hard_context_cap * (1 + policy.global_invariants.critical_section_max_headroom_ratio)
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
      "X-Meridian-Critical-Section-Lease": leaseActive ? "ACTIVE" : "NONE",
    },
    violations,
    degradations,
  };
}
