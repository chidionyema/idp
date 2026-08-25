@cp11 @phase2
Feature: Consensus check — a legacy/DAG mismatch is an alert, never a freeze
  Scenario: Mismatch is surfaced to the HUD
    Given the DAG answer differs from the legacy answer
    Then one alert reaches the cockpit Inbox with both hashes and the query
    And the legacy answer is returned to the caller
    And no service is stopped

  Scenario: Match rate is measured
    When I run "bin/sb consensus --json"
    Then the output has "reads", "matches", "mismatches", "rate"
