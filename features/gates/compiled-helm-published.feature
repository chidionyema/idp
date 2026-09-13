Feature: the compiled estate is published and read on the portal
  bin/idp-compile-helm renders every HelmRelease from git. That is only worth having if a person
  can see the answer: on 2026-09-12 a five-day-old right-sizing was invisible because the fact
  lived in a CI job's output and nothing rendered it.
  # Bound by sovereign/tests/bdd/test_compiled_helm_published.py. The page logic is graded by
  # backstage/packages/app/src/modules/home/compiled.test.ts.

  Scenario: CI compiles the estate on every pull request
    Given the estate's CI workflow
    When a pull request is opened
    Then the workflow runs bin/idp-compile-helm
    And a release that does not render fails the run

  Scenario: the compiled document reaches the portal
    Given the compiled document is written by CI
    And the compiled document is published
    When the render force-pushes the estate state
    Then the compiled document is carried with the other rendered state
    And the portal reads it through the proxy it already has

  Scenario: a disagreement between a claim and a rendered value is visible
    Given the compiled document is published
    And the compiled document names a workload and its rendered requests
    When the portal shows it
    Then a workload whose comment and value disagree appears with the rendered value
    And the number shown is the one the chart renders, never the one the file claims
