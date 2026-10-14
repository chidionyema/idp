// src/runtime/default-agent-wrapper.ts
import { ActiveMemoryEngine } from "../memory/active-memory-engine";
import {
  ActiveFocusController,
  ApprovalStoreAdapter,
  FocusPolicyDecision,
  ToolMetadata,
} from "../focus/active-focus-controller";
import {
  AttemptOutcomeStatus,
  ExtractedFactCandidate,
  GoalConstraintSpec,
  TrustProvenance,
} from "../types/active-runtime";

export interface AgentTurnInput {
  runId: string;
  tenantId: string;
  projectId?: string;
  agentId: string;
  userPrompt: string;
  provenance: TrustProvenance;
  constraints?: Partial<GoalConstraintSpec>;
}

export interface ModelStepResponse {
  type: "tool_call" | "final_answer" | "needs_clarification";
  toolName?: string;
  toolArgs?: Record<string, unknown>;
  content?: string;
  clarificationQuestion?: string;
  costUsd: number;
  extractedMemories?: ExtractedFactCandidate[];
}

export interface UnderlyingAgentDriver {
  step(params: {
    systemPromptWithActiveMemory: string;
    userPrompt: string;
    conversationScratchpad: string[];
    lockedStrategyClasses: string[];
  }): Promise<ModelStepResponse>;

  executeTool(
    toolName: string,
    args: Record<string, unknown>,
    idempotencyKey: string
  ): Promise<{
    outcome: AttemptOutcomeStatus;
    output: string;
    errorCode?: string;
    errorSummary?: string;
  }>;
}

export class DefaultActiveAgentHarness {
  constructor(
    private readonly memoryEngine: ActiveMemoryEngine,
    private readonly approvalStore: ApprovalStoreAdapter,
    private readonly toolRegistry: Map<string, ToolMetadata>,
    private readonly baseSystemPrompt: string
  ) {}

