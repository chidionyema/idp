# Bound by sovereign/tests/bdd/test_gate_trace_matrix.py. crew#495 CP1, founder 2026-08-27:
# "we need this definitely: a trace matrix". Generated from git and the tests, never typed.
Feature: Every scenario traces to the test that runs it
  Scenario: A feature nothing runs is listed first and counted as a finding
    Given a repository with one feature a test loads and one feature nothing loads
    When bin/trace-matrix renders it
    Then the page lists the unbound feature before the bound one
    And --check exits 1 naming one unbound feature

  Scenario: A repository where every feature is bound passes the check
    Given a repository with one feature a test loads and one feature nothing loads
    When the second feature gains a test that loads it
    Then --check exits 0 and the page has no UNBOUND row

  Scenario: A feature under docs/prose is counted as PROSE, never as a finding
    Given a repository with one feature a test loads and one feature nothing loads
    When the unbound feature moves under docs/prose
    Then --check exits 0 and the page counts one PROSE row and no UNBOUND row
