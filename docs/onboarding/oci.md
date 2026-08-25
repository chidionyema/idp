# Onboarding: Oracle identity (ADR 0004 step 1)

## What it is

`bin/idp-oci-bootstrap` builds the least-privilege identity OpenTofu uses for `platform/oci`:
compartment `estate`, group `estate-operators`, user `estate-tofu`, one policy scoped to that
compartment. The API key pair is generated on this machine; only the public half is registered
with Oracle, the private half goes into the sops vault (`secrets/<env>/OCI_API_PRIVATE_KEY.yaml`)
through `scripts/secret-add` on stdin. No key is downloaded from the console and none is kept on
the founder's admin user.

`bin/idp-oci-login` is the read side: it renders `~/.oci/config` (mode 600) and
`platform/oci/terraform.tfvars` from the vault and proves the identity with
`oci iam region-subscription list`. `bin/idp-verify` calls it as the `oci` drill row.

## Vault entries

| key | written by | secret |
|---|---|---|
| `OCI_REGION`, `OCI_TENANCY_OCID`, `OCI_TENANCY_NAME` | hand, once | no |
| `OCI_COMPARTMENT_OCID`, `OCI_USER_OCID`, `OCI_FINGERPRINT` | bootstrap | no |
| `OCI_API_PRIVATE_KEY` | bootstrap | yes, never printed |

## Why not `oci setup config`

It is interactive, writes the private key unvaulted under `~/.oci`, and registers it on whichever
user is logged in, which is the tenancy owner. A buyer's engineer would flag all three.

## Rotation

`bin/idp-oci-bootstrap --rotate` registers a new key and replaces the vault entry; delete the old
fingerprint in the console afterwards. Oracle allows three keys per user.
