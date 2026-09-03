# Onboarding: the OKE cluster and Flux (ADR 0004 step 3)

## Pieces

| path | what |
|---|---|
| `platform/oci/` | OpenTofu: OKE Basic cluster, one A1 worker pool (step 2) |
| `clusters/oke/platform.yaml` | Flux Kustomizations for Backstage and Chaos Mesh, sops decryption |
| `clusters/oke/catalog.yaml` | Flux `OCIRepository` pulling the estate catalog artifact |
| `platform/backstage/overlays/oke/` | base + image override + `backstage-env.sops.yaml` |
| `bin/idp-flux-bootstrap` | `flux bootstrap github` against the cluster, creates the `sops-age` secret |
| `bin/idp-catalog-push` | `flux push artifact` of the generated catalog to ghcr |

## Order

1. `bin/idp-oci-login` (identity from the vault; step 1).
2. `cd platform/oci && tofu apply` (step 2; ~15 min for OKE).
3. `bin/idp-flux-bootstrap` (this page): kubeconfig, `sops-age`, Flux.
4. `bin/idp-catalog-push` whenever `bin/catalog-gen` has run; Backstage rolls on the new digest.

## Why the catalog is an artifact, not a git file

`catalog/catalog-info.yaml` is generated from this machine's inventory and gitignored. Flux
reads git or OCI; OCI is the one that fits a generated file, so the catalog is pushed with
`flux push artifact` and pulled by `clusters/oke/catalog.yaml`.

## Known gap

The Backstage image is `idp/backstage:local`, built by compose and imported into k3d. OKE
needs it in ghcr for arm64; that build is idp#29. Until it merges the Flux `backstage`
Kustomization health check reports the Deployment as not ready.
