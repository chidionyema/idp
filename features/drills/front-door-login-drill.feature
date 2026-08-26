# crew#292 CP1. The login row of bin/idp-verify proves the front door redirects; it carries no
# credential, so it cannot prove anyone can get in. This drill signs in for real as the domain
# user platform/oci/identity creates, and is the executable spec for bin/idp-login-drill and the
# login-drill job of .github/workflows/oke-check.yml.
Feature: A drill signs in at the front door and sees the catalogue
  A door that redirects correctly and admits nobody is still a closed door. The only proof that
  the front door works is a sign-in that ends on a rendered catalogue, and it has to run without
  a person, so the account it uses belongs to Terraform and its password never leaves the vault.

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
