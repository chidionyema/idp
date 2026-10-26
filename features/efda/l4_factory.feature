Feature: Pack Factory
  As the estate operator
  I need packs to be generated and proven before they are trusted
  So that coverage is a pipeline and not a project

  Background:
    Given a corpus of observed failure artifacts

  Scenario: A baseline pack is generated for a new class
    Given no SkillPack exists for the class "efda-test-workload"
    When the baseline generator runs
    Then a SkillPack exists with coverageTier "baseline"
    And it carries at least ten technology-agnostic signatures
    And every signature has a confidence base of at most 0.50
    And its execution budget is the lowest tier
    And every signature may only report

  Scenario: Synthesis turns observations into a candidate
    When the synthesizer runs for the class "efda-test-agent"
    Then a candidate pack exists
    And it is tagged with the factory that generated it
    And it records the digest of the corpus it came from

  Scenario: A low-precision signature is not promoted
    Given a candidate whose signature fires on every artifact
    When the validator runs
    Then the candidate is rejected
    And the report names the precision floor

  Scenario: A mutating diagnostic question is rejected
    Given a candidate whose signature asks a question that mutates state
    When the validator runs
    Then the candidate is rejected
    And the report names the blast radius

  Scenario: A signature that ignores its budget is rejected
    Given a candidate whose match logic exceeds its wall clock budget
    When the validator runs
    Then the candidate is rejected
    And the report names the budget breach
