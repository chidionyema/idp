@cp11 @v2
Feature: Predictive pre-authorization — approve futures, not events
  Master Spec v1.0 §2.4, §3.4. Before each step the engine estimates the next
  three steps' spend. A predicted boundary surfaces one card. Silence halts at
  the boundary. Destructive ops are never auto-authorized.

  Scenario: A predicted budget boundary asks once, ahead of time
    Given a session with budget 10k tokens and 3 predicted steps costing 12k
    Then the session status is "waiting" before the boundary is reached
    And the ask names the refill amount and the steps it covers
    When I run "bin/sb approve <session_id> --by founder"
    Then all three steps run without another ask

  Scenario: Shadow-founder auto-approves only inside policy and above confidence
    Given the receipts hold at least 20 founder approvals of "budget_refill" with no denials
    When the same boundary is predicted
    Then the kernel writes a receipt kind "shadow_auth" with a confidence ≥ 0.95
    And the founder is not asked

  Scenario: Destructive ops are never auto-authorized
    Given the receipts hold 100 founder approvals of "git push --force"
    When a step asks for "git push --force"
    Then the session status is "waiting"
    And no "shadow_auth" receipt is written
