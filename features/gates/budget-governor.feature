# Founder essay, 2026-09-14, "PhD cold military surgeon": "Test-Time Compute Budgeting...
# Per-query budget... Expected Information Gain threshold... Budget exhaustion -> forced
# termination -- the agent stops thinking and executes the best-so-far plan when the budget
# runs out."
#
# Ticket: docs/tickets/2026-09-14-reasoning-gateway.md, deliverable D2. Gate: bin/idp-budget,
# which reuses bin/idp-trajectory's own budget_per_goal/authorize() for the branch ceiling and
# bin/idp-epistemic's target-normalisation for the information-gain ceiling (R43); the cost
# ceiling sums only a step's own declared cost_usd, never a fabricated number.
Feature: A reasoning run is halted the instant a ceiling trips, and the best-so-far plan survives

  Scenario: A run repeats tool calls past the per-goal branch budget
    Given a session that declares a plan and runs six distinct real tool calls
    When bin/idp-budget runs it with the default budget
    Then it exits 1 and names the branch budget as the cause

  Scenario: A run finishes its declared plan inside its budget
    Given a session that declares a plan, does three distinct tool calls, then completes the goal
    When bin/idp-budget runs it with the default budget
    Then it exits 0, because the plan completed before either ceiling was reached

  Scenario: The transcript cannot be read
    Given a transcript file that does not exist
    When bin/idp-budget runs it with the default budget
    Then it exits 2, because an unreadable transcript is never a clean bill
