# Prose until a drill runs them: crew#639 messaging day 0. A file moves under features/ the day a test names it (bin/spec-gate).

@cp4
Feature: the relay is the only writer and it never duplicates

  Scenario: the outbox row and the state change are one transaction (§11 test 1)
    Given a demo service inserts into outbox in the same transaction as its state write
    When the Go test kills the service between the two writes a hundred times under load
    Then a reconciliation query finds zero events without state and zero state without events


  Scenario: a relay crash mid-batch leaves no duplicates and no gaps (§11 test 2)
    Given the relay selects unpublished rows FOR UPDATE SKIP LOCKED in batches of 100
    And each publish carries Nats-Msg-Id outbox:{id} and the CloudEvents headers of §5.1
    When the Go test kills the relay with SIGKILL mid-batch a hundred times and restarts it
    Then a scan of Nats-Msg-Id over the stream shows each outbox id exactly once
    And every outbox id below the stream's last id is present


  Scenario: the relay is measurable
    When the relay serves /metrics
    Then it exposes outbox_unpublished_total, outbox_oldest_unpublished_seconds, relay_publish_errors_total and relay_duplicate_acks_total
    And a NOTIFY outbox_wake wakes the loop before the 200 ms poll
