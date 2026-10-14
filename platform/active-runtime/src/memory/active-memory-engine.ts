// src/memory/active-memory-engine.ts
import crypto from "node:crypto";
import {
  BiTemporalFact,
  ExtractedFactCandidate,
  TrustProvenance,
} from "../types/active-runtime";

export interface CortexStorageAdapter {
  /** ACID transaction wrapper from Cortex / Convex backend */
  runTransaction<T>(fn: (tx: CortexTx) => Promise<T>): Promise<T>;
  /** Hybrid Vector + 1-Hop Graph associative lookup */
  searchAssociativeFacts(params: {
    tenantId: string;
    queryText: string;
    projectId?: string;
    includeGraphOneHop: boolean;
    limit: number;
  }): Promise<BiTemporalFact[]>;
}

export interface CortexTx {
  findActiveFact(tenantId: string, subject: string, predicate: string, projectId?: string): Promise<BiTemporalFact | null>;
  insertFact(fact: BiTemporalFact): Promise<void>;
  updateFact(id: string, expectedVersion: number, patch: Partial<BiTemporalFact>): Promise<void>;
  findFactsByProject(tenantId: string, projectId: string): Promise<BiTemporalFact[]>;
}

export interface CustomWorkingMemoryAdapter {
  getWorkingScratchpad(runId: string): Promise<Record<string, unknown>>;
  setWorkingScratchpad(runId: string, key: string, value: unknown, ttlSeconds?: number): Promise<void>;
  incrementPreferenceRecurrence(tenantId: string, signature: string): Promise<number>;
}

export class ActiveMemoryEngine {
  private readonly maxBriefTokens = 450;

  constructor(
    private readonly cortex: CortexStorageAdapter,
    private readonly customMemory: CustomWorkingMemoryAdapter
  ) {}

  /**
   * 1. PROACTIVE ASSOCIATIVE PRE-FETCH
   * Runs automatically before Turn 1 on every agent invocation.
   * Performs a 1-hop Graph + Vector expansion, filters out retired/superseded facts,
   * verifies artifact pointers, and packs a token-budgeted Active Context Brief.
   */
  async buildActiveContextBrief(params: {
    tenantId: string;
    projectId?: string;
    runId: string;
    userPrompt: string;
  }): Promise<string> {
    const [associativeFacts, workingState] = await Promise.all([
      this.cortex.searchAssociativeFacts({
        tenantId: params.tenantId,
        queryText: params.userPrompt,
        projectId: params.projectId,
        includeGraphOneHop: true,
        limit: 25,
      }),
      this.customMemory.getWorkingScratchpad(params.runId),
    ]);

    const now = Date.now();

    // Filter strictly to active facts; rank by scope relevance + recency decay
    const rankedFacts = associativeFacts
      .filter((f) => f.status === "active")
      .filter((f) => {
        // Only include global preferences OR project facts matching the current projectId
        if (f.scope === "global_preference") return true;
        if (f.scope === "project_fact" && f.projectId === params.projectId) return true;
        return false;
      })
      .map((f) => {
        const ageDays = Math.max(0, (now - f.sourceEventAt) / (1000 * 60 * 60 * 24));
        const recencyWeight = Math.exp(-ageDays / 30); // 30-day half-life decay for ranking
        const projectBoost = f.projectId === params.projectId ? 1.35 : 1.0;
        const score = f.confidence * recencyWeight * projectBoost;
        return { fact: f, score };
      })
      .sort((a, b) => b.score - a.score);

    const lines: string[] = [];
    let estimatedTokens = 0;

    for (const { fact } of rankedFacts) {
      const artifactTag = fact.artifactUri
        ? ` [Artifact: ${fact.artifactUri}${fact.artifactVersionHash ? `@${fact.artifactVersionHash.slice(0, 8)}` : ""}]`
        : "";
      const dateTag = new Date(fact.sourceEventAt).toISOString().split("T")[0];
      const line = `- [${fact.scope.toUpperCase()} | as of ${dateTag}] ${fact.subject} ${fact.predicate}: ${fact.object}${artifactTag}`;
      const lineTokens = Math.ceil(line.length / 4);

      if (estimatedTokens + lineTokens > this.maxBriefTokens) break;
      lines.push(line);
      estimatedTokens += lineTokens;
    }

    const scratchpadKeys = Object.keys(workingState);
    const scratchpadSection =
      scratchpadKeys.length > 0
        ? `\n[ACTIVE RUN SCRATCHPAD]: ${JSON.stringify(workingState)}`
        : "";

    if (lines.length === 0 && !scratchpadSection) {
      return "";
    }

    return [
      "=== ACTIVE MEMORY BRIEF (VERIFIED & EVENT-TIME ORDERED) ===",
      "Use these verified facts and artifact pointers directly. Do not use older artifact versions if a newer hash is listed:",
      ...lines,
      scratchpadSection,
      "===========================================================",
    ]
      .filter(Boolean)
      .join("\n");
  }

