# Incident 2026-08-26 (crew#269): the first founder login at auth.<zone> was a 401. The argon2
# hash in the cluster vault was made from a different value than the password in the sops vault,
# and nothing compared the two stores. Probe: the `login` row of bin/idp-verify, proved both ways
# on idp#144.
Feature: The vault hash and the sops password agree
  A credential kept as a hash in one store and as plaintext in another is only proven when a real
  login with the plaintext succeeds. bin/idp-verify performs that login on every operator run.

  Scenario: The sops password opens the front door
    Given secrets/dev/CATALOGUE_FOUNDER_PASSWORD.yaml decrypts to the password behind vault authelia-users
    When bin/idp-verify runs
    Then the login row prints ok with the auth hostname of the estate zone

  Scenario: The sops password no longer matches the vault hash
    Given the sops file decrypts to a value the vault hash was not made from
    When bin/idp-verify runs
    Then the login row prints FAIL with the 401 and names bin/idp-vault-put as the repair
    And bin/idp-verify exits 1

  Scenario: No sops key on this machine
    Given no age key or no estate-secrets checkout is present
    When bin/idp-verify runs
    Then the login row prints BLIND and never ok
