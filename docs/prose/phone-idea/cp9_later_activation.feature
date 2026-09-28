@cp9
Feature: Later activation — an Icebox idea becomes work, still gated
  "Remember that idea, let's do it" must turn a kept RFC into a feature file
  and only move it to To Do after the same confirmation as a fresh idea.

  Scenario: Activating an Icebox card drafts a feature file
    Given an Icebox card holds a Markdown RFC
    When he tells hermes-v2 "remember that idea, let's do it" naming the card
    Then hermes-v2 drafts a feature file from that RFC's content
    And the card is not yet moved to To Do

  Scenario: The move still requires the confirmation gate
    Given hermes-v2 has drafted a feature file from an Icebox card
    When it presents the draft with inline buttons
    And he taps "To Do"
    Then the card moves from Icebox to To Do
    And it moves only after that tap
