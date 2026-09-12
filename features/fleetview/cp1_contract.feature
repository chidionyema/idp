Feature: CP1 the session contract
  Every runtime becomes one session record, validated against one schema.

  Scenario: the backend lists sessions from the sovereign engine
    Given the portal backend is running with the fleetview plugin
    And a sovereign session is running
    When I GET /api/fleetview/sessions
    Then the response is a JSON array
    And every element validates against schema/session.json
    And at least one element has runtime "sovereign"

  Scenario: the stream sends a change
    Given a sovereign session is running
    When its state changes
    Then /api/fleetview/stream delivers an event naming that session within 3 seconds

  Scenario: the route answers the spec's done-command
    Given the portal backend is running with the fleetview plugin
    And a sovereign session is running
    When I GET /api/fleetview/sessions over HTTP
    Then the status is 200
    And the body has available true
    And the body's sessions is a JSON array
    And the body names no unreachable adapter

  Scenario: a catalogue that cannot be read is not an empty board
    Given the portal backend is running with the fleetview plugin
    And the catalogue is not readable
    When I GET /api/fleetview/sessions over HTTP
    Then the status is 503
    And the body has available false
    And the body names the error
