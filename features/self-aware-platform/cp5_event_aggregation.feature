@cp5
Feature: Event aggregation behind Temporal — a storm becomes one event
  Founder's pasted design: "state changes are pushed to a bus the agent
  subscribes to. Failure: alert storms flood the agent's context and cause
  reaction loops. Fix: debounce and aggregate behind Temporal; 50 crashes in
  10s arrive as one cascading_failure event." This sits on the existing
  Sovereign Bus (crew#213), not a second event bus.

  Scenario: 50 crashes in 10 seconds collapse to one event
    Given the Sovereign Bus event aggregation window is 10 seconds
    When 50 crash events for related workloads are emitted within 10 seconds
    Then the subscribing agent receives exactly one "cascading_failure" event
    And that event lists all 50 underlying crashes by workload and timestamp

  Scenario: Events outside the window are not merged
    Given the aggregation window is 10 seconds
    When one crash event fires, then 15 seconds pass, then a second crash fires
    Then the agent receives two separate events, not one

  Scenario: Storm test proves the collapse ratio
    Given a test harness emitting N events uniformly across T seconds, for
      N in {10, 50, 200, 1000} and T in {1, 5, 10} seconds
    When the aggregation window is T seconds
    Then the agent-visible event count is less than N for every case where
      events fall inside a shared window
    And the harness prints N, T, and the resulting event count for each case

  Scenario: Aggregation does not drop information, only delivery count
    Given a cascading_failure event produced by aggregating 50 crashes
    Then every one of the 50 source crashes is still retrievable from the
      event's detail payload or a linked receipt, not discarded
