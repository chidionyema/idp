Feature: CP2 the board
  The founder sees every session on the portal, live, without a reload.

  Scenario: a running session is on the board
    Given I am signed in to the portal
    And a sovereign session is running
    When I open the fleet page
    Then the page answers within 2 seconds
    And the running session is listed with its runtime, task and state

  Scenario: the board updates itself
    Given the fleet page is open
    When a session finishes
    Then its state on the page changes within 3 seconds without a reload
