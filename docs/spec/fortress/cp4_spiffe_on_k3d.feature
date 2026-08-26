@cp4
Feature: Agent identity — SPIRE runs on the estate cluster and issues short-lived SVIDs
  The founder: "SPIFFE/SPIRE issuing short-lived cryptographic identities to
  agents as non-human identities." Deferred while the estate was one laptop
  with nothing to attest against; the k3d cluster (platform/k3d) changed that
  on 2026-08-24. The server attests the agent with k8s_psat (a projected
  service-account token the API server signs), workloads are attested by pod
  identity, and a pod holding no secret gets a one-hour X.509 SVID.
  Installed from platform/spire/values.yaml with spiffe/helm-charts-hardened
  (`make spire-up`); proved by `make spire-proof`.

  Scenario: The SPIRE server has attested the node agent
    When I run "make spire-status"
    Then the output contains "Attestation type  : k8s_psat"

  Scenario: A workload in the catalogue namespace receives an SVID from the Workload API
    When I run "make spire-proof"
    Then the output contains "SPIFFE ID:		spiffe://estate.internal/ns/backstage/sa/default"
    And the output contains "Received 1 svid"
