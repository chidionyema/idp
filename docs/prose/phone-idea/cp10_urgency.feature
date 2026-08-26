@cp10
Feature: Urgency — open decision, default is never interrupt
  Not yet answered by the founder: whether a "drop everything" phone message
  may interrupt an active laptop session. Until he rules otherwise, the
  default is no interruption, ever, without his explicit confirmation.

  Scenario: An urgent phone message during an active session changes nothing about it
    Given a Claude Code session is running on the laptop
    When an urgent phone message arrives at hermes-v2 during that session
    Then the session's process is unaffected
    And the session's transcript is unchanged
    And the session's branch has no new commit from the phone flow

  Scenario: An urgent card is flagged, once confirmed
    Given an urgent phone message has been confirmed to a board column
    Then the resulting card is flagged urgent
    And its priority ordering on the board reflects that flag
