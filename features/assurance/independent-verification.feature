Feature: Independent verification
  A verdict is evidence, not a claim. The estate's own verification engine
  decides whether the work was done, the receipt points at the exact report it
  read, and the agent that did the work may not sign its own acceptance.

  Scenario: A verified pipeline becomes a passing receipt
    Given a node owned by "pi-aee-research"
    And an NSVEE report whose status is "VERIFIED"
    When the report is turned into a verification receipt
    Then the receipt's verdict is "pass"
    And the receipt's evidence points at the report
    And the receipt's verifier is "nsvee"

  Scenario: A degraded sandbox is inconclusive, never a failure of the work
    Given a node owned by "pi-aee-research"
    And an NSVEE report whose status is "SANDBOX_DEGRADED"
    When the report is turned into a verification receipt
    Then the receipt's verdict is "inconclusive"
    And the node is not accepted by that receipt

  Scenario: The agent that did the work cannot sign its own objective acceptance
    Given a node owned by "pi-aee-research"
    When an objective-level receipt signed by "pi-aee-research" is recorded
    Then the recording is refused
    And the refusal says the acceptance must be independent

  Scenario: An independent verifier signs the objective acceptance
    Given a node owned by "pi-aee-research"
    And an objective-level receipt signed by "pi-aee-ops"
    When the receipt is recorded
    Then the receipt is in the graph
    And the node can be accepted with it
