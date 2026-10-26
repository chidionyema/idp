Feature: Remediation
  As the estate operator
  I need every action to be earned, bounded and reversible
  So that self-healing cannot become self-harm

  Background:
    Given the executor's allowlist

  Scenario: A baseline signature may only report
    Given a report whose signature is tier "T0"
    When the executor runs
    Then no action is taken
    And the executor logs "tier=T0, action=report_only"

  Scenario: A tier T1 action without a safety proof is refused
    Given a report whose signature is tier "T1" and has no safety proof
    When the executor runs
    Then no action is taken
    And the executor logs "safety_proof_missing"

  Scenario: An action the allowlist does not name is refused
    Given a report whose signature is tier "T1" with a safety proof
    And the allowlist is empty
    When the executor runs
    Then no action is taken
    And the executor logs "action_not_in_allowlist"

  Scenario: A tier T1 action below the confidence gate is refused
    Given a report whose signature is tier "T1" with a safety proof and confidence 0.84
    And the allowlist names that signature
    When the executor runs
    Then no action is taken
    And the executor logs the confidence gate

  Scenario: An allowed action is applied and recorded
    Given a report whose signature is tier "T1" with a safety proof and confidence 0.9
    And the allowlist names that signature with a rollback
    When the executor runs
    Then the action is applied
    And a RemediationArtifact records the action, the pre-state and the rollback point
