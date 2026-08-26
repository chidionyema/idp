@cp15
Feature: Cross-model consensus under a policy invariant
  Master Spec v1.0 §4.2. Destructive ops go to three models through LiteLLM;
  two of three must propose the same normalized tool call, AND the call must
  be inside the AGENTS.md allowlist. Policy beats consensus. Late votes are
  rejected; partial quorum on a destructive op is a hard fail.

  Scenario: Two of three agree and the call is allowed
    Given a destructive op proposal and three configured models
    When two models propose the same normalized tool call within 30 seconds
    And the call is in the allowlist
    Then the op proceeds with a receipt naming the three votes

  Scenario: Consensus outside policy is blocked
    When three models agree on a call not in the allowlist
    Then the op is blocked and the receipt says "policy"

  Scenario: A late vote does not count
    When only one model answers within 30 seconds
    Then the op fails hard and no retry happens without a founder signal

  Scenario: Non-destructive ops use one cheap model
    Given a non-destructive op
    Then exactly one model is called, the cheapest in the LiteLLM fallback chain

  Scenario: The default voters are three different models
    Given the shipped configuration with no consensus override
    Then the consensus list names three aliases and no alias appears twice
    And every alias is a model_name the LiteLLM proxy config serves

  Scenario: sb model-consensus reaches the vote
    Given a destructive op proposal and three configured models
    When two models propose the same normalized tool call within 30 seconds
    And the call is in the allowlist
    Then "sb model-consensus --op <op> --destructive" exits 0 with the verdict
