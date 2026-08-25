@cp33 @phase2 @superpower
Feature: Atomic time-travel rollback — one command rewinds code, DB, policy and config to any hash
  Delivered by cp9 + cp13 + cp15.

  Scenario: Rewind to a previous root
    Given the estate has advanced 20 roots since hash H
    When I run "bin/sb rewind H --by founder --signed"
    Then services are stopped, heads/main is H, projection views are rebuilt from the DAG
    And code, DB and policy all equal their state at H
    And nothing after H is deleted from the DAG
    And a signed receipt "[✓] REWIND | to:H | from:<prev>" is written
