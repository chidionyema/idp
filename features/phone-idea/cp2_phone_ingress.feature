@cp2
Feature: Phone ingress — hermes-v2 never touches the active laptop session
  The founder talks to hermes-v2 on Telegram from anywhere. Handling that
  message must never reach into whatever session is already running on the
  laptop.

  Scenario: hermes-v2 and the active session are separate processes
    Given a Claude Code session is running on the laptop
    And hermes-v2's gateway is running
    When a Telegram message arrives at hermes-v2
    Then hermes-v2's process handling it has a different PID from the session
    And no session file is shared between the two
