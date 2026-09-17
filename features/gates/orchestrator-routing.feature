Feature: Orchestrator proxy routing — all LLM calls route through the estate proxy
  As the estate routing invariant
  Every LLM call from the orchestrator must go through the configured proxy base URL
  So that the efficiency gateway, budget ceiling, and spend tracking apply to all agent sessions

  Background:
    Given the orchestrator source exists at platform/orchestrator.py
    And no direct vendor API keys are embedded in the orchestrator source

  Scenario: Orchestrator uses a configurable base URL, not a hardcoded vendor URL
    When the orchestrator module is loaded
    Then the LLM client is initialised with a base_url parameter
    And the base_url is read from an environment variable
    And the base_url does not contain a vendor API host literal

  Scenario: Orchestrator does not import any vendor SDK directly
    When the orchestrator source is scanned for vendor-specific imports
    Then there is no direct import of "openai" as a top-level SDK
    And there is no import of "anthropic" as a top-level SDK
    And the LangChain OpenAI adapter is used (routing-agnostic shim)

  Scenario: Teleological filter prunes 3 or more consecutive tool errors
    Given an agent state with 3 consecutive ToolMessage errors
    When the teleological filter runs
    Then the 3 error messages are removed from state
    And a goal reminder SystemMessage is injected

  Scenario: Teleological filter leaves fewer than 3 consecutive errors untouched
    Given an agent state with 2 consecutive ToolMessage errors
    When the teleological filter runs
    Then the 2 error messages remain in state

  Scenario: Pre-LLM gate halts the agent when any hook signals halt
    Given a hook orchestrator that signals halt with reason "budget exceeded"
    When the pre-LLM gate runs
    Then the state halt_reason is "budget exceeded"
    And the graph routes to verdict_complete rather than calling the LLM

  Scenario: Pre-LLM gate passes through cleanly when no hook halts
    Given a hook orchestrator that signals no halt
    When the pre-LLM gate runs
    Then the halt_reason remains empty
    And the graph routes to the LLM node

  Scenario: Circuit breaker trips at the configured turn threshold
    Given an AgentCircuitBreaker configured with a turn threshold
    When the turn count reaches the threshold
    Then the circuit breaker signals halt
    And the halt reason names the turn count

  Scenario: Orchestrator respects the proxy base URL from environment
    Given the environment variable for the proxy base URL is set to "http://llm-proxy:4000"
    When the orchestrator initialises its LLM client
    Then the client base_url is "http://llm-proxy:4000"
