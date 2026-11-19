# Private GitHub Repository `inbox/` — Conflict-Free Artifact Drop Airlock & Single-Sequencer Spec

This directory implements the **Olat Estate Private GitHub Repo `inbox/` Airlock** for instructions and artifacts synthesized in **Cloud Studio / Ephemeral Sandbox Channels** (`chidionyema/argo-sync` and `chidionyema/argon`).

> **Core Principle ("Container Proposes, Cloud Disposes")**:
> Concurrent Cloud Studio builders and specialist agents **never** push directly or force-push onto `main`. Builders emit immutable, content-addressed drop proposals (`HOP-01`/`HOP-02`); an independent out-of-process GitHub Actions grader verifies them (`HOP-03`, satisfying `Trap T1: Grader != Builder`); and a **single serialized linearizer (`HOP-06`, concurrency group `genesis-main-sequencer`)** checks for semantic touch-set collisions, re-runs the verification suite on the composed result, and fast-forwards `main`.

---

## 1. Why Content-Addressed `inbox/incoming/*.envelope.json` + Single Sequencer?

1. **Syntactic Conflict-Freedom at `HOP-02` (`S_a ⊔ S_b` Join-Semilattice)**:
   - Each Cloud Studio synthesis emits an immutable, content-addressed drop file:
     `inbox/incoming/DROP-<epoch>-<slug>.envelope.json` and pushes to proposal branch `refs/heads/inbox/DROP-<epoch>` (or `refs/heads/genesis-live`).
   - Because each drop writes a distinct content-addressed filename, concurrent drops cannot collide as Git objects at `HOP-02`.

2. **Semantic Conflict Detection at `HOP-06` (`T_files(DROP_i) ∩ T_files(DROP_j)`)**:
   - Syntactic conflict-freedom is **not** semantic conflict-freedom: two drops that both modify `src/lib/protocolEngine.ts` merge cleanly as `.envelope.json` files in `inbox/incoming/`, yet collide as engineering intent if branched from the same `baseCommitSha`.
   - Therefore, **`HOP-06` (`scripts/sequencer/inbox_hop_sequencer.ts` + `.github/workflows/genesis-inbox-sequencer.yml`)** runs under a strict single-instance lock (`concurrency: { group: "genesis-main-sequencer", cancel-in-progress: false }`):
     ```text
     SemanticCollision(DROP_i, DROP_j) <=>
       (T_files(DROP_i) ∩ T_files(DROP_j) != ∅) AND (baseCommit(DROP_j) != headCommit(DROP_i))
     ```
   - If two concurrent drops touch overlapping files from the same unchained base commit, the Sequencer quarantines the second drop (`QUARANTINE_DROP_B_REQUIRE_REBASE_ON_DROP_A`), composes only non-colliding drops, runs `npm test && npm run enforce` on the composed tree, and fast-forwards `main` (`0` force-pushes).

---

## 2. Deterministic 6-Hop Pipeline & Honest Execution Classification (`B0` Audit Standard)

Every hop is tagged with its exact on-disk implementation and honest execution boundary (`REAL_POSIX_AND_CI_EXECUTABLE` vs `SIMULATED_OR_DEFERRED`):

| Hop ID | Hop Name & Invariant (Copy-Paste-Safe ASCII) | On-Disk Executable / Workflow | Execution Reality Tag (`B0` Standard) |
| :--- | :--- | :--- | :--- |
| **`HOP-01`** | **Cloud Studio Pre-Flight Gate**<br>`AntiSlop(6/6) ∧ UnitTests(114/114) ∧ Laws(8/8)` | `npm test && npm run enforce` | `REAL_POSIX_AND_CI_EXECUTABLE`<br>Runs `node:test` + `scripts/enforcers/enforce_i1_to_i8.ts` in separate child processes. |
| **`HOP-02`** | **Propose-Only Drop Commit & Branch Push**<br>`Push(refs/heads/inbox/DROP-*, genesis-live) ∧ ForcePush(main) == BLOCKED` | `npm run sync:github`<br>(`scripts/sync/sync_genesis_live_to_github.ts`) | `REAL_POSIX_AND_CI_EXECUTABLE`<br>Signs `SOURCE_MANIFEST.json` (`Ed25519` + `SHA-256`) and pushes proposal branches only (`0` force-pushes to `main`). |
| **`HOP-03`** | **Out-of-Process GitHub Actions Airlock Grader**<br>`Grader != Builder ∧ SecretLeakage == 0` | `.github/workflows/genesis-verify.yml` | `REAL_POSIX_AND_CI_EXECUTABLE`<br>Independent GitHub Actions runner checks `AGENTS.md <= 120` lines, `npm test`, `npm run enforce`, and `Ed25519` manifest signature. |
| **`HOP-04`** | **Inbox Lease Ingestion**<br>`Lease(DROP_k, TTL=30s) -> inbox/sequencer-state.wal.json` | `npm run hop:sequencer`<br>(`inbox/sequencer-state.wal.json`) | `REAL_ATOMIC_WAL_FILE_HONEST_REDB_DEFERRED`<br>Uses POSIX atomic temp-file + `fs.renameSync` WAL today; native Rust `redb` daemon is explicitly deferred (`TIER_B_DEFERRED`). |
| **`HOP-05`** | **Canary & Reality Assimilation Model**<br>`ΔV(e) <= -α·||e||_W^2 < 0 ∧ ||z_t - H·x̂_t||_2 <= 0.0020` | `src/lib/protocolEngine.ts`<br>(`computeContinuousEstateMapReduceModel`) | `SIMULATED_TS_MODEL_HONEST_DEFERRED`<br>Deterministic TypeScript math model verified in unit tests; live 6s hardware telemetry daemon is explicitly deferred (`TIER_B_DEFERRED`). |
| **`HOP-06`** | **Single Named Sequencer & Fast-Forward to `main`**<br>`Lock(genesis-main-sequencer) ∧ Verify(Composed) => FastForward(main) + Receipt(ΔY > 0)` | `npm run hop:sequencer` + `.github/workflows/genesis-inbox-sequencer.yml` + `/inbox/PROMOTION_RECEIPT.json` | `REAL_POSIX_AND_CI_EXECUTABLE`<br>Single GitHub Actions linearizer orders drops, checks semantic touch-sets, runs verify suite, fast-forwards `main`, and signs `/inbox/PROMOTION_RECEIPT.json`. |

---

## 3. Queue Congestion Formulas (Copy-Paste-Safe ASCII Notation)

- **Little's Law**: `L = λ * W` (where `L` = work-in-progress drops in `inbox/incoming/`, `λ` = arrival rate, `W` = mean soak time across `HOP-01..06`).
- **Kingman Utilization Bound**: `ρ = λ / (c * μ) <= 0.35` (target steady-state utilization; alert threshold at `ρ > 0.75`).
  *(Note: Queue telemetry is modeled deterministically in `evaluateStudioToGithubInboxAndCongestion` until live production runner metrics are bound.)*

---

## 4. Runnable Commands

```bash
# 1. Run HOP-01 Pre-Flight (114 Unit Tests + 8 Law Enforcers + 8 Mutation Falsifiers)
npm test && npm run enforce

# 2. Run HOP-04/06 Single Sequencer & Semantic Touch-Set Collision Detector locally
npm run hop:sequencer

# 3. Run HOP-02 Propose-Only Sync (signs SOURCE_MANIFEST.json & pushes genesis-live + inbox/DROP-*)
npm run sync:github
```
