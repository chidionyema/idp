# Prose until a drill runs them: crew#639 messaging day 0. A file moves under features/ the day a test names it (bin/spec-gate).

@cp2
Feature: the broker is on and admitted

  Scenario: JetStream answers from inside the cluster
    Given platform/event-bus is no longer suspended in clusters/oke/platform.yaml
    And the HelmRelease pins chart 2.14.6 with a file store, TLS on ports 4222 and 6222, and num_replicas 1 on the two-node pool
    And the operator JWT and the system account come from an ExternalSecret over OCI Vault
    When nats server check jetstream runs from a GitHub runner over the tailnet
    Then it prints ok
    And ports 4222, 6222 and 8222 are rows in catalog/ports.yaml and bin/port-gate passes


  Scenario: every pod passes admission before it is applied
    When bin/idp-kyverno-dirs platform/event-bus runs
    Then it prints 0 fail
    And every container runs non-root, read-only root filesystem, with requests and probes set


  Scenario: R3 is one values change when the pool has three nodes
    Given the node pool has fewer than three Ready nodes
    Then the stream replica count is 1 and the ADR records why
    When the pool reaches three Ready nodes
    Then num_replicas becomes 3 in one values change and no application code changes
