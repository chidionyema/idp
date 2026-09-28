@cp35 @phase2 @superpower
Feature: Recover the last estate checkpoint — crash equals rebuild, never data loss
  Delivered by cp9 + cp13 + cp14.

  Scenario: Recover after a crash
    Given the worker, views and services are killed mid-write
    When I run "bin/sb recover --json"
    Then heads/main is the last fully committed root
    And projection views are rebuilt and match it
    And every service is running again
    And a receipt "[✓] RECOVER | root:<hash>" is written
