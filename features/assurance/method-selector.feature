Feature: The adaptive problem-solving method selector
  As the estate's decision layer
  I want a deterministic recommendation of the next problem-solving method
  So that a method is chosen from evidence rather than from habit, and never from a guess

  The founder's operational contract (OPERATIONAL_SPEC.md v0.1) is the specification of
  record. These scenarios are its BDD acceptance clause, bound to the real library in
  packages/method_selector - nothing here is mocked, because there is nothing to mock:
  the selector is a pure function over typed data.

  Scenario: A reproducible regression with history selects bisect, and Bayesian updating is not chosen by default
    Given a regression problem with repository history and a reproducible check
    When the selector runs
    Then git bisect is the recommended method
    And Bayesian inference is not among the ranked candidates
    And the recommendation grants no execution authority

  Scenario: A formal invariant without a model is refused for missing prerequisite evidence
    Given a formal problem with a property specification and no system model
    When the selector runs
    Then no method is recommended
    And the decision is an abstention
    And the missing prerequisite is the system model
    And a bounded probe is requested instead of an invented prerequisite

  Scenario: A high-risk production context needs explicit authorization for an experimental action
    Given a high risk incident with a replayable environment and no authorization
    When the selector runs
    Then the counterfactual experiment is not recommended
    And the decision names the missing authorization

  Scenario: An authorized experimental method is recommended, and only as a recommendation
    Given a high risk incident with a replayable environment and an explicit authorization
    When the selector runs
    Then the counterfactual experiment is recommended
    And the decision requires authorization

  Scenario: An exhausted budget schedules no method
    Given a regression problem with repository history and an exhausted budget
    When the selector runs
    Then no method is recommended
    And the decision is a refusal because the budget is exhausted

  Scenario: Contradictory observations force reassessment
    Given a regression problem with repository history and contradictory observations
    When the selector runs
    Then the decision is reassessment
    And the contradictions are carried in the selection

  Scenario: Missing evidence yields abstention, never an invented prerequisite
    Given a regression problem with no evidence at all
    When the selector runs
    Then no method is recommended
    And the decision is an abstention

  Scenario: Stale evidence yields abstention, never a stale recommendation
    Given a regression problem with only stale evidence
    When the selector runs
    Then no method is recommended
    And the decision is an abstention

  Scenario: An unavailable dependency is reported and the safe path is taken
    Given a regression problem with repository history and an unavailable dependency
    When the selector runs
    Then no method is recommended
    And the decision names the unavailable dependency

  Scenario: The same request replays to the same fingerprint and the same trace id
    Given a regression problem with repository history and a reproducible check
    When the selector runs twice
    Then both selections carry the same fingerprint
    And both selections carry the same trace id
    And both selections carry the same method

  Scenario: A malformed request is rejected rather than guessed
    Given a request with an unknown schema version
    When the selector runs safely
    Then the decision is a refusal
    And the reason code is an unknown schema version
