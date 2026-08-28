@cp6
Feature: The nervous system sees the tier
  Founder, 2026-08-25: "Because all traffic passes through the Gateway, OpenTelemetry
  automatically tracks exactly how many requests Free users make vs Pro users." This is LAW 3,
  the default nervous system, applied to the mesh.

  Scenario: Gateway spans carry the subscription tier
    Given a request passes through the Traefik gateway with a resolved subscription tier
    When the gateway emits its OpenTelemetry span
    Then the span carries the subscription tier as an attribute

  Scenario: Free-vs-Pro request counts are visible with no app code
    Given gateway spans for both Free and Pro requests have been collected
    When the trace store is queried for request counts grouped by tier
    Then Free and Pro request counts are visible
    And no application service emitted the tier attribute itself
