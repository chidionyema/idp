Feature: CP8 — the steering wheel

  Scenario: Steer a sovereign session
    Given a sovereign session "s-abc" is running
    When POST /nudge with session_id "s-abc", runtime "sovereign", by "founder"
    Then the Temporal signal is sent to workflow "s-abc"
    And a fleetview_signals row records ok=true

  Scenario: Steer a claude-code session writes the directives mailbox
    Given a claude-code session "idp:s-xyz" exists
    When POST /nudge with session_id "idp:s-xyz", runtime "claude-code", by "founder", text "check the signals"
    Then a file is written at ~/.claude/state/directives/s-xyz.json
    And the file contains text "check the signals"
    And a fleetview_signals row records ok=true

  Scenario: Steer an otto session publishes NATS steer event
    Given NATS_URL is configured
    And an otto session "otto:t-789" exists
    When POST /nudge with session_id "otto:t-789", runtime "otto", by "founder", text "pause and report"
    Then a NATS message is published on "estate.agent.otto.otto:t-789.steer"
    And a fleetview_signals row records the attempt

  Scenario: Unsupported runtime returns 422
    Given a session with runtime "dagster"
    When POST /nudge with runtime "dagster"
    Then the response is 422
    And no signal row is recorded

  Scenario: Steer with missing "by" field returns 400
    When POST /nudge with empty by field
    Then the response is 400
    And no signal row is recorded
