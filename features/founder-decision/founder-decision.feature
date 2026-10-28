Feature: The founder-decision door
  Any agent -- any harness, any model, laptop or cluster -- can put one structured decision
  in front of the founder on the estate's one Otto Telegram chat and read the answer back in
  the same shape it asked in.

  The founder answers with a comment, in his own words. The door matches deterministically,
  records the comment verbatim, and never invents an answer the founder did not give.

  Scenario: One decision is one message
    Given a decision asking about the AEI collector
    When the agent asks the founder
    Then the founder receives exactly one message
    And the message carries the decision id and the question

  Scenario: An option key is the answer
    Given a live decision with options ship and hold
    When the founder comments dec-1a2b3c4d ship
    Then the decision is answered
    And the reported option is ship
    And the founder's comment is stored verbatim

  Scenario: An unparsable comment is never coerced
    Given a live decision with options ship and hold
    When the founder comments dec-1a2b3c4d do it after the cluster comes back
    Then the decision is answered
    And the reported option is null
    And the answer is the founder's comment verbatim

  Scenario: Silence expires the decision
    Given a live decision whose deadline has passed
    When the agent reads the decision back
    Then the state is expired
    And no option is reported

  Scenario: Asking twice sends one message
    Given a decision that was already asked
    When the agent asks again with the same id
    Then no second message is sent
    And the decision is unchanged

  Scenario: The delivery path needs no model
    Given a decision asking which lane to take
    When the agent asks the founder
    Then the door makes exactly one transport call
    And the door names no model client

  Scenario: A chat message is not captured while two decisions are live
    Given two live decisions
    When the founder comments ship while two decisions are live
    Then neither decision is answered

  Scenario: An exact option key answers the only live decision
    Given one live decision with options ship and hold
    When the founder comments a bare option key
    Then the decision is answered
