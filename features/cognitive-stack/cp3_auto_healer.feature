# idp#3448 CP3. Founder: "Auto-Healer: a background LLM worker continuously reads the graph
# and checks it against live OpenTelemetry data; if the graph claims an edge (e.g. 'Service A
# calls Service B') the traces don't show, the worker deletes the edge. Graph must be
# empirically true, not human-written."
@cp3
Feature: Auto-Healer — an uncorroborated edge is deleted, never left as a human claim

  Scenario: A manufactured false edge is deleted within one healer cycle
    Given a CALLS edge in Memgraph from Service A to Service B
    And live OpenTelemetry traces over the healer's lookback window show no span from A to B
    When the auto-healer worker completes one cycle
    Then the CALLS edge from A to B is deleted
    And a log line names the deleted edge, its two nodes and the trace query that found nothing

  Scenario: A corroborated edge survives
    Given a CALLS edge in Memgraph from Service A to Service B
    And live OpenTelemetry traces show at least one span from A to B in the lookback window
    When the auto-healer worker completes one cycle
    Then the CALLS edge from A to B still exists

  Scenario: The healer's own workload is fenced and health-checked like every other
    Given the epistemic-fabric-healer Deployment
    Then its namespace carries a default-deny NetworkPolicy, a ResourceQuota and a LimitRange
    And its healthcheck names an object the row itself creates
