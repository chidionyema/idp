# Store a credential

The standard is the sops+age directory vault, `estate-secrets`, one file per secret
(`crew/docs/STANDARDS.md`, Secrets row; founder ruling 2026-08-24). A downloaded key file is a
credential on one laptop; it becomes an estate credential only when it is in the vault.

1. Ingress: `scripts/secret-add <env> <NAME> < file` in `estate-secrets`. The value is read from
   stdin so it never appears in a shell history or a process list.
2. Delete the download. `~/Downloads` is not a key store.
3. Consumers read the vault, never a pasted value. Example: the OCI API key is
   `OCI_API_KEY_PEM`, `OCI_USER_OCID`, `OCI_FINGERPRINT`; `bin/oci-login` (when written) renders
   `~/.oci/config` from the vault.

## What the standard does not yet cover

- **Root of trust is one age recipient on one machine** (`.sops.yaml` lists one `age1` key).
  Losing that laptop loses the vault. Enterprise shape: a second recipient held offline, and a
  KMS recipient (OCI Vault) once the tenancy exists so the cluster decrypts without the laptop.
- **Rotation** is not scheduled. Each secret file carries no expiry.

Both are tracked on crew; neither is solved by downloading a key to a different folder.
