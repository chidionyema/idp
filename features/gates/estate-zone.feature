# Founder, 2026-08-25 (crew#269): "how do i know what the backstage url is ... what if we migrate
# in the future"; 2026-08-26: "as always configurable". Gate: bin/estate-zone-gate, proved both
# ways in bin/idp-ci.
Feature: The estate zone is one configurable value
  Every hostname the platform publishes is <service>.<zone>. The zone is written once, in
  clusters/<cluster>/estate-config.yaml, and substituted by Flux; a migration changes one value.

  Scenario: A platform manifest names the zone as a literal
    Given clusters/x/estate-config.yaml declares ESTATE_ZONE
    And platform/edge/route.yaml lists the hostname catalogue.<zone> spelled out
    When bin/estate-zone-gate runs
    Then it exits 1 and prints that file and line

  Scenario: A platform manifest refers to the zone by substitution
    Given the same config
    And platform/edge/route.yaml lists the hostname catalogue.${ESTATE_ZONE}
    When bin/estate-zone-gate runs
    Then it exits 0

  Scenario: No cluster declares a zone
    Given no clusters/*/estate-config.yaml
    When bin/estate-zone-gate runs
    Then it exits 2 and prints BLIND, not a verdict
