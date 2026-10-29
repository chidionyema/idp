Feature: The estate's concurrency envelope
  What runs at the same time, on what capacity, at what cost. Independent work
  runs together up to the cap, dependent work waits, code that overlaps is
  never written by two workers at once, a cancellation gives the hold back, a
  restart resumes the same work under the same key, and the budget ceiling
  stops the work with the reason written down.

  Scenario: Independent work runs together and dependent work waits
    Given a graph of two independent nodes and one dependent node
    And a concurrency envelope that holds two at a time
    When the envelope admits the ready work
    Then two nodes are admitted together
    And the dependent node is not admitted

  Scenario: Code that overlaps is refused the same slot
    Given a graph of two nodes whose scopes overlap
    When the envelope admits the ready work
    Then one node is admitted
    And the refusal names the conflicting node and the path

  Scenario: Cancellation gives the hold back and stops the spend
    Given an admitted node holding a reservation
    When the node is cancelled
    Then the reservation is released
    And no money is committed

  Scenario: The budget ceiling stops the work and says why
    Given a concurrency envelope with a budget ceiling
    And a node whose reservation would cross the ceiling
    When the envelope admits the ready work
    Then the node is refused
    And the cutoff reason names the ceiling

  Scenario: A restart resumes the same work under the same key
    Given a node whose work has already been committed
    When the scheduler restarts from its journal and admits the work again
    Then the node is not admitted again
    And the committed spend is unchanged
