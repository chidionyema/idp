# docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md, section 4 (VER-01..04),
# tracked by idp#3525 CP4. Scenarios are the spec's own ACCEPT lines, not new criteria.

@cp4
Feature: Verification and selection — the gauntlet, strategy-slotted selection, claim-graph as NL verifier, capped volume

  Scenario: VER-01 — attestation stays bound to the SHA-256 of verified bytes
    Given a candidate that passed the three-stage gauntlet (structural compile / Z3 symbolic / execution tests)
    When the verified bytes are mutated after attestation
    Then the attestation is invalidated

  Scenario: VER-02 — weighted voting or multi-verifier is used where a real verifier exists, plain best-of-N is disallowed there
    Given a Z3-scored domain with selection set to weighted-vote
    When the harness runs candidates for that domain
    Then the harness honors weighted-vote selection
    Given an unverifiable domain
    When the harness scales candidate volume N for that domain
    Then N is capped

  Scenario: VER-03 — the claim-graph (DoD v3) is reused as the NL verifier for NL output candidates
    Given a set of NL output candidates
    When the claim-graph run executes over those candidates
    Then verdicts are produced and recorded in the trace

  Scenario: VER-04 — candidate volume is capped for tasks with no real verifier, regardless of config
    Given a task class with no real verifier
    When the harness detects that task class
    Then candidate volume N is capped at the declared constant
    And no config setting raises N above that constant
