Feature: CP5 the offering
  Tenant scope, history, alerts, and the pages a product ships with.

  Scenario: a tenant sees only its own fleet
    Given two tenants each have a running session
    When tenant B opens the fleet page
    Then only tenant B's session is listed

  Scenario: history replays
    Given a session finished yesterday
    When I open its drawer and press Replay
    Then its state changes are shown in order with timestamps

  Scenario: the product has its pages
    Then docs/marketing/index.md lists FleetView
    And bin/law32-gate passes for the fleetview plugins
