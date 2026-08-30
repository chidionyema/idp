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
    Given a receipt "ok cluster-state at T nodes=2 ready=2 pods=40 pods_not_ready=1 flux=20 flux_not_ready=0 ds=3 ds_short=0 events_warning=0 monitoring_rules=1 alert_watchdog=1 cpu_used_pct=40 cpu_req_pct=55 mem_used_pct=60 mem_req_pct=70" written 5 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "ok      cluster-state"

  Scenario: A stale receipt grades FAIL
    Given a receipt "ok cluster-state at T nodes=2 ready=2 pods=40 pods_not_ready=0 flux=20 flux_not_ready=0 ds=3 ds_short=0 events_warning=0 monitoring_rules=1 alert_watchdog=1" written 90 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "FAIL    cluster-state" and names the age

  Scenario: A node that is not Ready grades FAIL
    Given a receipt "ok cluster-state at T nodes=2 ready=1 pods=40 pods_not_ready=3 flux=20 flux_not_ready=0 ds=3 ds_short=0 events_warning=0 monitoring_rules=1 alert_watchdog=1" written 5 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "FAIL    cluster-state" and names ready=1

  # crew#406: Flux image automation never pushed and no receipt could say why. Every Flux and
  # External Secrets object's Ready condition is in the receipt; one not Ready fails the row.
  Scenario: A Flux object that is not Ready grades FAIL
    Given a receipt "ok cluster-state at T nodes=2 ready=2 pods=40 pods_not_ready=0 flux=20 flux_not_ready=1 ds=3 ds_short=0 events_warning=0 monitoring_rules=1 alert_watchdog=1" written 5 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "FAIL    cluster-state" and names not Ready

  Scenario: A receipt from a collector that predates the Flux rows grades FAIL, never clean
    Given a receipt "ok cluster-state at T nodes=2 ready=2 pods=40 pods_not_ready=0" written 5 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "FAIL    cluster-state" and names flux_not_ready

  # crew#320: telemetry-coverage read seen=0 for weeks because the k8s-infra otel-agent DaemonSet
  # created no pods and nothing said so. A DaemonSet short of desired fails the row and the
  # receipt carries the Warning events that name why.
  Scenario: A DaemonSet short of its desired count grades FAIL
    Given a receipt "ok cluster-state at T nodes=2 ready=2 pods=40 pods_not_ready=0 flux=20 flux_not_ready=0 ds=3 ds_short=1 events_warning=2 monitoring_rules=1 alert_watchdog=1" written 5 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "FAIL    cluster-state" and names DaemonSet

  Scenario: A receipt from a collector that predates the DaemonSet row grades FAIL, never clean
    Given a receipt "ok cluster-state at T nodes=2 ready=2 pods=40 pods_not_ready=0 flux=20 flux_not_ready=0" written 5 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "FAIL    cluster-state" and names ds_short

  # crew#539 DoD 1: the receipt counts the PrometheusRules Prometheus loaded and whether the
  # Watchdog alert is firing (the always-on alert that proves Prometheus -> Alertmanager is live).
  # A collector that predates the row, or a Prometheus with no rules, fails the row.
  Scenario: A receipt from a collector that predates the monitoring row grades FAIL, never clean
    Given a receipt "ok cluster-state at T nodes=2 ready=2 pods=40 pods_not_ready=0 flux=20 flux_not_ready=0 ds=3 ds_short=0 events_warning=0" written 5 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "FAIL    cluster-state" and names monitoring_rules

  # crew#387: an ExternalSecret whose controller stopped refreshing stays Ready while the Secret
  # drifts from the vault. The collector grades it not Ready past 2x its refreshInterval, so it
  # lands in flux_not_ready like an errored sync and the receipt fails.
  Scenario: An ExternalSecret that is Ready but has not refreshed in twice its interval grades FAIL
    Given a receipt "ok cluster-state at T nodes=2 ready=2 pods=40 pods_not_ready=0 flux=21 flux_not_ready=1 ds=3 ds_short=0 events_warning=0 monitoring_rules=1 alert_watchdog=1" written 5 minutes ago
    When bin/idp-cluster-state grades it
    Then the verdict line starts with "FAIL    cluster-state" and names not Ready
