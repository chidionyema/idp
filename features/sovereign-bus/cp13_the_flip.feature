@cp13 @phase2
Feature: The flip — the DAG becomes primary; the legacy DB becomes a read-only archive with a rollback path
  Scenario: Zero-downtime cutover
    When I run "bin/sb flip --by founder --signed"
    Then reads are served from projection views within config key flip.max_downtime_ms of downtime
    And the legacy DB is set read-only
    And a receipt "[✓] FLIP | root:<hash> | legacy:readonly" is signed

  Scenario: Rollback path
    When I run "bin/sb flip --rollback --by founder --signed"
    Then the legacy DB is writable again and consistent with the root at flip time
