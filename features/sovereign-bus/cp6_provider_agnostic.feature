@cp6
Feature: Provider agnostic — the runner and the model are configuration, never code
  LAW 34, LAW 46. The session engine does not know which agent CLI or model
  runs a step. A runner is a name in config; a model is a LiteLLM alias.

  Scenario: The engine runs with no vendor present
    When I run "bin/sb start --runner echo --task 'no vendor' --json"
    Then the session reaches "done"

  Scenario: No vendor import in the engine
    When I run "grep -rEl 'anthropic|openai|google\.generativeai|telegram' sovereign/engine"
    Then the output is empty

  Scenario: No hardcoded home, host or checkout
    When I run "grep -rn '/Users/\|127\.0\.0\.1:[0-9]\|localhost:[0-9]' sovereign bin/sb"
    Then the output is empty

  Scenario: A real agent runner is one config line away
    Given "claude" is on PATH
    When I run "bin/sb start --runner claude --repo <a scratch repo> --task 'say pong' --json"
    Then the session reaches "done"
    And the session's last step output contains "pong"
