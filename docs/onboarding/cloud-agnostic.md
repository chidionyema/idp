# Onboarding: keeping the platform cloud-agnostic

Founder ruling R36 (2026-08-25, crew#250): the platform must not know or care who owns the servers it runs on. This page is what that means when you add or change a manifest.

## Where a cloud may be named

- `platform/oci/`: the raw compute provisioner (OpenTofu). It creates the cluster and the vault and nothing else.
- `platform/secret-store/store.yaml`: the one ClusterSecretStore, `estate-vault`. To move vaults, change the `provider:` block here and nothing else; every ExternalSecret refers to `estate-vault`.
- `clusters/<cluster>/`: the per-cluster Flux rows. A cloud load balancer shape, a region, an instance principal: these are patched in here, never written into `platform/`.

## What the gate refuses

`bin/cloud-agnostic-gate` scans `platform/**` for provider annotations (`oci-load-balancer-*`, `service.beta.kubernetes.io/aws-*`, `alb.ingress.kubernetes.io`, `cloud.google.com/`), provider-only services (DynamoDB, Pub/Sub, Object Storage APIs) and ExternalSecrets provider blocks outside the store. Comment lines are not counted. It prints every offending line and exits 1; `bin/idp-ci` runs it on every pull request after proving it on `tests/fixtures/cloud-agnostic/{good,bad}`.

## How to add something that needs a cloud setting

Write the manifest provider-free in `platform/`, then add a `patches:` entry to the Flux Kustomization in `clusters/<cluster>/` that carries the provider-specific fields. `clusters/oke/edge.yaml` is the worked example: it patches the four OKE load-balancer annotations onto the Traefik HelmRelease that `platform/edge/traefik.yaml` defines without them. Data must use an S3-compatible API or the Postgres wire protocol; ingress is Cloudflare in front of the in-cluster Traefik with cert-manager, so a DNS change is the whole traffic switch.
