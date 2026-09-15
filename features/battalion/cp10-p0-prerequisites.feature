# docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md, section 9 (P0-01..03),
# tracked by idp#3525 CP10. Scenarios are the spec's own statements, reusing the ACCEPT
# lines of the REQs each P0 names (COST-01, CFG-01, UX-02) as its own proof obligation.

@cp10
Feature: The three P0 prerequisites gate every other claim in the Battalion

  Scenario: P0-01 — the breaker severs, or every COST-01-dependent claim in the spec is fiction
    Given request_ceiling.proxy_handler_instance
    When the same fault-injection test as COST-01 runs (synthetic 2M tok/hr load)
    Then it severs traffic rather than warning
    And until it severs, no section 1-8 claim depending on COST-01 may be made

  Scenario: P0-02 — the CFG-01 config document exists, or every axis is a code-level toggle, not a product capability
    Given the single hot-reloadable Battalion config document
    When its existence is checked
    Then it exists before any "seamless enable/disable of the full matrix" claim is made
    And until it exists, every axis in sections 3 and 5 is a code-level toggle only

  Scenario: P0-03 — the UX-02 edge-case suite is green, or "reliable as electricity" is marketing
    Given the UX-02 fault-injection suite covering every enumerated edge case
    When the suite is run
    Then it is green before any "reliable as electricity" claim is made
    And until every enumerated edge case has a passing degradation test, that claim is not verified
