# The one-hour buyer sandbox, step by step

A throwaway cluster-in-a-cluster a buyer's engineer can hold for one hour. It runs inside
the existing cluster, its control plane may not ask for more than a quarter of one processor
core, and it deletes itself on schedule. No cleanup step, no follow-up, nothing to remember.

## What launches, and what expires

One command creates a single Flux row pointing at `platform/sandbox/vcluster`. That folder
holds the sandbox control plane (vCluster, the open-source build, pinned) and a small demo
shop seeded inside it. The row carries the label `cleanup.kyverno.io/ttl: 1h`; the admission policy engine's
cleanup controller deletes the row when the hour is up, and Flux then removes everything the
row created. The one exception is the sandbox's own area of the cluster, which is marked so
the sweep skips it: the estate refuses such deletions at admission, and skipping it is what
keeps expiry from hanging. Empty, it costs nothing between runs.

## Launch (a person runs this; agents never deploy)

Command shape quoted from the vendor's own reference,
<https://fluxcd.io/flux/cmd/flux_create_kustomization/>:

```sh
flux create kustomization demo-sandbox \
  --namespace=flux-system \
  --source=GitRepository/flux-system \
  --path="./platform/sandbox/vcluster" \
  --prune=true \
  --interval=10m \
  --label=cleanup.kyverno.io/ttl=1h
```

## Verify it is up

```sh
flux get kustomizations -n flux-system demo-sandbox
kubectl -n demo-sandbox get pods
```

Expect the row `Ready True` and one running pod named `demo-sandbox-0` within about two
minutes. To hand the buyer's engineer a way in, the vendor's client tool connects with:

```sh
vcluster connect demo-sandbox -n demo-sandbox
```

## Expiry, and ending it early

Nothing to do: the hour elapses, the row disappears, the sweep runs. To end it early:

```sh
flux delete kustomization demo-sandbox -n flux-system --silent
```

To hold it longer than an hour, launch with a larger value in the label, for example
`cleanup.kyverno.io/ttl=4h`.

## Where the guarantees live

Every bound above is pinned by `tests/test_demo_sandbox_is_defined_and_expires.py`: the
open-source image, the processor ceiling, the no-storage rule, the marked survivor, and the
reaper's permission to delete exactly one extra kind of object.
