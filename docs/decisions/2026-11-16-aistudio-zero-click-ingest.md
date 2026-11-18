# ADR: AI Studio turns are events, not exports

Date: 2026-11-16. Instruction: I-8096-REV2. Closes `CLASS-MANUAL-EXPORT-FRICTION`.

## Decision

The edge worker (`platform/lifeboat`) accepts AI Studio work through two zero-click channels
— a browser stream tee and a Google Drive `changes.watch` push — and resolves both to one
commit on `lane/aistudio-auto-intake` keyed by `(path, sha256)`. The commit, the
`OMNIFLOW-EVENT/v1` assignment on idp#8133, the realtime `chronicle.aistudio_ready` frame and
the Greenlane dispatch happen without a human action.

## Why here

- The worker already has no database, no Mac mount and a vault-backed secret path; it is the
  one surface that can be reached by both a browser and Google's servers.
- The alternative (a local watcher on `~/Downloads`) is a Mac tether and fails the
  DARWIN_THIN_CLIENT rule.
- Implementing the engine in the worker keeps one implementation for both channels, so the
  dedup is structural rather than a convention.

## Consequences

- A leaked userscript token is limited to ingest (it cannot read the lane, spend a key, or
  reach the router).
- The Drive channel needs the founder's Google Drive watch channel registered once; until it
  is, channel 1 alone carries turns.
- The instruction's named broadcast surfaces (`mcp_doors`, `cloud_apis`, `dsh_web`,
  `telegram_spooler`) do not exist in this repository; the OMNIFLOW room, the realtime hook
  and the Telegram completion path are the broadcast that exists. The gap is recorded rather
  than filled with four unread layers.
