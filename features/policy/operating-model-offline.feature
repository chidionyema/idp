# crew#286 / crew#297: the parts of the operating-model gate that run with no pull request.
# Bound by sovereign/tests/bdd/test_policy_operating_model.py; steps run bin/policy-test and
# bin/pr-report for real, conftest included.
Feature: The operating-model policy is proved both ways before it gates a pull request
  Scenario: Correct work passes and every refusal fixture is refused
    Given policy/fixtures/opmodel-ok.json
    When bin/policy-test runs
    Then every opmodel-* row that expects 0 gets 0 and at least five rows expect and get 1
    And no row's exit code differs from the one it expects

  Scenario: The gate runs only where a pull request exists
    Given the reusable workflow .github/workflows/operating-model-gate.yml
    When the job is evaluated for a push event
    Then the job admits only pull_request and merge_group events so main stays green
    # merge_group added with the merge queue: a queued run re-grades the same pull request
    # (its number is derived from the queue branch name); a push to main still never runs it.
    # Incident: run 32922679927 on 5dac18e failed with `bin/pr-report: line 13: 1: pr number`.

  Scenario: A missing policy checkout is BLIND, never a pass
    Given IDP_ROOT names a directory with no policy/ dir
    When bin/pr-report runs
    Then it exits 2 with a line starting BLIND
