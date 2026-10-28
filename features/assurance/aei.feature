# AEI — the estate's execution evidence contract.
#
# Bound by packages/aei/tests/test_aei_bdd.py. Every scenario here runs against the real
# library in packages/aei/src/aei -- a scenario nobody runs is prose (bin/spec-gate).
#
# The rule the whole feature turns on: a measurement that was not taken is UNKNOWN, never
# zero, and never a fabricated span.
Feature: AEI — observed execution evidence
  As the estate
  I need observed, correlated and immutable execution evidence
  So that agent performance and optimisation claims can be verified

  Scenario: Every execution carries the canonical identifiers
    Given a valid task event
    Then the event carries run, task, agent, harness, trace and revision identifiers

  Scenario: Telemetry cannot silently accept unclassified data
    Given an event with an unclassified attribute
    When the event is validated
    Then the event is refused

  Scenario: Retries are idempotent but immutable
    Given a stored event
    When the same event is appended again
    Then the store records only one event
    And a conflicting event with the same id is rejected

  Scenario: A failed collector cannot stop an agent
    Given an unreachable collector
    When an agent emits an event
    Then the emit returns without waiting for the collector

  Scenario: Missing metrics remain unknown
    Given a trace without cost observations
    When the trace is analysed
    Then cost is unknown rather than zero

  Scenario: The observability contract is required
    Given a component manifest without a visualisation
    When the manifest is validated
    Then the manifest is refused

  Scenario: Run comparison requires verified outcomes
    Given two runs of the same task without verification
    When their performance is compared
    Then the comparison is not declared verified

  Scenario: Trace evidence survives restart
    Given a stored run
    When the store is reopened
    Then its events remain readable in append order

  Scenario: A router call is observed, never summarised
    Given a router that answers with a usage payload
    When the estate adapter calls the router
    Then the ledger records the observed model, tokens and latency
    And the prompt and the answer are absent from the ledger

  Scenario: The estate adapter never blocks the work it observes
    Given a collector that cannot be reached
    When the estate adapter emits through it
    Then the adapter returns without raising
