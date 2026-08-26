@cp3
Feature: Pre-flight dedup — hermes-v2 checks the board before drafting
  Founder's simple solve depends on hermes-v2 not creating duplicates: before
  it drafts anything it reads idp/board, active branches, worktrees and open
  PRs, read-only.

  Scenario: A matching card already exists
    Given idp/board has an open card whose title matches the phone idea's subject
    When he sends that idea to hermes-v2
    Then hermes-v2's reply names the matching card by ID
    And it asks whether to update that card or leave it
    And it drafts no new card before he answers

  Scenario: No match exists
    Given idp/board has no card matching the phone idea's subject
    And no active branch or open PR matches it either
    When he sends that idea to hermes-v2
    Then hermes-v2 proceeds to mode detection without asking about a duplicate
