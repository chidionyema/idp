@cp6 @kini @self-termination
Feature: Auto-termination acts, it does not only report
  KINI master spec (crew#284) CP6, spec section 5. engine/termination.py
  evaluates four rules; `sb self-check --enforce` acts on the verdict and a
  five-minute row on the estate scheduler runs it. Every session is treated
  as non-critical until a critical marker exists (residual on the ticket).

  Scenario: Langfuse unreachable for more than blind.halt_after_min minutes halts
    Given langfuse_blind_s one second over blind.halt_after_min
    Then the action is halt, and at the threshold it is continue

  Scenario: Confidence below terminate.min_confidence for low_confidence_steps steps soft-halts
    Given a low-confidence streak of terminate.low_confidence_steps
    Then the action is soft_halt, and one step fewer is continue

  Scenario: More than alerts.digest_over_per_hour alerts in an hour compresses to a signed digest
    Given alerts_last_hour one over alerts.digest_over_per_hour
    Then the action is digest, and at the cap it is continue

  Scenario: Enforcement stops running sessions on halt and nothing on continue
    Given sessions running, asking and done
    When sb self-check --enforce sees a halt verdict
    Then the running and asking sessions receive a stop signal naming self-termination and the reason
    And a continue verdict signals nothing

  Scenario: The check is a row on the estate scheduler
    Given scheduler/schedule.yml
    Then ai.estate.sovereign-self-check runs `sovereign.cli self-check --enforce --json` every five minutes

  Scenario: A critical session survives self-termination
    Given a running session started with --critical
    And a running session started without it
    When the verdict is halt or soft_halt
    Then only the session without the marker receives stop
    And the receipt lists the critical session under kept
