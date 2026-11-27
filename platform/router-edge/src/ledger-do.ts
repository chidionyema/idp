import type { ReserveRequest, ReserveResponse, SettleRequest } from "./types";
import { contextSnapshot, recordContext } from "./context-shadow";

interface ReservationEntry {
  estimatedUsd: number;
  expiresAtMs: number;
  role: string;
}

interface LedgerSnapshot {
  epochDay: string;
  dailyLimitUsd: number;
  spentUsd: number;
  reservations: Record<string, ReservationEntry>;
}

const DEFAULT_DAILY_LIMIT_USD = 25.0;
const STORAGE_KEY = "ledger_state_v1";

function utcDay(nowMs: number): string {
  return new Date(nowMs).toISOString().slice(0, 10);
}

export class BudgetLedgerDO implements DurableObject {
  private readonly state: DurableObjectState;

  constructor(state: DurableObjectState) {
    this.state = state;
  }

  private async load(nowMs: number): Promise<LedgerSnapshot> {
    const today = utcDay(nowMs);
    const stored = await this.state.storage.get<LedgerSnapshot>(STORAGE_KEY);
    if (!stored || stored.epochDay !== today) {
      const fresh: LedgerSnapshot = {
        epochDay: today,
        dailyLimitUsd: stored?.dailyLimitUsd ?? DEFAULT_DAILY_LIMIT_USD,
        spentUsd: 0,
        reservations: {},
      };
      await this.state.storage.put(STORAGE_KEY, fresh);
      return fresh;
    }
    // Reap expired reservations so crashed requests never leak budget
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

  private sumReserved(snap: LedgerSnapshot): number {
    let total = 0;
    for (const entry of Object.values(snap.reservations)) {
      total += entry.estimatedUsd;
    }
    return total;
  }

  async fetch(request: Request): Promise<Response> {
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
          activeReservations: Object.keys(snap.reservations).length,
        });
      }

      if (request.method === "POST" && url.pathname === "/configure") {
        const body = (await request.json()) as { dailyLimitUsd: number; resetSpend?: boolean };
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
        const body = (await request.json()) as ReserveRequest;
        if (!body.reservationId || body.estimatedUsd < 0 || !Number.isFinite(body.estimatedUsd)) {
          return Response.json({ error: "invalid_reserve_request" }, { status: 400 });
        }

        const result = await this.state.storage.transaction(async () => {
          const snap = await this.load(nowMs);
          const reservedUsd = this.sumReserved(snap);
          const remaining = snap.dailyLimitUsd - snap.spentUsd - reservedUsd;

          if (body.estimatedUsd > remaining + 1e-9) {
            const denied: ReserveResponse = {
              ok: false,
              code: "BUDGET_EXHAUSTED",
              remainingUsd: Number(Math.max(0, remaining).toFixed(6)),
              dailyLimitUsd: snap.dailyLimitUsd,
              spentUsd: Number(snap.spentUsd.toFixed(6)),
              reservedUsd: Number(reservedUsd.toFixed(6)),
            };
            return denied;
          }

          snap.reservations[body.reservationId] = {
            estimatedUsd: body.estimatedUsd,
            expiresAtMs: nowMs + Math.max(5_000, body.ttlMs || 120_000),
            role: body.role,
          };
          await this.state.storage.put(STORAGE_KEY, snap);

          const nextReserved = reservedUsd + body.estimatedUsd;
          const approved: ReserveResponse = {
            ok: true,
            code: "RESERVED",
            remainingUsd: Number(Math.max(0, snap.dailyLimitUsd - snap.spentUsd - nextReserved).toFixed(6)),
            dailyLimitUsd: snap.dailyLimitUsd,
            spentUsd: Number(snap.spentUsd.toFixed(6)),
            reservedUsd: Number(nextReserved.toFixed(6)),
          };
          return approved;
        });

        return Response.json(result, { status: result.ok ? 200 : 429 });
      }

      if (request.method === "POST" && url.pathname === "/settle") {
        const body = (await request.json()) as SettleRequest;
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
        const body = (await request.json()) as { reservationId: string };
        await this.state.storage.transaction(async () => {
          const snap = await this.load(nowMs);
          delete snap.reservations[body.reservationId];
          await this.state.storage.put(STORAGE_KEY, snap);
        });
        return Response.json({ ok: true });
      }

      return Response.json({ error: "not_found" }, { status: 404 });
    } catch (err) {
      // Strictly fail-closed: ledger errors always return 503
      return Response.json(
        { error: { type: "ledger_unavailable", detail: err instanceof Error ? err.message : String(err) } },
        { status: 503 }
      );
    }
  }
}
