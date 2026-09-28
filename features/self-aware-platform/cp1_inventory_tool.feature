@cp1
Feature: Inventory tool — one call answers what the estate is
  Founder: "the platform has all the maps and internal state to answer any
  question about itself." An agent asking "what is running, and who owns it"
  costs eight shell commands today. This is the first MCP call that answers
  it from what the estate already computed — crew/STATE.md and the Backstage
  catalog — never by re-measuring the estate itself.

  Scenario: One MCP call replaces the shell-command chain
    Given the estate MCP server is running behind Agentgateway
    When an agent calls mcp__estate__get_estate_inventory with no arguments
    Then the response lists every catalog entity with its owner and repo
    And the response cites the crew/STATE.md snapshot timestamp it read
    And the agent made exactly one tool call to get the answer

  Scenario: The tool never shells out
    Given the estate MCP server source for get_estate_inventory
    Then it contains no subprocess call, no shell="true", and no os.system
    And every fact in its response traces to crew/STATE.md or the Backstage catalog API, not a fresh probe of a running process

  Scenario: A stale snapshot is disclosed, not hidden
    Given crew/STATE.md is older than the freshness threshold in its own header
    When an agent calls get_estate_inventory
    Then the response marks itself "stale" with the snapshot's age in minutes
    And no field is silently dropped to hide the staleness
