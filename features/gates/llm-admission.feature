# crew#284 CP2: the router is a plain Deployment on the llm Kustomization (platform/llm/litellm.yaml).
# Kyverno refused its first shape after merge (envFrom secretRef, one optional) and the row sat
# "dry-run failed" for a day with no DNS record. Plain workloads are judged before the PR now.
Feature: The LiteLLM router is admitted by the cluster's policies before it is merged
  # Bound by sovereign/tests/bdd/test_gate_llm_admission.py (rung 4, incident 2026-08-26).

  Scenario: platform/llm renders clean under the cluster's admission policies
    Given platform/llm carries the litellm Deployment with its secrets mounted as files
    When bin/idp-kyverno-render platform/llm runs
    Then the plain workload passes every policy and it exits 0

  Scenario: The shape that was refused on the cluster is refused before the PR
    Given the litellm Deployment rewritten to take its secrets from envFrom
    When bin/idp-kyverno-render runs on that directory
    Then it reports FAIL for the plain workload and exits 1
