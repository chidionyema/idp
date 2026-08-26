Feature: the front door's OIDC client lives in the estate's own identity domain (crew#269, crew#281)
  Founder, 2026-08-26: "Do not ask the founder to use the GitHub UI." The GitHub OAuth App has no
  API and the Cloudflare Access route needs a token scope no API can grant, so the client is an
  application in the identity domain the estate already administers, created by Terraform with
  credentials it already holds. oauth2-proxy stays generic OIDC and sees only estate-config values.
  # Bound by sovereign/tests/bdd/test_identity_front_door.py. The tofu, apply and founder sign-in
  # scenarios live in docs/prose/front-door-oidc-rollout.feature until a drill runs them.

  Scenario: the pod names no cloud (R36)
    Given platform/identity/oauth2-proxy.yaml
    When bin/cloud-agnostic-gate runs
    Then every provider URL is a ${ESTATE_OIDC_*} substitution from clusters/oke/estate-config.yaml

  Scenario: the Cloudflare broker is gone and nothing names it (crew#288 CP3)
    Given the repository at HEAD
    Then the directory platform/access does not exist
    And .github/workflows/access-apply.yml and bin/idp-access-apply do not exist
    And no tracked file names platform/access, access-apply or ESTATE_LOGIN_GITHUB_USER, except this feature and the decision record that retires them
