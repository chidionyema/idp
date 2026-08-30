# Onboarding: backups on the Ops page

`bin/estate-backups` writes `docs/backups.json`, the file the Ops page's **Backups** tile reads,
from one recursive listing of the backup bucket (founder 2026-08-30: every backup with its
timestamp in the back office).

## Inputs

| Input | Where | What it gives |
|---|---|---|
| `--listing f.json` | `rclone lsjson :s3:<bucket> --recursive`, made by the `catalog-render` workflow step "backups from the backup bucket" | every object: path, size, modification time |
| `--bucket` / `BACKUPS_BUCKET` | workflow secret `SEED_R2_BACKUP_BUCKET`, default `prospector-backup` | the name printed on the tile |
| `RCLONE_S3_*` | workflow env from the `SEED_R2_*` secrets (names only; never a value in a file) | only when run without `--listing` |

## Grouping

An object under `offsite/<source>/…` belongs to `<source>` (the names in the offsite backup
declaration in the product's `ops/config/offsite_backup.yaml`). A top-level folder such as `db/`,
`ledger/`, `logs/`, `repo/` is `engine-<folder>`. One row per source: newest object, its stamp,
age in hours, number of copies, bytes. Rows sort stalest first so the page leads with the risk.

## States

- `ok`: a listing was read. The tile marks any source older than 30 hours `stale` (the widest
  interval the offsite declaration uses is 30 hours, so anything past it has missed a run).
- `BLIND` with a `reason`: no listing, an unreadable listing, or rclone refused. The tile says
  the bucket could not be listed and no backup is known to exist. Exit code is 0 in both cases:
  the render job carries on and the page says what it could not read.

## The road to the page

`catalog-render.yml` lists the bucket → `bin/catalog-render` runs `estate-backups` → the file is
committed to the `state/live-diagram` branch → Backstage's `/estate-state` proxy serves it →
`useBackups.ts` reads it every minute → `BackupsTile` in `Ops.tsx` draws it.

## Offline and tests

    python3 -m pytest tests/test_estate_backups.py -q
    bin/estate-backups --listing tests/fixtures/x.json --out /tmp/b.json --now 2026-08-30T10:30:00Z
