@cp6
Feature: Provider agnostic — the runner and the model are configuration, never code
  LAW 34, LAW 46. The session engine does not know which agent CLI or model
  runs a step. A runner is a name in config; a model is a LiteLLM alias.

  Scenario: The engine runs a step with no vendor present
    When the "echo" runner runs the task "no vendor"
    Then the step reports done
    And the step's output is "no vendor"

  Scenario: No vendor import in the engine
    When I run "grep -rEl 'anthropic|openai|google\.generativeai|telegram' sovereign/engine --include=*.py --exclude-dir=__pycache__"
    Then the output is empty

  Scenario: No hardcoded home, host or checkout
    When I run "grep -rn '/Users/\|127\.0\.0\.1:[0-9]\|localhost:[0-9]' sovereign bin/sb --include=*.py --exclude-dir=__pycache__ --exclude-dir=tests --exclude-dir=.venv"
    Then the output is empty

  Scenario: A new provider is one registry entry, not a code change
    Given a new runner "acme" is registered, the only change being that one dict entry
    When the "acme" runner runs the task "say pong"
    Then the step reports done
    And the step's output is "pong from acme"
