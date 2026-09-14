# idp#3448 CP1. Founder, 2026-09-14: "dont use kakfa we have etsrean" -- ingestion runs on the
# estate's existing NATS JetStream event-bus (platform/event-bus), not a new Kafka/Redpanda
# broker (already rejected for this estate in platform/event-bus/nats.yaml's own header: a
# JVM-class broker for a 4-6 OCPU cluster, LAW 43/THE HEADLINE/LAW 23). Publishers use the
# existing platform/messaging/cloudevent envelope, the same pattern order_paid already uses.
@cp1
Feature: Ingestion — GitHub, Slack, CI/CD and incident feeds land in event-bus streams

  Scenario: Four JetStream streams receive real events
    Given the epistemic-fabric namespace with its default-deny NetworkPolicy, ResourceQuota and LimitRange
    When a GitHub webhook, a Slack export, a CI/CD telemetry event and an incident log are each sent once
    Then the epistemic.github, epistemic.slack, epistemic.cicd and epistemic.incidents streams each carry at least one message
    And no stream is created outside those four without a matching ingestion source
    And no new broker (Kafka, Redpanda or otherwise) is deployed -- the existing event-bus namespace is the only bus

  Scenario: The row reconciles and its healthcheck names a real object
    Given the Flux row epistemic-fabric in clusters/oke/platform.yaml
    Then it reconciles Ready=True
    And its healthCheck names an object the row itself creates, per bin/idp-healthcheck-exists

  Scenario: The door shows live stream stats
    Given Backstage Catalog component epistemic-fabric-ingest
    When the founder opens its "Open stream stats" link
    Then `nats stream ls` over the existing event-bus port-forward shows all four streams with non-zero message counts
