# i8096 — recovered Genesis certifier bundle

Provenance, not a claim of operation. Every byte here was recovered from an archive the founder
supplied and verified against the manifest inside it before it was checked in.

## Source

- archive: `GEMINI_RECOVERY.zip`, 12,508 bytes
- archive sha256: `03f2307a60513d173e5bdeb8f51f737e44bb34e08f472d3771feafff5e8539c4`
- quarantined at: `~/.estate/quarantine/gemini-recovery-20261116T021446Z` (raw bytes + `SHA256SUMS`)
- recovery date: 2026-11-16

## Verified members

Each digest was recomputed from the landed bytes and equals `MANIFEST.json` and the digest the
founder supplied:

| path | sha256 | bytes |
|---|---|---|
| `src/certifier.rs` | `81b911b3…0a85` | 15,685 |
| `bin/genesis_realtime_symbiont.py` | `178e233a…22ec` | 8,522 |
| `specs/GenesisSplitAuthorityCertifier.tla` | `4c58230d…123a` | 7,826 |
| `features/six_certification_trials.feature` | `acf571d6…8297` | 4,039 |

## What each part is

- `bin/genesis_realtime_symbiont.py.recovered` — the realtime symbiont (checked in with a `.recovered` suffix so the estate's Python gates never grade archived evidence as source; it runs with `python3 <file>`): packs the ≤4 KiB genesis spore from
  `realtime_event_ring`, runs the reversible science stream over `experiment_preregistrations` /
  `experiment_trial_runs`, and emits a task-lease userscript. `GENESIS_DB_PATH` defaults to
  `/var/lib/genesis/genesis.db`; `REALTIME_BASE_URL` defaults to `http://127.0.0.1:4001`. It
  refuses the legacy history ledger with `HISTORY_QUARANTINE_VIOLATION`.
- `specs/GenesisSplitAuthorityCertifier.tla` — the split-authority certifier model: candidates,
  failure classes, independent certifier, adversary, SLA ticks, one-step rollback. It is a
  **different** model from `cage/i8046/specs/GenesisSplitAuthorityCertifier.tla` (that one models
  actor classes and protected primitives); the two are not interchangeable.
- `features/six_certification_trials.feature` — the seven demonstrations of self-certifying,
  quarantine-isolated, reversible autonomy.
- `src/certifier.rs` — the Rust certifier implementation the TLA describes.

## Boundaries (unproven, and said so)

- No `.cfg` for TLC and no `Cargo.toml` in the bundle: the TLA cannot be model-checked and the
  certifier cannot be built from this directory alone.
- No database schema: the symbiont's `pack-spore` and `science-stream` commands need a
  `genesis.db` with `realtime_event_ring`, `experiment_preregistrations` and
  `experiment_trial_runs`. Only `emit-userscript` needs no database, and that is the command the
  recovery test exercises.
- The feature file needs a BDD runner (behave/cucumber) that this repository does not currently
  carry; the scenarios are recorded, not executed here.
