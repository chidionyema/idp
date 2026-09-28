# Demo: the field that lands green and never runs

**Door (from the UI):** Backstage → **Catalog** → *idp* → **CI** — the gate is a row of
`bin/idp-ci`, so its verdict is a check on every pull request. Nothing to press.

Run the gate on the shape that took Otto's three homes out, and on the repository as it stands.

```
$ bin/idp-probe-host tests/fixtures/probe-host/bad.yaml
tests/fixtures/probe-host/bad.yaml: otto-gateway container 'otto-brain' sets readinessProbe.httpGet.host: 127.0.0.1 -- PodSecurity restricted refuses the pod at create, so the workload lands green and never runs; use an exec probe instead
FAIL  idp-probe-host: 1 probe or lifecycle host(s) a pod create would refuse
$ bin/idp-probe-host
PASS  idp-probe-host: no probe or lifecycle handler names a host
```

The bad fixture is the `otto-brain` sidecar exactly as it merged on 2026-09-10. It binds
`127.0.0.1` deliberately: it is Otto's lifeboat router, and the whole point is that reaching it
crosses no network, no Service and no CNI. Someone then noticed the kubelet probes the pod IP,
not loopback, and pointed the probe at loopback with `host: 127.0.0.1` to close the gap.

That does not close the gap, and it is worse than not working. The kubelet is not inside the
pod's network namespace, so the request would have left the node's loopback rather than the
pod's. And PodSecurity `restricted` — which every namespace in this estate enforces — forbids the
`host` field outright, because it lets a pod aim a kubelet-issued request wherever it likes.

The refusal happens at pod **create**, not at apply. So the manifest passed every gate, Flux
reconciled it, the Kustomization went Ready, and the branch read as landed — while the
ReplicaSet failed silently, over and over:

```
ReplicaFailure True FailedCreate | pods "otto-gateway-77776744bb-4dtvz" is forbidden:
violates PodSecurity "restricted:latest": probe or lifecycle host (container "otto-brain"
uses probe or lifecycle host "127.0.0.1")
```

The old single-home pod kept answering the whole time, so no alert fired and no page went dark.
The founder's assistant simply did not have the fallback he had been told it had, for hours.

The good fixture is the fix: an `exec` probe. It runs inside the container, where `127.0.0.1`
really is the sidecar, and it needs no `host` field for anything to refuse. Its second document
is the ordinary case the gate must leave alone — a container that binds the pod IP and probes it
with no `host` at all.
