# Prose until a drill runs them: crew#639 messaging day 0. A file moves under features/ the day a test names it (bin/spec-gate).

@cp7
Feature: dead letters are captured, alerted and replayed by hand

  Scenario: a poison message lands in DLQ with its headers (§11 test 5)
    Given a handler that always fails
    When the message reaches max_deliver 5
    Then the MAX_DELIVERIES advisory is captured in stream DLQ_ADVISORIES
    And the DLQ processor republishes it to dlq.orders.event.order.placed.v1 with its original headers and Nats-Msg-Id dlq:{stream}:{seq}
    And the DLQ arrival alert fires


  Scenario: replay is a manual audited action
    Given the handler is fixed
    When ops replay is run with the DLQ sequence
    Then the message is redelivered and processed once
    And the replay is recorded with who, when and which sequence
    And nothing replays without that command
