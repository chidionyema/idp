Feature: bin/litellm-up brings the proxy up on the config that is on disk
  A bind-mounted config the running process never re-reads is the class
  (2026-08-26): `docker compose up -d` leaves an unchanged container alone,
  so a merged llm/config.yaml served nothing until someone restarted the proxy
  by hand. The up script owns that restart.

  Scenario: The proxy is restarted when config.yaml changed after it started
    Given litellm-proxy started before the last change to llm/config.yaml
    When bin/litellm-up runs
    Then it logs "config.yaml is newer than the running proxy; restarting it"
    And bin/litellm-status lists every model_name in llm/config.yaml

  Scenario: The proxy is left alone when it already runs the config on disk
    Given litellm-proxy started after the last change to llm/config.yaml
    When bin/litellm-up runs
    Then it logs "proxy started after the last config.yaml change; no restart"
    And the container's StartedAt is unchanged
