@cp19 @phase1-gate
Feature: Receipts are a signed hash chain, not a JSON file
  Review, 2026-08-25: "a .json file in $HOME is editable by any process running as you."
  Every receipt carries prev_hash, its own hash, a monotonic counter and a
  signature from the estate key (macOS Keychain / Windows Credential Manager
  now; Secure Enclave / TPM in cp14). Any edit breaks the chain.

  Scenario: The chain verifies
    Given at least 10 receipts exist
    When I run "bin/sb verify-receipts --json"
    Then the output "ok" is true
    And the output "count" equals the line count

  Scenario: A tampered line is detected
    Given one receipt line's text is changed on disk
    When I run "bin/sb verify-receipts --json"
    Then the output "ok" is false
    And the output names the counter of the first broken line

  Scenario: A deleted halt is detected
    Given a receipt of kind "halt" is removed from the file
    When I run "bin/sb verify-receipts --json"
    Then the output "ok" is false

  Scenario: The signing key never leaves the keystore
    When I run "grep -rn 'PRIVATE KEY' sovereign ~/.estate/sovereign"
    Then the output is empty
