# Block-storage budget

Incident: `docs/incidents/2026-10-28-the-router-lost-every-model.md`. Block storage hit the 200 GB
Always Free allowance, every volume and node create answered `LimitExceeded`, and the cluster
could not repair itself.

`bin/idp-storage-budget [nodes]` counts committed demand before an apply: the largest
`boot_volume_size` in `platform/oci/main.tf` times `nodes` (default 2, the surge peak), plus every
`storageClass: oci-bv` claim under `platform/`, each rounded up to the 50 GB CSI minimum. It exits 1
and prints `FAIL` above 200 GB.

- Measured on main at the time of writing: 200 GB at 1 node, 300 GB at 2 nodes. A surge to two
  nodes does not fit, which is what stalled the node pool.
- Orphaned volumes are not in manifests. Reclaim them with the `oci-reclaim` intent (plan first).
- Raising the allowance means a paid account. That is a founder decision.
- The gate is report-only until it is wired into `ci-success`.
