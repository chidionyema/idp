@cp3
Feature: Headless billing primitive
  Founder, 2026-08-25: "The Tollbooth (Headless Billing) ... a headless Stripe sync worker ...
  continuously updates the Passport Office with the user's current subscription tier. If they
  stop paying, the Identity Primitive instantly revokes their Pro status."
  Chosen: a headless Stripe sync worker over Lago (Lago meters usage in front of a processor;
  Stripe is required either way, and Prospector needs real card processing now, not usage
  metering).

  Scenario: A successful payment upgrades the tier in identity
    Given the Stripe sync worker is subscribed to Stripe webhook events
    When a subscription payment succeeds
    Then the worker updates the user's tier to Pro in Ory Kratos
    And no application service processes the Stripe event directly

  Scenario: A lapsed payment revokes Pro without app code
    Given a user's subscription is currently Pro in Ory Kratos
    When Stripe reports the subscription has lapsed
    Then the Stripe sync worker downgrades the user's tier to Free in Ory Kratos
    And the next gateway request for that user carries X-Estate-Subscription-Tier: free
