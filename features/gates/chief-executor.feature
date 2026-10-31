Feature: The always-on chief executor
  The estate's headless executor runs on a schedule, takes one task per tick, and
  can only land work through the Greenlane. Spec: docs/specs/2026-10-31-always-on-chief-executor.md

  Background:
    Given the executor harness is "pi" with model "minimax_m27"

  Scenario: An empty queue is idle, not a failure
    Given the incident queue is empty and no claimed issue lacks a heartbeat
    When the scheduled tick runs
    Then it prints "idle" and exits 0
    And no claim is opened

  Scenario: One task per tick, from the head of the queue
    Given the head incident of estate_health is "memory-use"
    When the scheduled tick runs
    Then exactly one claim is opened for that task
    And the executor receives the task through the environment, never interpolated into a script

  Scenario: The executor never raises a pull request or pushes main
    When the executor finishes a task
    Then it pushes only "lane/agent-pi-<run>" as the estate App
    And no pull request is opened by the executor

  Scenario: A staged branch is promoted only against a claim
    Given a branch "staged/x" whose commits carry "Claim:" and "Agent:" trailers
    And its changed paths fit an open claim
    When the promotion step runs
    Then "lane/x" is pushed from the same head
    But a branch without a matching claim is left in place with its reason recorded on the claim issue

  Scenario: A founder-surface lane waits for the founder door
    Given a lane touches a path in the forced-review inventory
    When the Greenlane proves it green
    Then it does not land until the founder answers
    And on timeout it does not land

  Scenario: Any other green lane lands without a person
    Given a lane touches no founder surface and is green on top of main
    Then the Greenlane lands it

  Scenario: A task larger than the model window is refused, not truncated
    Given a task packet over 204800 tokens
    When the scheduled tick runs
    Then the tick records "task too large" on the claim and takes no action

  Scenario: Always on is measured by the goal, not by the process
    Given the chief-executor critical function
    Then it is green only when the newest scheduled run is under 30 minutes old
    And the last 12 ticks each produced "idle" or a lane
    And a run that exited green with neither is BLIND, not a pass
