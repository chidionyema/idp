# docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md, section 1 (COST-01..04),
# tracked by idp#3525 CP1. Scenarios are the spec's own ACCEPT lines, not new criteria.

@cp1
Feature: Cost & spend governance — hard breaker, hardware-signed activation, breakeven-gated ladder, graded costs

  Scenario: COST-01 — the router budget breaker severs traffic at breach, it does not warn
    Given a synthetic load of 2M tokens/hour hitting the router
    When the fault-injection test drives that load through the breaker
    Then the breaker trips
    And traffic degrades to the declared local lane
    And an audit event is recorded

  Scenario: COST-02 — provisioning paid compute requires a hardware-rooted signature, not just budget
    Given a request to activate a paid compute tier with no hardware signature
    When the activation is attempted
    Then no provisioning call is made
    Given the same request with a hardware signature and quorum
    When the activation is attempted
    Then provisioning proceeds

  Scenario: COST-03 — Rung 2 flat-rate rental activates only above the computed breakeven band
    Given simulated trace volume below the breakeven band (58M-233M tok/mo at current router prices)
    When the cost ladder is evaluated
    Then no activation proposal is produced
    Given simulated trace volume above the breakeven band
    When the cost ladder is evaluated
    Then an activation proposal is produced with the computed numbers

  Scenario: COST-04 — every hosting tier row carries a receipt grade, or it fails schema
    Given a cost table with a vendor-doc, a survey and a founder-supplied-unverified row
    When the config schema is validated
    Then each row's grade column is present
    Given a cost table row with no grade column
    When the config schema is validated
    Then that row fails schema validation
