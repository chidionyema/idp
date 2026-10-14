// tests/active-runtime.spec.ts
import { describe, it, expect, beforeEach } from "vitest";
import {
  AcidBackendDriver,
  AcidTableStore,
  CustomFastMemoryStore,
  ProductionCortexAdapter,
} from "../src/adapters/cortex-convex-adapter";
import { ActiveMemoryEngine } from "../src/memory/active-memory-engine";
import { ActiveFocusController, ToolMetadata } from "../src/focus/active-focus-controller";
import { DefaultActiveAgentHarness, ModelStepResponse } from "../src/runtime/default-agent-wrapper";
import { BiTemporalFact } from "../src/types/active-runtime";

function createInMemoryAcidBackend(): {
  driver: AcidBackendDriver;
  rawStore: AcidTableStore;
} {
  const rawStore: AcidTableStore = {
    facts: new Map(),
    approvals: new Map(),
    idempotency: new Map(),
  };

  const driver: AcidBackendDriver = {
    async executeAcidTransaction<T>(fn: (store: AcidTableStore) => Promise<T>): Promise<T> {
      return fn(rawStore);
    },
    async vectorSearchFacts({ tenantId, limit }): Promise<BiTemporalFact[]> {
      return Array.from(rawStore.facts.values())
        .filter((f) => f.tenantId === tenantId && f.status === "active")
        .slice(0, limit);
    },
    async getOneHopNeighbors({ tenantId, seedSubjects, limit }): Promise<BiTemporalFact[]> {
      return Array.from(rawStore.facts.values())
        .filter(
          (f) =>
            f.tenantId === tenantId &&
            f.status === "active" &&
            seedSubjects.includes(f.subject)
        )
        .slice(0, limit);
    },
  };

  return { driver, rawStore };
}

