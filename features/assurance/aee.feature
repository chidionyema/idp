# The AEE — the work graph and the execution contracts.
#
# Bound by packages/aee/tests/test_aee_bdd.py. Every scenario here runs against the real
# library in packages/aee/src/aee -- a scenario nobody runs is prose (bin/spec-gate).
#
# The rule the whole feature turns on: work is not done because it was attempted. It is
# accepted when the evidence its contract demands is present, and it is never lost quietly.
Feature: The AEE — a work graph that cannot lose work quietly
  As the estate
  I need a work graph whose invariants are enforced rather than documented
  So that no node is accepted without evidence, and no work disappears silently

  Background:
    Given an objective with one acceptance criterion
    And a graph owned by agent-a

  Scenario: A node is not accepted without a passing verification
    Given a graph with one node and no evidence
    When the node is completed
    Then the completion is refused for want of verification

  Scenario: A failed verification does not accept a node
    Given a graph with one node and a failed verification
    When the node is completed
    Then the completion is refused for want of verification

  Scenario: Evidence for another node does not accept this one
    Given a graph with two nodes and evidence for the second
    When the first node is completed
    Then the completion is refused for want of verification

  Scenario: A node is not completed while its parent is unaccepted
    Given a graph with a parent and a child
    And the child has a passing verification
    When the child is completed
    Then the completion is refused for want of acceptance

  Scenario: A node with passing evidence and accepted parents is accepted
    Given a graph with a parent and a child
    And both nodes have a passing verification
    When the parent and then the child are completed
    Then both nodes are accepted

  Scenario: A dependency loop is refused
    Given a graph with two dependent nodes
    When the plan is changed to close a loop
    Then the replan is refused for a cycle

  Scenario: A path outside the objective's scope is refused
    Given a graph with an authorised scope
    When a node outside that scope is added
    Then the node is refused for want of scope

  Scenario: A second agent may not mutate a graph it does not own
    Given a graph with one node
    When another agent adds a node
    Then the mutation is refused for want of ownership

  Scenario: Cancelling a node releases its reservation and blocks its dependents
    Given a graph with a reserved node and a dependent
    When the reserved node is cancelled
    Then the reservation is released
    And the dependent is blocked

  Scenario: A retry keeps the earlier attempt on the record
    Given a graph with a failed node
    When the node is retried
    Then the earlier attempt is still on the record

  Scenario: The same graph state has the same address
    Given two graphs with the same node
    Then they have the same digest
    And a third node changes the address

  Scenario: A receipt with a known cost names the ledger row it derives from
    Given an economic receipt with a known cost and no ledger hash
    Then the receipt is refused
