@cp14 @phase2
Feature: Projection views — hot SQLite/Redis stores compiled from the immutable DAG
  Scenario: Views are rebuilt from the DAG after a crash
    Given the projection store is deleted
    When I run "bin/sb rebuild --json"
    Then the views match the root hash
    And every read answers as before

  Scenario: Boot check
    When the kernel boots and the view hash differs from heads/main
    Then it rebuilds automatically and writes a receipt "[✓] REBUILD | root:<hash>"
