# Prose until the drill runs them: these need the cluster, Object Storage and the runner OIDC session (crew#345).
Feature: The platform verifies its own health every hour with no person logged in
  Scenario: A runner grades the cluster's own verdict on the machine identity
    Given the CronJob cluster-state (platform/state, idp#267) wrote state/cluster from the worker node's instance principal within the last hour
    And the verify-drill job holds an OCI session exchanged from its GitHub OIDC token and no key
    When bin/idp-verify-drill runs at minute 23 of every hour
    Then the identity row names service user estate-ci with ttype te, never a person's OCID or a browser login
    And the cluster row counts the ACTIVE cluster and node pools through the OCI API
    And the receipt row is the verdict of bin/idp-cluster-state: fresh, every node Ready

  Scenario: Twenty-four hours with nobody awake
    Given no oci session authenticate ran anywhere for 24 hours
    When crew's estate snapshot counts the scheduled verify-drill runs of the last 24 hours
    Then every one of them succeeded and the row reads GREEN, which is crew#345's acceptance criterion
