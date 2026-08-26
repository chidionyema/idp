@cp3
Feature: Observability and audit — OTel GenAI traces reach Langfuse
  The founder: "OpenTelemetry GenAI instrumentation on agent code, routed to
  Langfuse, giving an immutable audit trail (cost, latency, tokens, tool
  invocations) for EU AI Act."

  Scenario: The primary receiver answers
    Given observability/langfuse.yml is running
    When I run "bin/langfuse-status"
    Then the primary receiver on 127.0.0.1:3200 answers HTTP "200"

  Scenario: A real agent run produces a queryable, complete trace
    Given an agent has completed one real run with OTel GenAI instrumentation on
    When I query that trace through the Langfuse API
    Then the trace has non-null cost, latency, token count and tool-invocation fields
