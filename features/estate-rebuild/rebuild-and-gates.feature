# R35 scenarios (rebuild confidently, no error recurs). R36 (features/cloud-agnostic/) adds the
# cloud-agnostic scope on top; where the two disagree R36 wins, because a rebuild of the same
# cloud faster "is just automating our own lock-in" (founder, 2026-08-25).
# Founder, 2026-08-25 (crew#250, R35): "at the end of this we need to be able to tear down and
# rebuild confidently and make it impossible for errors to reoccur"; "missing out any part of the
# estate is novice"; "by the time you conclude I expect exponential improvement".
# Every scenario is graded by a command, never by an opinion.

Feature: The estate can be torn down and rebuilt from the phone, and no past error can recur

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

  Scenario: A stale local state file can never overwrite the shared remote state
    Given a checkout of platform/oci holds a terraform.tfstate from an earlier day
    When bin/idp-oke-rebuild or bin/idp-identity-apply initialises the remote backend
    Then the local file is moved aside as <name>.quarantine-<utc> and printed
    And init runs with -reconfigure, never with -migrate-state or -force-copy
    And tests/test_incident_state_force_copied_over_remote.py proves both ways
