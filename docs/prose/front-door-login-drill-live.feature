# Prose until the drill reads them: the login-drill job of .github/workflows/oke-check.yml runs the sign-in
# for real (crew#292 CP1, crew#297).
Feature: A drill signs in at the front door and sees the catalogue
  Background:
    Given clusters/oke/estate-config.yaml names ESTATE_ZONE and ESTATE_OIDC_DOMAIN_URL
    And platform/oci/identity has created the domain user estate-drill
    And that user is granted the estate-front-door application
    And its password is in the OCI vault as front-door-drill-password

  Scenario: The drill signs in and the catalogue renders
    Given a headless browser with no cookies
    When bin/idp-login-drill opens https://catalogue.<zone>/
    Then the browser is redirected to the identity domain in ESTATE_OIDC_DOMAIN_URL
    And the drill fills the username estate-drill and the password it read from the vault
    And the browser returns to catalogue.<zone>
    And that host answers 200 to the signed-in session
    And the Backstage shell renders the text "Catalog"
    And the script prints one line beginning "ok      login-drill  signed in as estate-drill"
    And bin/idp-login-drill exits 0

  Scenario: The password is wrong
    Given the vault secret front-door-drill-password no longer matches the domain user
    When bin/idp-login-drill runs
    Then the browser never leaves the identity domain
    And the script prints "FAIL    login-drill  credentials" and names the URL it was stuck on
    And the password does not appear anywhere in the output
    And bin/idp-login-drill exits non-zero

  Scenario: The domain demands a password change on first login
    Given the identity domain sets mustChange=true on the password Terraform supplied at create
    And that flag is read-only on the user and no password policy switches it off
    When bin/idp-identity-apply apply runs
    Then it sets the vault password on estate-drill once through the admin UserPasswordChanger
    And prints "ok      drill user password settled" and the flag reads false
    And a second run prints "ok      drill user password already settled" and changes nothing
    And if the drill still meets a change-password page it prints "FAIL    login-drill  password-change"
    And it does not set a new password itself, because the credential belongs to Terraform

  Scenario: The domain asks the drill user to consent to the front door
    Given the front-door application in platform/oci/identity sets bypass_consent = true
    When bin/idp-login-drill signs in
    Then the browser is never parked on /ui/v1/myconsole/consent
    And when it is, the FAIL line names that URL and the first words on the page

  Scenario: A later apply never overwrites the live drill password
    Given the drill user's password, schemas and write-only user extension are in ignore_changes
    When bin/idp-identity-apply plan runs after the drill is green
    Then it prints "No changes. Your infrastructure matches the configuration."
    And bin/idp-login-drill still signs in with the vault password

  Scenario: The JWKS the door validates against is private
    Given the identity domain's JWKS endpoint is unreachable or requires a credential
    When bin/idp-login-drill runs
    Then oauth2-proxy cannot validate the id token and the browser never reaches catalogue.<zone>
    And the script prints "FAIL    login-drill  session" or "FAIL    login-drill  credentials"
    And the stage names the layer, so nobody debugs Backstage for an identity fault
    And bin/idp-login-drill exits non-zero

  Scenario: The drill credential is never on a laptop and never in a log
    Given every file in this repository and every line the drill prints
    Then the password appears in neither
    And the only place it exists is the OCI vault secret Terraform wrote
    And the CI job reads it with the same GitHub OIDC to OCI token exchange as bin/idp-oke-rebuild

  Scenario: The door is green but Backstage shows its own guest sign-in page
    Given the front door signs the drill user in
    And Backstage still offers a guest "Enter" button instead of trusting the door's headers
    When the drill runs
    Then it prints "FAIL    login-drill  identity" naming the guest page
    And exits 1

  Scenario: The door's identity reaches Backstage's auth provider
    Given the drill user has signed in at the door
    When the drill asks Backstage's oauth2Proxy provider who the session is
    Then the answer is a user entity ref derived from the door's email header
    And the ok line names that ref

  Scenario: The refresh endpoint is asked at Backstage's real path
    Given the door forwarded a session to Backstage
    When the identity stage asks the auth backend who the session is
    Then it posts to /api/auth/oauth2Proxy/refresh, not to a versioned path
    And a 404 naming an unknown provider is reported as a FAIL, never as a guest

  Scenario: The drill reads the catalogue and sees no error, not only a shell
    Given the drill is signed in with a Backstage identity
    Then GET /api/catalog/entities?limit=5 with the door session and the Backstage token as Bearer answers 200 and a non-empty list
    And the page raised no JavaScript error while rendering
    And the page shows none of "Something went wrong", "Unexpected error", "Internal Server Error", "Failed to sign in"
    And the ok line names the entity count and "0 js errors"

  # crew#307: the founder's own account reached the resolver without x-auth-request-email.
  Scenario: A door request with a user name and no email still signs in
    Given the front door forwards x-auth-request-user "chidionyema" and no x-auth-request-email
    When Backstage's oauth2Proxy sign-in resolver runs
    Then it issues user:default/chidionyema
    And a request with neither header is refused with the reason in the message

  # crew#307, 13:15Z: 40 minutes after the */5 cron landed on main GitHub had fired zero scheduled
  # runs and nothing said so. Absence is graded on a second clock.