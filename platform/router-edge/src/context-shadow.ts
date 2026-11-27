import { gateRouterIngress } from "../context-governance/ts/context-budget-middleware/index";
import type { ContextPolicyManifest, SessionBudgetRecord } from "../context-governance/ts/context-budget-middleware/index";
import rawPolicy from "../context-governance/governance/context-policy.v1.json";

const KEY = "context_shadow_v1";
const MAX_SESSIONS = 128;
const policy = { ...rawPolicy, rollout_phase: "SHADOW" } as ContextPolicyManifest;
type Snapshot = {
  observations: number; estimatedTokens: number; warnings: number;
  sessions: Record<string, { record: SessionBudgetRecord; observedAt: number }>;
  lastObservation?: { sourceSha: string; observedAt: number; role: string; estimatedTokens: number; violations: string[] };
};
const empty = (): Snapshot => ({ observations: 0, estimatedTokens: 0, warnings: 0, sessions: {} });

async function digest(value: string): Promise<string> {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, "0")).join("");
}

export async function observeContext(
  stub: DurableObjectStub, request: Request, body: unknown, role: string, clientToken: string, sourceSha: string
): Promise<void> {
  const serialized = JSON.stringify(body);
  // A shadow measurement never makes a valid large inference fail or doubles an unbounded body.
  if (serialized.length > 1_048_576) return;
  const session = request.headers.get("x-meridian-session-id")?.slice(0, 128) || crypto.randomUUID();
  const mission = request.headers.get("x-meridian-mission-id")?.slice(0, 128) || "unattributed";
  const scope = await digest(JSON.stringify([await digest(clientToken), session, mission, role]));
  const contextRole = role === "role:coder" ? "role:surgical-patch"
    : role === "role:architect" ? "role:architecture-audit" : "role:ops-dispatch";
  const response = await stub.fetch("https://ledger.internal/context/observe", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ scope, role: contextRole, request: body, sourceSha }),
  });
  if (!response.ok) throw new Error("context_observer_unavailable");
}

export async function contextSnapshot(storage: DurableObjectStorage): Promise<Response> {
  const snapshot = await storage.get<Snapshot>(KEY) || empty();
  return Response.json({
    schema: "urn:estate:context:shadow-observation:v1", phase: "SHADOW",
    observations: snapshot.observations, estimatedTokens: snapshot.estimatedTokens,
    warnings: snapshot.warnings, retainedSessions: Object.keys(snapshot.sessions).length,
    lastObservation: snapshot.lastObservation ?? null,
    measurement: "estimate", providerUsageCoverage: null, cacheHitRatio: null,
    enforcementEnabled: false,
  });
}

export async function recordContext(state: DurableObjectState, input: unknown): Promise<Response> {
  const data = input as { scope: string; role: string; request: Record<string, unknown>; sourceSha: string };
  if (!data || !/^[a-f0-9]{64}$/.test(data.scope) || !Object.hasOwn(policy.roles, data.role) || !data.request || typeof data.sourceSha !== "string") {
    return Response.json({ error: "invalid_context_observation" }, { status: 400 });
  }
  return state.storage.transaction(async () => {
    const snapshot = await state.storage.get<Snapshot>(KEY) || empty();
    const now = Date.now();
    const ledger = {
      getSession: async () => snapshot.sessions[data.scope]?.record ?? null,
      putSession: async (_id: string, record: SessionBudgetRecord) => {
        snapshot.sessions[data.scope] = { record, observedAt: now };
      },
      // Mission enforcement is deliberately not inferred from this observation-only counter.
      getMissionTotal: async () => 0,
    };
    const result = await gateRouterIngress(data.request, new Headers({
      "x-meridian-role": data.role, "x-meridian-session-id": data.scope,
    }), policy, ledger);
    const tokens = Number(result.responseHeaders["X-Meridian-Context-Tokens"]);
    snapshot.observations += 1;
    snapshot.estimatedTokens += tokens;
    snapshot.warnings += result.violations.length;
    snapshot.lastObservation = {
      sourceSha: data.sourceSha.slice(0, 64), observedAt: now, role: data.role,
      estimatedTokens: tokens, violations: result.violations,
    };
    const ordered = Object.keys(snapshot.sessions).sort((a, b) => snapshot.sessions[b].observedAt - snapshot.sessions[a].observedAt);
    for (const key of ordered.slice(MAX_SESSIONS)) delete snapshot.sessions[key];
    await state.storage.put(KEY, snapshot);
    return Response.json({ observed: true, phase: "SHADOW" });
  });
}
