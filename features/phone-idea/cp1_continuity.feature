@cp1
Feature: Continuity — an active laptop session is never touched by the phone flow
  The founder: "what if I'm already deep in a session on the laptop and I
  quickly need to rush out and take my phone; there is a currently active
  session, then I think of an idea and I talk to my Hermes agent — what
  happens?" The active session must keep running.

  Scenario: An active session finishes on its own after he leaves
    Given a Claude Code session is running on a branch before he leaves
    When the session completes its work
    Then it commits on its own branch
    And it opens a pull request
    And it stops without waiting for further input

  Scenario: A phone message during the session injects nothing into it
    Given a Claude Code session is running on a branch
    When a Telegram message is sent to hermes-v2 during that session
    Then the session's transcript contains no line from that message
    And the session's working tree has no file the phone flow drafted
