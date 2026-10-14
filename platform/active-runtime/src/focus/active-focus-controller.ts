// src/focus/active-focus-controller.ts
import crypto from "node:crypto";
import {
  ApprovalTicket,
  AttemptOutcomeStatus,
  AttemptRecord,
  GoalConstraintSpec,
} from "../types/active-runtime";

export type FocusPolicyDecision =
  | { action: "COMPLETE"; summary: string }
  | { action: "ASK_CLARIFICATION"; question: string }
  | { action: "AWAIT_APPROVAL"; ticket: ApprovalTicket; reason: string }
  | { action: "SWITCH_STRATEGY"; lockedStrategyClasses: string[]; coachingDirective: string }
  | { action: "CONTINUE"; coachingDirective?: string }
  | { action: "HALT_ESCALATE"; reason: string; attemptLedger: AttemptRecord[] };

export interface ToolMetadata {
  toolName: string;
  strategyClass: string;
  capabilityTags: string[];
  requiresApproval: boolean;
  extractTargetResource: (args: Record<string, unknown>) => string;
}

export interface ApprovalStoreAdapter {
  getTicketByHash(payloadHash: string): Promise<ApprovalTicket | null>;
  createPendingTicket(ticket: ApprovalTicket): Promise<void>;
  consumeTicket(ticketId: string): Promise<boolean>;
}

export class ActiveFocusController {
  private readonly ledger: AttemptRecord[] = [];
  private readonly lockedStrategyClasses = new Set<string>();
  private readonly startedAt = Date.now();
  private spentUsd = 0;

  constructor(
    private readonly constraints: GoalConstraintSpec,
    private readonly approvalStore: ApprovalStoreAdapter
  ) {}

  /**
   * Canonical deterministic JSON serializer so key ordering never alters SHA-256 hashes.
   */
  static canonicalizePayload(value: unknown): string {
    if (value === null || typeof value !== "object") {
      return JSON.stringify(value);
    }
    if (Array.isArray(value)) {
      return `[${value.map((item) => ActiveFocusController.canonicalizePayload(item)).join(",")}]`;
    }
    const record = value as Record<string, unknown>;
    const sortedKeys = Object.keys(record).sort();
    const entries = sortedKeys.map(
      (k) => `${JSON.stringify(k)}:${ActiveFocusController.canonicalizePayload(record[k])}`
    );
    return `{${entries.join(",")}}`;
  }

  static computePayloadApprovalHash(params: {
    agentId: string;
    toolName: string;
    targetResource: string;
    args: Record<string, unknown>;
  }): string {
    const canonicalArgs = ActiveFocusController.canonicalizePayload(params.args);
    return crypto
      .createHash("sha256")
      .update(`${params.agentId}|${params.toolName}|${params.targetResource}|${canonicalArgs}`)
      .digest("hex");
  }

