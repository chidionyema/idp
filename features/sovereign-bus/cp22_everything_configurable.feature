@cp22 @phase1-gate
Feature: Everything is configurable — one config, defaults in one place, no literal in code
  Founder, 2026-08-25: "everything needs to be configurable." Every number,
  path, model alias, timeout, threshold, surface and policy is a named key
  in sovereign/config.py with a default, overridable by $ESTATE_HOME/estate.toml,
  then by environment, then by --flag. A literal elsewhere is a defect.

  Scenario: The whole config is listable, with its source
    When I run "bin/sb config --json"
    Then every key has "value", "default", "source" in {default, file, env, flag}
    And no secret value is printed; keys ending in TOKEN, KEY, SECRET show "set"/"unset"

  Scenario: File overrides default, env overrides file, flag overrides env
    Given estate.toml sets budget.default = 500
    And env SB_DEFAULT_BUDGET = 700
    When I run "bin/sb config --json"
    Then budget.default is 700 with source "env"
    When I run "bin/sb start --budget 900 --runner echo --task x --json"
    Then the session's budget is 900

  Scenario: No magic numbers outside config.py
    When I run "bin/sb config --lint"
    Then it reports 0 numeric or path literals in sovereign/ outside config.py, tests, and index.html

  Scenario: Every spec threshold is a key
    Then these keys exist with the spec's default: consensus.timeout_s=30, consensus.quorum="2/3",
      fsm.max_cycles=5, shadow.min_confidence=0.95, digest.max_lines=6, digest.time="09:00",
      branch.count=3, branch.budget_pct=10, blind.halt_after_min=5, alerts.digest_over_per_hour=50,
      step.start_to_close_min=30, card.poll_s=3, runner.default="echo", model.default, model.vision,
      model.consensus=[3 aliases], trust.backend="auto", presence.default="ghost"

  Scenario: Setting a key is a command, and a receipt
    When I run "bin/sb config set digest.max_lines 8 --by founder"
    Then estate.toml holds digest.max_lines = 8
    And a receipt of kind "config" is written
