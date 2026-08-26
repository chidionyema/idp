@cp5
Feature: Confirmation gate — hermes-v2 never writes to the board unannounced
  The founder, verbatim: "I need it to confirm to me if I want it on the
  board. That's a simple solve." This is the one rule the whole flow answers
  to.

  Scenario: A draft is shown before any board write
    Given hermes-v2 has drafted a feature file from a phone idea
    When it presents the draft in Telegram
    Then it shows three inline buttons: To Do, Icebox, Drop
    And it has made zero calls to a board-write tool

  Scenario Outline: The board write matches the button tapped
    Given hermes-v2 has presented a draft with inline buttons
    When he taps "<button>"
    Then the board-write tool is called exactly once
    And the card lands in the "<column>" column

    Examples:
      | button | column |
      | To Do  | To Do  |
      | Icebox | Icebox |

  Scenario: Drop writes nothing
    Given hermes-v2 has presented a draft with inline buttons
    When he taps "Drop"
    Then no board-write tool is called
    And the draft is discarded
