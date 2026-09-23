# docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md, section 2 (JIT-01..02),
# tracked by idp#3525 CP2. Scenarios are the spec's own ACCEPT lines, not new criteria.

@cp2
Feature: Compute provisioning is point-of-use, honoring each tier's real activation floor

  Scenario: JIT-01 — Apple Silicon and GPU tiers are not treated as interchangeable on activation floor
    Given a config that declares activation_floor per compute tier
    When the orchestrator models an Apple Silicon tier below 24 hours of granularity
    Then the orchestrator refuses
    Given a GPU tier declared per-second with no floor
    When the orchestrator models that tier at sub-24h granularity
    Then the orchestrator proceeds

  Scenario: JIT-02 — a cold start beyond the latency budget degrades to the next lane, marked in-trace
    Given a request running on a tier mid-flow
    When the instance is killed mid-flow
    Then the trace shows a DEGRADED marker
    And the response continues from the fallback lane
