# Prose until a drill runs them: crew#639 messaging day 0. A file moves under features/ the day a test names it (bin/spec-gate).

@cp5
Feature: a consumer has exactly-once effect

  Scenario: a consumer killed between commit and ack does not repeat its effect (§11 test 4)
    Given the consumer library inserts into processed_messages inside the handler transaction
    And AckSync is called only after commit
    When the Go test kills the consumer after commit and before ack
    Then the redelivered message hits the ON CONFLICT branch and is acked
    And the effect count is unchanged


  Scenario: long work heartbeats and permanent failure terminates
    Given a handler that runs longer than ack_wait of 30 seconds
    Then the library calls InProgress on a heartbeat well inside ack_wait
    When a handler returns a permanent error
    Then the library calls Term with the reason instead of waiting for max_deliver


  Scenario: the library defaults are the spec's
    When a durable pull consumer is created through the library
    Then ack_policy is explicit, ack_wait 30s, max_deliver 5, max_ack_pending 1000
    And its name is {service}-{purpose}
