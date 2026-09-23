# docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md, section 5b (FL-01..04),
# tracked by idp#3525 CP6. Scenarios are the spec's own statements, not new criteria.

@cp6
Feature: Free-lunch invariants — the only leverage claims allowed to call themselves free of downside

  Scenario: FL-01 — speculative decoding never changes the output distribution
    Given a draft model used for speculative decoding
    When its output is accepted or rejected by rejection sampling
    Then the final output distribution is identical to the target model's own distribution
    And only latency improves

  Scenario: FL-02 — the exact-match cache keeps its safeguards, or it forfeits the free-lunch claim
    Given the exact-match cache
    When a cache hit is served
    Then the TTL, the per-call opt-out, and the reuse-marked-in-trace safeguards are all present
    Given any one of those safeguards is removed
    When the cache is evaluated
    Then it no longer qualifies as a free-lunch claim

  Scenario: FL-03 — config_id trace tagging is pure information gain on already-paid infrastructure
    Given a routed call tagged with config_id
    When the tag is added
    Then no new cost is incurred

  Scenario: FL-04 — weighted verifier voting on Z3-scored branches costs the same as unweighted selection
    Given Z3-scored candidate branches
    When selection uses weighted verifier voting instead of unweighted selection
    Then the generation cost is unchanged
    And selection is strictly better with no added risk

  Scenario: Any other free-lunch claim is rejected at intake unless its tradeoff is named
    Given a proposed mechanism claimed to have no downside
    When it is not one of FL-01, FL-02, FL-03 or FL-04
    Then it is rejected at intake
    But it is accepted once its tradeoff is named explicitly
