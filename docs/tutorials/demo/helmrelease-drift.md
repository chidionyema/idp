# Demo: three things said everything was fine, and the controller had not run for 18 days

One minute. The estate's most expensive silence.

## Before

```
$ kubectl -n chaos-mesh get deploy chaos-controller-manager
NAME                        READY   UP-TO-DATE   AVAILABLE   AGE
chaos-controller-manager    0/0     0            0           18d
```

Three things said this was fine:

```
HelmRelease/chaos-mesh    Ready   UpgradeSucceeded
helm-controller           "release in-sync with desired state"
HELM STORED: replicas: 1
```

And the cluster said:

```
LIVE: replicas: 0
```

## Run it

```bash
cd ~/dev/code/idp
bin/idp-helmrelease-drift-coverage
```

## After

```
ok    helmrelease-drift  1 of 33 HelmRelease(s) can see the cluster disagree with them;
      32 cannot, 31 of those reporting Ready
      READY  cert-manager/cert-manager  (driftDetection unset)
      READY  chaos-mesh/chaos-mesh  (driftDetection unset)
      READY  dagster/dagster  (driftDetection unset)
      ...
```

## What to look at

**The cost was not the missing pod.** chaos-mesh ships 39 webhooks with
`failurePolicy: Fail`, all pointing at a Service with no endpoints. So every
object under `chaos-mesh.org/*` became uncreatable:

```
Workflow/backstage/backstage-pod-kill-first-run dry-run failed (InternalError):
  failed calling webhook "mworkflow.kb.io": ... EOF
```

`EOF` is what a Service with no endpoints answers. That message read like a
webhook bug for 18 days.

**Flux was telling the truth.** `"release in-sync with desired state"` is a
correct statement about *Helm's stored state*. helm-controller never compares
against the cluster, so a Deployment edited after the apply is invisible to it
forever. Both statements are true and the estate was still broken.

**The fence existed for 1 of 33 releases.** `driftDetection` is the mechanism for
exactly this. The one release using it carries the comment explaining why — the
same defect happened once before, the fence was applied to that one release, and
nobody asked how many others needed it.

## Prove the fix

```bash
kubectl -n flux-system wait --for=condition=Ready kustomization/chaos --timeout=280s
```

```
kustomization.kustomize.toolkit.fluxcd.io/chaos condition met
```

Then:

```
$ kubectl -n chaos-mesh get deploy chaos-controller-manager
NAME                        READY   UP-TO-DATE   AVAILABLE
chaos-controller-manager    1/1     1            1
```

**Better: find the next one before it costs you.** The gate names all 31 blind
releases. That list is the work.
