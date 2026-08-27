# crew#286, founder 2026-08-26: "The founder is the approving authority, never the implementing
# operator ... Every approval is a structured message. Nothing touches a GUI."
# Probe: bin/policy-test (six opmodel-* fixtures) and bin/pr-report <n> on a live PR.
Feature: The operating model is a gate on every pull request
  # Offline scenarios (policy fixtures, the pull_request guard, IDP_ROOT BLIND) are bound in
  # features/policy/operating-model-offline.feature. The scenarios here need a live pull request.
  # Bound by sovereign/tests/bdd/test_policy_operating_model_gate.py: each rule is judged by conftest over the
  # policy/fixtures/opmodel-*.json shape it names. The cross-repo caller scenario lives in
  # docs/prose/operating-model-gate-callers.feature until a drill reads the other repos.

  Scenario: An identity created without its scope in the same PR is refused
    Given a PR adds resource "oci_identity_domains_app" and no grant, policy or membership
    When bin/pr-report runs
    Then it exits 1 with a line starting rule=provisioning_complete and a fix:

  Scenario: An instruction that sends a person to a console is refused
    Given a PR body line "FOUNDER ACTION: sign in to the OCI console and add estate-tofu to Administrators"
    When bin/pr-report runs
    Then it exits 1 with rule=no_gui_actions

  # crew#473, founder 2026-08-27: "you need to approve all / no founder friction if can be avoided".
  # Nothing waits for APPROVE: any more; DENY: on the declared word is his veto and still refuses.
  Scenario: A founder-facing change with no approval word merges on green
    Given a PR touching backstage/ or platform/identity/ with no "Approval-word:" line
    When bin/pr-report runs
    Then the founder-facing change passes with no founder word

  Scenario: A DENY from the founder on the declared word refuses the PR
    Given a PR whose "Approval-word:" the founder answered with DENY: from his GitHub login
    When bin/pr-report runs
    Then it exits 1 with rule=founder_denied

  Scenario: Cost and canary are declared for every platform/oci change
    Given a PR touching platform/oci/ whose Cost-delta-usd-month beats estate-defaults.yaml infrastructure.monthly_cap_usd, or with no canary label
    When bin/pr-report runs
    Then it exits 1 with rule=cost_budget or rule=canary

  # crew#292 CP3: one gate, called by every active estate repo, not copied into each.
  Scenario: A drill added by the pull request satisfies drill_named
    Given a pull request that changes a platform layer and adds a row to drills/catalogue.yaml
    And its body says "Drill: <that row>"
    When bin/pr-report judges it
    Then the drill names come from the catalogue on main and the catalogue at the PR head
    And the gate passes

  # crew#254: the four Living Estate laws (crew/docs/ARCHITECTURE_LAWS.md) on every PR body.
  Scenario: Every pull request answers the four architecture laws
    Given a PR body with no "## Architecture laws" section, or one whose law line is a sentence
    When bin/pr-report runs
    Then it exits 1 with rule=architecture_laws
    And a body whose four law lines are commands, paths or n/a with a reason passes
