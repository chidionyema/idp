@cp34 @phase1 @superpower
Feature: Cryptographic auditing — SOC2 by default; the first feature delivered
  Delivered by cp19 + cp20. The audit log is .estate/audit.chain (the signed receipt chain).

  Scenario: An auditor verifies from a hash
    When I run "bin/sb audit --verify --json"
    Then the output "ok" is true and "entries" equals the chain length
    When I run "bin/sb audit --at <hash> --json"
    Then the output names who did what, when, under which policy, and which trust backend signed it
