@cp10 @phase2
Feature: Dual-read router — every read runs twice, legacy and DAG, and is compared
  Scenario: Both paths execute
    When a read goes through the router
    Then the legacy DB answered and the DAG walk answered
    And the receipt records both hashes and the latency of each

  Scenario: Reads never slow the caller past the key
    Then p95 router overhead stays under config key dualread.max_overhead_ms, measured over 1000 reads
