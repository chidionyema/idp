# Demo: the health check that waited on a Deployment nobody creates

One minute. A row that has been failing for days while CI stayed green.

## Before

```bash
kubectl -n flux-system get kustomization tailscale -o jsonpath='{.status.conditions[?(@.type=="Ready")].message}'
```

```
health check failed after 10m0.026651003s: timeout waiting for:
  [Deployment/tailscale/tailscale-operator status: 'NotFound']
```

`NotFound`. Not unhealthy, not starting — **does not exist**. And guacamole plus
three other rows were waiting behind it.

## Run it

```bash
cd ~/dev/code/idp
bin/idp-compile-helm --out /tmp/compiled.json
bin/idp-healthcheck-exists --root . /tmp/compiled.json clusters/oke/platform.yaml
```

## After

```
ok    healthcheck-exists  37 checked health check(s) name an object this tree creates;
      7 ungraded (created at runtime by an operator, or a kind this gate does not compare)
```

## What to look at

**The chart says `operator`, the row said `tailscale-operator`.** The release is
named `tailscale-operator`; the chart it pins calls the Deployment `operator`. One
word of difference, and the wait could never be satisfied.

**`NotFound` is the whole diagnostic.** An object that is unhealthy reports its
status. An object that does not exist reports `NotFound`, forever. Those two
messages look similar in a status field and mean completely different things.

**The gate has a must-fail.** Point it at the old name and it refuses:

```bash
bin/idp-healthcheck-exists --root tests/fixtures/healthcheck-exists/bad \
  tests/fixtures/healthcheck-exists/bad/compiled.json \
  tests/fixtures/healthcheck-exists/bad/cluster.yaml
# FAIL  healthcheck-exists  tailscale waits on Deployment/tailscale/tailscale-operator,
#       which no release and no plain manifest in this tree declares.
# rc=1
```

A guard that passes on the tree where the defect lived is decoration. This one
failed on the first run for the right reason, and the fixture proves it still
does.

## The blind spot, named

An operator can create an object at runtime. `Deployment/healing/estate` is made
by the k8sgpt operator from a `K8sGPT` object, and no chart emits it. The gate
calls that **ungraded** and prints the count — it will not claim a proof it does
not have, and it will not refuse correct work.

But the exemption needs a custom resource in the tree naming the object. The
`tailscale-operator` Deployment had no chart, no manifest and no operator input.
Nothing saved it.
