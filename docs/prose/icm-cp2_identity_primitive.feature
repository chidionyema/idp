@cp2
Feature: Headless identity primitive
  Founder, 2026-08-25: "The Passport Office (Headless Identity) ... Ory Kratos/Oathkeeper or
  Keycloak ... only job is to mint JWTs, handle password resets, and store user metadata."
  Chosen: Ory Kratos + Oathkeeper, headless and API-only, over Keycloak (Java/WildFly admin
  console, adapter-based integration that fights a gateway-first architecture).

  Scenario: Kratos mints a JWT for a valid login
    Given Ory Kratos is deployed from idp manifests on the cluster
    When a user submits valid credentials
    Then Kratos mints a JWT
    And the JWT is accepted by Oathkeeper's decision endpoint

  Scenario: A password reset does not touch application code
    Given Ory Kratos is deployed from idp manifests on the cluster
    When a user requests a password reset
    Then Kratos completes the reset flow
    And no application service is involved in the reset

  Scenario: User metadata and tier live only behind universal protocols
    Given Ory Kratos is deployed from idp manifests on the cluster
    When Kratos stores user metadata and subscription tier
    Then the data lands in a Postgres row or S3-compatible object storage only
    And no provider-only datastore is used
