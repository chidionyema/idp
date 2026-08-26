@cp2
Feature: Model routing — LiteLLM is the universal API layer
  The founder: "LiteLLM as the universal API/abstraction layer with fallback
  chains and per-agent cost logging; every agent points its base URL at LiteLLM."

  Scenario: The proxy is up with a real fallback chain
    Given llm/litellm.yml and llm/config.yaml are the compose definition
    When I run "bin/litellm-status"
    Then the proxy row reads "up" with HTTP "200"
    And at least one fallback chain is configured in the router settings

  Scenario: Every non-CLI agent's base URL points at the proxy
    Given hermes-v2 and prospector's operator.py factory are the two agent configs
    When I search each for its LLM base URL
    Then each resolves to "http://127.0.0.1:4000/v1"
    And claude_cli and gemini_cli remain excluded, on purpose, as subscription clients
