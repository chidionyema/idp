@cp12 @phase2
Feature: AI sandbox and zero-cost forks — agents query a copy-on-write fork, production untouched
  Founder: "sb fork staging creates a full copy of production state in under a
  second ... Zero database copies." Binary blobs are zero-cost via CAS; DB state
  forks are in-memory, capped by config key fork.max_parallel (default 3), spilling
  to disk beyond that.

  Scenario: Fork under a second
    When I run "bin/sb fork staging --json"
    Then the output "elapsed_ms" is under config key fork.max_ms
    And .estate/heads/staging equals the current root
    And no file under the legacy DB changed

  Scenario: Agent writes land on the fork only
    Given a session started with "--branch staging"
    When it writes ten rows
    Then production's root is unchanged
    And staging's root advanced ten times
    And the fork's receipts are chained separately from main

  Scenario: Switch and drop
    When I run "bin/sb switch staging" then "bin/sb drop staging"
    Then the working pointer moved and then the branch is gone from heads/
    And its DAG nodes remain (archived, never deleted)

  Scenario: The cap is a key
    Given fork.max_parallel is 3 and three forks exist
    When I run "bin/sb fork fourth --json"
    Then the output "storage" is "disk"
