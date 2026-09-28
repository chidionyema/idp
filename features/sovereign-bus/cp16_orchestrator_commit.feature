@cp16 @phase2
Feature: Orchestrator agent — one atomic commit across UI, API, schema and policy
  Scenario: A cross-stack change is one commit
    Given a session changes a UI file, an API file, a schema and a policy line
    Then exactly one root commit is produced
    And a failure in any part leaves the root unchanged
