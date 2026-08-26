# Prose until a drill runs them: these need gh, the live run history and bin/idp-verify (crew#292 CP2, crew#297).
Feature: The drills row of bin/idp-verify grades the live run history
  Scenario: A drill ran inside its window
    Given a catalogue entry whose workflow has a successful run newer than max_age_hours
    When bin/idp-verify runs
    Then the drills row for that entry prints ok with the age in hours and the cap

  Scenario: Every graded drill is green
    Given every non-pending catalogue entry printed ok
    When bin/idp-verify runs
    Then the summary line is "ok drills N/N green within window", N being the graded entries
    And the drills row does not set the exit code

  Scenario: A drill has gone stale
    Given a catalogue entry whose last successful run is older than max_age_hours
    When bin/idp-verify runs
    Then that entry's row prints FAIL with the workflow file, the age and the cron string
    And the summary line is "FAIL drills k of N stale:" followed by the names
    And bin/idp-verify exits 1

  Scenario: A drill has never run at all
    Given a catalogue entry whose workflow has no successful run on record
    When bin/idp-verify runs
    Then that entry's row prints FAIL saying no successful run has ever been recorded
    And it counts as stale in the summary line

  # The catalogue carries the drill the estate is missing rather than staying quiet about it.
  # login-drill is declared here before the job that runs it exists (branch feat/login-drill).
  Scenario: A pending drill is named but never graded
    Given a catalogue entry with pending: true
    When bin/idp-verify runs
    Then that entry's row prints n/a saying the drill is not merged yet
    And it is excluded from the N of the summary line and counted as pending
    And it can never make bin/idp-verify exit 1

  Scenario: Freshness cannot be measured
    Given gh is not installed, or gh auth status fails
    When bin/idp-verify runs
    Then the drills row prints one BLIND line naming the reason, not one FAIL per drill
    And it never prints ok
    And the drills row does not set the exit code, because unknown is not failed

  Scenario: The catalogue is missing or empty
    Given drills/catalogue.yaml does not exist, or declares no drills
    When bin/idp-verify runs
    Then the drills row prints BLIND naming the file
    And it never prints ok

  # Founder, 2026-08-26: "we need test discipline" -- the front door had failed three times on first
  # use, each found by hand. policy/operating_model.rego rule drill_named.
  Scenario: The catalogue names a workflow that was retired
    Given an entry whose workflow file no longer exists under .github/workflows
    And GitHub still lists a green run for that workflow name from before it was deleted
    When bin/idp-verify runs
    Then the drills row prints FAIL naming the missing file
    And the old run history is never consulted

  Scenario: login-drill is graded, not pending
    Given drills/catalogue.yaml has no pending flag on login-drill
    When bin/idp-verify runs
    Then the drills row grades login-drill by the age of its last green oke-check.yml run
    And a run older than 26 hours is a FAIL, never n/a

  # crew#311: a policy statement that is in git but not live fails every apply with a 409 that names
  # nothing. The check grades the live tenancy-root policy against platform/oci/policy/*.json.
  Scenario: The check names a policy statement that is in git but not live
    Given platform/oci/policy/estate-operators.statements.json holds the estate-operators statements
    When bin/idp-oke-rebuild --check runs its iam-policy row
    Then a live policy equal to the file prints ok with the statement count
    And a statement missing live prints FAIL naming the statement and "founder runs bin/idp-oci-bootstrap"
    And a policy the identity cannot read prints BLIND, never ok
