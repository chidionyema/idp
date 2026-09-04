# crew#396 step 1: "close the laptop" fails at the first hop while the workflow engine is a
# launchd job on the Mac. The engine is the official Temporal chart on the estate's cluster.
Feature: The workflow engine runs in the cluster, not on the Mac
  # Bound by sovereign/tests/bdd/test_cp0_temporal_in_cluster.py

  Scenario: The Temporal row renders and is pinned to the official chart
    Given the Flux row temporal in clusters/oke/platform.yaml
    When platform/temporal is built with kustomize
    Then the HelmRelease uses chart temporal from https://go.temporal.io/helm-charts at a pinned version
    And Helm hooks are off so Flux owns the schema and namespace jobs
    And both persistence stores point at the estate database with a password from the vault Secret
    And every bundled store and metrics stack is disabled

  Scenario: The Mac no longer owns the engine
    Given the launchd template for the Temporal server
    Then it is gone and bin/idp-install-launchd says why

  Scenario: Every object the chart renders passes the pinned policy set
    Given the chart rendered with the HelmRelease values
    When Kyverno judges every rendered object with the two scoped exceptions
    Then nothing fails
