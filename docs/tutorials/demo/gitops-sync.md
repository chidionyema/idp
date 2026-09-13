# Demo: the drift that names the pull request that caused it

Two minutes. One command, and the estate's own drift comes back with a name on it.

Spec: `docs/specs/2026-09-13-gitops-sync-engine.md`.

## Before

Flux knows everything about a drifting object except who broke it:

```
$ kubectl get kustomizations -A
flux-system/temporal   False   health check failed after 20m0.03s: timeout waiting for: [HelmRelease/temporal]
```

Twenty minutes. The cluster is telling you, and the number is real, and there is
nothing in it that tells you which change to look at.

## Run it

```bash
cd ~/dev/code/idp
bin/idp-gitops-drift
```

## After

```
ok    gitops-drift 63 drift(s): 63 attributed to a pull request, 0 unattributed
      flux-system/temporal (Kustomization) -> #3223: health check failed after 20m0.036186674s: timeout waiting for: [HelmRelease/temporal/temporal statu
      commerce/lago (HelmRelease) -> #3268: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled re
      flux-system/scheduling (Kustomization) -> #3223: dependency 'flux-system/edge' is not ready
```

Sixty-three is the honest number, and it is much larger than the six a hand
reading found. A Kustomization waiting on an unready dependency, or one mid
reconcile, is also not reconciled — and reading only `Ready: False` while
grepping by hand misses all of them.

## What to look at

**Every drift now carries a pull request.** `#3223` is the change that last
touched the file owning `flux-system/temporal`. Whoever merged it can be told, and
can fix it.

**The reason is Flux's own words.** Not a summary, not a severity this tool
invented. `health check failed after 20m0.036186674s` is exactly what the
Kustomization's `Ready` condition says.

**The fingerprint ignores time.** Run it twice in a row and the set is identical
— the same drifts get the same fingerprints, so the sensor reports the situation
once however long it burns rather than every five minutes for a day.

## Prove the attribution is real

Pick any drift's pull request and check it against the file the tool named:

```bash
bin/idp-gitops-drift --json | jq -r '.drifts[] | "\(.object) \(.file) \(.pull_request)"' | head -3
git log -1 --format='%h %s' origin/main -- platform/observability/langfuse.yaml
```

The pull request in the second line is the one the tool reported in the first. If
it is not, the tool is wrong and that is a defect worth filing.

## The blind case, which is the point

```bash
PATH=/usr/bin bin/idp-gitops-drift ; echo "exit=$?"
```

```
BLIND gitops-drift: kubectl is not installed, so nothing was read
exit=2
```

Exit `2`, not `0`. A tool that cannot read the cluster and a cluster with nothing
wrong must never print the same thing. That distinction is the whole reason
`bin/idp-compile-helm` exists in its current shape: its first version reported
eleven failed charts as an empty estate and exited `0`.
