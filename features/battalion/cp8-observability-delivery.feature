# docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md, section 6
# (OBS-01, OBS-02, GOV-01, GOV-02), tracked by idp#3525 CP8.
# Scenarios are the spec's own ACCEPT lines, not new criteria.

@cp8
Feature: Observability and delivery — generated catalog entities, the estate's own board, no laptop dependency, destructive-class spend

  Scenario: OBS-01 — the hosting matrix and the CFG-01 surface are generated catalog entities
    Given bin/catalog-gen
    When it runs
    Then catalog entities exist for the hosting matrix and the CFG-01 config surface
    And each renders tier, cost, receipt-grade and current toggle state
    And no bespoke dashboard is built

  Scenario: OBS-02 — founder-facing deliverables render on the estate's own board
    Given a founder-facing deliverable from the Battalion
    When it is published
    Then it renders on the local board at 127.0.0.1:8787 /look, or a permanent collector page, or is pushed as a file
    And no external publish appears in the trace unless tagged # vendor-surface-intended with a reason

  Scenario: GOV-01 — zero laptop dependency in the production routing path
    Given a dependency scan of the routing path
    When it runs
    Then it shows zero laptop-resolved targets
    And dev-local convenience files outside the routing path are exempt by classification record

  Scenario: GOV-02 — autonomous money-spending actions inherit the destructive capability class
    Given the capability classifier
    When a tier-activation action is classified
    Then it maps to the destructive capability class
    And it requires quorum and a hardware signature, no separately invented authority
