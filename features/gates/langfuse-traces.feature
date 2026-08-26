# crew#286 CP6: every agent session traces to the estate's one Langfuse with a crew#N tag.
# Langfuse is a HelmRelease on the observability Kustomization (platform/observability/langfuse.yaml),
# seeded by LANGFUSE_INIT_* from the vault (platform/oci/langfuse.tf); nobody signs up.
Feature: Agent sessions trace to the estate's Langfuse, tagged with their crew issue

  Scenario: The release renders under the cluster's admission policies
    Given platform/observability carries the langfuse HelmRelease and its values
    When bin/idp-kyverno-render platform/observability runs
    Then every rendered workload passes the restricted profile and it exits 0

  Scenario: The seed secrets have no human author
    Given platform/oci/langfuse.tf
    When tofu plan runs
    Then the four langfuse-init-* vault secrets come from random_uuid and random_password, never a variable a person types

  Scenario: A tag query returns the session
    Given a hermes-agent session run with HERMES_LANGFUSE_TAGS=crew#286
    When GET /api/public/traces?tags=crew%23286 is called with the project keys
    Then at least one trace is returned and it carries the tag crew#286
