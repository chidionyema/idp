# Onboarding: a HelmRelease that cannot see the cluster disagree with it

`bin/idp-helmrelease-drift-coverage`, rule `helmrelease-drift-is-detectable`.

## The incident

`chaos-controller-manager` ran at **0 replicas for 18 days** while three separate
things reported everything was fine:

```
chaos-controller-manager   0/0   0   0   18d
HelmRelease/chaos-mesh     Ready  UpgradeSucceeded
helm-controller            "release in-sync with desired state"
```

Helm's own storage held `replicas: 1`. The live Deployment held `replicas: 0`:

```
HELM STORED: replicas: 1
LIVE:        replicas: 0
```

The cost was not a missing pod. chaos-mesh ships **39 admission webhooks with
`failurePolicy: Fail`**, all pointing at a Service with no endpoints, so every
object under `chaos-mesh.org/*` became uncreatable estate-wide:

```
Workflow/backstage/backstage-pod-kill-first-run dry-run failed (InternalError):
  failed calling webhook "mworkflow.kb.io": ... Post https://...:443/...: EOF
```

`EOF` from a Service with no endpoints. The chaos Kustomization reported that for
18 days and it read like a webhook bug.

## Why Flux never fixed it

**helm-controller diffs the manifest in Helm storage against the rendered chart,
and never against the cluster.** A Deployment edited after the apply is invisible
to it forever. The release is genuinely "in-sync with desired state" — Helm's
stored state — while the cluster says something else.

## The fence already existed and was switched off

`spec.driftDetection` compares Helm storage against the resources **actually in
the cluster** and re-applies the difference on every reconcile.

Measured 2026-09-13: **1 of 33 HelmReleases had it enabled.** The one that did
carries the comment explaining why — `platform/observability-collector/k8s-infra.yaml`:

> this HelmRelease still read Ready with an empty namespace and telemetry-coverage
> fell to seen=2/97. driftDetection re-applies whatever is missing on every
> reconcile

The same defect, one incident earlier. The estate learned the lesson, applied the
fence to one release, and never asked how many others needed it. **31 releases
report Ready while unable to see the cluster disagree with them.**

## What the gate does

```bash
bin/idp-helmrelease-drift-coverage
bin/idp-helmrelease-drift-coverage --json | jq .summary
bin/idp-helmrelease-drift-coverage --fail-on-blind-ready   # once the count is zero
```

```
ok    helmrelease-drift  1 of 33 HelmRelease(s) can see the cluster disagree with them;
      32 cannot, 31 of those reporting Ready
      READY  cert-manager/cert-manager  (driftDetection unset)
      READY  chaos-mesh/chaos-mesh  (driftDetection unset)
      ...
```

It **names** every blind release and does **not** fail on them by default.
Switching `driftDetection` on re-applies any difference on every reconcile, and
for a release carrying a postRenderer patch or a deliberately hand-tuned field
that is a behaviour change which has to be decided per release, not batched by a
gate. `--fail-on-blind-ready` is the flag a caller uses once the count has been
driven to zero, to keep it there.

A cluster that cannot be read exits `2` with `BLIND`, never `0` with an empty
report. `--from <file>` reads a `kubectl get -o json` document instead, which is
what makes the rule gradable offline against a fixture with no cluster.

## The fix, and the proof

```yaml
spec:
  driftDetection:
    mode: enabled
```

Applied to `platform/chaos/mesh/helmrelease.yaml`. Within one reconcile the
controller-manager came back:

```
deployment.apps/chaos-controller-manager   1/1   1   1   18d
pod/chaos-controller-manager-5db74d664-qg24b   1/1   Running   0   40s
```

and the Kustomization that had been False for 18 days met its condition:

```
$ kubectl -n flux-system wait --for=condition=Ready kustomization/chaos --timeout=280s
kustomization.kustomize.toolkit.fluxcd.io/chaos condition met
```

## Tests

```bash
python3 -m pytest tests/bdd/test_helmrelease_drift_coverage.py -q
```

The fixtures prove the rule both ways offline: a Ready release with
`driftDetection` unset is refused, and the same release with the fence on passes.

## What is not done

**The other 31 releases are still blind.** Enabling `driftDetection` on each is a
per-release decision with real blast radius, and this page names them rather than
batching a change across 31 live workloads.
