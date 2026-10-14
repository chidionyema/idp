// tests/hardening.spec.ts: regression tests for the defects fixed while storing the package.
import { describe, it, expect, beforeEach } from "vitest";
import {
  AcidBackendDriver,
  AcidTableStore,
  CustomFastMemoryStore,
  ProductionCortexAdapter,
} from "../src/adapters/cortex-convex-adapter";
import { ActiveMemoryEngine } from "../src/memory/active-memory-engine";
import { ActiveFocusController, ToolMetadata } from "../src/focus/active-focus-controller";
import { DefaultActiveAgentHarness } from "../src/runtime/default-agent-wrapper";
import { ActiveMcpProxyServer } from "../src/mcp/active-mcp-proxy";
import { BiTemporalFact } from "../src/types/active-runtime";

function backend(): { driver: AcidBackendDriver; rawStore: AcidTableStore } {
  const rawStore: AcidTableStore = { facts: new Map(), approvals: new Map(), idempotency: new Map() };
  const driver: AcidBackendDriver = {
    async executeAcidTransaction<T>(fn: (s: AcidTableStore) => Promise<T>): Promise<T> {
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

const constraints = {
  goalId: "g",
  projectId: "p",
  tenantId: "t",
  maxAttempts: 6,
  maxSameStrategyFailures: 2,
  maxBudgetUsd: 1,
  maxWallClockMs: 60_000,
  forbiddenCapabilities: [],
  protectedResourcePatterns: [],
};

describe("hardening", () => {
  let rawStore: AcidTableStore;
  let cortex: ProductionCortexAdapter;
  let engine: ActiveMemoryEngine;
  let driver: AcidBackendDriver;

  beforeEach(() => {
    const b = backend();
    rawStore = b.rawStore;
    driver = b.driver;
    cortex = new ProductionCortexAdapter(driver, { embed: async () => [0.1] });
    engine = new ActiveMemoryEngine(cortex, new CustomFastMemoryStore());
  });

  it("a global preference never supersedes a project fact that shares subject and predicate", async () => {
    await engine.consolidateTurnCandidates({
      tenantId: "t",
      projectId: "p",
      runId: "r1",
      provenance: "user_direct",
      candidates: [
        { scope: "project_fact", subject: "Format", predicate: "style", object: "csv", explicitPermanenceIntent: true, confidence: 1 },
      ],
    });
    const res = await engine.consolidateTurnCandidates({
      tenantId: "t",
      runId: "r2",
      provenance: "user_direct",
      candidates: [
        { scope: "global_preference", subject: "Format", predicate: "style", object: "bullets", explicitPermanenceIntent: true, confidence: 1 },
      ],
    });
    expect(res.promoted).toBe(1);
    const active = Array.from(rawStore.facts.values()).filter((f) => f.status === "active");
    expect(active).toHaveLength(2);
    expect(active.find((f) => f.scope === "project_fact")?.object).toBe("csv");
  });

  it("an approved-and-consumed payload needs a fresh approval, never a replay", async () => {
    const controller = new ActiveFocusController(constraints, cortex);
    const tool: ToolMetadata = {
      toolName: "send",
      strategyClass: "smtp",
      capabilityTags: [],
      requiresApproval: true,
      extractTargetResource: () => "bob",
    };
    const args = { body: "x" };
    const first = await controller.validateBeforeToolExecution({ agentId: "a", tool, args });
    if (first.allowed || first.decision.action !== "AWAIT_APPROVAL") throw new Error("expected AWAIT_APPROVAL");
    const t = rawStore.approvals.get(first.decision.ticket.ticketId)!;
    rawStore.approvals.set(t.ticketId, { ...t, status: "approved" });
    expect((await controller.validateBeforeToolExecution({ agentId: "a", tool, args })).allowed).toBe(true);

    // The ticket is now consumed. The same payload must open a NEW pending ticket.
    const again = await controller.validateBeforeToolExecution({ agentId: "a", tool, args });
    expect(again.allowed).toBe(false);
    if (again.allowed || again.decision.action !== "AWAIT_APPROVAL") throw new Error("expected AWAIT_APPROVAL");
    expect(again.decision.ticket.ticketId).not.toBe(t.ticketId);
    expect(again.decision.ticket.status).toBe("pending");
  });

  it("a model that keeps calling a protected path is halted instead of looping forever", async () => {
    const tools = new Map<string, ToolMetadata>([
      [
        "edit_file",
        {
          toolName: "edit_file",
          strategyClass: "code_mutation",
          capabilityTags: [],
          requiresApproval: false,
          extractTargetResource: (a) => String(a.path),
        },
      ],
    ]);
    const harness = new DefaultActiveAgentHarness(engine, cortex, tools, "p");
    let steps = 0;
    const res = await harness.runAgent(
      {
        step: async () => {
          steps++;
          if (steps > 100) throw new Error("harness looped without a circuit breaker");
          return { type: "tool_call", toolName: "edit_file", toolArgs: { path: "a.test.ts" }, costUsd: 0 };
        },
        executeTool: async () => ({ outcome: "progress", output: "" }),
      },
      { runId: "r", tenantId: "t", agentId: "a", userPrompt: "u", provenance: "user_direct", constraints: { maxAttempts: 4 } }
    );
    expect(res.status).toBe("ESCALATED_BLOCKER");
    expect(steps).toBe(4);
  });

  it("a model that keeps calling an unregistered tool is halted", async () => {
    const harness = new DefaultActiveAgentHarness(engine, cortex, new Map(), "p");
    let steps = 0;
    const res = await harness.runAgent(
      {
        step: async () => {
          steps++;
          if (steps > 100) throw new Error("harness looped without a circuit breaker");
          return { type: "tool_call", toolName: "ghost", costUsd: 0 };
        },
        executeTool: async () => ({ outcome: "progress", output: "" }),
      },
      { runId: "r", tenantId: "t", agentId: "a", userPrompt: "u", provenance: "user_direct", constraints: { maxAttempts: 3 } }
    );
    expect(res.status).toBe("ESCALATED_BLOCKER");
    expect(steps).toBe(3);
  });

  it("MCP proxy: unclassified tools fail closed, and one idempotency key executes upstream once", async () => {
    let calls = 0;
    const proxy = new ActiveMcpProxyServer(
      {
        listTools: async () => [{ name: "send_webhook" }],
        callTool: async () => {
          calls++;
          await new Promise((r) => setTimeout(r, 10));
          return { content: "sent" };
        },
      },
      driver,
      []
    );
    const registry = await proxy.buildEnforcedToolRegistry();
    expect(registry.get("send_webhook")?.requiresApproval).toBe(true);

    const [a, b] = await Promise.all([
      proxy.executeIdempotentTool("send_webhook", { url: "u" }, "run:1:abc"),
      proxy.executeIdempotentTool("send_webhook", { url: "u" }, "run:1:abc"),
    ]);
    expect(calls).toBe(1);
    expect(a.outcome).toBe("progress");
    expect(b).toEqual(a);

    await proxy.executeIdempotentTool("send_webhook", { url: "u" }, "run:1:abc");
    expect(calls).toBe(1); // served from the ledger
  });
});
