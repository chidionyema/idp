# docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md, section 3 (ROUTE-01..06),
# tracked by idp#3525 CP3. Scenarios are the spec's own ACCEPT lines, not new criteria.

@cp3
Feature: Routing and escalation — one router, an independently toggleable matrix, verifier-driven escalation, local floor

  Scenario: ROUTE-01 — all model calls traverse the standardized router, direct calls are rogue
    Given the network policy governing egress from the estate
    When anything but the router attempts to reach a provider API directly
    Then the network policy denies the egress
    And the bypass attempt alerts

  Scenario: ROUTE-02 — resource tier, candidate volume, selection method and escalation pattern are independent config axes
    Given the same 50-task set
    When it is executed against at least 4 different config cells with no code change between cells
    Then results are queryable by config_id in Langfuse
    Given a config cell is toggled off mid-run
    When the toggle is applied
    Then new requests reroute within one poll interval

  Scenario: ROUTE-03 — verifier-driven escalation makes misroute risk zero by construction
    Given an adversarial misroute suite of wrong-cheap-answer attempts
    When those attempts run through the router
    Then they escalate
    Given right-cheap-answer attempts in the same suite
    When those attempts run through the router
    Then they pass without touching expensive lanes

  Scenario: ROUTE-04 — NL-judgment escalation is signaled by disagreement between two cheap models
    Given a seeded disagreement corpus
    When the corpus runs through the router
    Then the escalate rate tracks the seeded disagreement rate
    Given agreement cases in the same corpus
    When those cases run through the router
    Then they never escalate

  Scenario: ROUTE-05 — semantic intent routing is a named gap, present as a toggleable axis, default off
    Given the config schema for the routing matrix
    When the schema is reviewed
    Then a filter_depth axis is present and toggleable
    And it defaults to off
    And the gap is recorded

  Scenario: ROUTE-06 — the fallback chain terminates at the always-on local model, never at a paid pool
    Given all external lanes are killed
    When a request is made
    Then the local model answers with a DEGRADED marker
    And no request drops
