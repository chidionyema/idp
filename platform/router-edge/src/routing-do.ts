import type {
  CircuitRecord,
  PlanRequest,
  PlanResponse,
  RolePool,
} from "./types";
import { selectCapabilities } from "./capability_pool.mjs";

const ROLES_KEY = "roles_v1";
const CIRCUITS_KEY = "circuits_v1";
const LEARNED_413_TTL_MS = 10 * 60 * 1000; // 10 minutes
const BASE_COOLDOWN_MS = 15_000;
const MAX_COOLDOWN_MS = 300_000;

export class RoutingStateDO implements DurableObject {
  private readonly state: DurableObjectState;

  constructor(state: DurableObjectState) {
    this.state = state;
  }

  private async getRoles(): Promise<Record<string, RolePool>> {
    return (await this.state.storage.get<Record<string, RolePool>>(ROLES_KEY)) ?? {};
  }

  private async getCircuits(): Promise<Record<string, CircuitRecord>> {
    return (await this.state.storage.get<Record<string, CircuitRecord>>(CIRCUITS_KEY)) ?? {};
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const nowMs = Date.now();

    if (request.method === "GET" && url.pathname === "/roles") {
      const roles = await this.getRoles();
      return Response.json({ roles });
    }

    if (request.method === "PUT" && url.pathname === "/roles") {
      const body = (await request.json()) as { roles: Record<string, RolePool> };
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
      const req = (await request.json()) as PlanRequest;
      const roles = await this.getRoles();
      const pool = roles[req.role] ?? roles["role:default"];
      if (!pool) {
        return Response.json({ error: "unknown_role", role: req.role }, { status: 404 });
      }

      const circuits = await this.getCircuits();
      const response: PlanResponse = selectCapabilities(pool, req, circuits, nowMs);
      return Response.json(response);
    }

    if (request.method === "POST" && url.pathname === "/record") {
      const body = (await request.json()) as {
        backendId: string;
        outcome: "success" | "payload_too_large" | "transient_failure";
        statusCode?: number;
        observedTokens?: number;
      };

      const circuits = await this.getCircuits();
      const prev: CircuitRecord = circuits[body.backendId] ?? { failures: 0, openUntilMs: 0 };

      if (body.outcome === "success") {
        circuits[body.backendId] = {
          failures: 0,
          openUntilMs: 0,
          learnedMaxContextTokens: prev.learnedMaxContextTokens,
          learnedMaxExpiresMs: prev.learnedMaxExpiresMs,
        };
      } else if (body.outcome === "payload_too_large") {
        // Learn the tighter payload ceiling immediately without tripping the circuit for small requests
        const safeCap = Math.max(512, Math.floor((body.observedTokens ?? 4096) * 0.85));
        circuits[body.backendId] = {
          ...prev,
          learnedMaxContextTokens: prev.learnedMaxContextTokens
            ? Math.min(prev.learnedMaxContextTokens, safeCap)
            : safeCap,
          learnedMaxExpiresMs: nowMs + LEARNED_413_TTL_MS,
          lastErrorCode: 413,
          lastErrorAtMs: nowMs,
        };
      } else {
        const failures = prev.failures + 1;
        const cooldown = Math.min(MAX_COOLDOWN_MS, BASE_COOLDOWN_MS * Math.pow(2, Math.min(failures - 1, 5)));
        circuits[body.backendId] = {
          ...prev,
          failures,
          openUntilMs: nowMs + cooldown,
          lastErrorCode: body.statusCode ?? 503,
          lastErrorAtMs: nowMs,
        };
      }

      await this.state.storage.put(CIRCUITS_KEY, circuits);
      return Response.json({ ok: true, circuit: circuits[body.backendId] });
    }

    return Response.json({ error: "not_found" }, { status: 404 });
  }
}
