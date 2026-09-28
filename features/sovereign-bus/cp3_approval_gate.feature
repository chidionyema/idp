@cp3
Feature: Approval gate — a session that needs the founder waits for him, durably
  A step that needs a hand (force push, spend over cap, delete) parks the
  session in "waiting" and asks once. Approve and it continues; deny and it
  ends cleanly with a receipt. It never proceeds on silence.

  Scenario: Deny ends the session with a receipt
    Given a running session started with "--runner ask --task 'needs: git push --force'"
    When I run "bin/sb show <session_id> --json" within 5 seconds
    Then the output "status" is "waiting"
    And the output "asking" is "git push --force"
    When I run "bin/sb deny <session_id> --by founder"
    And I run "bin/sb show <session_id> --json" within 5 seconds
    Then the output "status" is "denied"
    And the receipts file has a line with kind "deny" for <session_id>

  Scenario: Approve lets the session continue
    Given a running session started with "--runner ask --task 'needs: git push --force'"
    When I run "bin/sb approve <session_id> --by founder"
    And I run "bin/sb show <session_id> --json" within 10 seconds
    Then the output "status" is "done"

  Scenario: Silence is not consent
    Given a running session started with "--runner ask --task 'needs: rm -rf build'"
    When 15 seconds pass with no signal
    Then the output of "bin/sb show <session_id> --json" "status" is still "waiting"
