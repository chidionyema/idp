# crew#286, founder 2026-08-26: "The founder is the approving authority, never the implementing
# operator ... Every approval is a structured message. Nothing touches a GUI."
# Probe: bin/policy-test (six opmodel-* fixtures) and bin/pr-report <n> on a live PR.
Feature: The operating model is a gate on every pull request
  # Offline scenarios (policy fixtures, the pull_request guard, IDP_ROOT BLIND) are bound in
  # features/policy/operating-model-offline.feature. The scenarios here need a live pull request.

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

  # crew#292 CP3: one gate, called by every active estate repo, not copied into each.
  Scenario: Every active estate repo runs the one gate, with the policy in one place
    Given hermes-v2 and crew each have .github/workflows/operating-model-gate.yml
    And each file's only job is `uses: chidionyema/idp/.github/workflows/operating-model-gate.yml@main`
    When a pull request opens on any of them
    Then the reusable workflow checks the caller repo out to . and chidionyema/idp to ./.idp
    And it runs .idp/bin/pr-report with IDP_ROOT=./.idp, so the rego and the budget have one copy
    And idp's own ci.yml calls the same file, so idp is not a special case of the gate

  # Incident 2026-08-26: idp#191 added the chaos-pod-kill row and was refused for naming it,
  # because pr-report read the catalogue from main only (tests/test_incident_gate_read_catalogue_from_main.py).
  Scenario: A drill added by the pull request satisfies drill_named
    Given a pull request that changes a platform layer and adds a row to drills/catalogue.yaml
    And its body says "Drill: <that row>"
    When bin/pr-report judges it
    Then the drill names come from the catalogue on main and the catalogue at the PR head
    And the gate passes
