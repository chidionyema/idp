@cp5
Feature: Protocols — official MCP SDK replaces the proprietary board schema, fronted by Agentgateway
  The founder: "official MCP Python/TypeScript SDKs replacing the proprietary
  board schemas; agents reach SQLite databases and internal tools through MCP;
  Agentgateway securing agent-to-tool connections." Strict bar: unlike SPIFFE,
  Agentgateway has a standalone non-k8s runtime and the gap it closes (zero
  authz/audit between an agent and a tool server) exists today, so it is
  adopted now, scoped to fronting these MCP servers only.

  Scenario: The board and estate.db are MCP tools, not a proprietary schema
    Given an MCP server built on the official modelcontextprotocol SDK
    When an agent lists available tools
    Then the crew board and catalog/estate.db are each exposed as an MCP tool

  Scenario: Every MCP call passes through Agentgateway
    Given "docker compose -f idp/mcp/agentgateway.yml" is running
    When an agent calls a board tool and a database tool
    Then both calls round-trip through Agentgateway and return HTTP 200
    And no agent reaches either MCP server by any other path
