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

1. A CNI that enforces policy, and on this cluster that is not a small change. Calico in
   policy-only mode beside flannel was staged and is **ruled out by Oracle in writing**:
   "Installing the Calico network policy engine alongside the flannel CNI plugin causes network
   issues. For this reason, Kubernetes Engine does not support the installation of Calico
   alongside the flannel CNI plugin."
   (docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengsettingupcalico.htm, read 2026-09-04).
   Oracle's supported route is to replace flannel: disable the flannel cluster add-on, remove its
   daemonset, and apply Calico — swapping the datapath under a running estate, which is the road
   that took coredns down here in idp#505 and had to be reverted in idp#514. The alternative is a
   cluster built on VCN-native pod networking, and Oracle is equally explicit that "after a cluster
   has been created, you cannot change the CNI plugin you originally selected for it"
   (contengpodnetworking.htm, same day), so that means recreating the cluster —
   `bin/idp-oke-rebuild --teardown-rebuild`, with downtime for the run. `platform/oci/main.tf:15`
   pins `cni_type = "flannel"` and line 13 pins `cluster_type = "basic"`.
   Either way this is a founder decision, not a merge.
2. A flow log from that CNI, read over a full cycle of the estate's scheduled work, so
   `../allowances.yaml` is corrected from observed traffic rather than from a grep.
3. Re-run `bin/idp-ns-fence-gen`, add the row to `clusters/oke/platform.yaml`, and merge.

Until step 1, `bin/ns-fence-gate --live` reports that no CNI enforces policy rather than reporting
that the namespaces are fenced, because the second sentence would not be true.
