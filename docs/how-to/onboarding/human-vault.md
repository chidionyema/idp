# Human secret door — onboarding

How to move a person-held secret into the estate through the human door (decision 0017).

## When this door, not the vault

Use the human door when a person holds the value: a token shown once in a vendor console, a key
delivered by mail, anything born outside code. If code can mint the value, it does not come this
way — Terraform or a bootstrapper writes it straight to the cloud vault (see
docs/reference/policy/root-trust.md, which registers every root either way).

## Steps

1. The secret's owner opens the Bitwarden web vault (a phone browser is fine), goes to Secrets
   Manager, and adds a new secret to the estate's project. The secret's name is the name the
   cluster will use.
2. Add an `ExternalSecret` next to the consuming workload with
   `secretStoreRef: {kind: ClusterSecretStore, name: human-vault}` and `remoteRef.key` set to
   that name. `platform/human-vault/access-token.yaml` is the shape to copy.
3. Add the register row in docs/reference/policy/root-trust.md naming where the value was born.
4. Push the branch; the founder applies. The value itself never appears in the branch, a
   terminal, or a chat.

## What exists underneath

`platform/human-vault/` holds the store, its TLS chain and its admission exceptions; the
Bitwarden SDK server rides the external-secrets chart (platform/secrets/external-secrets.yaml).
The bridge's own credential is the one root registered as `bitwarden-machine`.
