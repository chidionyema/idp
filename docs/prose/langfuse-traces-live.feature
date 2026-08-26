# Prose until a drill runs them: these need tofu against the vault and the live Langfuse API (crew#286 CP6).
Feature: Agent sessions trace to the live Langfuse, tagged with their crew issue
  Scenario: The seed secrets have no human author
    Given platform/oci/langfuse.tf
    When tofu plan runs
    Then the two keys and the user password come from random_uuid and random_password, and the user email is the ESTATE_FOUNDER_EMAIL repo variable, never a value typed into a file

  Scenario: A tag query returns the session
    Given a hermes-agent session run with HERMES_LANGFUSE_TAGS=crew#286
    When GET /api/public/traces?tags=crew%23286 is called with the project keys
    Then at least one trace is returned and it carries the tag crew#286
