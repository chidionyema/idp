# Restore the shop database

The whole shop is one SQLite file: `/data/store.db` on claim `prospector-store-api-data` in
namespace `prospector`. It holds the accounts, the 202-pack catalogue, the price history, the
orders, the entitlements and 41,035 analytics events. Losing it loses the shop, not the logins.

A copy is made every day at 03:17 UTC (`17 3 * * *`) by `platform/prospector/store-db-backup.yaml`, into bucket
`estate-shop-backups` (`platform/oci/shop-backups.tf`), and kept for `shop_backup_retention_days`.
The pod uses the worker node's own identity, so there is no key to rotate and none to lose.

## Is there a backup, and how old is it

One object answers it. `shop/latest.json` is written last in each run, so its presence means the
copy above it landed.

```
oci os object get --bucket-name estate-shop-backups --name shop/latest.json --file -
```

It carries `stamp`, `object`, `bytes`, `sha256`, `integrity` and the row counts at the time of the
copy. A `stamp` more than a day old means the job has not run and that is the incident, before any
restore is discussed.

## Restoring

**This destroys the live database. It needs the founder's word first, naming the object.** There
is no undo: the current file is gone the moment it is overwritten.

Restore is four steps. Take the API down first — SQLite has one writer and copying a file underneath
a running writer is how a good backup becomes a bad database.

```
kubectl -n prospector scale deploy prospector-store-api --replicas=0
kubectl -n prospector wait --for=delete pod -l app.kubernetes.io/name=prospector-store-api --timeout=180s
```

Then a pod that can reach the bucket and write the claim. It runs as uid 10001, the user the API
owns its files as; anything else restores a file the API cannot open. The security context is the
one the namespace enforces — non-root, read-only root filesystem, all capabilities dropped, seccomp
`RuntimeDefault` — and a bare image with none of it is refused at admission.

```
kubectl -n prospector run restore --image=ghcr.io/oracle/oci-cli:20260826 --restart=Never \
  --overrides='{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":10001,"runAsGroup":10001,"fsGroup":10001,"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"r","image":"ghcr.io/oracle/oci-cli:20260826","command":["sleep","900"],"env":[{"name":"HOME","value":"/tmp"}],"securityContext":{"allowPrivilegeEscalation":false,"readOnlyRootFilesystem":true,"capabilities":{"drop":["ALL"]},"seccompProfile":{"type":"RuntimeDefault"}},"resources":{"requests":{"cpu":"100m","memory":"256Mi"},"limits":{"cpu":"500m","memory":"512Mi"}},"volumeMounts":[{"name":"d","mountPath":"/data"},{"name":"t","mountPath":"/tmp"}],"livenessProbe":{"exec":{"command":["true"]},"periodSeconds":10},"readinessProbe":{"exec":{"command":["true"]},"periodSeconds":10}}],"volumes":[{"name":"d","persistentVolumeClaim":{"claimName":"prospector-store-api-data"}},{"name":"t","emptyDir":{}}]}}'
kubectl -n prospector wait --for=condition=Ready pod/restore --timeout=180s
```

Pull the copy, check it before it touches `/data`, then put it in place.

```
kubectl -n prospector exec restore -- sh -c '
  set -eu
  oci --auth instance_principal os object get --bucket-name estate-shop-backups \
    --name shop/store-<STAMP>.db --file /tmp/store.db
  python3 -c "
import sqlite3
d = sqlite3.connect(\"/tmp/store.db\")
print(\"integrity\", d.execute(\"pragma integrity_check\").fetchone()[0],
      \"packs\", d.execute(\"select count(*) from Packs\").fetchone()[0],
      \"orders\", d.execute(\"select count(*) from Orders\").fetchone()[0])"
  rm -f /data/store.db /data/store.db-wal /data/store.db-shm
  cp /tmp/store.db /data/store.db
  ls -la /data'
kubectl -n prospector delete pod restore
kubectl -n prospector scale deploy prospector-store-api --replicas=1
```

**The `rm -f` of `store.db-wal` and `store.db-shm` is the whole trap.** On 2026-08-25 a restore left
a stale write-ahead log next to the new file; SQLite replayed it over the top, and `/catalog`
answered `[]` with 78 packs sitting on disk. The restore reported success. Delete the sidecar files
or the restore silently undoes itself.

Do not compare hashes between two runs of the backup job. `vacuum` does not produce byte-identical
output across runs, so two good copies of the same data have different `sha256` values. The check
that means something is `pragma integrity_check` plus the row counts, which is what the job itself
refuses on.

## Proving it, before you need it

The `packs` and `orders` counts printed above must match `shop/latest.json`, and the site's
`/catalog` must answer with the catalogue after the API comes back. Both are one command, and both
are the point: a backup nobody has restored is a claim, not a backup.
