# Oracle Cloud tenancy

Reference for the Oracle Cloud Infrastructure (OCI) account that ADR 0004 names as the
Kubernetes target. Recorded from the tenancy page on 2026-08-24. OCIDs and the object storage
namespace are identifiers, not credentials: Oracle documents them as safe to share, and nothing
here grants access. API keys and the private key live in the sops vault
(`estate-secrets`, `OCI_*` names) and never in this repository.

| Field | Value |
|---|---|
| Tenancy name | `chidionyema` |
| Tenancy OCID | `ocid1.tenancy.oc1..aaaaaaaaz7z44jl6onnqfaxi2ieqve2lhvubao7fvz2ygadrpl5mxkna36ya` |
| Home region | `uk-london-1` (console shows `LHR`) |
| Object storage namespace | `lr7j97fk6nor` |
| Audit retention | 365 days |
| Root compartment | `chidionyema (root)` |
| Plan | Free Tier; Always Free resources only (ruling R23) |
| Always Free A1 allowance | 2 OCPU / 12 GB since 2026-06-15 (was 4 / 24); not restored after a teardown |

## What is true now (measured 2026-08-25, commands in `crew/STATE.md`)

- `oci` CLI is configured on the login machine from the sops vault (`bin/idp-oci-login`); key `estate-tofu`.
- OKE cluster `estate` is ACTIVE, v1.35.2, one A1 node Ready, in compartment `estate`. Flux delivers
  `platform/oke` from `main`. Live state is the `OKE nodes` and `OKE flux` rows of `crew/STATE.md`,
  regenerated hourly. Do not read this page for state; run
  `KUBECONFIG=~/.kube/oke-estate kubectl get nodes,kustomizations -A`.
- R26 (2026-08-25): no VM runs on the founder's Mac. Containers and k8s are here, on OKE.

## How to update this page

The console page is Profile → Tenancy at https://cloud.oracle.com. Change the table, open a
pull request. ADR 0002: documentation is code and the portal renders it.
