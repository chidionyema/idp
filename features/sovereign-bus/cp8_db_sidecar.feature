@cp8 @phase2
Feature: DB sidecar — every legacy write is diffed, hashed, and passed through untouched
  Founder, 2026-08-25: "If legacy DB consistency is hard, build the sidecar." The
  sidecar sits on the legacy DB's write path (config key sidecar.target: the
  named DB and its API), computes the diff of each write, appends a Merkle node
  and a signed receipt, then forwards the write. DB logic is never changed.

  Scenario: The legacy DB is named before anything is built
    When I run "bin/sb config --json"
    Then "sidecar.target" names a real database and write path on this estate

  Scenario: A write is mirrored, not altered
    Given the sidecar is attached to the target
    When one row is written through the legacy API
    Then the legacy DB holds exactly that row
    And .estate/dag/ gained one node whose diff reproduces the row
    And the audit chain gained one receipt with the node hash

  Scenario: Sidecar failure never blocks the legacy write
    Given the DAG directory is read-only
    When a write goes through
    Then the legacy DB still holds the row
    And a receipt of kind "sidecar_degraded" is written when the DAG is writable again
