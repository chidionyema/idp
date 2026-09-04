# A Flux dry-run fails on an admission webhook, and dozens of objects go not-Ready

## The shape

`bin/idp-cluster-state` reports a Kustomization that cannot dry-run, with a message naming an
admission webhook rather than anything about the manifest:

```
Kustomization flux-system/edge: ClusterPolicy/protect-namespaces dry-run failed (InternalError):
  Internal error occurred: failed calling webhook "mutate-policy.kyverno.svc":
  failed to call webhook: Post "https://kyverno-svc.kyverno.svc:443/policymutate?timeout=10s": EOF
```

Everything that depends on that Kustomization then reports `dependency '<name>' is not ready`, and
the count grows on every interval. On 2026-09-04 one such message held **45 Flux objects**: `edge`
blocked `identity`, `identity` blocked `weave-gitops`, and the founder's deploy button at
`catalogue.${ESTATE_ZONE}/deploy` drew an empty Applications list because its own Kustomization had
never finished applying. The pods were Running throughout. Only the admission endpoints were dead.

## The recovery

One run, and it touches no node, no file and no policy:

**oke-check → mode `break-glass` → playbook `webhooks-restart`.**

It restarts the Deployments in `external-secrets` and `kyverno`, waits for both rollouts, then
reconciles `edge` — the root of the blocked branch — and prints every Kustomization.

**Do not reach for `cilium-unchain`.** It contains the same two restarts, which is how this was
recovered on run 33133317589, but it also deletes the CNI configuration from every node and rolls
CoreDNS. That is a far larger blast radius than a hung webhook needs, and reaching for it out of
habit is how a five-minute recovery becomes a cluster-wide one.

## What this playbook is not

It is a mitigation, not a fix. The estate has now hit this shape twice (runs 33133317589 and
33857758131) and nothing here explains why an admission endpoint stops answering while its pod stays
healthy and its probes stay green. That question is open, and running this playbook does not close
it — record the run in the follow-up issue so the next occurrence has a third data point rather than
a third restart.
