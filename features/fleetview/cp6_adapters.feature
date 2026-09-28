Feature: CP6 — NATS adapters

  Scenario: Claude Code tool event reaches NATS
    Given the NATS event bus is reachable
    And a claude-code prompt-ledger file contains a new tool row
    When the claude_code_adapter runs one cycle
    Then a message is published on "estate.agent.claude-code.*.tool"
    And the message validates against the estate.agent.event schema

  Scenario: Stream endpoint relays NATS events as SSE frames
    Given NATS_URL is configured
    And a steer event arrives on "estate.agent.sovereign.s1.steer"
    When a client is connected to GET /stream
    Then the client receives a data frame containing session_id "s1"

  Scenario: Stream falls back to heartbeat when NATS is not configured
    Given NATS_URL is not set
    When a client connects to GET /stream
    Then the client receives heartbeat comments every 30 seconds
    And no NATS connection is attempted
