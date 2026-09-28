# Prose until a drill runs them: crew#639 messaging day 0. A file moves under features/ the day a test names it (bin/spec-gate).

@cp3
Feature: the contracts are gated, not reviewed

  Scenario: a subject that breaks the grammar cannot be published
    Given bin/messaging-subject-gate reads {domain}.{kind}.{aggregate}.{action}.{version}
    When it grades the good fixture orders.event.order.placed.v1
    Then it exits 0
    When it grades the bad fixtures prod.orders.event.order.placed.v1, orders.event.order.place.v1 and orders.event.Order.placed.v1
    Then it exits non-zero for each and names the rule broken


  Scenario: a breaking schema change fails CI (§11 test 7)
    Given platform/messaging/schemas/orders/order_placed/v1.proto is tagged on main
    When a pull request renumbers a field or changes its type
    Then buf breaking fails the build against the previous tag
    And an additive optional field passes


  Scenario: the first stream exists with the locked values
    When nats stream info ORDERS_EVENTS runs
    Then subjects are orders.event.>, storage file, retention limits, max_age 30 days, duplicate_window 15 minutes
    And deny_delete and deny_purge are true
    And SUBJECTS.md lists orders.event.order.placed.v1 with its schema path
