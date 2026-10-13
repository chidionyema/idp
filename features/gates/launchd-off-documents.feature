# Bound by sovereign/tests/bdd/test_gate_launchd_off_documents.py. Incident 2026-10-13: 15 jobs
# installed from ~/Documents/code/idp on 2026-09-20/21 had never run; launchd cannot read
# ~/Documents (macOS TCC) and every log held only "Operation not permitted".
Feature: launchd jobs run from the runtime tree, never from ~/Documents
  Scenario: The installer points jobs at ~/.estate/runtime/idp
    Given a home with a runtime tree at .estate/runtime/idp
    When bin/idp-install-launchd installs cockpit
    Then the rendered plist runs from the runtime tree, not the checkout
    And its log directory exists before launchd opens it

  Scenario: The installer refuses a tree launchd cannot read
    Given a home with no runtime tree and a checkout under Documents
    When bin/idp-install-launchd installs cockpit from that checkout
    Then it exits 2 and names macOS TCC
    And nothing is written to Library/LaunchAgents

  Scenario: Jobs the cluster owns are never loaded on the Mac
    Given a home with a runtime tree at .estate/runtime/idp
    When bin/idp-install-launchd installs idp, scheduler and sovereign-worker
    Then each is skipped because it runs on the cluster
    And nothing is written to Library/LaunchAgents
