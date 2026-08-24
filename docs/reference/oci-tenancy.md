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

## What is not yet true

- No `oci` CLI is configured on any machine in the estate, and no API key exists.
- Nothing is provisioned. R23: local `idp-verify` goes green before any OCI resource is created.
- A1 (Ampere) capacity in `uk-london-1` has not been checked; that check is step 1 of ADR 0004.

## How to update this page

The console page is Profile → Tenancy at https://cloud.oracle.com. Change the table, open a
pull request. ADR 0002: documentation is code and the portal renders it.
