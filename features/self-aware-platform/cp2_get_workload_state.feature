@cp2
Feature: get_workload_state — one fat tool call, catalog plus metrics plus desired state
  Founder's pasted design: "get_workload_state(app) returns catalog + metrics +
  desired state in one payload." Failure mode he named: payload bloat — raw
  logs and raw timeseries kill the context. Fix he named: summarize by
  default; drilling is a separate tool (cp3).

  Scenario: One call answers "why is X down"
    Given a workload "app-x" registered in the Backstage catalog
    When an agent calls mcp__estate__get_workload_state("app-x")
    Then the response includes the catalog entry (owner, repo, dependencies)
    And the response includes summarized metrics (not raw timeseries points)
    And the response includes desired vs actual state for app-x
    And the agent needed exactly one tool call, not eight shell commands

  Scenario: The payload never carries raw logs or raw timeseries
    Given a workload with 10,000 log lines and 90 days of metric samples
    When get_workload_state is called for it
    Then the response contains no raw log line
    And the response contains no per-sample timeseries array
    And numeric metrics are pre-aggregated (min, max, mean, last, or similar)

  Scenario: Payload stays under the byte ceiling regardless of workload size
    Given a property test generating workloads with 1 to 100,000 log lines, 0 to 500 dependencies, and 0 to 10,000 metric samples
    When get_workload_state is called for each generated workload
    Then every response body is under the configured byte ceiling
    And this holds for at least 500 generated cases in one property-test run
