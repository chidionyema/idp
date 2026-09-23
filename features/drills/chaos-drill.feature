# crew#292 CP4: "make one pod-kill experiment run weekly and be graded by the drills row".
# A runner has no kube path (bin/idp-oke-rebuild:131), so the Workflow leaves a receipt in
# Object Storage from the node's identity and the drill reads it with the runner's OIDC session.
Feature: The weekly pod-kill experiment is graded from outside the cluster
  # Bound by sovereign/tests/bdd/test_gate_chaos_drill.py, which judges the receipt pod with the Kyverno CLI
  # against the pinned policy set. The receipt, grading and red-row scenarios live in
  # docs/prose/chaos-drill-live.feature until the drill runs them.

  Scenario: A Task pod is admitted without probes, a long-running pod is not
    Given the receipt container spec from platform/chaos/backstage-pod-kill.yaml as a Pod
    When Kyverno judges it owned by a WorkflowNode
    Then it is admitted
    When Kyverno judges the same Pod owned by a ReplicaSet
    Then require-pod-probes refuses it
