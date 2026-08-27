Feature: the estate vault is seeded by the machine identity, never from a laptop (crew#284, crew#248)
  Founder, 2026-08-26: "get it done." The two vault entries every KINI checkpoint waited on
  (litellm-upstream, prospector-engine-env, github-app) needed a founder line on a laptop whose OCI key
  crew#227 had already deleted. The seed runs in Actions on the OIDC-exchanged identity from
  repository secrets named SEED_<KEY> (litellm-upstream by the oke-check apply step, idp#241; the other two here); bin/idp-vault-put reads them in-process and prints nothing.
  # Bound by sovereign/tests/bdd/test_gate_vault_seed.py.

  Scenario: every key the vault entries need arrives as a SEED_ secret
    Given .github/workflows/vault-seed.yml
    Then every KEY=KEY pair passed to bin/idp-vault-put has a SEED_KEY in the step's env
    And the workflow is dispatch-only with entries all, prospector-engine-env, github-app, flux-writer and temporal-db

  Scenario: no value can reach the log
    Given .github/workflows/vault-seed.yml
    Then the run step never echoes, prints or cats the seed env file and removes it at the end

  Scenario: the git-writer credential never holds the LLM (crew#284)
    Given clusters/oke/platform.yaml and clusters/oke/image-automation.yaml
    Then the git-writer ExternalSecret is a resource of platform/image-automation, not platform/secret-store

  Scenario: secret-store carries only the store (crew#284)
    Given clusters/oke/secrets.yaml
    Then platform/secret-store has no ExternalSecret; every consumer owns its own
