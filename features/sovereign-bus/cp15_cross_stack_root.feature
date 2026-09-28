@cp15 @phase2
Feature: Cross-stack root — one Merkle root over code, DB, policy and AI policy
  Scenario: One root, four children
    When I run "bin/sb root --json"
    Then the root node points to "code_root", "db_root", "policy_root", "ai_policy_root"
    And changing any child changes the root
