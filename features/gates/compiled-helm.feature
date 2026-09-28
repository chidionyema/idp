Feature: the estate is compiled from git before its numbers are believed
  A Helm chart decides a workload's real resources at render time. Editing the value in a values
  file, or writing a postRenderer patch against a Deployment the chart owns, does not change what
  the cluster runs unless the chart renders it that way.
  # Bound by sovereign/tests/bdd/test_compiled_helm.py. The compiler is bin/idp-compile-helm.

  Scenario: a rendered workload declares the resources the estate intends
    Given the estate is compiled from git
    When I read the rendered langfuse-web in observability
    Then its rendered cpu request is 500m
    And the rendered request equals the rendered limit

  Scenario: every release renders, so no chart is a blind spot
    Given the estate is compiled from git
    When I compile every release
    Then every release renders, 25 of them
