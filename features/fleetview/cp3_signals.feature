Feature: CP3 the four signals
  Stop, approve, deny and steer act on a real session and leave an audit row.

  Scenario: stop ends a session
    Given a sovereign session is running
    When I press Stop on its row
    Then the session is stopped within 5 seconds
    And the newest fleetview_audit row names the session, the signal and me

  Scenario: a signal from an unauthenticated caller is refused
    When a request without a portal identity posts a signal
    Then the response is 401
    And no audit row is written
