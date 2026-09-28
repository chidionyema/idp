# Scope the verdict signing key to the prover

crew#631 CP2. The verdict signing key `verdict-hmac-key` may be read by the prover identity
(service user `estate-ci`, group `estate-provers`) and by nobody else. Agents on a laptop act as
`estate-operators`; pods act as the worker nodes. Both grants now carry
`where target.secret.name != 'verdict-hmac-key'`.

## What the pipeline does on its own

- `platform/oci/policy/estate-operators.statements.json` narrows the operators' secret grant; the
  compartment copy lands on `oke-check` apply (`platform/oci/iam.tf`).
- `platform/oci/vault.tf` narrows the worker nodes' grant on the same apply.
- `platform/oci/provers.tf` grants `estate-provers` a read on that one secret; it waits (count 0)
  until the group exists, then lands on the next apply.
- `bin/idp-iam-policy-drift` grades the live policy against the file on every check.

## The one founder step

The tenancy copy of the operators policy and the group `estate-provers` are written only by the
tenancy owner. One command does both, quoting nothing from a console:

```
cd ~/dev/code/idp && bin/idp-oci-bootstrap
```

It signs in once in the browser, reconciles the tenancy policy to the file, creates the group and
puts `estate-ci` in it. Then dispatch `oke-check` with mode `apply` from Actions.

## Proof, both ways

From a laptop session as `estate-tofu` (what agents hold):

```
bin/idp-cloud secret get verdict-hmac-key
```

expects `NotAuthorizedOrNotFound` (exit 1). From the runner, the hourly `verdict-langfuse.yml` run
is green and its verdict verifies with `bin/idp-verdict verify`. Until the founder step, the
laptop read still succeeds and `bin/idp-iam-policy-drift` prints the scoped line as missing from
the tenancy policy with the fix.
