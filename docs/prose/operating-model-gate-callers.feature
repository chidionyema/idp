# Prose until a drill reads hermes-v2 and crew: needs the other repositories checked out (crew#286, crew#297).
Feature: Every active estate repo runs the one operating-model gate
  Scenario: Every active estate repo runs the one gate, with the policy in one place
    Given hermes-v2 and crew each have .github/workflows/operating-model-gate.yml
    And each file's only job is `uses: chidionyema/idp/.github/workflows/operating-model-gate.yml@main`
    When a pull request opens on any of them
    Then the reusable workflow checks the caller repo out to . and chidionyema/idp to ./.idp
    And it runs .idp/bin/pr-report with IDP_ROOT=./.idp, so the rego and the budget have one copy
    And idp's own ci.yml calls the same file, so idp is not a special case of the gate

  # Incident 2026-08-26: idp#191 added the chaos-pod-kill row and was refused for naming it,
  # because pr-report read the catalogue from main only (tests/test_incident_gate_read_catalogue_from_main.py).