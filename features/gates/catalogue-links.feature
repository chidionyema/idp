# crew#269 row 3 (founder, 2026-08-25: "how do i know what the backstage url is"). Every URL
# lives in the catalogue, so a Component the founder cannot open from the catalogue is a
# regression. Gate: bin/catalog-links-check, run by bin/idp-ci on the fixture (both ways) and
# by bin/idp-verify on the live catalogue.
Feature: Every Component in the catalogue carries a URL a person can open
  Resources are files, sockets and jobs; Components are the services and websites a person
  opens. Each Component must carry at least one http(s) link with no unsubstituted variable.

  Scenario: The clean inventory yields a catalogue where every Component has a URL
    Given tests/fixtures/inventory.json, where every repo has a github remote
    When bin/catalog-gen writes the catalogue and bin/catalog-links-check reads it
    Then it prints "catalog: every entity carries a URL" and exits 0

  Scenario: A checkout with no remote is refused
    Given tests/fixtures/inventory.no-remote.json, one repo with remote "(none)"
    When bin/catalog-gen writes the catalogue and bin/catalog-links-check reads it
    Then it names the Component and its path and exits 1

  Scenario: No catalogue on this machine
    Given catalog/catalog-info.yaml does not exist
    When bin/catalog-links-check runs
    Then it prints BLIND and exits 2, never ok

  Scenario: A product's UIs enter the catalogue from the product's own repository
    Given prospector carries catalog-info.yaml with a Component per HTTPRoute hostname in deploy/k8s/base/edge.yaml
    And backstage/app-config.container.yaml lists that file as a url location
    When the cluster's Backstage reconciles its locations
    Then prospector-store-web and prospector-store-api appear with links to mumchimp.com and api.mumchimp.com
    And a hostname the edge serves that the file does not name fails prospector's unit suite
