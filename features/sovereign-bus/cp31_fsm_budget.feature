@cp16
Feature: Finite state machine and budget enforcer
  Master Spec v1.0 §4.3, §5. init → planning → tool_use → synthesis → terminal.
  Every transition spends from a pre-allocated budget with optimistic locking.
  Zero means halt. Five planning cycles means pause. Blind means halt.

  Scenario: Budget exhaustion halts, state is kept, refill resumes
    Given a session with budget 2k tokens
    When the budget reaches zero
    Then the session status is "halted" with reason "budget"
    And its state hash is in the receipt
    When a signed refill of 10k arrives
    Then the session resumes from the same step

  Scenario: Cycle detection
    When a session repeats planning→tool_use→synthesis five times
    Then it pauses before the sixth with reason "cycle"

  Scenario: Blind execution is refused
    Given Langfuse is unreachable for more than 5 minutes
    Then every non-critical session is halted with reason "blind"

  Scenario: Concurrent spend cannot overdraw
    Given two activities spend from one budget at the same time
    Then the final balance equals start minus both spends, never negative
