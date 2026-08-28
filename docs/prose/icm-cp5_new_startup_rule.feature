@cp5
Feature: New-startup rule
  Founder, 2026-08-25: "The New Startup Rule: deploy the Gateway, Identity, and Billing
  primitives. You write a tiny 50-line API in Python that reads the headers."

  Scenario: A 50-line Python API gets auth and tiering for free on day 1
    Given a new 50-line Python API is deployed behind the existing Traefik gateway
    When a request reaches it carrying X-Estate-User-Id and X-Estate-Subscription-Tier
    Then the API enforces tier-gated behaviour using only those headers
    And the API contains no authentication or billing code of its own

  Scenario: The new API ships with a demo and an onboarding doc
    Given the 50-line Python API is added to the mesh
    When it is presented as done
    Then a demo script and an onboarding doc exist for it (LAW 32)
