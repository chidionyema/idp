# Prose until a drill runs them: crew#639 messaging day 0. A file moves under features/ the day a test names it (bin/spec-gate).

@cp6
Feature: permissions make the outbox the only path

  Scenario: an app credential cannot publish a business event (§11 test 6)
    Given accounts SYS, PLATFORM and APP-ORDERS exist from committed JWTs with seeds in OCI Vault
    And user orders-app has publish deny on *.event.> and *.cmd.>
    When orders-app publishes to orders.event.order.placed.v1
    Then the client receives a permissions violation
    And the violation is visible in the SYS account log on the cluster


  Scenario: the relay credential is narrow
    Given user orders-relay has publish allow only on orders.event.> and orders.cmd.> fully-qualified subjects
    When orders-relay publishes to billing.event.invoice.issued.v1
    Then it receives a permissions violation
    When orders-relay calls a $JS.API stream delete verb
    Then it receives a permissions violation
