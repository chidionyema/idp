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

  Scenario: a pull request's planned changes are the PR, not drift (incident 2026-08-26, run 32925504695)
    Given oke-check runs bin/idp-oke-rebuild --check on a pull_request touching platform/oci
    And the workflow sets OKE_CHECK_EXPECT_CHANGES=1 only for pull_request events
    When tofu plan exits 2
    Then the planned resource changes are printed and the check passes
    And on schedule or workflow_dispatch the same exit 2 is drift and the check fails
    And exit 1 never passes on any event

  Scenario: a lost-state apply never re-creates a vault that already exists (incident 2026-08-26 02:26Z)
    Given the shared state no longer holds oci_kms_vault.estate
    And an ACTIVE vault named estate-secrets holds the estate's secrets
    When bin/idp-oke-rebuild --apply runs
    Then bin/idp-recreate-guard refuses with the exact "tofu import" command and no vault is created
    And a plan that creates nothing, or a create with no live namesake, passes
  Scenario: the secret store is never repointed at a vault while secrets still live in the current one (incident 2026-08-26 02:26Z)
    Given flux-system/estate-vars names a vault that holds ACTIVE secrets
    When bin/idp-flux-bootstrap sees a different vault_id in the tofu outputs
    Then it refuses with rc 3 and names the import, and switches only when the current vault is empty

  Scenario: a failing rebuild step shows its cause, not only its footer (incident 2026-08-26, run 32930359052)
    Given a step whose output has an Error line followed by ten footer lines
    When the step fails
    Then the Error line and the footer are both on screen
    And a passing step prints one receipt line and nothing else

  Scenario: node cycling is never asked of a BASIC cluster (incident 2026-08-26, run 32930359052)
    Given the estate cluster type is BASIC_CLUSTER
    Then the a1 node pool carries no node_cycling_* keys
    And a node is replaced by surging the pool to 2 and deleting the old node
