@cp2
Feature: LiteLLM is real
  crew#284 CP2, Master Spec v1.0 §3.3 and §4.2. The model router is an estate
  service, not a stand-in: the kernel finds it through the estate secret store,
  the running router serves every voter named in model.consensus, and a
  destructive op reaches quorum through that live router with two different
  models agreeing. These scenarios call the real proxy; where this host has no
  vault or no router they skip by name, never pass by mock.

  Scenario: The kernel finds the router in the estate secret store
    Given this host has the estate secret store
    When the kernel resolves its configuration with no estate.env at all
    Then litellm.base_url and litellm.api_key come from the store
    And the api key is not the proxy master key

  Scenario: The live router serves every consensus voter
    Given the live router answers
    Then the consensus list names three different aliases
    And GET /models on the live router lists every one of them

  Scenario: A destructive op reaches quorum through the live router
    Given the live router answers
    When the kernel decides a destructive op through the live router
    Then two different models agree before the deadline
    And the model_consensus receipt names each voter and its elapsed time
