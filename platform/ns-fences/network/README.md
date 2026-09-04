# These NetworkPolicies are generated, complete, and deliberately not applied

`clusters/oke/platform.yaml` has no row for this directory, and that is not an oversight.

**This cluster runs flannel.** Measured 2026-09-04 with `kubectl get daemonset -n kube-system`:
`kube-flannel-ds`, two ready, and no Cilium, Calico, Antrea or kube-router anywhere. Flannel gives
pods an address and a route; it does not implement NetworkPolicy. The API server accepts a policy
object, stores it, and shows it in `kubectl get`, and nothing on the node ever reads it.

Sixteen NetworkPolicies were already in the cluster when this was measured — `flux-system` for ten
days, `otto-golden` carrying a both-ways `default-deny-all` for forty-one hours, `otto-gateway`,
`weave-gitops`. None of them has ever denied a packet. Applying thirty-eight more would add nothing
to the estate's security and would let the estate go on claiming a protection it does not have,
which is the `silent-green` failure the incident ledger already counts four times.

The second reason is worse than the first. The flows in `../allowances.yaml` come from a scan of
every manifest for `<service>.<namespace>.svc` references, and that scan is known to be incomplete:
it cannot see a flow whose address arrives through a secret, an operator's client-go call to the
API server, or Prometheus scraping a namespace it monitors. Today that costs nothing, because
nothing enforces the policies. The day a policy-enforcing CNI is installed, all thirty-eight would
activate at once against allowances nobody could validate, and every missing flow would fail
simultaneously.

## What has to happen before this directory is wired in

1. A CNI that enforces policy. The staged decision is Calico in policy-only mode beside flannel —
   the configuration Project Calico documents for exactly this cluster shape, where flannel keeps
   the networking it already does. It is the smaller road than replacing the CNI, and replacing the
   CNI is the road that took coredns down here in idp#505 and had to be reverted in idp#514.
2. A flow log from that CNI, read over a full cycle of the estate's scheduled work, so
   `../allowances.yaml` is corrected from observed traffic rather than from a grep.
3. Re-run `bin/idp-ns-fence-gen`, add the row to `clusters/oke/platform.yaml`, and merge.

Until step 1, `bin/ns-fence-gate --live` reports that no CNI enforces policy rather than reporting
that the namespaces are fenced, because the second sentence would not be true.
