# Founder essay, 2026-09-14, "PhD cold military surgeon": "Process Reward Models... evaluates
# the correctness of each step in a reasoning process, rather than just the final outcome... No
# 'Blind' Assumptions: If the agent says 'I assume the database is up,' the control plane blocks
# the reasoning step until the agent explicitly runs a check_db_connection tool."
#
# Ticket: docs/tickets/2026-09-14-reasoning-gateway.md, deliverable D1. Gate: bin/idp-prm, which
# imports bin/idp-epistemic's claim/evidence/witness logic and bin/idp-trajectory's plan-binding
# logic rather than re-implementing either (R43) and applies both PER STEP, so a hallucinated or
# off-goal step is named at the step, not only when the whole transcript is later graded.
Feature: A reasoning step is graded as it happens, not only at the end of the transcript

  Scenario: A step claims verified state with zero evidence gathered so far
    Given a session that declares a plan and then claims verified state with no tool call
    When bin/idp-prm grades the transcript
    Then it exits 1 and names the step, the factual vector, and the blind claim

  Scenario: A step's claim is backed by independent evidence gathered earlier in the same run
    Given a session that declares a plan, gathers three independent readings, then claims verified state
    When bin/idp-prm grades the transcript
    Then it exits 0, because every step scored at least 0.8 on all three vectors

  Scenario: The transcript cannot be read
    Given a transcript file that does not exist
    When bin/idp-prm grades it
    Then it exits 2, because an unreadable transcript is never a clean bill
