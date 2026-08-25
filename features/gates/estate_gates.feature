Feature: Every active estate repository runs the same merge-blocking gates
  Founder, 2026-08-25: the security scan and the executable-spec rule (R29)
  apply estate-wide, to every repository pushed in the last 30 days, not to
  idp alone. One composite action per gate lives in idp; each repository
  calls it from a job whose name is the required status check.

  Scenario: A leaked secret cannot reach main in any active repository
    Given a repository pushed in the last 30 days
    When a pull request adds a committed credential
    Then the security-scan job ends with "SECURITY-SCAN FAIL"
    And the ruleset estate-security-scan refuses the merge

  Scenario: Code without an executable spec cannot reach main
    Given a pull request that changes a .py, .ts or bin/ file
    And it changes no *.feature, test or bin/estate-diagram file
    Then the spec-gate job fails naming the code files
    And the ruleset estate-security-scan refuses the merge

  Scenario: The gate permits code that arrives with its spec
    Given a pull request that changes a .py file and a *.feature file
    Then the spec-gate job passes

  Scenario: The rollout is one command, run once
    When bin/estate-security-rollout --apply runs
    Then every active repository without the caller workflow gets one pull request
    And bin/repo-rulesets --apply then requires both checks on each of them

  Scenario: A required check that cannot report never blocks a repository
    Given an active repository whose default branch has no .github/workflows/security-scan.yml
    When bin/repo-rulesets runs
    Then that repository is printed as WAITING and the estate-security-scan ruleset is not applied to it
    And a repository with the workflow on its default branch gets the ruleset

  Scenario: The architecture diagram is drawn from the catalogue, never by hand
    Given catalog/catalog-info.yaml written by bin/catalog-gen from the inventory
    When bin/estate-diagram runs
    Then docs/architecture/live.md names every repository, listening port and scheduled job in the catalogue
    And the counts on each repository node equal the dependsOn edges pointing at it
    And rendering the same catalogue twice gives the same bytes
    And bin/estate-diagram --check exits 1 while the page on disk differs from the catalogue and 0 after a render

  Scenario: The live architecture page reaches main on a schedule, through a pull request
    Given scheduler/schedule.yml holds com.estate.catalog-render with after: com.estate.inventory
    When the inventory job finishes
    Then bin/catalog-render renders the catalogue and the page in a detached worktree at origin/main
    And a changed page is pushed to branch state/live-diagram and its pull request is set to auto-merge
    And an unchanged page commits nothing
    And a missing inventory exits 3 BLIND instead of rendering an empty page

  Scenario: A launchd job that backgrounds children declares AbandonProcessGroup
    Given a launchd template whose program starts a child with nohup, setsid or disown and then exits
    When bin/plist-gate grades it
    Then it fails unless the job declares AbandonProcessGroup or KeepAlive
    And the same template with AbandonProcessGroup true passes
    And ai.estate.scheduler carries AbandonProcessGroup, so dagster-daemon outlives scheduler-up
