// tests/telemetry-and-webhooks.spec.ts
import { describe, it, expect, beforeEach } from "vitest";
import {
  AcidBackendDriver,
  AcidTableStore,
  CustomFastMemoryStore,
  ProductionCortexAdapter,
} from "../src/adapters/cortex-convex-adapter";
import { ActiveMemoryEngine } from "../src/memory/active-memory-engine";
import { ToolMetadata } from "../src/focus/active-focus-controller";
import { DefaultActiveAgentHarness, ModelStepResponse } from "../src/runtime/default-agent-wrapper";
import { ActiveRuntimeTelemetry } from "../src/telemetry/active-otel-exporter";
import { ApprovalWebhookHandler } from "../src/webhooks/approval-webhook-handler";
import { BiTemporalFact } from "../src/types/active-runtime";

function createTestBackend(): { driver: AcidBackendDriver; rawStore: AcidTableStore } {
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
    async getOneHopNeighbors(): Promise<BiTemporalFact[]> {
      return [];
    },
  };

  return { driver, rawStore };
}

describe("Day-0 Observability & Cryptographic Approval Webhooks", () => {
  const SECRET = "whsec_day0_production_secret_key_998877";
  let driver: AcidBackendDriver;
  let cortexAdapter: ProductionCortexAdapter;
  let memoryEngine: ActiveMemoryEngine;
  let telemetry: ActiveRuntimeTelemetry;
  let webhookHandler: ApprovalWebhookHandler;

  beforeEach(() => {
    const backend = createTestBackend();
    driver = backend.driver;
    cortexAdapter = new ProductionCortexAdapter(driver, {
      embed: async () => [0.1, 0.2],
    });
    memoryEngine = new ActiveMemoryEngine(cortexAdapter, new CustomFastMemoryStore());
    telemetry = new ActiveRuntimeTelemetry();
    webhookHandler = new ApprovalWebhookHandler(SECRET, driver, telemetry);
  });

  it("rejects forged HMAC signatures and expired replay timestamps with HTTP 401", async () => {
    const body = JSON.stringify({
      ticketId: "appr_123",
      expectedPayloadHash: "a".repeat(64),
      decision: "approve",
      reviewerId: "sec_ops_lead",
    });

    const nowSec = Math.floor(Date.now() / 1000);

    // 1. Forged signature -> 401
    const forgedRes = await webhookHandler.handleWebhook({
      headers: {
        "x-fleet-timestamp": String(nowSec),
        "x-fleet-signature": "v0=deadbeef00000000000000000000000000000000000000000000000000000000",
      },
      rawBody: body,
    });
    expect(forgedRes.statusCode).toBe(401);

    // 2. Valid signature but 10 minutes old (outside 5-minute replay window) -> 401
    const staleTimestamp = nowSec - 600;
    const staleSig = ApprovalWebhookHandler.signWebhookPayload(SECRET, staleTimestamp, body);
    const replayRes = await webhookHandler.handleWebhook({
      headers: {
        "x-fleet-timestamp": String(staleTimestamp),
        "x-fleet-signature": staleSig,
      },
      rawBody: body,
    });
    expect(replayRes.statusCode).toBe(401);
    expect(replayRes.body.error).toContain("replay window");
  });

  it("suspends agent on Tier-2 action, blocks mismatched payloadHash, and automatically resumes agent on valid approval", async () => {
    const deployTool: ToolMetadata = {
      toolName: "execute_prod_migration",
      strategyClass: "db_migration",
      capabilityTags: ["prod_schema_write"],
      requiresApproval: true,
      extractTargetResource: (args) => String(args.migrationId),
    };

    const harness = new DefaultActiveAgentHarness(
      memoryEngine,
      cortexAdapter,
      new Map([[deployTool.toolName, deployTool]]),
      "Production migration agent."
    );

    let migrationExecutedCount = 0;
    const createAgentDriver = () => {
      let stepCount = 0;
      return {
        step: async (): Promise<ModelStepResponse> => {
          stepCount++;
          if (stepCount === 1) {
            return {
              type: "tool_call",
              toolName: "execute_prod_migration",
              toolArgs: { migrationId: "2026_10_add_indexes", dryRun: false },
              costUsd: 0.02,
            };
          }
          return {
            type: "final_answer",
            content: "Production migration 2026_10_add_indexes completed after approval.",
            costUsd: 0.01,
          };
        },
        executeTool: async () => {
          migrationExecutedCount++;
          return {
            outcome: "progress" as const,
            output: "Migration applied cleanly.",
          };
        },
      };
    };

    const turnInput = {
      runId: "run_migration_1",
      tenantId: "tenant_prod",
      projectId: "proj_db",
      agentId: "agent_dba",
      userPrompt: "Run migration 2026_10_add_indexes in production.",
      provenance: "user_direct" as const,
    };

    // Pass 1: Agent runs and pauses at AWAITING_APPROVAL
    const initialRun = await harness.runAgent(createAgentDriver(), turnInput);
    expect(initialRun.status).toBe("AWAITING_APPROVAL");
    expect(migrationExecutedCount).toBe(0);

    if (initialRun.decision.action !== "AWAIT_APPROVAL") {
      throw new Error("Expected AWAIT_APPROVAL decision");
    }

    const ticket = initialRun.decision.ticket;
    telemetry.recordApprovalEvent({
      agentId: turnInput.agentId,
      toolName: deployTool.toolName,
      event: "requested",
    });

    // Register suspended run checkpoint so webhook approval resumes execution automatically
    webhookHandler.registerSuspendedRun({
      runId: turnInput.runId,
      ticketId: ticket.ticketId,
      expectedPayloadHash: ticket.payloadHash,
      turnInput,
      resumeCallback: (input) => harness.runAgent(createAgentDriver(), input),
      createdAt: Date.now(),
    });

    const nowSec = Math.floor(Date.now() / 1000);

    // Attempt with a tampered payloadHash -> 409 Conflict & telemetry counter incremented
    const tamperedBody = JSON.stringify({
      ticketId: ticket.ticketId,
      expectedPayloadHash: "f".repeat(64),
      decision: "approve",
      reviewerId: "principal_dba",
    });
    const tamperedRes = await webhookHandler.handleWebhook({
      headers: {
        "x-fleet-timestamp": String(nowSec),
        "x-fleet-signature": ApprovalWebhookHandler.signWebhookPayload(SECRET, nowSec, tamperedBody),
      },
      rawBody: tamperedBody,
    });
    expect(tamperedRes.statusCode).toBe(409);
    expect(migrationExecutedCount).toBe(0);

    // Valid approval with matching SHA-256 payloadHash -> 200 OK & automatic agent resumption
    const validBody = JSON.stringify({
      ticketId: ticket.ticketId,
      expectedPayloadHash: ticket.payloadHash,
      decision: "approve",
      reviewerId: "principal_dba",
    });
    const validRes = await webhookHandler.handleWebhook({
      headers: {
        "x-fleet-timestamp": String(nowSec),
        "x-fleet-signature": ApprovalWebhookHandler.signWebhookPayload(SECRET, nowSec, validBody),
      },
      rawBody: validBody,
    });

    expect(validRes.statusCode).toBe(200);
    expect(validRes.body.newStatus).toBe("approved");
    expect(validRes.body.resumedRunStatus).toBe("COMPLETED");
    expect(migrationExecutedCount).toBe(1);

    // Verify OpenTelemetry snapshot captured the full lifecycle
    const snap = telemetry.getSnapshot();
    expect(snap.approvalEvents.requested).toBe(1);
    expect(snap.approvalEvents.replay_or_hash_blocked).toBe(1);
    expect(snap.approvalEvents.approved).toBe(1);
  });
});
