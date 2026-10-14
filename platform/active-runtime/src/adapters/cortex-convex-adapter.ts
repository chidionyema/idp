// src/adapters/cortex-convex-adapter.ts
import {
  CortexStorageAdapter,
  CortexTx,
  CustomWorkingMemoryAdapter,
} from "../memory/active-memory-engine";
import { ApprovalStoreAdapter } from "../focus/active-focus-controller";
import { ApprovalTicket, BiTemporalFact } from "../types/active-runtime";

export interface VectorEmbedder {
  embed(text: string): Promise<number[]>;
}

/**
 * Low-level transactional driver interface compatible with Convex/Cortex backend mutations
 * or an in-memory ACID test store.
 */
export interface AcidBackendDriver {
  executeAcidTransaction<T>(fn: (store: AcidTableStore) => Promise<T>): Promise<T>;
  vectorSearchFacts(params: {
    tenantId: string;
    embedding: number[];
    limit: number;
  }): Promise<BiTemporalFact[]>;
  getOneHopNeighbors(params: {
    tenantId: string;
    seedSubjects: string[];
    limit: number;
  }): Promise<BiTemporalFact[]>;
}

export interface AcidTableStore {
  facts: Map<string, BiTemporalFact>;
  approvals: Map<string, ApprovalTicket>;
  idempotency: Map<
    string,
    {
      outcome: "progress" | "blocked" | "failed" | "needs_info" | "done";
      output: string;
      errorCode?: string;
      errorSummary?: string;
    }
  >;
}

export class ProductionCortexAdapter implements CortexStorageAdapter, ApprovalStoreAdapter {
  constructor(
    private readonly backend: AcidBackendDriver,
    private readonly embedder: VectorEmbedder
  ) {}

  async runTransaction<T>(fn: (tx: CortexTx) => Promise<T>): Promise<T> {
    return this.backend.executeAcidTransaction(async (store) => {
      const tx: CortexTx = {
        findActiveFact: async (tenantId, subject, predicate, projectId) => {
          for (const fact of store.facts.values()) {
            // A global lookup (no projectId) matches only global facts: it must never
            // supersede a project-scoped fact that happens to share subject and predicate.
            const matchesProject = fact.projectId === projectId;
            if (
              fact.tenantId === tenantId &&
              fact.subject === subject &&
              fact.predicate === predicate &&
              fact.status === "active" &&
              matchesProject
            ) {
              return { ...fact };
            }
          }
          return null;
        },

        insertFact: async (fact) => {
          if (store.facts.has(fact.id)) {
            throw new Error(`ACID violation: Fact ${fact.id} already exists.`);
          }
          store.facts.set(fact.id, { ...fact });
        },

        updateFact: async (id, expectedVersion, patch) => {
          const existing = store.facts.get(id);
          if (!existing) {
            throw new Error(`ACID violation: Fact ${id} not found.`);
          }
          if (existing.version !== expectedVersion) {
            throw new Error(
              `CAS Conflict on Fact ${id}: expected version ${expectedVersion}, found ${existing.version}`
            );
          }
          store.facts.set(id, { ...existing, ...patch });
        },

        findFactsByProject: async (tenantId, projectId) => {
          const results: BiTemporalFact[] = [];
          for (const fact of store.facts.values()) {
            if (fact.tenantId === tenantId && fact.projectId === projectId) {
              results.push({ ...fact });
            }
          }
          return results;
        },
      };

      return fn(tx);
    });
  }

  async searchAssociativeFacts(params: {
    tenantId: string;
    queryText: string;
    projectId?: string;
    includeGraphOneHop: boolean;
    limit: number;
  }): Promise<BiTemporalFact[]> {
    const queryVector = await this.embedder.embed(params.queryText);
    const directHits = await this.backend.vectorSearchFacts({
      tenantId: params.tenantId,
      embedding: queryVector,
      limit: params.limit,
    });

    if (!params.includeGraphOneHop || directHits.length === 0) {
      return directHits;
    }

    const seedSubjects = Array.from(new Set(directHits.map((f) => f.subject)));
    const oneHopHits = await this.backend.getOneHopNeighbors({
      tenantId: params.tenantId,
      seedSubjects,
      limit: params.limit,
    });

    const deduped = new Map<string, BiTemporalFact>();
    for (const fact of [...directHits, ...oneHopHits]) {
      deduped.set(fact.id, fact);
    }

    return Array.from(deduped.values()).slice(0, params.limit);
  }

  /**
   * Several tickets can share one payload hash over time (spent, expired, then re-requested).
   * Return the one the gate should act on: a live approved ticket, else a live pending one,
   * else a rejected one, else the newest.
   */
  async getTicketByHash(payloadHash: string): Promise<ApprovalTicket | null> {
    return this.backend.executeAcidTransaction(async (store) => {
      const now = Date.now();
      const matches = Array.from(store.approvals.values()).filter(
        (t) => t.payloadHash === payloadHash
      );
      if (matches.length === 0) return null;

      const live = (t: ApprovalTicket) => t.expiresAt > now;
      const best =
        matches.find((t) => t.status === "approved" && live(t)) ??
        matches.find((t) => t.status === "pending" && live(t)) ??
        matches.find((t) => t.status === "rejected") ??
        [...matches].sort((a, b) => b.createdAt - a.createdAt)[0];
      return { ...best };
    });
  }

  async createPendingTicket(ticket: ApprovalTicket): Promise<void> {
    await this.backend.executeAcidTransaction(async (store) => {
      store.approvals.set(ticket.ticketId, { ...ticket });
    });
  }

  /**
   * Atomic Compare-And-Swap ticket consumption: guarantees that even if two workers
   * race on the same approved ticket, only one succeeds and the second halts safely.
   */
  async consumeTicket(ticketId: string): Promise<boolean> {
    return this.backend.executeAcidTransaction(async (store) => {
      const existing = store.approvals.get(ticketId);
      if (!existing || existing.status !== "approved" || existing.expiresAt <= Date.now()) {
        return false;
      }
      store.approvals.set(ticketId, {
        ...existing,
        status: "consumed",
      });
      return true;
    });
  }
}

/**
 * High-speed Custom Working Memory Adapter with TTL scratchpad and recurrence tracking.
 */
export class CustomFastMemoryStore implements CustomWorkingMemoryAdapter {
  private readonly scratchpad = new Map<
    string,
    Map<string, { value: unknown; expiresAt: number }>
  >();
  private readonly recurrenceCounters = new Map<string, number>();

  async getWorkingScratchpad(runId: string): Promise<Record<string, unknown>> {
    const bucket = this.scratchpad.get(runId);
    if (!bucket) return {};
    const now = Date.now();
    const result: Record<string, unknown> = {};
    for (const [key, entry] of bucket.entries()) {
      if (entry.expiresAt > now) {
        result[key] = entry.value;
      } else {
        bucket.delete(key);
      }
    }
    return result;
  }

  async setWorkingScratchpad(
    runId: string,
    key: string,
    value: unknown,
    ttlSeconds = 3600
  ): Promise<void> {
    let bucket = this.scratchpad.get(runId);
    if (!bucket) {
      bucket = new Map();
      this.scratchpad.set(runId, bucket);
    }
    bucket.set(key, {
      value,
      expiresAt: Date.now() + ttlSeconds * 1000,
    });
  }

  async incrementPreferenceRecurrence(
    tenantId: string,
    signature: string
  ): Promise<number> {
    const compositeKey = `${tenantId}:${signature}`;
    const next = (this.recurrenceCounters.get(compositeKey) ?? 0) + 1;
    this.recurrenceCounters.set(compositeKey, next);
    return next;
  }
}