  /**
   * Wraps ANY agent driver so Active Memory pre-fetch, Active Focus obstacle recovery,
   * payload-bound approvals, and post-turn memory consolidation execute by default.
   */
  async runAgent(
    driver: UnderlyingAgentDriver,
    input: AgentTurnInput
  ): Promise<{
    status: "COMPLETED" | "NEEDS_CLARIFICATION" | "AWAITING_APPROVAL" | "ESCALATED_BLOCKER";
    responseText: string;
    decision: FocusPolicyDecision;
    memoryStats: { promoted: number; ignoredEphemeral: number; blockedStaleOrUntrusted: number };
  }> {
    // 1. Pre-Turn Associative Active Memory Injection
    const activeBrief = await this.memoryEngine.buildActiveContextBrief({
      tenantId: input.tenantId,
      projectId: input.projectId,
      runId: input.runId,
      userPrompt: input.userPrompt,
    });

    const fullSystemPrompt = [this.baseSystemPrompt, activeBrief].filter(Boolean).join("\n\n");

    // 2. Initialize Active Focus Controller with safe production defaults
    const fullConstraints: GoalConstraintSpec = {
      goalId: input.runId,
      projectId: input.projectId ?? "global",
      tenantId: input.tenantId,
      maxAttempts: input.constraints?.maxAttempts ?? 8,
      maxSameStrategyFailures: input.constraints?.maxSameStrategyFailures ?? 2,
      maxBudgetUsd: input.constraints?.maxBudgetUsd ?? 1.5,
      maxWallClockMs: input.constraints?.maxWallClockMs ?? 120_000,
      forbiddenCapabilities: input.constraints?.forbiddenCapabilities ?? ["drop_production_table", "disable_test_suite"],
      protectedResourcePatterns: input.constraints?.protectedResourcePatterns ?? [
        /\.test\.(ts|js|py)$/,
        /migrations\/.*_prod/,
      ],
    };

    const focusController = new ActiveFocusController(fullConstraints, this.approvalStore);
    const scratchpadHistory: string[] = [];
    const collectedMemoryCandidates: ExtractedFactCandidate[] = [];
    const allStrategyClasses = Array.from(
      new Set(Array.from(this.toolRegistry.values()).map((t) => t.strategyClass))
    );

    let lockedClasses: string[] = [];
    // Pre-flight rejections (unknown tool, forbidden capability, protected path, locked class)
    // never reach the attempt ledger, so they need their own bound or a stubborn model loops forever.
    let preflightRejections = 0;

    const consolidate = () =>
      this.memoryEngine.consolidateTurnCandidates({
        tenantId: input.tenantId,
        projectId: input.projectId,
        runId: input.runId,
        provenance: input.provenance,
        candidates: collectedMemoryCandidates,
      });

    const escalatePreflightLoop = async () => {
      const decision: FocusPolicyDecision = {
        action: "HALT_ESCALATE",
        reason: `Active Focus circuit breaker tripped: ${preflightRejections} tool calls rejected before execution (limit ${fullConstraints.maxAttempts}).`,
        attemptLedger: focusController.getAttemptLedger(),
      };
      return {
        status: "ESCALATED_BLOCKER" as const,
        responseText: decision.reason,
        decision,
        memoryStats: await consolidate(),
      };
    };

    // 3. Active Focus Execution Loop
    while (true) {
      const stepStart = Date.now();
      const modelStep = await driver.step({
        systemPromptWithActiveMemory: fullSystemPrompt,
        userPrompt: input.userPrompt,
        conversationScratchpad: scratchpadHistory,
        lockedStrategyClasses: lockedClasses,
      });

      if (modelStep.extractedMemories?.length) {
        collectedMemoryCandidates.push(...modelStep.extractedMemories);
      }

      // Case A: Agent determined it needs user clarification
      if (modelStep.type === "needs_clarification") {
        const decision = focusController.recordAttemptAndEvaluate({
          agentId: input.agentId,
          toolName: "clarification_gate",
          strategyClass: "dialogue",
          args: {},
          outcome: "needs_info",
          clarificationQuestion: modelStep.clarificationQuestion,
          costUsd: modelStep.costUsd,
          durationMs: Date.now() - stepStart,
          availableStrategyClasses: allStrategyClasses,
        });
        const memoryStats = await consolidate();
        return {
          status: "NEEDS_CLARIFICATION",
          responseText: modelStep.clarificationQuestion ?? "Could you clarify your requirement?",
          decision,
          memoryStats,
        };
      }

      // Case B: Agent completed the task
      if (modelStep.type === "final_answer") {
        const decision = focusController.recordAttemptAndEvaluate({
          agentId: input.agentId,
          toolName: "final_response",
          strategyClass: "synthesis",
          args: {},
          outcome: "done",
          completionSummary: modelStep.content,
          costUsd: modelStep.costUsd,
          durationMs: Date.now() - stepStart,
          availableStrategyClasses: allStrategyClasses,
        });
        const memoryStats = await consolidate();
        return {
          status: "COMPLETED",
          responseText: modelStep.content ?? "",
          decision,
          memoryStats,
        };
      }

      // Case C: Tool Execution -> Run Pre-Execution Guard & Approval Gate
      const toolMeta = this.toolRegistry.get(modelStep.toolName ?? "");
      if (!toolMeta) {
        scratchpadHistory.push(`SYSTEM ERROR: Unknown tool "${modelStep.toolName}". Pick a registered tool.`);
        preflightRejections++;
        if (preflightRejections >= fullConstraints.maxAttempts) return escalatePreflightLoop();
        continue;
      }

      const preCheck = await focusController.validateBeforeToolExecution({
        agentId: input.agentId,
        tool: toolMeta,
        args: modelStep.toolArgs ?? {},
      });

      if (!preCheck.allowed) {
        if (preCheck.decision.action === "AWAIT_APPROVAL") {
          const memoryStats = await consolidate();
          return {
            status: "AWAITING_APPROVAL",
            responseText: preCheck.decision.reason,
            decision: preCheck.decision,
            memoryStats,
          };
        }

        if (preCheck.decision.action === "SWITCH_STRATEGY") {
          lockedClasses = preCheck.decision.lockedStrategyClasses;
          scratchpadHistory.push(preCheck.decision.coachingDirective);
          preflightRejections++;
          if (preflightRejections >= fullConstraints.maxAttempts) return escalatePreflightLoop();
          continue;
        }

        // HALT_ESCALATE, and any decision the gate may grow later: stop, never fall through to execute.
        const haltReason =
          preCheck.decision.action === "HALT_ESCALATE"
            ? preCheck.decision.reason
            : `Pre-execution gate returned an unexpected decision "${preCheck.decision.action}".`;
        const memoryStats = await consolidate();
        return {
          status: "ESCALATED_BLOCKER",
          responseText: haltReason,
          decision: preCheck.decision,
          memoryStats,
        };
      }

      // Execute tool with deterministic idempotency key
      const execResult = await driver.executeTool(
        toolMeta.toolName,
        modelStep.toolArgs ?? {},
        preCheck.idempotencyKey
      );

      const postDecision = focusController.recordAttemptAndEvaluate({
        agentId: input.agentId,
        toolName: toolMeta.toolName,
        strategyClass: toolMeta.strategyClass,
        args: modelStep.toolArgs ?? {},
        outcome: execResult.outcome,
        errorCode: execResult.errorCode,
        errorSummary: execResult.errorSummary,
        costUsd: modelStep.costUsd,
        durationMs: Date.now() - stepStart,
        availableStrategyClasses: allStrategyClasses,
      });

      if (postDecision.action === "SWITCH_STRATEGY") {
        lockedClasses = postDecision.lockedStrategyClasses;
        scratchpadHistory.push(
          `TOOL FAILED (${toolMeta.toolName}): ${execResult.errorSummary}\n${postDecision.coachingDirective}`
        );
        continue;
      }

      if (postDecision.action === "HALT_ESCALATE") {
        const memoryStats = await consolidate();
        return {
          status: "ESCALATED_BLOCKER",
          responseText: postDecision.reason,
          decision: postDecision,
          memoryStats,
        };
      }

      scratchpadHistory.push(
        `TOOL RESULT (${toolMeta.toolName} -> ${execResult.outcome}): ${execResult.output}`
      );
      if (postDecision.action === "CONTINUE" && postDecision.coachingDirective) {
        scratchpadHistory.push(postDecision.coachingDirective);
      }
    }
  }
}