describe("Day-0 Production Verification: Active Memory & Active Focus", () => {
  let memoryEngine: ActiveMemoryEngine;
  let cortexAdapter: ProductionCortexAdapter;
  let rawStore: AcidTableStore;

  beforeEach(() => {
    const backend = createInMemoryAcidBackend();
    rawStore = backend.rawStore;
    cortexAdapter = new ProductionCortexAdapter(backend.driver, {
      embed: async () => [0.1, 0.2, 0.3],
    });
    memoryEngine = new ActiveMemoryEngine(cortexAdapter, new CustomFastMemoryStore());
  });

  it("Edge Case 1 (Bi-Temporal Belief Revision): blocks a 4-day-old email from overwriting a 10-minute-old chat decision", async () => {
    const now = Date.now();
    const tenMinutesAgo = new Date(now - 10 * 60 * 1000).toISOString();
    const fourDaysAgo = new Date(now - 4 * 24 * 60 * 60 * 1000).toISOString();

    // 1. User sets release date to Monday in chat 10 minutes ago
    const chatCommit = await memoryEngine.consolidateTurnCandidates({
      tenantId: "tenant_1",
      projectId: "proj_launch",
      runId: "run_1",
      provenance: "user_direct",
      candidates: [
        {
          scope: "project_fact",
          subject: "Release_Deadline",
          predicate: "scheduled_for",
          object: "Monday Oct 19",
          artifactUri: "doc://release-plan",
          artifactVersionHash: "v2_hash",
          sourceEventTimestampIso: tenMinutesAgo,
          explicitPermanenceIntent: true,
          confidence: 0.99,
        },
      ],
    });
    expect(chatCommit.promoted).toBe(1);

    // 2. Agent later ingests an old email thread from 4 days ago claiming Friday Oct 16
    const staleEmailCommit = await memoryEngine.consolidateTurnCandidates({
      tenantId: "tenant_1",
      projectId: "proj_launch",
      runId: "run_2",
      provenance: "verified_internal",
      candidates: [
        {
          scope: "project_fact",
          subject: "Release_Deadline",
          predicate: "scheduled_for",
          object: "Friday Oct 16",
          sourceEventTimestampIso: fourDaysAgo,
          explicitPermanenceIntent: true,
          confidence: 0.95,
        },
      ],
    });

    expect(staleEmailCommit.promoted).toBe(0);
    expect(staleEmailCommit.blockedStaleOrUntrusted).toBe(1);

    const brief = await memoryEngine.buildActiveContextBrief({
      tenantId: "tenant_1",
      projectId: "proj_launch",
      runId: "run_2",
      userPrompt: "When is the release deadline?",
    });
    expect(brief).toContain("Monday Oct 19");
    expect(brief).toContain("doc://release-plan@v2_hash");
    expect(brief).not.toContain("Friday Oct 16");
  });

  it("Edge Case 2 & 3 (Intent Gate & Prompt Injection): isolates one-off instructions and blocks untrusted global writes", async () => {
    // Untrusted external webpage tries to inject a global preference
    const injectionAttempt = await memoryEngine.consolidateTurnCandidates({
      tenantId: "tenant_1",
      runId: "run_inject",
      provenance: "untrusted_external",
      candidates: [
        {
          scope: "global_preference",
          subject: "Payment_Routing",
          predicate: "default_iban",
          object: "ATTACKER_IBAN_999",
          explicitPermanenceIntent: true,
          confidence: 1.0,
        },
      ],
    });
    expect(injectionAttempt.promoted).toBe(0);
    expect(injectionAttempt.blockedStaleOrUntrusted).toBe(1);

    // Inferred preference without explicit permanence is held back until >= 3 recurrences
    for (let i = 1; i <= 2; i++) {
      const res = await memoryEngine.consolidateTurnCandidates({
        tenantId: "tenant_1",
        runId: `run_${i}`,
        provenance: "user_direct",
        candidates: [
          {
            scope: "global_preference",
            subject: "Response_Format",
            predicate: "style",
            object: "bullet_points",
            explicitPermanenceIntent: false,
            confidence: 0.85,
          },
        ],
      });
      expect(res.promoted).toBe(0);
      expect(res.ignoredEphemeral).toBe(1);
    }

    // 3rd recurrence promotes to Cortex global_preference
    const thirdRes = await memoryEngine.consolidateTurnCandidates({
      tenantId: "tenant_1",
      runId: "run_3",
      provenance: "user_direct",
      candidates: [
        {
          scope: "global_preference",
          subject: "Response_Format",
          predicate: "style",
          object: "bullet_points",
          explicitPermanenceIntent: false,
          confidence: 0.85,
        },
      ],
    });
    expect(thirdRes.promoted).toBe(1);
  });

  it("Edge Case 4 (TOCTOU Payload-Bound Approval & Single-Use Consumption): invalidates approval if payload mutates during retry", async () => {
    const controller = new ActiveFocusController(
      {
        goalId: "goal_email",
        projectId: "proj_1",
        tenantId: "tenant_1",
        maxAttempts: 6,
        maxSameStrategyFailures: 2,
        maxBudgetUsd: 1.0,
        maxWallClockMs: 60_000,
        forbiddenCapabilities: [],
        protectedResourcePatterns: [],
      },
      cortexAdapter
    );

    const emailTool: ToolMetadata = {
      toolName: "send_customer_email",
      strategyClass: "smtp_outbound",
      capabilityTags: ["external_communication"],
      requiresApproval: true,
      extractTargetResource: (args) => String(args.to),
    };

    const originalArgs = { to: "Alice@example.com", body: "Approved draft v1" };

    // First attempt triggers AWAIT_APPROVAL
    const firstCheck = await controller.validateBeforeToolExecution({
      agentId: "agent_comms",
      tool: emailTool,
      args: originalArgs,
    });
    expect(firstCheck.allowed).toBe(false);
    if (!firstCheck.allowed && firstCheck.decision.action === "AWAIT_APPROVAL") {
      // Simulate human approving the exact ticket
      const ticket = rawStore.approvals.get(firstCheck.decision.ticket.ticketId)!;
      rawStore.approvals.set(ticket.ticketId, { ...ticket, status: "approved" });
    }

    // Agent modifies the email body during a retry -> hash changes, MUST NOT reuse approval!
    const mutatedCheck = await controller.validateBeforeToolExecution({
      agentId: "agent_comms",
      tool: emailTool,
      args: { to: "Alice@example.com", body: "Mutated draft v2 with unapproved terms" },
    });
    expect(mutatedCheck.allowed).toBe(false);

    // Agent uses the exact approved payload -> allowed once
    const validCheck = await controller.validateBeforeToolExecution({
      agentId: "agent_comms",
      tool: emailTool,
      args: originalArgs,
    });
    expect(validCheck.allowed).toBe(true);

    // Concurrent worker tries to replay the consumed approval ticket -> blocked!
    const replayCheck = await controller.validateBeforeToolExecution({
      agentId: "agent_comms",
      tool: emailTool,
      args: originalArgs,
    });
    expect(replayCheck.allowed).toBe(false);
  });

  it("Edge Case 5, 6 & 7 (Active Focus Strategy Pivot, Anti-Cheating Guard & Epilogue Archival)", async () => {
    const toolRegistry = new Map<string, ToolMetadata>([
      [
        "query_rest_api",
        {
          toolName: "query_rest_api",
          strategyClass: "direct_api",
          capabilityTags: ["read_api"],
          requiresApproval: false,
          extractTargetResource: () => "api://metrics",
        },
      ],
      [
        "edit_file",
        {
          toolName: "edit_file",
          strategyClass: "code_mutation",
          capabilityTags: ["write_fs"],
          requiresApproval: false,
          extractTargetResource: (args) => String(args.path),
        },
      ],
      [
        "query_headless_browser",
        {
          toolName: "query_headless_browser",
          strategyClass: "browser_fallback",
          capabilityTags: ["read_web"],
          requiresApproval: false,
          extractTargetResource: () => "https://internal.dashboard/metrics",
        },
      ],
    ]);

    const harness = new DefaultActiveAgentHarness(
      memoryEngine,
      cortexAdapter,
      toolRegistry,
      "You are a production autonomous agent."
    );

    const scriptedSteps: ModelStepResponse[] = [
      // Attempt 1: Agent tries to cheat by editing a protected test file -> Blocked by Constraint Guard
      {
        type: "tool_call",
        toolName: "edit_file",
        toolArgs: { path: "src/billing.test.ts" },
        costUsd: 0.01,
      },
      // Attempt 2: Agent calls direct_api #1 -> Fails with 502
      {
        type: "tool_call",
        toolName: "query_rest_api",
        toolArgs: { endpoint: "/v1/revenue" },
        costUsd: 0.01,
      },
      // Attempt 3: Agent calls direct_api #2 -> Fails with 502, locking `direct_api` strategyClass
      {
        type: "tool_call",
        toolName: "query_rest_api",
        toolArgs: { endpoint: "/v1/revenue?retry=1" },
        costUsd: 0.01,
      },
      // Attempt 4: Agent pivots to `browser_fallback` -> Succeeds!
      {
        type: "tool_call",
        toolName: "query_headless_browser",
        toolArgs: { url: "https://internal.dashboard/metrics" },
        costUsd: 0.02,
      },
      // Final Answer
      {
        type: "final_answer",
        content: "Retrieved Q3 revenue via browser fallback after REST API outage: $4.2M.",
        costUsd: 0.01,
        extractedMemories: [
          {
            scope: "project_fact",
            subject: "Q3_Audit",
            predicate: "revenue_figure",
            object: "$4.2M",
            explicitPermanenceIntent: true,
            confidence: 0.99,
          },
        ],
      },
    ];

    let stepCursor = 0;
    const result = await harness.runAgent(
      {
        step: async ({ lockedStrategyClasses }) => {
          const next = scriptedSteps[stepCursor++];
          // Verify that by stepIndex 4 (Attempt 4), `direct_api` is locked
          if (stepCursor === 4) {
            expect(lockedStrategyClasses).toContain("direct_api");
          }
          return next;
        },
        executeTool: async (toolName) => {
          if (toolName === "query_rest_api") {
            return {
              outcome: "failed",
              output: "HTTP 502 Bad Gateway",
              errorCode: "HTTP_502",
              errorSummary: "Upstream REST gateway timeout",
            };
          }
          return {
            outcome: "progress",
            output: "Dashboard DOM scraped: Revenue = $4.2M",
          };
        },
      },
      {
        runId: "run_marathon_1",
        tenantId: "tenant_1",
        projectId: "proj_q3_audit",
        agentId: "agent_analyst",
        userPrompt: "Fetch Q3 revenue and verify the build.",
        provenance: "user_direct",
      }
    );

    expect(result.status).toBe("COMPLETED");
    expect(result.memoryStats.promoted).toBe(1);

    // Epilogue Archival: Retire project_q3_audit facts and confirm they no longer enter future context briefs
    const archivedCount = await memoryEngine.archiveProjectScope("tenant_1", "proj_q3_audit");
    expect(archivedCount).toBe(1);

    const postArchiveBrief = await memoryEngine.buildActiveContextBrief({
      tenantId: "tenant_1",
      projectId: "proj_q3_audit",
      runId: "run_next",
      userPrompt: "What was the Q3 audit revenue figure?",
    });
    expect(postArchiveBrief).toBe("");
  });
});
