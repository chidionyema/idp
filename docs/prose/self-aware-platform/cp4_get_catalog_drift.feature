@cp4
Feature: get_catalog_drift — dark matter is visible, on the laptop substrate
  Founder's pasted design: "the server reads typed catalog-info.yaml
  annotations, never string-greps. Failure: dark matter, resources applied
  outside the catalog are invisible. Fix: get_catalog_drift() compares
  catalog vs live API and lists untracked resources." Substrate is the
  laptop until k8s (fly-destroyed, oke-not-live): live state here is launchd
  jobs, colima containers, and catalog/ports.yaml.

  Scenario: A launchd job with no catalog entity is reported as drift
    Given a launchd job "com.example.orphan" is loaded and running
    And no Backstage catalog entity references "com.example.orphan"
    When mcp__estate__get_catalog_drift() is called
    Then the response lists "com.example.orphan" under untracked launchd jobs

  Scenario: A colima container with no catalog entity is reported as drift
    Given a colima container is running with no matching catalog entity
    When get_catalog_drift() is called
    Then the response lists that container under untracked containers

  Scenario: A port bound outside catalog/ports.yaml is reported as drift
    Given a process is listening on a port absent from catalog/ports.yaml
    When get_catalog_drift() is called
    Then the response lists that port under untracked ports

  Scenario: Everything cataloged and running is not flagged
    Given every currently running launchd job, colima container and bound
      port has a matching catalog-info.yaml entity or ports.yaml row
    When get_catalog_drift() is called
    Then the response's untracked lists are all empty

  Scenario: Drift detection reads typed annotations, never string-greps
    Given the get_catalog_drift implementation
    Then it parses catalog-info.yaml as structured YAML
    And it contains no regex or substring match against free-text file content
      used to decide whether an entity is cataloged
