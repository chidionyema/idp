# Prose until a drill runs them: these need the tenancy, the scheduled rehearsal and the registry (crew#297).
Feature: The estate rebuilds from an empty tenancy and every incident is a gate
  Background:
    Given the estate inventory is the catalogue in Backstage
    And every component in it names its build, its deploy, its health alert and its rebuild step

  Scenario: Every component of the estate is covered, or a command says which is not
    When I run "bin/estate-coverage"
    Then it prints one line per component with build, deploy, alert and rebuild each marked ok
    And it prints zero lines marked GAP
    And CI fails a pull request that adds a workload without a row in the inventory

  Scenario: A full rebuild from an empty tenancy, started from the phone
    Given the Oracle tenancy holds no cluster
    When the founder runs the "rebuild" workflow from the GitHub mobile app or a Telegram command
    Then no step asks a person for a hand
    And within the measured time budget the cluster, secrets, portal, prospector and DNS are running
    And a Telegram message arrives with the elapsed time and one green line per component
    And the portal answers at its public address

  Scenario: The rebuild is rehearsed on a schedule
    Given the weekly rebuild rehearsal is scheduled
    When the week passes
    Then the rehearsal has run and its Telegram receipt shows the same green lines as the last one
    And a rehearsal that fails or does not run is itself an alert to the founder

  Scenario: A broken workload is reported to the founder within ten minutes
    Given every workload is running
    When one workload is broken on purpose
    Then a Telegram alert naming the workload and the cause arrives within ten minutes
    And when it is repaired a recovery message follows

  Scenario: Every past incident is a gate proved both ways
    Given the incident record lists every failure that has happened on this estate
    When I run "bin/estate-coverage --incidents"
    Then it prints one line per incident naming the gate that refuses that class of error
    And each gate has a recorded proof that it refuses the bad case and permits the good case
    And it prints zero incidents without a gate

  Scenario: A deploy cannot point at an image nobody builds
    Given a manifest references an image tag
    When the tag does not exist in the registry
    Then CI refuses the pull request before it reaches the cluster

  Scenario: Improvement is measured, not felt
    Given each rebuild rehearsal records elapsed time, hand steps, gaps and incidents without a gate
    When the founder reads the last four receipts
    Then hand steps and gaps are zero and stay zero
    And elapsed time has not grown
    And every new incident since the previous rehearsal has a gate by the next one
