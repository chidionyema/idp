# crew#345: "zero-touch OCI auth, no local oci session authenticate". A session that wants the
# cluster state no longer needs a kube path or a laptop token: the CronJob in platform/state
# writes a receipt from the node's identity and bin/idp-cluster-state grades it from a runner.
Feature: The cluster reports its own state and a runner grades it without a laptop
  # Bound by sovereign/tests/bdd/test_gate_cluster_state.py.

  Scenario: The receipt pod is admitted as a Job pod and refused as a long-running one
    Given the receipt container spec from platform/state/cluster-state.yaml as a Pod
    When Kyverno judges it owned by a Job
    Then it is admitted
    When Kyverno judges the same Pod owned by a ReplicaSet
    Then require-pod-probes refuses it

  Scenario: A fresh receipt with every node Ready grades ok
    Given a receipt "ok cluster-state at T nodes=2 ready=2 pods=40 pods_not_ready=1 flux=20 flux_not_ready=0" written 5 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "ok      cluster-state"

  Scenario: A stale receipt grades FAIL
    Given a receipt "ok cluster-state at T nodes=2 ready=2 pods=40 pods_not_ready=0 flux=20 flux_not_ready=0" written 90 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "FAIL    cluster-state" and names the age

  Scenario: A node that is not Ready grades FAIL
    Given a receipt "ok cluster-state at T nodes=2 ready=1 pods=40 pods_not_ready=3 flux=20 flux_not_ready=0" written 5 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "FAIL    cluster-state" and names ready=1

  # crew#406: Flux image automation never pushed and no receipt could say why. Every Flux and
  # External Secrets object's Ready condition is in the receipt; one not Ready fails the row.
  Scenario: A Flux object that is not Ready grades FAIL
    Given a receipt "ok cluster-state at T nodes=2 ready=2 pods=40 pods_not_ready=0 flux=20 flux_not_ready=1" written 5 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "FAIL    cluster-state" and names not Ready

  Scenario: A receipt from a collector that predates the Flux rows grades FAIL, never clean
    Given a receipt "ok cluster-state at T nodes=2 ready=2 pods=40 pods_not_ready=0" written 5 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "FAIL    cluster-state" and names flux_not_ready
