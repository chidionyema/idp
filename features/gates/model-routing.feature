Feature: Model routing is an estate service, not a laptop process
  crew#284 CP2, crew#313. The router (LiteLLM) is the platform's model-routing row and runs
  on the cluster as the Flux Kustomization `llm`. The founder's Mac being off, asleep or
  swapped does not change whether a model call is routed.

  Scenario: The cluster router carries every hosted model the laptop router carries
    Given llm/config.yaml lists the hosted models and the local ollama lane
    When platform/llm/config.yaml is compared entry for entry
    Then every hosted entry is identical
    And no entry points at host.docker.internal
    And every fallback names a model the cluster serves

  Scenario: The router is reachable at llm.<zone> through the one edge
    Given the prospector edge has a listener https-llm for llm.${ESTATE_ZONE}
    When the HTTPRoute in namespace llm attaches to it
    Then external-dns publishes the hostname
    And callers authenticate with the master key from the estate vault

  Scenario: Upstream keys reach the pod only from the estate vault
    Given the vault holds one JSON secret litellm-upstream
    When the ExternalSecret materialises it in namespace llm
    Then every os.environ reference in the router config resolves from that Secret
    And no key is written in the repository

  Scenario: The founder picks and adds models in the Admin UI, never by pull request
    Given the router runs the -database image with litellm-db in namespace llm
    And general_settings.store_model_in_db is true so a model added in the UI outlives a restart
    When the founder opens https://llm.<zone>/ui and signs in
    Then the login is UI_USERNAME and UI_PASSWORD from the vault entry litellm-ui, mounted like the upstream keys
    And no username or password is written in the repository
    And every provider key the UI can bind to is an os.environ name the pod already exports
