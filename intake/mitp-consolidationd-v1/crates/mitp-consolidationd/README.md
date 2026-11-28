# mitp-consolidationd

The estate's sleep cycle: staged evidence-gated promotion, episodic→semantic
distillation (the dream pass), and Brier/CUSUM revalidation for the
unified-memory-server. Pure Rust 2021, zero dependencies, zero `unsafe`.

Design + edge-case register: `Design_Proposal_TP-MEMORY_Consolidation_Dreaming_Rust.md`.
Grounding research: `Grounded_Research_One_Mind_Scientist_Engineer_Creator.md` §5.

## What it fixes

- **G1** promotion daemon that was never deployed — this is it
- **G2** default-score mass-promotion bug — evidence is required; defaults are inadmissible
- **G3** version-bump recency corruption — bookkeeping never touches `memories`; side tables only (static-tested)
- **G4/G6** no sleep pass / no dreaming — distiller with budget gate, poison scan, dedupe, shadow mode
- **G5** no revalidation — Brier + CUSUM surveillance with oracle-class-aware demotion

## Layout

- `src/config.rs` — env config, fail-closed defaults (shadow ON, budget 0)
- `src/host.rs` — velocity-aware host-survival gate (CBF-style, E7)
- `src/owasp.rs` — zero-dep port of security_core.py write guard (E6)
- `src/evidence.rs` — evidence-weighted promotion gate (E1/G2)
- `src/quality.rs` — memory_quality side-table model (G3/E2)
- `src/distill.rs` — dream pass: cluster, scan, budget, dedupe (E4/E6/E8/E12)
- `src/revalidate.rs` — Brier + one-sided CUSUM surveillance (G5/E9)
- `src/sql.rs` — SQL templates incl. migration M-001; invariants static-tested
- `src/store.rs` — MemoryStore/TenantTx traits + MockStore
- `src/cycle.rs` — the sleep-cycle orchestrator
- `src/receipts.rs` — JSON receipts; every cycle receipts, even empty (E14)
- `catalog/tp-memory.policy.json` — versioned weights/thresholds (E10)

## Verification status

`cargo test` equivalent executed on stable Rust via the playground executor
(sandbox lacks a local toolchain): **53/53 unit + integration tests pass in
debug AND release modes**; binary compiles and `selftest`/`host-gate` run.
Greenlane `cargo test` + 3/3 clean-room certification still required for the
OPERATIONAL stamp, per estate law.

## Estate wiring

1. Run migration M-001 (embedded in `sql.rs::MIGRATION_M001`) on the memory DB.
2. Implement `MemoryStore`/`TenantTx` over sqlx in the estate executor crate;
   every statement in `sql.rs` maps 1:1.
3. Wire `DistillModel` to pennyd (the sole model door); budget via
   `MITP_DISTILL_BUDGET_MICRO`.
4. Schedule the cycle (CronJob, nightly + idle-triggered); it shares advisory
   lock 883921 with the legacy Python curation worker, which this replaces.
