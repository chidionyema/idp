// src/mcp/active-mcp-proxy.ts
import { ToolMetadata } from "../focus/active-focus-controller";
import { AttemptOutcomeStatus } from "../types/active-runtime";
import { AcidBackendDriver } from "../adapters/cortex-convex-adapter";

export interface RawMcpToolCall {
  name: string;
  arguments: Record<string, unknown>;
}

export interface RawMcpServerConnection {
  listTools(): Promise<Array<{ name: string; description?: string }>>;
  callTool(
    name: string,
    args: Record<string, unknown>
  ): Promise<{ isError?: boolean; content: string; errorCode?: string }>;
}

type ToolExecutionResult = {
  outcome: AttemptOutcomeStatus;
  output: string;
  errorCode?: string;
  errorSummary?: string;
};

export class ActiveMcpProxyServer {
  private readonly catalog = new Map<string, ToolMetadata>();
  /** Same-process concurrent calls with one idempotency key share one upstream execution. */
  private readonly inFlight = new Map<string, Promise<ToolExecutionResult>>();

  constructor(
    private readonly upstreamMcp: RawMcpServerConnection,
    private readonly acidBackend: AcidBackendDriver,
    explicitToolPolicies: ToolMetadata[]
  ) {
    for (const meta of explicitToolPolicies) {
      this.catalog.set(meta.toolName, meta);
    }
  }

  /**
   * Synchronizes upstream MCP tools and enforces a FAIL-CLOSED policy:
   * Any newly discovered MCP tool without an explicit policy is automatically
   * placed in `unclassified_external` with `requiresApproval: true`.
   */
  async buildEnforcedToolRegistry(): Promise<Map<string, ToolMetadata>> {
    const upstreamTools = await this.upstreamMcp.listTools();
    for (const tool of upstreamTools) {
      if (!this.catalog.has(tool.name)) {
        this.catalog.set(tool.name, {
          toolName: tool.name,
          strategyClass: `unclassified_${tool.name}`,
          capabilityTags: ["unclassified_side_effect"],
          requiresApproval: true, // Fail-closed default
          extractTargetResource: (args) =>
            String(
              args.path ??
                args.url ??
                args.recipient ??
                args.table ??
                "unspecified_resource"
            ),
        });
      }
    }
    return new Map(this.catalog);
  }

  /**
   * Executes a tool through the MCP proxy with ACID idempotency deduplication.
   * If an Active Focus retry or network blip replays the exact same step and payload,
   * the cached outcome is returned without executing duplicate external side effects.
   */
  async executeIdempotentTool(
    toolName: string,
    args: Record<string, unknown>,
    idempotencyKey: string
  ): Promise<ToolExecutionResult> {
    const running = this.inFlight.get(idempotencyKey);
    if (running) return { ...(await running) };

    const execution = this.executeOnce(toolName, args, idempotencyKey);
    this.inFlight.set(idempotencyKey, execution);
    try {
      return await execution;
    } finally {
      this.inFlight.delete(idempotencyKey);
    }
  }

  private async executeOnce(
    toolName: string,
    args: Record<string, unknown>,
    idempotencyKey: string
  ): Promise<ToolExecutionResult> {
    // 1. Check ACID Idempotency Ledger
    const cached = await this.acidBackend.executeAcidTransaction(async (store) => {
      return store.idempotency.get(idempotencyKey) ?? null;
    });

    if (cached) {
      return { ...cached };
    }

    // 2. Invoke Upstream MCP Tool
    try {
      const rawResult = await this.upstreamMcp.callTool(toolName, args);

      const formattedResult: ToolExecutionResult = rawResult.isError
        ? {
            outcome:
              rawResult.errorCode === "ECONNREFUSED" ||
              rawResult.errorCode === "RATE_LIMIT"
                ? "blocked"
                : "failed",
            output: rawResult.content,
            errorCode: rawResult.errorCode ?? "TOOL_ERROR",
            errorSummary: rawResult.content.slice(0, 240),
          }
        : {
            outcome: "progress",
            output: rawResult.content,
          };

      // 3. Persist in ACID Idempotency Ledger
      await this.acidBackend.executeAcidTransaction(async (store) => {
        store.idempotency.set(idempotencyKey, formattedResult);
      });

      return formattedResult;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return {
        outcome: "failed",
        output: message,
        errorCode: "UNHANDLED_EXCEPTION",
        errorSummary: message.slice(0, 240),
      };
    }
  }
}
