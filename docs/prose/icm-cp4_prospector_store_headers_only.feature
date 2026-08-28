@cp4
Feature: Prospector Store.Api reads trusted headers only
  Founder, 2026-08-25: "our .NET API should not know what a JWT is. It should not contain
  Stripe SDKs. It should not know how to salt a password." Founder addition, 2026-08-25:
  "prospector store will be adding ability for subscriptions and will be a good use case to
  test this." This is the proving ground for the whole mesh. Cross-links: crew#232, crew#235,
  crew#239. Any change to Store.Web or ports 3000/8000/9000 is owned by the crew#259 sync.

  Scenario: Store.Api has zero JWT, Stripe SDK or password-hashing references
    Given a grep of Store.Api for JWT parsing, the Stripe SDK and password-hashing calls
    When the count is measured
    Then the count is 0

  Scenario: Store.Api authorizes purely from trusted headers
    Given Store.Api receives a request with X-Estate-User-Id and X-Estate-Subscription-Tier
    When Store.Api evaluates whether the request may access a Pro-only catalog item
    Then Store.Api's decision depends only on the two headers
    And Store.Api makes no call to Stripe or to a JWT library

  Scenario: A differential replay agrees between the old and new auth paths
    Given a recorded corpus of Store.Api requests under the old in-app auth path
    When the same requests are replayed against the header-only path
    Then every authorization decision matches between the two paths

  Scenario: Store subscriptions work changes coordinate through the storefront sync
    Given work on this checkpoint touches Store.Web or ports 3000, 8000 or 9000
    When that work begins
    Then it is coordinated through crew#259 before Store.Web or those ports change
