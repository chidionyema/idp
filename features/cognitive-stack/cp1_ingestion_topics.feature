# idp#3448 CP1. Founder: "Ingestion: Redpanda or Kafka. Pipe GitHub webhooks, Slack exports,
# CI/CD telemetry, incident logs into topics."
@cp1
Feature: Ingestion — GitHub, Slack, CI/CD and incident feeds land in topics

  Scenario: Four topics receive real events
    Given the epistemic-fabric-ingest namespace with its default-deny NetworkPolicy, ResourceQuota and LimitRange
    When a GitHub webhook, a Slack export, a CI/CD telemetry event and an incident log are each sent once
    Then the github, slack, cicd and incidents topics each carry at least one message
    And no topic is created outside those four without a matching ingestion source

  Scenario: The row reconciles and its healthcheck names a real object
    Given the Flux row epistemic-fabric in clusters/oke/platform.yaml
    Then it reconciles Ready=True
    And its healthCheck names an object the row itself creates, per bin/idp-healthcheck-exists

  Scenario: The door shows a live topic list
    Given Backstage Catalog component epistemic-fabric-ingest
    When the founder opens its "Open topic list" link
    Then the Redpanda Console shows all four topics with non-zero message counts
