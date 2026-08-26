# ADR 0007 (crew#269, founder 2026-08-26: "seamless and secure"): the front door federates to
# the estate identity domain (platform/oci/identity) and the estate holds no password for a person. Probe: the `login` row of bin/idp-verify,
# which follows the redirect chain a browser would and never carries a credential.
Feature: The front door is a federated login with no local password
  A door with its own password has a password that must travel, and every route it travels is a
  place it leaks. The door redirects to an identity the founder already holds.
  # Bound by sovereign/tests/bdd/test_gate_front_door_login.py. The seven scenarios that probe the
  # live door through bin/idp-verify live in docs/prose/front-door-login-live.feature until a drill runs them.

  Scenario: No manifest holds a user database
    Given every file under platform/
    Then no ExternalSecret renders a users file and no ForwardAuth points at authelia
    And the Middleware in front of every route outside identity points at oauth2-proxy

