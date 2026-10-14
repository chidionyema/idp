// eslint.config.mjs
export default [
  {
    files: ["src/agents/**/*.ts", "src/workflows/**/*.ts"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "@cortexmemory/sdk",
              message:
                "Direct Cortex SDK access is forbidden in agents. Use createFleetGateway() so Active Memory bi-temporal guards run automatically.",
            },
            {
              name: "@modelcontextprotocol/sdk",
              message:
                "Direct MCP tool execution is forbidden in agents. Route all tools through ActiveMcpProxyServer for Active Focus & Approval gates.",
            },
          ],
        },
      ],
    },
  },
];
