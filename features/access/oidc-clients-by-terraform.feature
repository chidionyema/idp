Feature: OIDC clients are provisioned by Terraform, never by a console (crew#281)
  Founder, 2026-08-26: "Do not ask the founder to use the GitHub UI." The front door's OIDC
  client comes from platform/access; its id and secret land in the estate vault unseen.

  Scenario: the access module is valid and names the vault secrets the front door reads
    Given the directory platform/access
    When tofu validate runs with the providers installed
    Then it prints "The configuration is valid"
    And main.tf writes oci_vault_secret oauth2-proxy-client-id and oauth2-proxy-client-secret

  Scenario: a session reads estate-defaults.yaml before asking the founder anything
    Given estate-defaults.yaml at the repository root
    Then handoff_protocol.mode is lazy_consensus and timeout_minutes is 60
    And policy.oauth_creation is terraform-automated

  Scenario: the apply runs unattended and waits, never asks, while the token lacks scope (CP4)
    Given the workflow .github/workflows/access-apply.yml on an hourly schedule and workflow_dispatch
    And bin/idp-oci-login rendered platform/access/backend_override.tf for remote state
    When bin/idp-access-apply runs and the Cloudflare token sees 0 accounts
    Then it prints "WAITING access" and exits 0 with nothing applied
    And on the first tick after the token gains Account -> Zero Trust: Edit it applies without a person
