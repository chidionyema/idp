@cp12 @v2 @branch-budget-10pct
Feature: Temporal branching — fork silently, merge the winner, keep the losers
  Master Spec v1.0 §3.2. Branches are Temporal child workflows on git branches.
  Losing branches are archived, never deleted.

  Scenario: A decision point forks three silent branches
    When I run "bin/sb start --runner claude --repo <repo> --task 'refactor X' --branches 3 --json"
    Then three child sessions run in Ghost mode
    And zero messages are sent during their run
    And when all finish, exactly one receipt "[✓] BRANCH_MERGE | main←<winner> | hash:<sha>" is emitted
    And the two losing git branches still exist

  Scenario: Stop during branches freezes all of them
    Given three branches are running
    When I run "bin/sb stop <parent_id> --by founder"
    Then all three child sessions are "stopped" within 10 seconds
    And the receipt records the parent hash

  Scenario: A branch is capped at 10 percent of the parent budget and halts with a receipt
    Given a parent session with budget 10000 tokens and branches costing 2000 tokens per step
    When the three branches run
    Then each child budget is 10 percent of the parent budget
    And each child halts with a receipt reason "branch_budget_cap"
