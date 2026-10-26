Feature: Reasoning Layer
  As the estate operator
  I need a ranked, cited diagnosis of a failure
  So that a human reads a conclusion instead of a log

  Background:
    Given an artifact for the class "efda-test-agent"
    And a specialist SkillPack for that class

  Scenario: The artifact produces a report with a named cause
    When the reasoning layer runs
    Then the report's status is "DIAGNOSED"
    And the report names a cause
    And the report's confidence is at least 0.5
    And the report cites at least one evidence reference
    And the report names the pack it came from

  Scenario: A thin artifact falls back to a human
    Given an artifact whose evidence is thin
    When the reasoning layer runs
    Then the report's status is "NEEDS_HUMAN"
    And the report lists the questions that were asked

  Scenario: An uncorroborated hypothesis is not propagated
    Given an artifact whose own assessment claims a cause nothing supports
    When the reasoning layer runs
    Then the report warns "UNCORROBORATED_HYPOTHESIS"
    And the report does not name that cause

  Scenario: A tampered artifact is refused
    Given an artifact whose payload was changed after it was written
    When the reasoning layer runs
    Then the report's status is "TAMPER_DETECTED"

  Scenario: A pack that costs too much does not starve the layer
    Given a pack whose match logic exceeds its wall clock budget
    When the reasoning layer runs
    Then the report records the budget breach
    And the reasoning layer moves to the next signature
