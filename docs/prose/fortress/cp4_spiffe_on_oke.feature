@cp4 @crew227
Feature: Agent identity — SPIRE runs on the estate cluster through Flux and issues short-lived SVIDs
  KINI spec 4.4: SPIFFE IDs authenticate every A2A message; a revoked SVID is instant
  isolation. Until 2026-08-27 SPIRE ran only on the laptop k3d cluster by hand
  (cp4_spiffe_on_k3d.feature); OKE, where the agents run, had no identity issuer.
  The row is platform/spire, applied by the same Flux that applies every other row.

  Scenario: The cluster carries the SPIRE row and Flux waits for it to be healthy
    When I run "python3 -m pytest -q tests/test_spire_row.py"
    Then every property passes and the Kyverno case is not BLIND

  Scenario: The cluster-state receipt shows the identity issuer running
    When I run "gh workflow run oke-check.yml -f mode=check" and read job cluster-state
    Then the daemonsets row lists "spire-agent" with desired equal to ready
    And the helmreleases row lists "spire-mgmt/spire Ready"
