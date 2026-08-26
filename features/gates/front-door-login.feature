# ADR 0007 (crew#269, founder 2026-08-26: "seamless and secure"): the front door federates to
# the estate identity domain (platform/oci/identity) and the estate holds no password for a person. Probe: the `login` row of bin/idp-verify,
# which follows the redirect chain a browser would and never carries a credential.
Feature: The front door is a federated login with no local password
  A door with its own password has a password that must travel, and every route it travels is a
  place it leaks. The door redirects to an identity the founder already holds.

  Scenario: An unauthenticated request is sent to the identity domain
    Given the estate zone in clusters/oke/estate-config.yaml
    When bin/idp-verify runs
    Then https://catalogue.<zone>/ answers 302 to <ESTATE_OIDC_DOMAIN_URL>/oauth2/v1/authorize, directly or via /oauth2/start
    And the login row prints ok

  # Incident 2026-08-26 02:31Z (crew#269): the redirect was right and the founder's first sign-in
  # returned 500. oauth2-proxy fetched /admin/v1/SigningCert/jwk to verify the id_token and the domain
  # answered 401: a new identity domain keeps its signing certificate private. The login row was green
  # because it graded the way in and never the way back.
  Scenario: The identity domain's signing keys are readable by the relying party
    Given the login row printed ok
    When bin/idp-verify requests <ESTATE_OIDC_DOMAIN_URL>/admin/v1/SigningCert/jwk without a credential
    Then it answers 200 with at least one key and the jwks row prints ok
    And bin/idp-identity-apply is what sets signingCertPublicAccess, by a SCIM PATCH, never a console

  Scenario: The signing keys are private
    Given the JWKS endpoint answers 401
    When bin/idp-verify runs
    Then the jwks row prints FAIL naming the 500 the callback will return and the apply command
    And bin/idp-verify exits 1

  Scenario: The door answers anything else
    Given the catalogue answers 200, 401, 500, or a Location that is not the identity domain
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

  Scenario: the login row refuses a placeholder client id (idp#149 review, 2026-08-26)
    Given the catalogue answers 302 to the identity domain's authorize page
    And the client_id in that Location is empty or "replace-in-console"
    When bin/idp-verify runs the login row
    Then the row is FAIL and names the FOUNDER ACTION that fills the vault secrets
    And a 302 carrying any other client_id is ok

