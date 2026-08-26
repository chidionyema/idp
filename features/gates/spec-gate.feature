Feature: The spec gate grades executed specs, not touched files
  Founder ruling R29 (2026-08-25): a PR that changes code changes the executable spec, or CI blocks it.

  # crew#297: 63 of 79 feature files were named by no test and the gate passed PRs that only touched them.
  Scenario: The spec gate counts a feature file only when a test names it
    Given a PR that changes code and a *.feature file no tracked test names
    When bin/spec-gate runs
    Then the feature does not count as executable spec and the gate prints FAIL
    And a new *.feature file no test names is refused with the pytest-bdd binding shown
    And every run prints "residual spec-gate N feature file(s) named by no test"
