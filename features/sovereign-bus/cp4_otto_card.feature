@cp4
Feature: Otto's card — the chat is a status line, edited in place, never appended
  Founder: "too noisy", "9 pinned messages", "the chat is pure chaos".
  Otto owns exactly one pinned card and one message per live session. State
  changes edit those messages. Nothing else is ever sent to the chat by the
  session engine.

  Scenario: One pinned card, edited not re-sent
    Given the Otto card writer is configured with the estate bot and chat
    When I run "bin/sb card --json"
    Then the output has "card_message_id"
    When a session is started with "--runner echo --task 'hello'"
    And I run "bin/sb card --json"
    Then "card_message_id" is unchanged
    And "edits" increased by at least 1
    And "sends" is unchanged

  Scenario: One message per live session, collapsed when it ends
    Given a running session started with "--runner sleep --task 'sleep 20'"
    Then the session has exactly one "line_message_id" in the chat
    When the session ends
    Then the same "line_message_id" now reads as a one-line "done" entry
    And no new message was sent for that session

  Scenario: The card never carries alerts
    Given an estate alert is raised through estate_alert.py
    Then the alert is appended to the inbox file
    And the telegram ledger records "inboxed", not "sent"
    And the chat message count from the session engine is unchanged
