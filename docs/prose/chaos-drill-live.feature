# Prose until the drill runs them: these need the cluster, Object Storage and the runner OIDC session (crew#292 CP4, crew#297).
Feature: The weekly pod-kill experiment leaves a receipt and the runner grades it
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
