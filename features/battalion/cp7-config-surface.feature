# docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md, section 5c (CFG-01, CFG-02),
# tracked by idp#3525 CP7. Scenarios are the spec's own ACCEPT lines, not new criteria.

@cp7
Feature: One hot-reloadable config document is the single point of control for every axis

  Scenario: CFG-01 — a config diff toggling any axis takes effect on the next request, no restart
    Given the single Battalion config document
    When a config diff toggles selection method from gate to weighted-vote, or filter_depth from off to on
    Then the change takes effect on the next request with zero process restart
    And the change is visible as a version bump in the OBS-01 catalog entity

  Scenario: CFG-02 — the config schema is generated from the spec's own REQ list, and a mismatch fails CI
    Given the spec's REQ list with each config-relevant REQ tagged
    When the schema-generation check runs
    Then schema fields equal the tagged REQs
    Given a new REQ is added without a matching schema field
    When CI runs
    Then it fails
