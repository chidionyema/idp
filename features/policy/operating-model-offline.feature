# crew#286 / crew#297: the parts of the operating-model gate that run with no pull request.
# Bound by sovereign/tests/bdd/test_policy_operating_model.py; steps run bin/policy-test and
# bin/pr-report for real, conftest included.
Feature: The operating-model policy is proved both ways before it gates a pull request
  Scenario: Correct work passes and every refusal fixture is refused
    Given policy/fixtures/opmodel-ok.json
    When bin/policy-test runs
    Then the opmodel-ok row is 0 and every other opmodel-* row is 1
    And no row's exit code differs from the one it expects

  Scenario: The gate runs only where a pull request exists
    Given the reusable workflow .github/workflows/operating-model-gate.yml
    When the job is evaluated for a push event
    Then the job carries if: github.event_name == 'pull_request' so main stays green
    # Incident: run 32922679927 on 5dac18e failed with `bin/pr-report: line 13: 1: pr number`.

  Scenario: A missing policy checkout is BLIND, never a pass
    Given IDP_ROOT names a directory with no policy/ dir
    When bin/pr-report runs
    Then it exits 2 with a line starting BLIND
