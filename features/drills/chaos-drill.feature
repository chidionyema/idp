# crew#292 CP4: "make one pod-kill experiment run weekly and be graded by the drills row".
# A runner has no kube path (bin/idp-oke-rebuild:131), so the Workflow leaves a receipt in
# Object Storage from the node's identity and the drill reads it with the runner's OIDC session.
Feature: The weekly pod-kill experiment is graded from outside the cluster
  Scenario: A finished experiment leaves a receipt
    Given the Workflow backstage-pod-kill ran its experiment step without a StatusCheck abort
    When its receipt step runs as the worker node's instance principal
    Then object chaos/backstage-pod-kill in bucket estate-drill-receipts starts with "ok backstage-pod-kill accomplished at"
    And the pod ran non-root with a read-only root filesystem and no secret mounted

  Scenario: The runner grades the receipt's age
    Given the chaos-drill job holds an OCI session from the GitHub OIDC token and no key
    When bin/idp-chaos-drill runs
    Then it prints "ok      chaos-drill  ok backstage-pod-kill accomplished at ... (Nh old, max 194h)"
    And drills/catalogue.yaml row chaos-pod-kill is green in bin/idp-verify

  Scenario: A missing or stale receipt is a red row
    Given no object chaos/backstage-pod-kill exists, or one older than 194 hours
    When bin/idp-chaos-drill runs
    Then it prints FAIL with the reason and exits 1, and the oke-check.yml run is red

  Scenario: A Task pod is admitted without probes, a long-running pod is not
    Given the receipt container spec from platform/chaos/backstage-pod-kill.yaml as a Pod
    When Kyverno judges it owned by a WorkflowNode
    Then it is admitted
    When Kyverno judges the same Pod owned by a ReplicaSet
    Then require-pod-probes refuses it
