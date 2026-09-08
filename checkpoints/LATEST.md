# CHECKPOINT — 2026-09-08, crew#920 Otto enterprise readiness

## RESUME HERE

**The estate is blocked on one founder action, pinned to Telegram (message_id 43319).**

Flux is deadlocked estate-wide. 0 of 80 Kustomizations Ready: 15 ArtifactFailed, 61
DependencyNotReady, 4 Progressing. Every artifact fetch fails with
`dial tcp 10.96.202.29:80: i/o timeout` against `source-controller.flux-system.svc.cluster.local.`

### The measurement (two angles, LAW 15)

- `helm-controller` pod is on node `10.0.148.221`, the same node as `source-controller`
  (`10.244.117.185`). 31 of 32 HelmReleases are Ready. Its fetches from that ClusterIP work.
- `kustomize-controller` pod is on node `10.0.159.197` (`10.244.3.87`). 0 of 80 Kustomizations
  Ready, every fetch timing out against the same ClusterIP, same port 80.

Same service, same artifact, only the node differs. Every GitRepository and OCIRepository is
Ready with a stored artifact, so the sources are fine and the path to them is not.

### Cause, and what was eliminated

Two CNIs hold `10.244.0.0/16` at once: `kube-flannel-ds` 2/2 Running since 2026-08-25, and
Calico since 38h ago. Seven pods still carry no `cni.projectcalico.org/podIP`:
`identity/oauth2-proxy`, `estate-db/cnpg-controller`, `observability/superset`, and four
short-lived `receipt-*` jobs.

Eliminated: Felix is looping normally with no errors; both flux pods are on Calico; VXLAN is up
with tunnel addresses on both nodes; `flux-system/allow-egress` permits all same-namespace
traffic on all ports; no Calico GlobalNetworkPolicies exist; both kube-proxy pods have been
quiet and healthy since 2026-08-27.

Not measured: that the double CNI is the reason. This session holds `agent-reader` and cannot
create a pod, exec into one, or restart a controller, so the probe that would settle it could
not run.

### The staged action

```
kubectl -n kube-system delete daemonset kube-flannel-ds
kubectl -n identity rollout restart deploy/oauth2-proxy
kubectl -n estate-db rollout restart deploy/cnpg-controller
kubectl -n observability rollout restart deploy/superset
```

Confirm with `kubectl get kustomization -A | grep -c True`.

### What is queued behind it

1. `chi-signoz-clickhouse-cluster-0-0-0` is crash-looping at 31 restarts on the old config.
   `d0816557` (PR #2535, merged, CI green) fixes it and is waiting on Flux.
2. `signoz-clickhouse` then gets endpoints, and langfuse's database job stops timing out.
3. observability catches up from `a38150d4`.
4. langfuse-web and langfuse-worker drop 1000m -> 500m each (#2429). That returned CPU is what
   lets the queue on two nodes at 91% and 95% requested finally schedule.
5. Otto's verify lane leaves gemini (#2518).

## IN FLIGHT

Worktree `scratchpad/wt-flux`, branch `fix/flux-control-plane-colocates`: a podAffinity patch in
`clusters/oke/flux-system/kustomization.yaml` pinning kustomize-controller to
source-controller's node, so the control plane never again deadlocks on the overlay it is
responsible for repairing. It takes effect only after Flux is applying again.

## STILL OPEN, crew#920

- Ephemeral/shadow cluster, issue #2471 under umbrella #2470 (vcluster). Not started.
- JIT break-glass broker proved end to end with one real tap on the founder's phone.
- Ten scheduled jobs folded onto the one scheduler. Blocked: another session holds that repo.
- The capability board graded.

## MERGED THIS SESSION

- #2535 -> `d0816557` — ClickHouse system-log TTL inside the engine string, plus the LAW 45 gate
  `bin/idp-clickhouse-system-log-ttl` and its fixture pair, registered in `rules.yaml`.
- #2527 — otto-golden rehearsal, CI green.
