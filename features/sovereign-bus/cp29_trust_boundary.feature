@cp14
Feature: Trust boundary — the founder is the root certificate
  Master Spec v1.0 §4.1. Overrides are signed on this Mac (Touch ID through
  LocalAuthentication, key held in the Secure Enclave). Receipts are an
  append-only transparency log with a monotonic counter. No signature, no act.

  Scenario: A destructive approval requires a hardware signature
    Given a session asks for "git push --force"
    When I run "bin/sb approve <session_id> --by founder" without a signature
    Then the command is refused with "signature required"
    When the approval is signed with Touch ID
    Then the session continues
    And the intervention log gains one entry with counter n+1 and a valid signature

  Scenario: Replay is rejected
    Given a captured signed approval
    When it is submitted a second time
    Then it is refused with "counter already used"

  Scenario: Degraded mode is logged, not silent
    Given the Secure Enclave is unavailable
    Then approvals fall back to the configured multi-signature set
    And the receipt records "attestation:fallback"
