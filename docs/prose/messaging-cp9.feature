# Prose until a drill runs them: crew#639 messaging day 0. A file moves under features/ the day a test names it (bin/spec-gate).

@cp9
Feature: the platform is accepted, backed up and demoed

  Scenario: the eight acceptance tests are green on the throwaway cluster
    Given the portability drill's k3s job runs the messaging suite
    When the run finishes
    Then scenarios for §11 tests 1 to 8 are green and the run id is on crew#639


  Scenario: node loss is survived and two-node loss halts cleanly (§11 test 3)
    Given a sustained publish on a three-node k3s cluster with R3
    When one node stops
    Then publishes succeed after reconnect jitter with zero failures
    When a second node stops
    Then publishes halt and resume on restart with no loss


  Scenario: a stream backup restores and replays with correct dedupe (§11 test 8)
    Given a nightly nats stream backup shipped off-cluster
    When it is restored into a scratch cluster and a test consumer replays 1000 messages
    Then the effect count is 1000 and a second replay changes nothing


  Scenario: the demo and the onboarding exist
    When bin/idp-messaging-demo runs on main
    Then it inserts one orders.event.order.placed.v1 through the demo outbox, watches the relay publish, the consumer process once, and prints ok demo with the trace id
    And docs/how-to/onboard-a-service-to-messaging.md walks a new service through outbox table, credentials and first consumer
    And the bus, relay and DLQ processor are catalogue entities with a weekly drill row
