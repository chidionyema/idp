Feature: The estate's allocation policy
  One request in, one decision out: the same node, supply, budget and deadline
  always buy the same contract, and a deterministic lane is preferred over a
  model lane whenever it can do the work.

  Scenario: The same request is allocated the same way every time
    Given a node that needs summarising
    And a supply of one deterministic lane and one model lane
    When the node is allocated one hundred times
    Then every allocation is identical

  Scenario: A deterministic lane is chosen over a model lane
    Given a node that needs summarising
    And a supply of one deterministic lane and one model lane
    When the node is allocated
    Then the contract names the deterministic lane
    And the reason is the deterministic bypass

  Scenario: A learned policy proposes and the deterministic policy decides
    Given a node that needs summarising
    And a supply of one deterministic lane and one model lane
    When the node is allocated with the model lane proposed in shadow
    Then the contract still names the deterministic lane
    And the disagreement is recorded

  Scenario: A node no lane can take is refused with the reason
    Given a node that needs summarising
    And a supply of one deterministic lane that cannot summarise
    When the node is allocated
    Then the allocation is refused
    And the refusal names the lane and what it cannot do
