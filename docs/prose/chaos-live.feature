# Prose until a drill runs it: needs the live cluster and a one-off Workflow (crew#292 CP4, crew#297).
Feature: A chaos experiment injects for real on the cluster
  Scenario: The first run is a receipt, not a promise
    Given the label has been applied by Flux
    When a one-off Workflow with the Schedule's templates is created in namespace backstage
    Then its Accomplished condition is True within 90s
    And backstage answered /healthcheck 200 throughout (StatusCheck did not abort)
