# Prose until a drill runs them: crew#639 messaging day 0. A file moves under features/ the day a test names it (bin/spec-gate).

@cp1
Feature: the messaging day-0 design is accepted before any code

  Scenario: the specification is the founder's document, saved to the estate standard
    Given crew/docs/specs/issue-639.md carries the founder's specification v0.1 verbatim under the principal review
    And idp/docs/decisions/0012-messaging-day-0.md records decisions D1 to D8 and the R1 day-0 ruling
    And crew/docs/STANDARDS.md has an "Event bus" row naming NATS JetStream and a "Platform daemons" row naming Go
    When crew/scripts/pr-evidence.py check runs on the pull request
    Then it passes
    And every checkpoint CP1 to CP10 on crew#639 has a feature file under docs/prose tagged with its number


  Scenario: MiniMax builds only against a scenario, never against prose
    Given every checkpoint from CP2 on names the scenario that grades it
    When a worker session asks pi_execute to build a checkpoint
    Then the task text is the feature file and the accept-when line, nothing else
    And pi_gate refuses the result until the scenario's commands print the expected output
