Feature: CP1 the session contract
  Every runtime becomes one session record, validated against one schema.

  Scenario: the backend lists sessions from the sovereign engine
    Given the portal backend is running with the fleetview plugin
    When I GET /api/fleetview/sessions
    Then the response is a JSON array
    And every element validates against schema/session.json
    And at least one element has runtime "sovereign"

  Scenario: the stream sends a change
    Given a sovereign session is running
    When its state changes
    Then /api/fleetview/stream delivers an event naming that session within 3 seconds