  /**
   * PRE-EXECUTION GATE:
   * 1. Checks Forbidden Capabilities & Protected Resource Patterns (anti-shortcut guard).
   * 2. Checks whether the Strategy Class is already locked due to repeated failures.
   * 3. Verifies Payload-Bound Approval Token for Tier-2 consequential actions.
   */
  async validateBeforeToolExecution(params: {
    agentId: string;
    tool: ToolMetadata;
    args: Record<string, unknown>;
  }): Promise<
    | { allowed: true; idempotencyKey: string }
    | { allowed: false; decision: FocusPolicyDecision }
  > {
    const targetResource = params.tool.extractTargetResource(params.args);

    // 1. Constraint & Anti-Cheating Guard
    const violatedCap = params.tool.capabilityTags.find((tag) =>
      this.constraints.forbiddenCapabilities.includes(tag)
    );
    if (violatedCap) {
      return {
        allowed: false,
        decision: {
          action: "SWITCH_STRATEGY",
          lockedStrategyClasses: Array.from(this.lockedStrategyClasses),
          coachingDirective: `CONSTRAINT BLOCKED: Tool "${params.tool.toolName}" uses forbidden capability "${violatedCap}". Achieve the goal without mutating protected constraints.`,
        },
      };
    }

    const hitsProtectedPath = this.constraints.protectedResourcePatterns.some((pattern) =>
      pattern.test(targetResource)
    );
    if (hitsProtectedPath) {
      return {
        allowed: false,
        decision: {
          action: "SWITCH_STRATEGY",
          lockedStrategyClasses: Array.from(this.lockedStrategyClasses),
          coachingDirective: `PROTECTED RESOURCE BLOCKED: "${targetResource}" matches a protected resource rule (e.g., test assertions or production config). Fix the underlying implementation instead.`,
        },
      };
    }

    // 2. Strategy Lock Guard
    if (this.lockedStrategyClasses.has(params.tool.strategyClass)) {
      return {
        allowed: false,
        decision: {
          action: "SWITCH_STRATEGY",
          lockedStrategyClasses: Array.from(this.lockedStrategyClasses),
          coachingDirective: `STRATEGY LOCKED: Strategy class "${params.tool.strategyClass}" has already failed repeatedly in this run. Select a tool from a different strategy class.`,
        },
      };
    }

    // 3. Consequential Action Approval Gate (Payload-Bound SHA-256)
    const payloadHash = ActiveFocusController.computePayloadApprovalHash({
      agentId: params.agentId,
      toolName: params.tool.toolName,
      targetResource,
      args: params.args,
    });

    if (params.tool.requiresApproval) {
      const existingTicket = await this.approvalStore.getTicketByHash(payloadHash);
      const now = Date.now();

      // A consumed or expired ticket is spent: the same payload needs a fresh approval,
      // never a replay of the old one.
      if (
        !existingTicket ||
        existingTicket.expiresAt <= now ||
        existingTicket.status === "consumed" ||
        existingTicket.status === "expired"
      ) {
        const newTicket: ApprovalTicket = {
          ticketId: `appr_${crypto.randomUUID()}`,
          payloadHash,
          agentId: params.agentId,
          toolName: params.tool.toolName,
          targetResource,
          status: "pending",
          createdAt: now,
          expiresAt: now + 30 * 60 * 1000, // 30-minute approval window
        };
        await this.approvalStore.createPendingTicket(newTicket);
        return {
          allowed: false,
          decision: {
            action: "AWAIT_APPROVAL",
            ticket: newTicket,
            reason: `Consequential action "${params.tool.toolName}" targeting "${targetResource}" requires explicit approval bound to payload hash ${payloadHash.slice(0, 12)}.`,
          },
        };
      }

      if (existingTicket.status === "rejected") {
        return {
          allowed: false,
          decision: {
            action: "HALT_ESCALATE",
            reason: `User rejected consequential action "${params.tool.toolName}" on "${targetResource}".`,
            attemptLedger: [...this.ledger],
          },
        };
      }

      if (existingTicket.status !== "approved") {
        return {
          allowed: false,
          decision: {
            action: "AWAIT_APPROVAL",
            ticket: existingTicket,
            reason: `Waiting for approval on ticket ${existingTicket.ticketId}.`,
          },
        };
      }

      // Single-use consumption so retries cannot replay a consumed approval token
      const consumed = await this.approvalStore.consumeTicket(existingTicket.ticketId);
      if (!consumed) {
        return {
          allowed: false,
          decision: {
            action: "HALT_ESCALATE",
            reason: `Approval ticket ${existingTicket.ticketId} was already consumed by a concurrent worker.`,
            attemptLedger: [...this.ledger],
          },
        };
      }
    }

    const idempotencyKey = `${this.constraints.goalId}:${this.ledger.length}:${payloadHash.slice(0, 16)}`;
    return { allowed: true, idempotencyKey };
  }

