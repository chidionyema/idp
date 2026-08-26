# ADR 0007 (crew#269, founder 2026-08-26: "seamless and secure"): the front door federates to
# GitHub and the estate holds no password for a person. Probe: the `login` row of bin/idp-verify,
# which follows the redirect chain a browser would and never carries a credential.
Feature: The front door is a federated login with no local password
  A door with its own password has a password that must travel, and every route it travels is a
  place it leaks. The door redirects to an identity the founder already holds.

  Scenario: An unauthenticated request is sent to GitHub
    Given the estate zone in clusters/oke/estate-config.yaml
    When bin/idp-verify runs
    Then https://catalogue.<zone>/ answers 302 to https://github.com/login/oauth/authorize, directly or via /oauth2/start
    And the login row prints ok

  Scenario: The door answers anything else
    Given the catalogue answers 200, 401, 500, or a Location that is not GitHub
    When bin/idp-verify runs
    Then the login row prints FAIL and names the Middleware and the identity pods
    And bin/idp-verify exits 1

  Scenario: No zone is configured
    Given clusters/oke/estate-config.yaml has no ESTATE_ZONE
    When bin/idp-verify runs
    Then the login row prints BLIND and never ok

  Scenario: No manifest holds a user database
    Given every file under platform/
    Then no ExternalSecret renders a users file and no ForwardAuth points at authelia
    And the Middleware in front of every route outside identity points at oauth2-proxy

  # Incident 2026-08-26 (idp#146 live): the chart handed the secrets to the pod as env vars, the
  # cluster policy refused the Deployment and the catalogue answered 500.
  Scenario: The secrets reach the pod as one mounted file, never as environment variables
    Given the oauth2-proxy HelmRelease values the row ships
    When the chart is rendered and the cluster policy set is applied to it
    Then no rule fails
    And the same values with the chart's env-var wiring turned on are refused by secrets-not-from-env-vars
