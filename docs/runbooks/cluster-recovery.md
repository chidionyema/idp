# Cluster recovery: phantom node pool, storage fit (idp#7343)

State measured 2026-10-28: OKE pool `a1` size 2, both instances TERMINATED, the
NODEPOOL_RECONCILE work request FAILED, so OKE will not create replacements.

## Order

1. **Reconcile the pool records (plan, then apply).**
   `ESTATE_AGENT=<name> ~/.estate/bin/estate-execute oci-nodepool-reconcile` prints, per pool,
   node id / pool says / instance says / verdict. A phantom is a node whose instance is
   TERMINATED, TERMINATING or absent; the instance's state is the truth, never the pool record.
   Read the table. Then `... oci-nodepool-reconcile apply=true` removes each phantom with
   `delete-node --is-decrement-size true`, one at a time, and re-reads the pool.
   It never touches a RUNNING/STOPPED/PROVISIONING node and never deletes volumes or instances.
2. **Free volume quota if needed:** `oci-reclaim` (separate door, idp#7318).
3. **tofu apply** with node pool size 1 and boot volume 50 GB, so storage fits the 200 GB
   Always Free allowance: 3 live PersistentVolumes x 50 + 1 boot volume x 50 = 200 GB.
4. **Verify** (below).

## Verify

- `estate-execute oke-check` (or the oke-check workflow): node pool `ACTIVE`, node `Ready`.
- `https://mumchimp.com` answers (a real response, not the 503 "Starting up").
- Re-run the reconcile door in plan: it must print "no phantom nodes".

## Who decides what

- Agents may run the dry run at any time.
- `apply=true` and `tofu apply` are production mutations: the founder decides.
- The door's rules are code (`platform/estate/libexec/oci-nodepool-reconcile.py`), proved by
  `tests/estate/test_oci_nodepool_reconcile.py`; change the rule there, not at the prompt.
