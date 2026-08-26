@cp1
Feature: Data — the catalog database is green before any governance layer is judged
  The founder: "The Data — fix the database today." A buyer's engineer runs
  bin/idp-verify before reading a single row of the fortress-stack spec.

  Scenario: idp-verify passes clean
    Given the catalog generator has written catalog/catalog-info.yaml
    When I run "bin/idp-verify"
    Then the last line of output is "PASS"
    And the fallback renderer serves the same entity count as the source YAML
