# Prose until the drill runs them: these need the cluster, Object Storage and the runner OIDC session (crew#345).
Feature: The platform verifies its own health every hour with no person logged in
  Scenario: The cluster writes its own verdict from inside
    Given the CronJob health/cluster-health-receipt fires at minute 7 of every hour
    When its init container lists nodes, Flux Kustomizations and HelmReleases through a read-only ClusterRole
    And its receipt container runs as the worker node's instance principal
    Then object health/cluster in bucket estate-drill-receipts starts with "ok cluster-health at" when every node and every Flux object is ready
    And the pod ran non-root with a read-only root filesystem and no secret mounted

  Scenario: A runner grades the verdict on the machine identity
    Given the verify-drill job holds an OCI session exchanged from its GitHub OIDC token and no key
    When bin/idp-verify-drill runs at minute 23 of every hour
    Then the identity row names service user estate-ci with ttype te, never a person's OCID or a browser login
    And the cluster row counts the ACTIVE cluster and node pools through the OCI API
    And the receipt row is green only when health/cluster starts with ok and is under 2 hours old

  Scenario: Twenty-four hours with nobody awake
    Given no oci session authenticate ran anywhere for 24 hours
    When crew's estate snapshot counts the scheduled verify-drill runs of the last 24 hours
    Then every one of them succeeded and the row reads GREEN, which is crew#345's acceptance criterion
