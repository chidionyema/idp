# Vendor-independence audit — swap paths per vendor

Founder principle 2026-09-17: **"we must be able to run vendor independent"**. A single vendor's
outage, price hike, deprecation, or unilateral policy change must never be able to trap the
estate. Every vendor row below names one alternative that the estate is engineered to accept,
the concrete steps to swap, and the blast radius if the vendor disappeared tomorrow.

The claim "vendor-independent" is theatre until every row here MEETS. `bin/idp-vendor-audit`
(to be written) will grade this file against the code the same way `bin/idp-rules render-agents-md`
grades AGENTS.md against `rules.yaml`.

## Format

Each row: **what** the estate uses it for · **why here today** · **swap path** · **effort** ·
**blast radius on sudden loss**.

---

## OCI (Oracle Cloud Infrastructure)

- **What:** OKE (managed Kubernetes), IAM (session-token exchange from GitHub OIDC), Object
  Storage (state receipts), Vault (KMS), Container Instances (occasional).
- **Why here today:** Free-tier envelope covered the estate's compute + storage cost for
  eighteen months; OIDC-to-session-token exchange lets GitHub Actions runners act as the estate
  without a static credential (ADR 0004).
- **Swap path:** AWS EKS + IAM Roles for Service Accounts (IRSA) is the closest parallel;
  Google GKE + Workload Identity is second. `bin/idp-cloud` is the only door — replacing its
  three `oci ce cluster …` calls with `aws eks describe-cluster --query …` or
  `gcloud container clusters get-credentials …` is where the swap lives. Terraform files under
  `platform/terraform/oci/*` would need EKS or GKE peers.
- **Effort:** ~2 sprints. Not a script; a migration.
- **Blast radius on loss:** Total cluster loss. Object-storage receipts recoverable from Flux
  git state. IAM identity recoverable from `bin/idp-oci-bootstrap` output tracked in vault.

## GitHub (repo hosting + Actions + OIDC + App + GHCR)

- **What:** Git remote for 45 repos, CI/CD runners, OIDC identity provider, GitHub App for
  installation-scoped tokens, GHCR for container images.
- **Why here today:** OIDC identity provider integration with OCI already wired; App-based
  identity per lane (`platform/github-app/lanes.json`) is the estate's identity model.
- **Swap path:** GitLab (self-hosted or SaaS) is the drop-in for repo + CI + OIDC + registry.
  Gitea + Woodpecker is the self-hosted variant. The estate's Actions workflows would need
  translation to `.gitlab-ci.yml` shape; OIDC audience contract stays the same; GHCR images
  can be mirrored to any OCI registry (`bin/build-image` is registry-agnostic today per R24).
  The GitHub App equivalent on GitLab is a project access token per lane.
- **Effort:** ~3 sprints. Repo mirror + workflow rewrite is the bulk.
- **Blast radius on loss:** Source history preserved everywhere it is cloned; CI stops
  immediately; GHCR images preserved via last successful `docker pull` on OKE nodes for their
  lifetime but no new builds.

## Cloudflare (DNS + Tunnels + WAF)

- **What:** Public DNS for `chidionyema.tech` and vendor domains; Cloudflare Tunnels for
  founder-only surfaces (Backstage portal, Grafana); WAF on public API surface.
- **Why here today:** Free tier covered the cost; Tunnels replaced the need to expose a public
  ingress load balancer for founder-only surfaces; API tokens are already in the vault.
- **Swap path:** Route 53 + AWS Global Accelerator for DNS; Tailscale Funnel or a WireGuard
  bastion for private-surface exposure; ModSecurity or AWS WAF for L7 protection. DNS records
  are declared under `platform/cloudflare/*.yaml` — a swap is a `terraform mv` per record.
- **Effort:** ~1 sprint. DNS migration is the risk.
- **Blast radius on loss:** Public DNS goes stale within TTL (300s default); founder surfaces
  cut off; L7 rules re-implemented at Kubernetes ingress.

## Tailscale (mesh)

- **What:** Cluster-to-founder-Mac SSH (Hermes agent gateway), founder phone → private
  services, laptop dev-time cluster reachability.
- **Why here today:** Zero-trust mesh with SSO-tied ACLs; free tier for personal use.
- **Swap path:** Headscale (self-hosted Tailscale-compatible) is a byte-compatible drop-in.
  WireGuard raw is the second option (loses SSO integration). ACLs in
  `platform/tailscale/policy.hujson` are portable to Headscale as-is.
- **Effort:** ~2 days for Headscale, ~1 week for raw WireGuard.
- **Blast radius on loss:** Hermes agent cannot reach founder's Mac; broken-mac salvage path
  breaks; phone cannot reach private surfaces. Cluster-internal networking unaffected.

## Bitwarden Secrets Manager (human vault)

- **What:** The single door for human-generated secrets (vendor API keys, console credentials)
  that a person originated. ADR 0017 governs.
- **Why here today:** SOC 2 Type II, open-source client, per-secret access policies.
- **Swap path:** HashiCorp Vault (OSS or Cloud) is the drop-in for scoped secret storage.
  1Password Business is the SaaS peer. `bin/idp-human-vault-probe` is the door — replacing
  its `bw` calls with `vault kv get …` is the swap.
- **Effort:** ~1 sprint.
- **Blast radius on loss:** Human-originated secrets need re-provisioning from vendor consoles.
  Estate-born secrets (sops-age vault) are untouched.

## GHCR (container registry)

- **What:** Every image the estate builds lands here (per R24, amd64+arm64).
- **Why here today:** No cost while public; tight OIDC integration with GitHub Actions runner.
- **Swap path:** Quay.io, Docker Hub, Harbor (self-hosted), GAR (Google Artifact Registry), or
  ECR. `bin/build-image` accepts `--registry` today (verify claim — this may need a code change).
  Kubernetes pull secrets under `platform/*/imagepull-*.yaml` would need re-issuance.
- **Effort:** ~3 days.
- **Blast radius on loss:** All existing images still on OKE nodes for their cache TTL; new
  deploys blocked until the swap lands.

---

## What is deliberately not in this file

- **age + sops** — both open-source, no server, no vendor. Not a swap target.
- **Homebrew** — dev-time convenience only; Level 0 of `bin/idp-workstation-bootstrap` already
  spans apt/dnf/apk/brew.
- **Local container runtimes** — AGENTS.md 2026-09-17 mandate says the estate does not depend
  on any specific one. Any OCI-compliant runtime works.

## Next steps

- [ ] `bin/idp-vendor-audit` — read this file, grade every claim against a probe (e.g. does
      `bin/build-image` actually accept `--registry`?), refuse on drift.
- [ ] Per-row expansion when a swap becomes concrete work.
- [ ] Wire into `bin/idp-ci` as a `WARN` when a swap-path claim is undocumented for a vendor
      newly appearing in `rules.yaml` or `platform/*.yaml`.
