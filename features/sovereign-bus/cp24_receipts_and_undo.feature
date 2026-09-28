@cp9
Feature: Zero-noise receipts — one line, a hash, a budget delta, and undo
  Master Spec v1.0 §2.2. Receipt: "[✓] KIND | file:… | hash:<git sha> | budget:-1.2k | state:<session>".
  The hash is the git commit the step produced; undo reverts to that commit's parent.

  Scenario: Every step that writes emits one receipt line
    Given a session with runner "claude" and a scratch repo
    When a step commits a file
    Then the session line is exactly one receipt line
    And the receipt contains a git commit hash that exists in the repo
    And the receipt contains a token budget delta

  Scenario: Undo reverts to the receipt's hash
    When I run "bin/sb undo <session_id> --by founder"
    Then the repo HEAD is the parent of the receipt's hash
    And a receipt of kind "undo" is written
