# Founder, 2026-08-25 (crew#250): "Rebuilding the same Oracle cluster faster is just automating
# our own lock-in." Sits beside features/estate-rebuild/rebuild-and-gates.feature (R35) and outranks it where they disagree. The platform must
# not know or care who owns the servers it runs on: GitOps-only hydration, abstracted secrets,
# S3-compatible and Postgres wire-protocol data only, provider-agnostic ingress.
Feature: Disposable compute, universal state
  The Kubernetes cluster is one ephemeral compute node. It can be destroyed, recreated on another
  provider, and heal itself from git and the vault. No application manifest names a cloud.
  # The four migration drills live in docs/prose/cloud-agnostic-drills.feature until a drill runs them.
  # Bound by sovereign/tests/bdd/test_gate_cloud_agnostic.py.

  Scenario: No provider-specific service or annotation in the platform
    Given a platform tree with no provider-specific reference outside platform/oci, platform/secret-store and clusters/
    When bin/cloud-agnostic-gate counts provider-specific annotations, services and API groups
    Then the count is zero and it exits 0
    And a tree that adds one is refused with the file and line that introduced it
    And a root that cannot be read is BLIND, never zero
