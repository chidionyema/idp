# Disk Sentinel: checkpoint, 2026-11-05

Resume point for the disk work. Everything below was measured on the founder's Mac on
2026-11-05; a claim without a measurement is marked as one.

## Landed and operating

`disk-sentinel` is a tracked estate resource at `infra/macos/tools/disk-sentinel/`, installed
under `~/.local/share/disk-sentinel`, with three launchd jobs that `bin/idp-inventory --plane
mac` reports MANAGED (`dev.disksentinel.monitor`, `.scan`, `.dashboard`). Merged as
PRs 7718-7722; the last commit `4c336616f` landed in `b4749`.

Verbs: `tick`, `scan --auto|--force`, `review`, `status`, `open`, `admit`, `probe`,
`verify -- <cmd>`, `policy`, `forensics [--deep|--quick]`, `elephant [--deep|--quick]`.

Behaviour that exists and was proven:

- `scan --auto` retries every 30 minutes; DEFERRED (busy or under reserve), PARTIAL
  (a directory timed out), COMPLETE (stamps a 24-hour window so the next tick does no I/O).
- Four modes by absolute free space: NORMAL >20 GiB, WARNING 15-20, CRITICAL 3-15,
  EMERGENCY <3. Below the 15 GiB reserve, discretionary work is refused (exit 75) unless
  `--force`; `admit` gives any job the same answer.
- Event-triggered capture: a drop past 512 MiB in 5 minutes writes one bounded capture
  (capacity, swap, mode, samples, top CPU, this user's large open files) with a 15-minute
  cooldown.
- `probe`: one readdir per directory, reporting entries/latency/verdict.
- `verify -- <cmd>`: measures free space before and after a cleanup and records a receipt
  with the command, exit status, both readings, delta and verdict.

## What the investigation established

- The volume holds real work, not a leak: 82.54 GiB attributed in 403 s once cloud provider
  trees were pruned, of 90 GiB used. Owners: Users 58.5, Applications 13.1, Library 3.7,
  private 2.8, System 2.7.
- The earlier "60 GB missing" was a walk that never finished: it descended into
  `~/Library/CloudStorage`, where one readdir of a Google Drive mount cost 38.5 ms against
  0.5 ms locally. Pruning it turned a 20-minute stall into a 403-second completion.
- `/System/Library/Caches/com.apple.coresymbolicationd/data` (5.19 GiB) is on the **sealed,
  read-only System volume** (`mount`: `sealed, read-only`). It cannot be removed by root.
  Do not attempt `rm`; do not disable SIP.
- Free space oscillates 0.4-4.4 GiB under load (CacheDelete reclaims, applications refill).
  The largest single rise in 437 samples was +3.05 GiB; there was never a 5.19 GiB reclaim.

## Blocked / next

1. A 15 GiB reserve against 90 GiB of real work on a 113 GiB disk does not fit. Closing the
   ~12 GiB deficit needs an attached external SSD moving `~/Documents/code` (11.74 GiB),
   `~/Library` (10.60) or `~/.estate` (7.63) - every one is live work or a deployed surface
   (`~/.estate/frontend/idp` is what /fleet serves). No external volume is attached.
2. Wire `admit` into the estate job preflight so the reserve binds other jobs. Do this when
   free space is above the reserve, or it refuses every estate job on landing.
3. Remaining arithmetic gap (~7.5 GiB): 1 GiB sleepimage, APFS metadata, dataless/cloud
   files, 177 access-restricted paths.

## How to resume

```bash
disk-sentinel status          # mode, free space, last investigation verdict
disk-sentinel probe           # metadata latency for the usual suspects
disk-sentinel elephant --deep --force   # full attribution (~7 min, prunes cloud trees)
disk-sentinel verify -- <cmd> # prove a cleanup actually returned capacity
```
