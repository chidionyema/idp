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
