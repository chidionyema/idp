# Onboarding: Otto staging

This page is for anyone picking up work on the new Otto agent platform's deployment, or reviewing
it for the first time. It names where the pieces live and what each one is responsible for.

## Where the manifests live
`platform/otto-staging/` in the `idp` repository, mirroring the shape every other platform layer
uses (`platform/hermes-agent/` is the closest sibling, and the one this lane copied its pattern
from):

- `namespace.yaml` — the area of the cluster itself, carrying the annotation that stops Flux, and the
  cluster's own admission policy, from ever pruning it away.
- `quota.yaml` — a `ResourceQuota` and `LimitRange` sized for one small pod; a runaway process here
  cannot starve the node.
- `network-policy.yaml` — a both-ways default-deny `NetworkPolicy`, plus four narrow holes: DNS,
  ingress from the shared edge gateway on the webhook port, egress to the estate's trace
  collector, and egress to the public internet on port 443 only (Telegram's own API has no fixed
  address range to name instead).
- `telegram-secret.yaml` — the vault-fed secret naming the vault key the bot token lives in. The
  Kubernetes Secret it produces is mounted as a file, never as a pod environment variable, because
  the cluster's own admission policy refuses the latter.
- `config.yaml` — a `ConfigMap` for the one file the new process reads its own configuration from.
- `deployment.yaml` — the pod itself: one replica, the same container image the production
  Architect gateway runs, only the command different.
- `httproute.yaml` — the two public paths this lane owns on the shared `otto.<zone>` host.
- `kustomization.yaml` — the list above, plus the pinned image tag.

## Where the deployment is wired in
`clusters/oke/platform.yaml` carries the Flux `Kustomization` row named `otto-staging`, listed
right after `hermes-agent`'s own row. It depends on `scheduling`, `secret-store` and `edge` — the
same dependencies `mcp`'s row declares, because like `mcp` this lane has its own route on the
shared Gateway and needs it to exist first.

## Where the catalog entity comes from
`bin/catalog-platform` reads every Flux `Kustomization` under `clusters/<cluster>/` and emits one
Backstage entity per row, using a plain-English name and description named in that script's own
`LAYERS` table. This lane's row (`"otto-staging"`) sits next to `"hermes-agent"`'s own row in that
table; running `bin/catalog-platform` regenerates `backstage/platform/catalog-info.yaml` from it —
never hand-edit that generated file.

## What still needs a decision, honestly
The new process's own configuration schema (what `config.yaml` should actually carry, beyond the
one fact this lane already commits to — the webhook and health paths) had not landed upstream as
of this branch; `config.yaml` carries a placeholder and says so in its own comment. Update that
file, not this one, once the schema exists.
