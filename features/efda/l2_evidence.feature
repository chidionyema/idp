Feature: L2 Evidence Layer
  As the estate operator
  I need every failure to leave evidence at a known address
  So that the next actor reads the evidence instead of reconstructing it

  Background:
    Given the Redis checkpoint sink is running
    And the efda wrapper is installed

  Scenario: The wrapper captures an agent failure
    Given a wrapper-managed process is running with runner_id "efda-test-run-010"
    When the agent exits with code 1
    Then an artifact exists for "efda-test-run-010"
    And the artifact validates against the agent schema
    And the artifact's integrity.writer_identity names a spiffe identity

  Scenario: The artifact address is deterministic
    Given a wrapper-managed process is running with runner_id "efda-test-run-011"
    When the agent exits with code 1
    Then the artifact's address is "oke/default/efda-test-agent/efda-test-run-011/artifact.json"

  Scenario: A controller cannot declare a failure without an artifact reference
    Given the registry CRDs are installed
    When a controller declares the status phase "Failed"
    Then the write is refused
    And the refusal names "diagnosticArtifactRef"

  Scenario: The read-first contract is enforced on a relaunch
    Given a runner "efda-test-run-012" has no artifact
    When the supervisor attempts to relaunch "efda-test-run-012"
    Then the relaunch is refused
    And a SCHEMA_VIOLATION artifact is created
    And the task is routed to human review
