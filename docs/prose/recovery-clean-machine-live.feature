# Prose until the drill runs them: these need the vault, GitHub, R2 and the runner OIDC session (crew#300, crew#516 CP8).
Feature: The estate comes back on a machine that has never seen it
  Scenario: A clean runner recovers every load-bearing copy on the machine identity
    Given a GitHub runner holding no key file, no rclone config and no laptop state
    And the runner exchanged its OIDC token for a one-hour OCI session as service user estate-ci
    When bin/idp-recover-drill runs at 04:41 every Sunday, on dispatch, or on a pull request that touches it
    Then the vault is found by its name estate-secrets, never through tofu state
    And an App installation token is minted for the lane recovery, which can read and never write
    And chidionyema/idp, chidionyema/crew and chidionyema/claude-estate clone on that token and each row names the tip
    And every bundles/<repo>/latest.bundle in R2 is read with keys taken from the vault entry prospector-engine-env
    And every bundle passes git bundle verify; complete histories are cloned, incremental ones are counted as needing their remote
    And bin/idp-verify-drill from the fresh idp clone grades the live cluster on the same session
    And the rows are the artifact recover-receipt and the last line is one verdict: ok, FAIL or BLIND

  Scenario: The drill is graded like every other drill
    Given drills/catalogue.yaml row recover-clean-machine carries the workflow's own cron verbatim
    When the drills row of bin/idp-verify asks GitHub for the last green run
    Then a run older than 194 hours is a red row, and a red row is an incident, not a note
