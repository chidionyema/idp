@fixture-pending-unclaimed
Feature: A pending feature nobody has claimed
  The must-fail half of the branch-policy guard (R39/R41). Under
  SB_BDD_STRICT=1 this scenario must fail; without it, it must skip.

  Scenario: Steps that were never written
    Given a step nobody has bound
