@cp8
Feature: Presence — Ghost is the default; the chat is the fire alarm, not the control room
  Master Spec v1.0 §2. The system may never push a message that pulls the
  founder into conversation. The chat carries three things: what he starts,
  a catastrophe, one daily digest of at most six lines.

  Scenario: Routine execution sends nothing
    Given three sessions run to done within budget
    Then the Otto card was edited
    And zero new messages were sent to the chat
    And the inbox received every state change as a receipt

  Scenario: A catastrophe is exactly one message
    Given a session's receipt hash no longer matches the repo
    When integrity verification fails
    Then exactly one message is sent, containing the hash and the remediation command
    And the session is halted

  Scenario: The daily digest is six lines, signed
    When I run "bin/sb digest --json"
    Then the text has at most 6 lines
    And the text ends with the receipts-file hash it was built from
