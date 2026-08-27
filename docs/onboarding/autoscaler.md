# Node autoscaling (crew#539 CP4)

**What you can do now:** stop sizing the node pool. A pod that no node can hold adds a node
(up to `estate-defaults.yaml node_pool.max_nodes`); ten minutes of an unneeded node removes it.

## How it works
- `platform/autoscaler`: the Kubernetes Cluster Autoscaler for OKE (Oracle's manifest, one
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
