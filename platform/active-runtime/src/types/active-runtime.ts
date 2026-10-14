// src/types/active-runtime.ts
import { z } from "zod";

export type TrustProvenance = "user_direct" | "verified_internal" | "untrusted_external";
export type MemoryScope = "ephemeral_turn" | "project_fact" | "global_preference";
export type FactLifecycleStatus = "active" | "superseded" | "archived";

export interface BiTemporalFact {
  id: string;
  tenantId: string;
  scope: MemoryScope;
  projectId?: string;
  subject: string;
  predicate: string;
  object: string;
  /** Pointer to exact versioned document/commit so resuming agents never read stale files */
  artifactUri?: string;
  artifactVersionHash?: string;
  /** When the real-world decision/event actually happened (prevents stale email overwrites) */
  sourceEventAt: number;
  /** When Cortex ingested the record */
  ingestedAt: number;
  provenance: TrustProvenance;
  confidence: number;
  recurrenceCount: number;
  version: number;
  status: FactLifecycleStatus;
  supersededById?: string;
}

export type AttemptOutcomeStatus =
  | "progress" // Step succeeded and advanced toward goal
  | "blocked" // External dependency / permission / outage blocked execution
  | "failed" // The chosen strategy itself failed (bad query, test failure, etc.)
  | "needs_info" // Ambiguous user requirement; cannot guess safely
  | "done"; // Terminal goal verified complete

export interface AttemptRecord {
  attemptId: string;
  stepIndex: number;
  agentId: string;
  toolName: string;
  strategyClass: string;
  strategyFingerprint: string;
  outcome: AttemptOutcomeStatus;
  errorCode?: string;
  errorSummary?: string;
  hypothesisForFailure?: string;
  costUsd: number;
  durationMs: number;
  timestamp: number;
}

export interface GoalConstraintSpec {
  goalId: string;
  projectId: string;
  tenantId: string;
  maxAttempts: number;
  maxSameStrategyFailures: number;
  maxBudgetUsd: number;
  maxWallClockMs: number;
  /** Capabilities or file globs the agent is strictly forbidden from mutating (anti-cheating) */
  forbiddenCapabilities: string[];
  protectedResourcePatterns: RegExp[];
}

export interface ApprovalTicket {
  ticketId: string;
  payloadHash: string;
  agentId: string;
  toolName: string;
  targetResource: string;
  status: "pending" | "approved" | "rejected" | "consumed" | "expired";
  approvedBy?: string;
  expiresAt: number;
  createdAt: number;
}

export const ExtractedFactCandidateSchema = z.object({
  scope: z.enum(["ephemeral_turn", "project_fact", "global_preference"]),
  subject: z.string().min(1),
  predicate: z.string().min(1),
  object: z.string().min(1),
  artifactUri: z.string().optional(),
  artifactVersionHash: z.string().optional(),
  sourceEventTimestampIso: z.string().optional(),
  explicitPermanenceIntent: z.boolean(),
  confidence: z.number().min(0).max(1),
});

export type ExtractedFactCandidate = z.infer<typeof ExtractedFactCandidateSchema>;
