# Prose until a drill runs them: crew#639 messaging day 0. A file moves under features/ the day a test names it (bin/spec-gate).

@cp8
Feature: the bus is observed in the estate collector, never by scanning files

  Scenario: every messaging workload is seen by the backend (LAW 50)
    When bin/idp-telemetry-coverage runs
    Then it lists the nats, relay, dlq-processor and exporter pods as seen by SigNoz


  Scenario: one trace spans request, commit, publish and consumer
    Given the relay copies traceparent from the outbox row to the message header
    And the consumer library starts a child span from it
    When bin/idp-messaging-demo prints its trace id
    Then a SigNoz query by that id returns spans from the demo service, the relay and the consumer


  Scenario: the seven alerts route to alertmanager
    Given PrometheusRule rows for node down, store above 70 percent, pending growing 15 minutes, redelivery above 1 percent, relay backlog above 30 seconds, DLQ arrival, and certificate under 21 days
    Then each fires in a unit test with synthetic series
    And none routes to the founder's chat
