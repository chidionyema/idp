# crew#286, founder 2026-08-26: "The founder is the approving authority, never the implementing
# operator ... Every approval is a structured message. Nothing touches a GUI."
# Probe: bin/policy-test (six opmodel-* fixtures) and bin/pr-report <n> on a live PR.
Feature: The operating model is a gate on every pull request
  Scenario: An identity created without its scope in the same PR is refused
    Given a PR adds resource "oci_identity_domains_app" and no grant, policy or membership
    When bin/pr-report runs
    Then it exits 1 with a line starting rule=provisioning_complete and a fix:

  Scenario: An instruction that sends a person to a console is refused
    Given a PR body line "FOUNDER ACTION: sign in to the OCI console and add estate-tofu to Administrators"
    When bin/pr-report runs
    Then it exits 1 with rule=no_gui_actions

  Scenario: A founder-facing change names the word he replies with
    Given a PR touching backstage/ or platform/identity/ with no "Approval-word:" line
    When bin/pr-report runs
    Then it exits 1 with rule=founder_approval_required

  Scenario: Cost and canary are declared for every platform/oci change
    Given a PR touching platform/oci/ whose Cost-delta-usd-month beats estate-defaults.yaml infrastructure.monthly_cap_usd, or with no canary label
    When bin/pr-report runs
    Then it exits 1 with rule=cost_budget or rule=canary

  Scenario: Correct work passes and the refusal is posted as a comment
    Given policy/fixtures/opmodel-ok.json
    When bin/policy-test runs
    Then the opmodel-ok row is 0 and the five opmodel-* refusals are 1
    And a refused PR in CI carries one comment listing each rule= line and its fix
