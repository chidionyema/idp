// src/index.ts
import { ActiveMemoryEngine } from "./memory/active-memory-engine";
import { DefaultActiveAgentHarness, UnderlyingAgentDriver, AgentTurnInput } from "./runtime/default-agent-wrapper";
import {
  AcidBackendDriver,
  CustomFastMemoryStore,
  ProductionCortexAdapter,
  VectorEmbedder,
} from "./adapters/cortex-convex-adapter";
import { ActiveMcpProxyServer, RawMcpServerConnection } from "./mcp/active-mcp-proxy";
import { ToolMetadata } from "./focus/active-focus-controller";

export async function createFleetGateway(config: {
  acidBackend: AcidBackendDriver;
  embedder: VectorEmbedder;
  upstreamMcp: RawMcpServerConnection;
  explicitToolPolicies: ToolMetadata[];
  baseSystemPrompt: string;
}) {
  const cortexAdapter = new ProductionCortexAdapter(config.acidBackend, config.embedder);
  const customMemory = new CustomFastMemoryStore();
  const memoryEngine = new ActiveMemoryEngine(cortexAdapter, customMemory);

  const mcpProxy = new ActiveMcpProxyServer(
    config.upstreamMcp,
    config.acidBackend,
    config.explicitToolPolicies
  );
  const enforcedToolRegistry = await mcpProxy.buildEnforcedToolRegistry();

  const harness = new DefaultActiveAgentHarness(
    memoryEngine,
    cortexAdapter,
    enforcedToolRegistry,
    config.baseSystemPrompt
  );

  return {
    memoryEngine,
    cortexAdapter,
    mcpProxy,
    /**
     * Binds any agent step model into the enforced Active Memory + Active Focus runtime.
     */
    registerAgent(agentStepFn: UnderlyingAgentDriver["step"]) {
      const boundDriver: UnderlyingAgentDriver = {
        step: agentStepFn,
        executeTool: (toolName, args, idempotencyKey) =>
          mcpProxy.executeIdempotentTool(toolName, args, idempotencyKey),
      };

      return {
        invoke: (input: AgentTurnInput) => harness.runAgent(boundDriver, input),
      };
    },
  };
}
