@cp1
Feature: Gateway auth at the edge
  Founder, 2026-08-25: "The Gateway ... intercepts every request. It catches the JWT ... asks
  the Identity Primitive: Is this token valid, and what is their subscription tier?" and "If
  the JWT is invalid, or the user hasn't paid, the Gateway rejects the request ... The request
  never even reaches your .NET API."

  Scenario: Traefik ForwardAuth calls the identity primitive before any backend is reached
    Given Traefik ForwardAuth is wired to the Ory Oathkeeper decision endpoint
    When a request carries a valid JWT for a paid subscriber
    Then Traefik injects X-Estate-User-Id and X-Estate-Subscription-Tier
    And the request reaches the backend service

  Scenario: An invalid JWT is rejected at the edge
    Given Traefik ForwardAuth is wired to the Ory Oathkeeper decision endpoint
    When a request carries an invalid or missing JWT
    Then Traefik returns 401 Unauthorized
    And no backend service receives the request

  Scenario: A lapsed subscriber is rejected at the edge
    Given Traefik ForwardAuth is wired to the Ory Oathkeeper decision endpoint
    When a request carries a valid JWT for a lapsed subscriber requesting a Pro-only route
    Then Traefik returns 402 Payment Required
    And no backend service receives the request

  Scenario: Spoofed trust headers from the internet are stripped
    Given a request arrives at the edge already carrying X-Estate-User-Id and X-Estate-Subscription-Tier
    When Traefik processes the request
    Then the incoming X-Estate-User-Id and X-Estate-Subscription-Tier headers are stripped
    And only the values ForwardAuth injects reach the backend
