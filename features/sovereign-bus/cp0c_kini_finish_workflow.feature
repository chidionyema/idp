# crew#396 step 3: "type 'Finish KINI', close the laptop, wake up to a green dashboard". The seven
# KINI checkpoints (crew#284) run as one durable workflow on the in-cluster engine (cp0) and
# worker (cp0b): every activity retries, and a platform fault heals and re-runs instead of
# failing the run.
Feature: The KINI checkpoints finish as one durable workflow
  # Bound by sovereign/tests/bdd/test_cp0c_kini_finish_workflow.py

  Scenario: Every checkpoint verdict comes from pytest's exit, and the unknown branch is never silent
    Given a checkpoint bound to a passing bdd file
    Then the checkpoint activity returns pass
    Given a checkpoint bound to a failing bdd file
    Then the checkpoint activity returns fail
    Given a checkpoint bound to no bdd file
    Then the checkpoint activity returns unbound
    Given a checkpoint whose conftest cannot import
    Then the checkpoint activity returns platform-fault

  Scenario: A checkpoint that flakes is retried and a platform fault is healed, not failed
    Given a worker on a local Temporal with a checkpoint that fails once and then passes
    And a checkpoint that reports a platform fault once and then passes
    When KiniFinishWorkflow runs
    Then every checkpoint is green
    And the flaky checkpoint ran twice under its RetryPolicy
    And the faulting checkpoint healed once and ran twice

  Scenario: The workflow and both activities are on the worker the cluster runs
    Then sovereign.engine.worker registers KiniFinishWorkflow, kini_run_checkpoint and kini_cluster_ready
    And bin/idp-kini finish starts it by the one workflow id in config
    And the worker Deployment can read nodes through its own ServiceAccount
