# platform/oci

ADR 0004 step 2: one OKE Basic cluster and one Always Free A1 worker, built by Oracle's own
[terraform-oci-oke](https://github.com/oracle-terraform-modules/terraform-oci-oke) module.

```
tofu -chdir=platform/oci init      # downloads the oci provider and the module; no credentials
tofu -chdir=platform/oci validate  # the CI receipt (bin/idp-ci row `oci`)
tofu -chdir=platform/oci plan      # needs ~/.oci/config; the receipt for every change
```

`terraform.tfvars` is gitignored: it holds the tenancy and compartment OCIDs and the SSH public
key, all identifiers. The API private key lives in the sops vault and reaches `~/.oci/config`
through `bin/idp-oci-login`. Nothing in this directory is a secret and nothing names a machine.

Sizing is pinned by validation rules to the Always Free allowance (2 OCPU / 12 GB). Raising it
is paid infrastructure and refused by ruling R14.
