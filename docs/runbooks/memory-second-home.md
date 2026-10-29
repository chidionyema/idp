# Runbook: memory's second home

idp#7397, child of the reliability plan #7362 (item S4 for memory). The write gate's degraded mode
is #7351 / #7369, not this page.

## Why it exists

On 2026-10-28 Oracle removed the tenancy's OKE entitlement and the cluster went dark. Unified
memory, Active Memory and Active Focus all went with it, for three different reasons, each graded:

| Service | Why it went down | Diagnosis |
|---|---|---|
| Unified memory | One home: estate-db, the memory server and the MCP gateway all on the one cluster, no backup, no copy | `docs/diagnoses/2026-10-28-unified-memory-had-one-home.yaml` (0.9988) |
| Active Memory | Its only fallback was the last good brief in router RAM for 30 minutes: 841 reads ended `nothing to serve` | `docs/diagnoses/2026-10-28-active-memory-had-nothing-to-serve.yaml` (1.0000) |
| Active Focus | The ledger was up, but every gh read (the background refresh too) was cut at the router's 3.0 s budget; the search takes 4.6 s. An unreadable ledger also threw away the register already on disk | `docs/diagnoses/2026-10-28-active-focus-killed-by-its-own-deadline.yaml` (0.9984) |

## The homes

| Order | Home | Written by | Depends on |
|---|---|---|---|
| 1 | The memory server, through the door | agents (`remember`) | the cluster |
| 2 | Last good answer in router RAM (30 min) | the router | the router process |
| 3 | R2 object `memory/snapshot.json` | `.github/workflows/memory-snapshot.yml`, every 15 min | GitHub Actions and Cloudflare R2, not OCI, not the laptop |
| 4 | Local copy `~/.estate/memory/snapshot.json` | the router (good briefs, once a minute) and `bin/memory-snapshot pull` | this machine's disk, bounded to 4 MiB, never written below `ESTATE_DISK_FLOOR_MB` (1024) |

Focus has its own ledger, GitHub, which stayed up. When gh cannot answer in time the router now
serves the last register (the cache file, or the snapshot's copy), with every heartbeat aged to
now, so a claim that lapsed since is shown lapsed. The edit gates do not fall back: whether an
edit is covered is decided on the ledger alone.

Everything served from homes 2 to 4 says how old it is, in the block the model reads:
`Active Memory (memory server unreachable; from the snapshot, facts 2h00m old)`.

## Commands

```bash
bin/memory-snapshot check   # read R2, print the age of each half; exit 1 past 6 h
bin/memory-snapshot pull    # R2 -> the local copy on this machine
```

Both need `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` and `R2_BUCKET` by name from the
vault (`source ~/Documents/code/estate-secrets/scripts/secret-load`).

## Proof

- Built: `tests/test_memory_snapshot.py`, `tests/test_active_memory.py` (the three
  `second home` tests), `tests/test_estate_memory_focus.py` (the `unreadable ledger` tests).
- Operating, continuously: every scheduled `memory-snapshot` run reads its upload back and compares
  sha256, and goes red when no fact has come through the door for 6 hours.
- Operating, at the reader: the router logs `active_memory brief unreadable for <agent>: ...
  serving snapshot age=<s>s` when it answers from the snapshot. That line in
  `~/Library/Logs/litellm-local.log` during a door outage is the proof this works. A green CI run
  is not.

## Not done here (each needs another lane's file)

1. `bin/litellm-local` stages only `door.py focus.py runtimes.json` into the launchd router's
   memory dir. `snapshot.py` must join that list or the staged laptop router never finds its
   snapshot. The file is held by #7142; asked there.
2. The in-cluster router loads `active_memory.py` from a ConfigMap (`platform/llm/kustomization.yaml`,
   held by #7311) without `snapshot.py`, so in a cluster the fallback is not shipped. It degrades to
   today's behaviour, with no error.
3. Restore, as opposed to read: estate-db has no backup. A CNPG backup to R2 is what lets the
   disaster-recovery cluster (k3s on the A1 VM) come back with its memory rather than empty.
