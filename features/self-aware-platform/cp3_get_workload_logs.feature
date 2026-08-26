@cp3
Feature: get_workload_logs — the separate drill-down tool for raw detail
  Founder's fix for fat-tool bloat: "summarize by default, drill on demand
  via a separate get_workload_logs(tail=50)." This tool exists precisely so
  cp2 never has to inline raw logs.

  Scenario: An agent drills into logs only when it asks
    Given get_workload_state("app-x") returned a summary with no raw logs
    When an agent calls mcp__estate__get_workload_logs("app-x", tail=50)
    Then the response contains the last 50 log lines for app-x
    And no other tool call was needed to reach the raw log content

  Scenario: tail is bounded even when a larger value is requested
    When get_workload_logs("app-x", tail=1000000) is called
    Then the response contains at most the server's configured maximum tail
      lines, not 1,000,000 lines
    And the response states the maximum it enforced

  Scenario: get_workload_state and get_workload_logs are distinct tools
    Given the MCP tool list exposed by the estate server
    Then get_workload_state and get_workload_logs are registered as two
      separate tools, not one tool with a hidden verbose flag
