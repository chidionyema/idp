Feature: The estate twin knows what the estate actually is
  The estate has three inventories and every one reports DECLARED state as if it were
  ACTUAL state. Measured 2026-09-12: 1,523 unmerged branches, 178 worktrees, 722 files on
  branches that exist on no commit of main, 11 deployments scaled to zero, and three agents
  deployed and dead (research 0/1, hindsight 0/1, otto-gateway 2/13). No inventory could
  name a single one of those.

  This is the acceptance surface for docs/tickets/2026-09-12-estate-twin.md. Every scenario
  is written so that the wrong implementation fails it, not so that the right one passes.

  Background:
    Given the estate twin has a stream of runtime and code events
    And its graph is the estate's own asset database, not a new one

  Scenario: A dead agent is visible without anybody running a command
    Given an agent is deployed and every one of its pods is not ready
    When the twin has read the runtime state
    Then the agent is listed as dead
    And the listing names the namespace, the workload and how long it has been that way

  Scenario: A deployment scaled to zero is dead, not absent
    Given a deployment exists in the cluster with zero replicas
    When the twin has read the runtime state
    Then the deployment is listed as dead
    And it is not reported as running

  Scenario: A capability stranded on a branch is visible
    Given a branch is unmerged and adds a file that exists on no commit of main
    When the twin has read the code state
    Then the branch is listed as stranded
    And the listing names how many files it adds that main does not have

  Scenario: A branch that only edits existing files is not stranded
    Given a branch is unmerged and adds no file that main does not have
    When the twin has read the code state
    Then the branch is not listed as stranded

  Scenario: The twin and the catalogue generator cannot disagree
    Given both the twin and bin/catalog-dark-matter have read the same git state
    When their counts of stranded branches are compared
    Then the two counts are equal

  Scenario: A stopped emitter is visible as stale, not as healthy
    Given no event has arrived for a domain within its freshness window
    When the twin answers a query about that domain
    Then the answer is UNKNOWN
    And it is not MEASURED_OK

  Scenario: Replaying the same events changes nothing
    Given the twin has read a set of events
    When the same events arrive again
    Then the graph holds the same rows as before

  Scenario: The twin adds no second store, bus or server
    Given the estate already runs one event bus, one asset database and one MCP server
    When the twin is inspected
    Then it defines no second NATS stream
    And it writes no second SQLite file
    And it registers no second MCP server
