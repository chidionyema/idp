# The deploy button

Founder, 2026-09-04: "install weaveops ... so i can do the deploynents nyself", and
"WE ARE STRCTILY GITOPS". His consultation post on the same subject is recorded verbatim at
`~/.claude/docs/founder/2026-09-04T0706Z-hello-i-see-you-i-agree-taking-the-f6729f06.md`.

## What went in

Weave GitOps, the Flux project's own dashboard. The vendor's chart, pinned: `weave-gitops`
4.0.36, application version `v0.38.0`, from `oci://ghcr.io/weaveworks/charts`. Read from the
registry on 2026-09-04; the chart's own config blob says
`{"name":"weave-gitops","version":"4.0.36","appVersion":"v0.38.0"}`.

It lives in `platform/weave-gitops/` and is applied by the `weave-gitops` row in
`clusters/oke/platform.yaml`, like every other layer.

## Where it answers

<https://catalogue.mumchimp.com/deploy>

There is no password and there will never be one. The server runs with
`--insecure-no-authentication-user=founder`, which the vendor documents as the mode for running
behind an auth proxy (`website/docs/guides/anonymous-access.mdx`: "It is designed to be used with
other external authentication systems like auth proxies"). The proxy is the estate's own: the
HTTPRoute attaches `login-forward-auth`, so an unauthenticated request is answered by oauth2-proxy
and never reaches the pod. That is decision 0003 — one login, at the gateway, never in an app.

It is served under `/deploy` rather than on its own hostname because the server supports
`--route-prefix` (`website/docs/guides/run-ui-subpath.mdx`), so no new gateway listener and no new
certificate were needed. The HTTPRoute deliberately does **not** strip the prefix: the server
expects to see it and writes its own asset URLs under it.

## Why it cannot fall out of step with the automation

Nothing about this is a second control plane, and the estate's GitOps discipline is untouched.

1. **It holds no state.** It reads the same Flux objects the controllers read, in the same
   cluster. When it reports a revision, that is the revision Flux itself recorded after applying.
2. **It cannot write a workload.** Its permissions (`platform/weave-gitops/rbac.yaml`) allow
   `get/list/watch` on what it draws, and `patch` on Flux's own resources and nothing else. The
   Reconcile button writes the annotation `reconcile.fluxcd.io/requestedAt`; the Suspend button
   writes `spec.suspend`. An image, a replica count or a manifest can only change by a commit.
3. **A pause heals itself.** Every layer's Flux Kustomization is itself declared in
   `clusters/oke/platform.yaml` and re-applied by the parent on a 10-minute interval, so a
   suspend set in the UI is put back automatically. A pause is a pause, not a silent decision.
4. **The cluster still refuses people.** `platform/edge/flux-only-writes.yaml` rejects every
   `ocid1.user.*` principal on create, update and delete. The dashboard's ServiceAccount presents
   as `system:serviceaccount:*`, which is why it works at all — and why nobody's laptop does.

`kubectl apply`, `flux reconcile` from a terminal and `kubectl port-forward` are all absent by
design. The install is a merged pull request; the door is a URL behind the one login.

## What it does not read

Secrets. `rbac.viewSecretsEnabled` is set to `false`, against the chart's default of `true`. A
deploy button has no reason to hold a credential (LAW 21).

## The honest caveat

Weaveworks, the company, shut down in 2024 and Weave GitOps is community-maintained at
Apache-2.0, last release `v0.38.0`. It does one narrow job against Flux's stable API, holds no
state, and can be removed by deleting `platform/weave-gitops/` and its row — no workload is
touched by its removal.

Gimlet's Capacitor was the first choice and was rejected on evidence: the repository has moved to
Capacitor Next, whose chart requires a commercial licence (`LICENSE_KEY: "message laszlo at
gimlet.io"` in its published values), and the still-free `v0.4.8` image serves absolute asset
paths (`/assets/index-*.js`, read out of the image on 2026-09-04), so it cannot share the
catalogue hostname without a new gateway listener in another repository.
