@cp4
Feature: Agent identity — SPIFFE/SPIRE deferred to the k8s exit, decision recorded honestly
  The founder: "SPIFFE/SPIRE issuing short-lived cryptographic identities to
  agents as non-human identities." Strict bar: a single-laptop estate has no
  second node to attest against, so a SPIRE server here would attest itself.
  Deferred to crew#78 (the k8s exit), not adopted now.

  Scenario: No SPIRE control plane runs on the laptop
    When I run "docker ps --format '{{.Names}}'"
    Then no container name contains "spire"

  Scenario: The deferral and the interim control are on the record
    When I read the body of chidionyema/crew issue 78
    Then it records the SPIFFE/SPIRE deferral to the k8s exit
    And it records the interim per-agent sops+age key as the current identity boundary
