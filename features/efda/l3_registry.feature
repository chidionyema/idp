Feature: Component Registry
  As the estate operator
  I need every component enumerated, owned and covered
  So that "all components" is a fact and not a memory

  Background:
    Given the registry reconciler runs against a cluster with one annotated workload

  Scenario: An unregistered workload is registered and covered
    When the reconciler runs
    Then a ComponentRegistration exists for the observed workload
    And its status.coverageState is "BASELINE"
    And its status.packRef is not empty
    And a SkillPack exists for its component class

  Scenario: The coverage report is published
    When the reconciler runs
    Then a CoverageReport exists
    And it counts the observed components
    And it lists the components that are not compliant

  Scenario: The registry snapshot is published for the gate
    When the reconciler runs
    Then the registry snapshot names every registered component class

  Scenario: A component that left the cluster is an orphan
    Given a ComponentRegistration for a workload that no longer exists
    When the reconciler runs
    Then that registration's status.coverageState is "ORPHAN"
    And it is listed as not compliant
