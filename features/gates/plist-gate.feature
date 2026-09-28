# Bound by sovereign/tests/bdd/test_gate_plist_gate.py. Incident 2026-08-25: ai.estate.scheduler
# ran 28 ticks and dagster-daemon never outlived scheduler-up.
Feature: A launchd job that backgrounds children declares AbandonProcessGroup
  Scenario: A launchd job that backgrounds children declares AbandonProcessGroup
    Given a launchd template whose program starts a child with nohup, setsid or disown and then exits
    When bin/plist-gate grades it
    Then it fails unless the job declares AbandonProcessGroup or KeepAlive
    And the same template with AbandonProcessGroup true passes
    And ai.estate.scheduler carries AbandonProcessGroup, so dagster-daemon outlives scheduler-up
