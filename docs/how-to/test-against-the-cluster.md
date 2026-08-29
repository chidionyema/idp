# Test a change against the cluster in seconds

**Who this is for:** anyone changing a service that runs on the cluster.
**What it saves:** the 13-minute build-push-deploy round trip for every try.

## The idea

Your code runs on your laptop. mirrord plugs it into a real pod on the cluster, so it sees the
pod's environment variables, its files (read-only), its DNS and the traffic the pod receives (a
copy — the real pod keeps answering). You edit, rerun, and see the result at once.

## Once

```
brew install metalbear-co/mirrord/mirrord
bin/idp-kube staging          # kubeconfig for the staging cluster
```

## Every time

```
cd hermes-agent
mirrord exec -f ../idp/.mirrord/hermes-agent.json -- python main.py
```

A config file per service lives under `.mirrord/`. Add one for a new service by copying
`hermes-agent.json` and changing `target.path` and `target.namespace`.

## The fence

The cluster admits a mirrord agent only into a namespace labelled `idp.platform/dev-loop=allowed`
(`platform/edge/dev-loop-policy.yaml`). Production namespaces never carry that label, so pointing
mirrord at production is refused by the cluster, not by a rule you have to remember. Every checked-in
config mirrors traffic and mounts the remote filesystem read-only; do not add `steal` or `fs: write`.
