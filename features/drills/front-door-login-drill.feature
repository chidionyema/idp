# crew#292 CP1. The login row of bin/idp-verify proves the front door redirects; it carries no
# credential, so it cannot prove anyone can get in. This drill signs in for real as the domain
# user platform/oci/identity creates, and is the executable spec for bin/idp-login-drill and the
# login-drill job of .github/workflows/oke-check.yml.
Feature: A drill signs in at the front door and sees the catalogue
  A door that redirects correctly and admits nobody is still a closed door. The only proof that
  the front door works is a sign-in that ends on a rendered catalogue, and it has to run without
  a person, so the account it uses belongs to Terraform and its password never leaves the vault.
  # Bound by sovereign/tests/bdd/test_gate_login_drill_heartbeat.py. The sign-in scenarios need the live
  # front door and live in docs/prose/front-door-login-drill-live.feature; the login-drill job runs them.

  Scenario: A drill that never runs is a failed drill
    Given the newest successful login-drill run is older than 20 minutes
    When bin/idp-drill-heartbeat grades login-drill.yml
    Then it prints FAIL with the age, the run id and the dispatch command
    And a run with no successful run on record is FAIL, and an unreadable API is BLIND, never ok
    And drill-heartbeat.yml runs every 15 minutes and opens or comments "P0: login drill failed" on FAIL