  /**
   * POST-STEP FOCUS POLICY EVALUATION:
   * Evaluates the outcome of an attempt and decides whether to continue, switch strategy,
   * ask for clarification, or escalate with a complete diagnostic ledger.
   */
  recordAttemptAndEvaluate(params: {
    agentId: string;
    toolName: string;
    strategyClass: string;
    args: Record<string, unknown>;
    outcome: AttemptOutcomeStatus;
    errorCode?: string;
    errorSummary?: string;
    hypothesisForFailure?: string;
    clarificationQuestion?: string;
    completionSummary?: string;
    costUsd: number;
    durationMs: number;
    availableStrategyClasses: string[];
  }): FocusPolicyDecision {
    this.spentUsd += params.costUsd;

    const strategyFingerprint = crypto
      .createHash("sha256")
      .update(`${params.strategyClass}|${params.toolName}|${params.errorCode ?? "ok"}`)
      .digest("hex")
      .slice(0, 16);

    const record: AttemptRecord = {
      attemptId: `att_${crypto.randomUUID()}`,
      stepIndex: this.ledger.length + 1,
      agentId: params.agentId,
      toolName: params.toolName,
      strategyClass: params.strategyClass,
      strategyFingerprint,
      outcome: params.outcome,
      errorCode: params.errorCode,
      errorSummary: params.errorSummary,
      hypothesisForFailure: params.hypothesisForFailure,
      costUsd: params.costUsd,
      durationMs: params.durationMs,
      timestamp: Date.now(),
    };

    this.ledger.push(record);

    // Policy Rule 1: Done wins immediately
    if (params.outcome === "done") {
      return {
        action: "COMPLETE",
        summary: params.completionSummary ?? "Goal verified complete.",
      };
    }

    // Policy Rule 2: Missing user intent / ambiguity means pause and ask (never guess)
    if (params.outcome === "needs_info") {
      return {
        action: "ASK_CLARIFICATION",
        question:
          params.clarificationQuestion ??
          "Additional clarification is required before choosing an execution path.",
      };
    }

    // Policy Rule 3: Hard Budget / Attempt / Wall-Clock Circuit Breakers
    const elapsedMs = Date.now() - this.startedAt;
    if (
      this.ledger.length >= this.constraints.maxAttempts ||
      this.spentUsd >= this.constraints.maxBudgetUsd ||
      elapsedMs >= this.constraints.maxWallClockMs
    ) {
      return {
        action: "HALT_ESCALATE",
        reason: `Active Focus circuit breaker tripped (attempts=${this.ledger.length}/${this.constraints.maxAttempts}, cost=$${this.spentUsd.toFixed(4)}/$${this.constraints.maxBudgetUsd}, elapsed=${elapsedMs}ms).`,
        attemptLedger: [...this.ledger],
      };
    }

    // Policy Rule 4: Progress continues normally
    if (params.outcome === "progress") {
      return { action: "CONTINUE" };
    }

    // Policy Rule 5: Failed or Blocked -> check failure count for this strategyClass
    const failuresInClass = this.ledger.filter(
      (a) =>
        a.strategyClass === params.strategyClass &&
        (a.outcome === "failed" || a.outcome === "blocked")
    ).length;

    if (failuresInClass >= this.constraints.maxSameStrategyFailures) {
      this.lockedStrategyClasses.add(params.strategyClass);
    }

    const remainingClasses = params.availableStrategyClasses.filter(
      (c) => !this.lockedStrategyClasses.has(c)
    );

    if (remainingClasses.length === 0) {
      return {
        action: "HALT_ESCALATE",
        reason: `All available strategy classes (${params.availableStrategyClasses.join(", ")}) have been exhausted or blocked.`,
        attemptLedger: [...this.ledger],
      };
    }

    if (this.lockedStrategyClasses.has(params.strategyClass)) {
      return {
        action: "SWITCH_STRATEGY",
        lockedStrategyClasses: Array.from(this.lockedStrategyClasses),
        coachingDirective: [
          `ACTIVE FOCUS PIVOT REQUIRED: Strategy class "${params.strategyClass}" failed ${failuresInClass} times (latest error: ${params.errorSummary ?? "unknown"}).`,
          `Locked strategy classes: [${Array.from(this.lockedStrategyClasses).join(", ")}].`,
          `You MUST switch to one of the remaining strategy classes: [${remainingClasses.join(", ")}]. Do not repeat the failed approach.`,
        ].join(" "),
      };
    }

    return {
      action: "CONTINUE",
      coachingDirective: `Previous attempt on "${params.toolName}" returned ${params.outcome} (${params.errorSummary ?? "error"}). Adjust parameters or switch strategy if the root cause persists.`,
    };
  }

  getAttemptLedger(): AttemptRecord[] {
    return [...this.ledger];
  }
}
