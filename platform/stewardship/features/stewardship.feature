Feature: Bounded autonomous estate stewardship
  Scenario: A discovery persists beyond its originating task
    Given an agent observes a reproducible recurring failure
    When it records an observation with evidence references
    Then the append-only case remains queryable across sessions
  Scenario: Telemetry or evidence must not be fabricated
    Given an observation has no verified supporting source
    Then it must be marked unverified rather than proven
  Scenario: Small reversible change may proceed under delegated authority
    Given a valid claim, baseline, rollback, independent verification and budget
    When the change is low-risk and isolated
    Then the policy permits execution subject to existing estate gates
  Scenario: Shared or irreversible change cannot silently proceed
    Given a shared, high-risk or irreversible proposal
    When the policy is evaluated
    Then execution is refused unless the relevant authority is granted
  Scenario: Faster but incorrect is not an improvement
    Given paired before and after measurements
    When latency improves but verified success decreases
    Then the improvement is not accepted
  Scenario: Evidence ledger detects mutation
    Given a stored observation
    When its contents are modified directly
    Then integrity verification fails
