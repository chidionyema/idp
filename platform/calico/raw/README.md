# Road B — raw operatorless calico-node (kubernetes datastore)

The estate's network policy enforcement layer (crew#839), as a **plain operatorless Calico** that
replaces the `tigera-operator` HelmRelease route which wedged on this cluster. See
`platform/calico/calico.yaml` (the operator deck being retired) header for the full Road B
rationale, and `bin/idp-oke-break-glass` `pb_tigera_reset` for the teardown guard.

## Provenance
Byte-source for the manifests in this directory: **Calico v3.32.2 `manifests/calico.yaml`**
(`https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/calico.yaml`). It is
the canonical non-operator install: ServiceAccounts, ConfigMap `calico-config`, the calico-node
DaemonSet, calico-kube-controllers Deployment, and the ClusterRoles/Bindings the two accounts
use. The ~7,000-line CRD block in that file is intentionally **not** vendored here: the
`crd.projectcalico.org` kinds already exist on the cluster from the prior operator install and
Calico OSS registers/updates them itself on first boot.

Image tags are pinned to the same **v3.32.2** the operator deck used, so CRDs and node agree.

## Deltas from canonical `manifests/calico.yaml`
Capital-D decisions Road B fixed for this exact OKE cluster (all documented in the operator-deck
header), applied verbatim here:

| Canonical | This manifest | Why |
|---|---|---|
| `IP: autodetect` (firstFound) | `IP_AUTODETECTION_METHOD: interface=enp0s6` | Phantom-underlay fix. Live operator node `.221` autodetected `cilium_host` 10.0.1.218/32 and never peered cross-node; the real host NIC is `enp0s6` (10.0.148.221/20, 10.0.159.197/20) on both nodes. |
| `CALICO_IPV4POOL_IPIP: Always` | `CALICO_IPV4POOL_IPIP: None` | Road B is VXLAN-only, no IPIP. |
| `CALICO_IPV4POOL_VXLAN: Never` | `CALICO_IPV4POOL_VXLAN: Always` + `FELIX_VXLANENABLED: true` | VXLAN (same encapsulation flannel runs today). `CALICO_NETWORKING_BACKEND` stays `bird` (no literal "vxlan" string exists in Calico OSS); with no BGP peers + VXLAN pools, bird is the harmless control backend. |
| pool unset | `CALICO_IPV4POOL_CIDR: 10.244.0.0/16` | Must match the CIDR flannel uses today, or every running pod's address strands. |
| IPv6 on | `FELIX_IPV6SUPPORT: false`, `CALICO_IPV6POOL_VXLAN: Never` | Cluster is IPv4-only (operator deck default). |
| typha present (operator) | `typha_service_name: "none"` | 2-node estate; operatorless runs no typha. |
| namespace `calico-system` / `tigera-operator` | `kube-system` | Non-operator installs live in kube-system. |
| ClusterRoles `calico-node`, `calico-cni-plugin`, `calico-kube-controllers`, `calico-tier-getter` | the same names under an `estate-` prefix | A ClusterRole has no namespace, so moving the ServiceAccounts to `kube-system` did not separate the cluster-scoped RBAC from the operator's. This row used to claim the unprefixed names "cannot collide"; they did. See below. |

Kept byte-faithful to the reviewed vendor reference: the `upgrade-ipam`, `install-cni`, and
`ebpf-bootstrap` init containers (only `install-cni` is load-bearing in iptables mode; the other
two are no-ops and kept for review fidelity), the volume set, probes, tolerations, and
priority classes.

## Wiring — deliberately NOT done in this PR
This directory is **review-only**. The `calico` Flux Kustomization in
`clusters/oke/platform.yaml` stays `suspend: true`. Landing raw calico-node is a separate
cluster-control change: un-suspend + re-point that row here, tear the operator deck out
(`bin/idp-oke-break-glass tigera-reset` guards on flannel still routing 2/2 + the row suspended),
let raw calico-node come up under flannel, prove cross-node traffic, then disable the OCI flannel
add-on and purge flannel artifacts. That ordering is why this PR deliberately touches neither
the operator deck nor the Flux row.

## Why the cluster-scoped RBAC carries an `estate-` prefix

The operator route left two ServiceAccounts in `calico-system` holding the finalizer
`tigera.io/cni-protector`. The operator adds that finalizer so the CNI binaries are not pulled
out from under running pods mid-upgrade, and the operator is the only thing that removes it. The
operator was deleted from git on 2026-09-06, so no controller will ever remove it. Measured:

    $ kubectl get ns calico-system -o jsonpath='{range .status.conditions[*]}{.type}: {.message}{"\n"}{end}'
    NamespaceContentRemaining:    Some resources are remaining: serviceaccounts. has 2 resource instances
    NamespaceFinalizersRemaining: Some content in the namespace has finalizers remaining: tigera.io/cni-protector in 2 resource instances

`calico-system` has been `Terminating` since then, and the cluster-scoped ClusterRoles the
operator owned went with it:

    $ kubectl -n flux-system get events --field-selector type=Warning
    kustomization/calico  timeout waiting for: [ClusterRole/calico-cni-plugin status: 'Terminating',
                                                ClusterRole/calico-node status: 'Terminating']

That is a deadlock and not a slow delete. This deck declared ClusterRoles with those exact names,
so Flux applied them, then waited on objects that can never become Ready and can never finish
deleting — every 10 minutes, for 37 hours. Because the Kustomization never completed, it also
never pruned, which is why the superseded `tigera-operator` HelmRelease was still sitting in the
cluster three days after git dropped it: the thing blocking the reconcile was the thing the
reconcile would have cleaned up.

Renaming is the fix a repository can actually apply. Clearing a finalizer means patching a live
object, and git is the only writer of this cluster (decision 0023) — there is no manifest that
expresses "remove someone else's finalizer", and server-side apply cannot drop a `metadata.
finalizers` entry it does not own. Under a name the operator never used, the deck stops waiting
on a tombstone and converges. The tombstones stay until `calico-system` is cleared by hand; they
hold nothing but their names, and nothing references them.
