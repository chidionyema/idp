# Onboarding: writing a probe for a loopback-only container

**Door (from the UI):** Backstage → **Catalog** → *idp* → **CI**. The gate runs as a row of
`bin/idp-ci` on every pull request; you meet it as a red or green check, not as a command.

## The rule

A probe or lifecycle handler in this repository never sets `host`. Not `127.0.0.1`, not a pod
IP, not a Service name. PodSecurity `restricted` rejects the field, every namespace this estate
runs workloads in enforces `restricted`, and the rejection lands at pod *create* — long after
the manifest itself has passed review, passed admission and been reconciled by Flux.

That timing is the danger. A workload with a `host:` in it merges green and stays green. Its
Deployment reports `ReplicaFailure/FailedCreate` and `Available=False`, its old ReplicaSet keeps
serving, and nothing about the pull request or the Flux row says the new version never ran.

## What to write instead

If the container binds `0.0.0.0` or the pod IP, write an ordinary `httpGet` with a `path` and a
`port` and no `host`. The kubelet sends the probe to the pod IP already; naming it adds nothing.

If the container binds `127.0.0.1` — which is right for a sidecar nothing outside the pod should
reach — use an `exec` probe. It runs inside the container, so loopback there is the process you
are probing:

```yaml
readinessProbe:
  exec:
    command: ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4010/health/liveliness', timeout=2)"]
```

Do not widen the bind to make an `httpGet` probe work. The loopback bind is R20 and, for a
lifeboat, it is the feature: a router you reach without crossing a network is the one that still
answers when the network is what broke.

## When the gate fires

It names the file, the workload, the container and the exact field. Replace that probe with an
`exec` one, or delete the `host` line if the container was never loopback-only to begin with.
Run `bin/idp-probe-host` with no arguments to check the whole tree before you push.
