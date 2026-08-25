@cp18 @phase1-gate
Feature: Budget wall — the phase-1 exit test
  Review, 2026-08-25: "cp1–7 without a budget enforcer is a prettier while True."
  No session runs without a pre-allocated token budget. At zero it hard-halts
  with a signed receipt. cp8 onward do not start until this is green.

  Scenario: An agent burns its budget and is halted
    When I run "bin/sb start --runner burn --task 'burn 100 tokens per step' --budget 100 --json"
    And I run "bin/sb show <session_id> --json" within 10 seconds
    Then the output "status" is "halted"
    And the output "reason" is "budget"
    And the output "budget_remaining" is 0
    And the last receipt has kind "halt", the session's state hash, and a valid signature

  Scenario: No session starts without a budget
    When I run "bin/sb start --runner echo --task 'x' --json" with SB_DEFAULT_BUDGET unset
    Then the command is refused with "budget required"

  Scenario: A signed refill resumes from the same step
    Given a session halted for budget at step 3
    When I run "bin/sb refill <session_id> --tokens 1000 --by founder --signed"
    Then the session resumes at step 3
