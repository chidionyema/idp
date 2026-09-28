@cp3 @kini @worker-registry
Feature: The live worker serves every workflow the CLI can start
  KINI master spec (crew#284) CP3. `sb run --branches N` starts
  BranchParentWorkflow on the estate task queue. A workflow the worker does
  not register is accepted by Temporal and never picked up, so the run hangs
  with no error. The rule: every workflow the CLI starts, and every activity
  those workflows call, is registered by sovereign.engine.worker.

  Scenario: Branch workflows are registered on the live worker
    Given the worker module sovereign.engine.worker
    Then WORKFLOWS contains SessionWorkflow, BranchParentWorkflow and BranchChildWorkflow
    And every activity name the shadow workflow executes is in ACTIVITIES

  Scenario: A real fork and merge runs on the registered worker
    Given a worker built from sovereign.engine.worker.WORKFLOWS and ACTIVITIES
    When BranchParentWorkflow forks two children over a scratch repo
    Then a BRANCH_MERGE receipt names the winner
