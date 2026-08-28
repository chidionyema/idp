# Node autoscaling (crew#539 CP4)

**What you can do now:** stop sizing the node pool. A pod that no node can hold adds a node
(up to `estate-defaults.yaml node_pool.max_nodes`); ten minutes of an unneeded node removes it.

## How it works
- `platform/oci/autoscaler`: the Kubernetes Cluster Autoscaler for OKE (Oracle's manifest, one
  replica) in `kube-system`, `--nodes=1:<max>:$(NODEPOOL_ID)`.
- The pool id, compartment and region come from the vault entry `oke-autoscaler`, written by
  `bin/idp-autoscaler-seed` on every `oke-check` apply (found by cluster name, never typed).
- Identity: the worker nodes' dynamic group plus `platform/oci/autoscaler.tf` (Oracle's six
  statements, compartment-scoped). The cluster is BASIC, so instance principal, not workload identity.
- Terraform hands `size` to the autoscaler (`ignore_initial_pool_size = true`) and a `moved`
  block keeps the live pool; a scale-out is never read as drift and never shrunk by an apply.

## Money
`policy/node_pool.rego` prices base plus burst under the one cap: with the 6 OCPU / 24 GB pool
the base is USD 42.34 paid a month, the burst node USD 0.096/h, and `node_pool.burst_hours_monthly: 60`
is USD 5.76 (total 48.10 under 50). A longer burst allowance is a founder edit of that number; the
policy and the Terraform precondition refuse one the cap cannot hold.

## Demo
`oke-check` mode=check after merge shows the row Ready in the receipt (`state/cluster`:
`kube-system/cluster-autoscaler` Running). Scale-out proof: `platform/scheduling`'s balloon
(a0d64ea4, crew#539 CP1) goes Pending when the node is full and the pool goes to 2 within
`--max-node-provision-time` (25 m); `oci ce node-pool get` shows `size: 2`.

## Do not
- `oke-check mode=surge-node` resizes the pool by hand; Oracle's rule is that a managed pool is
  never resized manually. Scale the autoscaler to 0 first (`kubectl -n kube-system scale deploy
  cluster-autoscaler --replicas 0`) and back after `surge-finish`.
- Burst hours are not metered by anything yet (no metrics stack, crew#539 CP2); the
  scale-down timers are the bound today.

## Preemptible pool (crew#539 CP10)

**What you can do now:** burst onto half-price capacity without touching a pod spec. A second
pool, `a1-spot` (same shape, `preemptible_config.enable = true`, size 0), is the autoscaler's
second `--nodes=0:<spot_max_nodes>:$(SPOT_NODEPOOL_ID)` line; its id travels through the same
vault entry (`bin/idp-autoscaler-seed` writes `SPOT_NODEPOOL_ID`).

- Who lands there: `platform/scheduling/capacity-affinity.yaml` (Kyverno mutate at admission).
  `infrastructure-critical` pods carry a required `estate.io/capacity NotIn [preemptible]`; every
  other pod in an idp namespace carries a preferred `In [preemptible]` (weight 50). Oracle reclaims
  a preemptible node with 30 s notice and TERMINATE is the only action on OKE.
- Money: `node_pool.spot_max_nodes` × `node_pool.spot_hours_monthly` × half the burst node price
  (`a1_preemptible_discount`, Oracle's published 50 %), under the same USD cap as base and burst
  (`policy/node_pool.rego`, `terraform_data.burst_cap`). With the defaults: 30 h × USD 0.048 = USD 1.44;
  total 49.54.
- Labels reach new nodes only, so the running node has no `estate.io/capacity` label; that is why
  the radio-room rule is `NotIn`, and why the label is never read as a required `In [on-demand]`.
