@cp12
Feature: Provider agnostic — the model and the transport are both swappable
  LAW 34: nothing in this flow is written against one vendor's shape.

  Scenario: The flow's logic carries no vendor-specific import
    Given the mode-detection code and the confirmation-gate code for this flow
    Then neither imports a single named model provider directly
    And neither imports a single named messaging vendor directly
    And both are reached only through hermes-v2's platform adapter interface
