# The cutover: flannel out, Calico in

This directory is merged and suspended. Nothing here reaches the cluster until the Flux row in
`clusters/oke/platform.yaml` reads `suspend: false`, and that is one line.

## Why the estate needs it

Nothing in this cluster enforces NetworkPolicy. A pod in one namespace reaches a pod in another
by IP with no credential; that was measured on `estate` and answered HTTP 200 in 4ms. Sixteen
policy objects sit in the cluster looking like protection and denying nothing, and Superset's
manifest claimed one of them protected it until crew#839 took the claim out. For a buyer's
engineer this is a one-sitting finding, which is the bar the headline sets.

## Why it is a replacement and not an addition

Oracle: *"Installing the Calico network policy engine alongside the flannel CNI plugin causes
network issues. For this reason, Kubernetes Engine does not support the installation of Calico
alongside the flannel CNI plugin."* The only other road is a cluster built on VCN-native pod
networking, and Oracle is equally plain that the CNI plugin cannot be changed after a cluster is
created — that road is `bin/idp-oke-rebuild --teardown-rebuild`, with downtime for the whole run
rather than for one datapath swap.

## The order, and why each step is where it is

1. **Disable Oracle's flannel add-on** on the cluster, so the add-on controller stops reinstalling
   flannel. If this is skipped, flannel comes back underneath Calico and the two fight over the
   same routes — the failure Oracle's sentence is about. This is a cluster property, not a
   manifest: it is the one step Flux cannot take.
2. **Remove the flannel daemonset.** `kube-flannel-ds` in `kube-system`.
3. **Unsuspend this row.** Flux installs the operator, the operator writes the CNI configuration
   and rolls `calico-node` onto both nodes on the same 10.244.0.0/16 VXLAN pool flannel used.
4. **Prove it.** `bin/ns-fence-gate --live` refuses to report a pass while no CNI enforces policy,
   so a clean line from it is the receipt that step 3 worked — not a guess from a quiet Flux.

## What breaks the moment step 3 finishes, and it is not nothing

Sixteen policies stop being decoration and start denying. Read them before the cutover, because
they were written against a network that never tested them:

- `otto-gateway` carries a both-ways `default-deny-all` with holes for DNS, ingress from `edge`,
  the collector, the event bus and its own in-namespace database. That set is deliberate and
  documented — the door never dials out. It is also the login door, so it is the first thing to
  check after the cutover, and the first thing to fix forward if a flow was missed.
- `otto-golden` is the same shape plus outbound HTTPS.
- `flux-system` allows all egress and ingress only from its own pods, plus scraping and webhooks.
  Egress being open is what keeps the estate's repair path alive during the cutover.
- `weave-gitops` fences its dashboard only.

The thirty-nine generated policies in `platform/ns-fences/network/` stay unwired through all of
this. They come from a grep of the manifests for `<service>.<namespace>.svc`, which cannot see a
flow whose address arrives in a secret or an operator's call to the API server. They are wired in
only after a Calico flow log has been read over a full cycle of the estate's scheduled work and
`platform/ns-fences/allowances.yaml` has been corrected from what was observed.

## Backing out

Re-enable the flannel add-on and suspend this row. The pool, the encapsulation and the per-node
subnet length here are the ones flannel uses today, so pod addressing is unchanged in both
directions; what moves is which daemonset owns the route.
