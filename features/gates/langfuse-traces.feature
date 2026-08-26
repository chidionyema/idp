# crew#286 CP6: every agent session traces to the estate's one Langfuse with a crew#N tag.
# Langfuse is a HelmRelease on the observability Kustomization (platform/observability/langfuse.yaml),
# seeded by LANGFUSE_INIT_* from the vault (platform/oci/langfuse.tf); nobody signs up.
Feature: Agent sessions trace to the estate's Langfuse, tagged with their crew issue
  # Bound by sovereign/tests/bdd/test_gate_langfuse_render.py. The tofu and live-API scenarios live in
  # docs/prose/langfuse-traces-live.feature until a drill runs them.

  Scenario: The release renders under the cluster's admission policies
    Given platform/observability carries the langfuse HelmRelease and its values
    When bin/idp-kyverno-render platform/observability runs
    Then every rendered workload passes the restricted profile and it exits 0