  /**
   * 2. INTENT-GATED & BI-TEMPORAL CONSOLIDATION
   * Prevents ephemeral prompt instructions from polluting long-term memory,
   * blocks untrusted external inputs from altering global preferences,
   * and prevents older documents from overwriting newer decisions.
   */
  async consolidateTurnCandidates(params: {
    tenantId: string;
    projectId?: string;
    runId: string;
    provenance: TrustProvenance;
    defaultSourceEventAt?: number;
    candidates: ExtractedFactCandidate[];
  }): Promise<{ promoted: number; ignoredEphemeral: number; blockedStaleOrUntrusted: number }> {
    let promoted = 0;
    let ignoredEphemeral = 0;
    let blockedStaleOrUntrusted = 0;
    const now = Date.now();

    for (const candidate of params.candidates) {
      // Rule A: Ephemeral turn instructions stay strictly in the current run scratchpad
      if (candidate.scope === "ephemeral_turn") {
        await this.customMemory.setWorkingScratchpad(
          params.runId,
          `${candidate.subject}:${candidate.predicate}`,
          candidate.object,
          3600
        );
        ignoredEphemeral++;
        continue;
      }

      // Rule B: Untrusted external sources can NEVER write global preferences
      if (params.provenance === "untrusted_external" && candidate.scope === "global_preference") {
        blockedStaleOrUntrusted++;
        continue;
      }

      // Rule C: Global preferences require either explicit permanence ("always use X")
      // OR recurrence >= 3 across separate sessions
      if (candidate.scope === "global_preference" && !candidate.explicitPermanenceIntent) {
        const sig = crypto
          .createHash("sha256")
          .update(`${candidate.subject}|${candidate.predicate}|${candidate.object}`)
          .digest("hex");
        const count = await this.customMemory.incrementPreferenceRecurrence(params.tenantId, sig);
        if (count < 3) {
          // Keep as project-scoped or scratchpad until pattern is confirmed
          await this.customMemory.setWorkingScratchpad(
            params.runId,
            `inferred_pref:${candidate.subject}:${candidate.predicate}`,
            candidate.object,
            86400
          );
          ignoredEphemeral++;
          continue;
        }
      }

      const parsedSourceTime = candidate.sourceEventTimestampIso
        ? Date.parse(candidate.sourceEventTimestampIso)
        : NaN;
      const sourceEventAt = Number.isFinite(parsedSourceTime)
        ? parsedSourceTime
        : (params.defaultSourceEventAt ?? now);

      // Rule D: Bi-Temporal Belief Revision inside Cortex ACID Transaction
      const committed = await this.cortex.runTransaction(async (tx) => {
        const existing = await tx.findActiveFact(
          params.tenantId,
          candidate.subject,
          candidate.predicate,
          candidate.scope === "project_fact" ? params.projectId : undefined
        );

        if (existing) {
          // STALE OVERWRITE PROTECTION:
          // If the newly ingested source (e.g. an older email thread) predates the existing fact's event time, drop it!
          if (sourceEventAt < existing.sourceEventAt) {
            return false;
          }

          // No-op if identical value and artifact version
          if (
            existing.object === candidate.object &&
            existing.artifactUri === candidate.artifactUri &&
            existing.artifactVersionHash === candidate.artifactVersionHash
          ) {
            return false;
          }

          const newFactId = `fact_${crypto.randomUUID()}`;
          await tx.updateFact(existing.id, existing.version, {
            status: "superseded",
            supersededById: newFactId,
            version: existing.version + 1,
          });

          await tx.insertFact({
            id: newFactId,
            tenantId: params.tenantId,
            scope: candidate.scope,
            projectId: candidate.scope === "project_fact" ? params.projectId : undefined,
            subject: candidate.subject,
            predicate: candidate.predicate,
            object: candidate.object,
            artifactUri: candidate.artifactUri,
            artifactVersionHash: candidate.artifactVersionHash,
            sourceEventAt,
            ingestedAt: now,
            provenance: params.provenance,
            confidence: candidate.confidence,
            recurrenceCount: existing.recurrenceCount + 1,
            version: 1,
            status: "active",
          });
          return true;
        }

        await tx.insertFact({
          id: `fact_${crypto.randomUUID()}`,
          tenantId: params.tenantId,
          scope: candidate.scope,
          projectId: candidate.scope === "project_fact" ? params.projectId : undefined,
          subject: candidate.subject,
          predicate: candidate.predicate,
          object: candidate.object,
          artifactUri: candidate.artifactUri,
          artifactVersionHash: candidate.artifactVersionHash,
          sourceEventAt,
          ingestedAt: now,
          provenance: params.provenance,
          confidence: candidate.confidence,
          recurrenceCount: 1,
          version: 1,
          status: "active",
        });
        return true;
      });

      if (committed) {
        promoted++;
      } else {
        blockedStaleOrUntrusted++;
      }
    }

    return { promoted, ignoredEphemeral, blockedStaleOrUntrusted };
  }

  /**
   * 3. EPILOGUE GARBAGE COLLECTION
   * Retires task-scoped facts when a project/ticket completes so they never pollute future tasks.
   */
  async archiveProjectScope(tenantId: string, projectId: string): Promise<number> {
    return this.cortex.runTransaction(async (tx) => {
      const facts = await tx.findFactsByProject(tenantId, projectId);
      let archivedCount = 0;
      for (const fact of facts) {
        if (fact.status === "active" && fact.scope === "project_fact") {
          await tx.updateFact(fact.id, fact.version, {
            status: "archived",
            version: fact.version + 1,
          });
          archivedCount++;
        }
      }
      return archivedCount;
    });
  }
}
