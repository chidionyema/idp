# Prose until a drill runs them: these need tofu with providers, the identity domain, or the founder.
Feature: the front door OIDC client is applied by Terraform and used by the founder (crew#269, crew#281)
  Scenario: the identity module is valid and writes the two vault secrets the pod reads
    Given the directory platform/oci/identity
    When tofu validate runs with the providers installed
    Then it prints "The configuration is valid"
    And main.tf writes oci_vault_secret oauth2-proxy-client-id and oauth2-proxy-client-secret
    And platform/identity/external-secret.yaml reads those two names and nothing cloud-specific

  Scenario: the apply refuses a domain mismatch
    Given ESTATE_OIDC_DOMAIN_URL in estate-config differs from DOMAIN_BASE_URL
    When bin/idp-identity-apply plan runs
    Then it prints "FAIL    identity" and exits 2 before any tofu call

  Scenario: the founder signs in with the identity he already has
    Given the apply has run and oauth2-proxy has restarted on the new secrets
    When the founder opens https://catalogue.<zone>/
    Then he is sent to the identity domain's sign-in page, not to GitHub
    And after signing in the catalogue renders
    And a user the domain has not granted the app is refused at the identity provider
