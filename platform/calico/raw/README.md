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
| namespace `calico-system` / `tigera-operator` | `kube-system` | Non-operator installs live in kube-system. RBAC names are unprefixed and cannot collide with the operator's `calico-system` accounts. |

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
