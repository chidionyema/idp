Feature: L1 Checkpoint Layer
  As the estate operator
  I need running agents and scripts to survive stall-kill
  So that at most 30 seconds of work is lost on any SIGKILL

  Background:
    Given the Redis checkpoint sink is running
    And the efda wrapper is installed

  Scenario: A checkpoint is written on the periodic tick
    Given a wrapper-managed process is running with runner_id "efda-test-run-001"
    When the process makes progress for 31 seconds
    Then the checkpoint key "efda:ckpt:efda-test-run-001" exists
    And the checkpoint holds at least one completed step

  Scenario: A checkpoint is written on SIGTERM
    Given a wrapper-managed process is running with runner_id "efda-test-run-002"
    When the wrapper receives SIGTERM
    Then the checkpoint key "efda:ckpt:efda-test-run-002" exists
    And the process exits with code 143

  Scenario: A SIGKILL leaves a partial artifact and the last checkpoint
    Given a wrapper-managed process is running with runner_id "efda-test-run-003"
    And the checkpoint for "efda-test-run-003" holds the steps "step_a" and "step_b"
    When the wrapper is SIGKILLed
    Then a partial artifact exists for "efda-test-run-003"
    And the artifact's failure_class is "hard_kill"
    And the checkpoint for "efda-test-run-003" still holds "step_a"

  Scenario: An unreachable sink falls back to the local WAL
    Given the Redis checkpoint sink is stopped
    And a wrapper-managed process is running with runner_id "efda-test-run-004"
    When the process is killed
    Then a local WAL entry exists for "efda-test-run-004"
    And when the sink returns the WAL drains the artifact
