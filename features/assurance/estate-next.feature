Feature: What is planned, what is blocking, when (crew#403 CP6)
  Founder, 2026-08-27, the third time that day: "what major capabilities and showcase do you have
  planned and what is outstanding or blocking ... and when to expect". The page answers it,
  generated from the open checkpoint rows, the newest feed handoff per lane and the Expect line.

  Scenario: An open checkpoint with no Expect line is a red row
    Given an issue with an open checkpoint row and no Expect line
    When estate-next renders the page
    Then the row carries NO DATE

  Scenario: An open checkpoint named on a lane's red line is BLOCKING and dated
    Given an issue with an open checkpoint row, an Expect line, and a lane whose red line names it
    When estate-next renders the page
    Then the row is BLOCKING with its date

  Scenario: A handoff older than the lane window does not make a checkpoint ACTIVE
    Given an issue named only by a handoff from yesterday
    When estate-next renders the page
    Then the row is PLANNED
