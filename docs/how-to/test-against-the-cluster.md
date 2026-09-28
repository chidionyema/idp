# Test a change against the cluster in seconds

**Who this is for:** anyone changing a service that runs on the cluster.
**What it saves:** the 13-minute build-push-deploy round trip for every try.

## The idea

Your code runs on your laptop. mirrord plugs it into the cluster's `staging` namespace
(`platform/staging`), so it sees the cluster's DNS and every service by name; when staging holds a
copy of your service it also sees that pod's environment variables, its files (read-only) and a
copy of the traffic the pod receives (the real pod keeps answering). You edit, rerun, and see the
result at once.

## Once

```
brew install metalbear-co/mirrord/mirrord
```

## Every time

```
cd hermes-agent
../idp/bin/idp-dev hermes-agent -- python main.py
```

`bin/idp-dev` takes the kubeconfig from `bin/idp-kube` (never a hand-set context), looks for
`deployment/<service>` in staging, and runs mirrord with `.mirrord/<service>.json` retargeted at
staging when it is there, or `.mirrord/staging.json` (targetless) when it is not. Add a config for
a new service by copying `hermes-agent.json` and changing `target.path`.

## The fence

The cluster admits a mirrord agent only into a namespace labelled `idp.platform/dev-loop=allowed`
(`platform/edge/dev-loop-policy.yaml`); `staging` is the one that carries it. Production namespaces
never do, so pointing mirrord at production is refused by the cluster, not by a rule you have to
remember. Every checked-in config mirrors traffic and mounts the remote filesystem read-only; do
not add `steal` or `fs: write`. Staging is capped by a ResourceQuota at the floor the feature
register prices (`bin/idp-features plan`), so nothing tried there can crowd production.
