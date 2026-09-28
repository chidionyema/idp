# Prose until a drill runs them: crew#639 messaging day 0. A file moves under features/ the day a test names it (bin/spec-gate).

@cp10
Feature: the founder used it

  Scenario: one button on the portal runs the demo
    Given a portal action named Messaging demo
    When the founder presses it
    Then the demo runs and its receipt appears on the page
    And his confirmation is a comment on crew#639
