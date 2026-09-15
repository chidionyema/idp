# docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md, section 10 (UX-01..03),
# tracked by idp#3525 CP9. Scenarios are the spec's own ACCEPT lines, not new criteria.

@cp9
Feature: UX and reliability — as seamless and reliable as electricity

  Scenario: UX-01 — every tier/model/axis switch is invisible to the requester on the success path
    Given identical requests issued across 5 different config cells
    When the client-side integration test runs
    Then the responses are schema-identical
    And only the Langfuse trace differs between them

  Scenario: UX-02 — every enumerated edge case has a named, tested degradation path
    Given the enumerated edge-case matrix: cold start beyond JIT-02's budget, mid-request tier eviction, budget breach mid-stream, verifier timeout, all lanes down simultaneously, config hot-reload mid-request, and a malformed/adversarial CFG-01 edit disabling every lane
    When the fault-injection suite runs one test per row
    Then each row asserts a DEGRADED-marked response or a rejected config edit
    And never a 5xx or timeout with no marker

  Scenario: UX-03 — CFG-01 rejects any write that would leave zero enabled lanes reachable
    Given a CFG-01 write that would disable all lanes including the always-on local floor
    When the write is attempted
    Then it is rejected at the schema layer, not the runtime layer
    And the write never lands
