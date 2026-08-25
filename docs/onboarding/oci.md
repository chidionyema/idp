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

## Runbook, as run on 2026-08-25

What the founder does: sign in once in the browser tab that opens. Nothing else.

What the script does, in order, and what each line looks like:

```
login   browser opens once; sign in as the tenancy owner (token lives 1 hour)
iam     compartment estate
iam     group estate-operators
iam     user estate-tofu
iam     policy estate-operators-manage-estate
vault   OCI_API_PRIVATE_KEY written
vault   OCI_FINGERPRINT written
key     registered on estate-tofu, fingerprint 9b:1d:3a...
vault   OCI_USER_OCID written
vault   OCI_COMPARTMENT_OCID written
vault   committed and pushed
done    next: bin/idp-oci-login
```

Then `bin/idp-oci-login` renders `~/.oci/config` and proves the key. A key uploaded seconds
ago answers 401 for several minutes; login retries every 30 s for up to 8 minutes and prints
`wait oci 401 after a fresh key upload` while it does.

Two things broke on the first run and are now guarded:

1. Oracle identity domains refuse a user without a primary email
   (`error.identity.user.primaryEmailNotSpecified`). The vault now carries
   `OCI_SERVICE_USER_EMAIL`; the script refuses to start without it.
2. The script printed `iam user estate-tofu` with an empty OCID and went on to upload the key
   to user "". `ensure` now fails on an empty OCID and the run stops there.

If the token expires mid-run, re-run the script: it reuses a live session, otherwise opens
the browser again, and every IAM step is idempotent.
