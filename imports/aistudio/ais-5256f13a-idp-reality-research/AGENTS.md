# IDP REALITY RESEARCH PLATFORM — AGENT & SINGLE-ENGINEER COMMAND MANIFEST

> **CRITICAL DIRECTIVE FOR ALL CODING AGENTS & ENGINEERS**:
> Before modifying any subsystem in this repository, read the linked specification for your assigned **Critical Lane**. Every implementation MUST preserve the 4 Founder Epistemic Invariants (`INV-01` through `INV-04`) and pass deterministic unit tests before merge.

---

## 1. Saved Master Documents & Canonical Links

| Document | Path | Purpose |
| :--- | :--- | :--- |
| **Agent Routing & Critical Lanes** | `/AGENTS.md` | Immediate entry point for all AI agents and engineers; maps all 5 critical lanes, 5 Estate Multiplier Kernels, and invariants. |
| **Estate Exponential Multiplier Master Plan (`chidionyema/idp`)** | `/docs/ESTATE_EXPONENTIAL_MULTIPLIER_PLAN.md` | Forensic synthesis of `PR #7324`–`#7515`, Founder Devil's Bargain laws, 5 Exponential "Gifts That Keep Giving" (`estate-dispatchd`, Tenets `T1–T9`, `NSVEE P1–P5`, `$3/d` Spend Governor, Movie Director & Two-Hats Factory), and Greenlane `lane-submit` runbook. |
| **Master Architecture & Consultant Dossier** | `/docs/IDP_MASTER_ARCHITECTURE_AND_ROADMAP.md` | Saved Founder Vision, Master Spec v3.4, Incident Post-Mortems (`INC-2026-*`), RFC Trade-offs (`RFC-01`–`RFC-05`), and External Consultant Brief. |
| **Single-Engineer Operational Spec & Code** | `/docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md` | Step-by-step, copy-pasteable schemas, algorithms, and single-operator deployment runbooks for all 5 critical lanes. |
| **Executable Reference Kernels (Lanes 1–5 & Multipliers M1–M5)** | `/src/lanes/operationalKernels.ts` & `/src/data/estateMultiplierData.ts` | Pure TypeScript kernels tested via `node:test`, plus downstream Gemini 3.5 Flash / MiniMax M2.7 build prompts. |

---

## 2. The 5 Critical Engineering Lanes (Immediate Routing Table)

A single engineer (assisted by fast coding models) can bring the entire IDP core online by executing these 5 lanes in order. Zero distributed-systems bloat (no Kafka/Spark/Kubernetes sprawl—use embedded DuckDB/Iceberg, RocksDB/CSR, Redpanda single-binary, and Polars/JAX):

### Lane 1 — Epistemic Intake & BLAKE3 Merkle Provenance (`packages/epistemic-intake`)
- **Fixes Incident**: `INC-2026-107` (Unbounded lineage DAG OOM on unstructured workers)
- **Governing RFC**: `RFC-04` (Option B — Inline BLAKE3 Merkle-Span Proofs in Arrow Footers)
- **Single-Engineer Stack**: Rust / TypeScript streaming intake + BLAKE3 content-addressed blob store (`cas://blake3/<hash>`) + Apache Arrow IPC record batches.
- **Hard Acceptance Gate**: Heap memory `< 1.5GB` under 10x burst; 100% of extracted claims resolve to a 32-byte BLAKE3 root + `[byte_start, byte_end]` span in `< 15ms`.

### Lane 2 — Immutable Bitemporal Reality Spine (`packages/bitemporal-spine`)
- **Fixes Incident**: `INC-2026-089` (+14.2% illusory backtest alpha from mutated restatements)
- **Governing RFC**: `RFC-01` (Option B — Apache Iceberg Bitemporal Spine + DuckDB ASOF Compute)
- **Single-Engineer Stack**: DuckDB + Parquet/Iceberg append-only partitioning on `(t_known_date, entity_shard)`.
- **Hard Acceptance Gate**: Zero `UPDATE` or `DELETE` statements permitted on fact tables. All historical research queries MUST supply `as_of_t_known` and filter `t_known_from <= $as_of_t_known`.

### Lane 3 — Lock-Free MVCC & Epoch-CSR Causal Ontology (`packages/causal-ontology`)
- **Fixes Incident**: `INC-2026-094` (42-minute graph lock cascade during maritime chokepoint shock)
- **Governing RFC**: `RFC-02` (Option B — Append-Only MVCC Edge Log + 500ms Epoch CSR Snapshot)
- **Single-Engineer Stack**: Append-only edge log + double-buffered Compressed Sparse Row (`CSRGraphSnapshot`) arrays in memory (`row_ptr`, `col_idx`, `edge_weight`, `t_known`).
- **Hard Acceptance Gate**: Writers never block readers; 3-hop to 5-hop cross-silo supply-chain contagion traversal completes in `< 15ms`.

### Lane 4 — Streaming Divergence & Bayesian Falsification Gate (`packages/asymmetry-engine` & `packages/falsification-harness`)
- **Fixes Incidents**: `INC-2026-102` (6.4-hour batch delay) & `INC-2026-111` (Correlated cloud-cover sensor dropout false positive)
- **Governing RFCs**: `RFC-03` (Option A — Stateful Streaming ASOF Join) & `RFC-05` (Option A — Hierarchical Bayesian Observation-Channel SCM)
- **Single-Engineer Stack**: Incremental rolling Wasserstein-1 (`L1 Earth Mover`) divergence kernel + 5-gate Bayesian sensor-confounding refutation filter.
- **Hard Acceptance Gate**: End-to-end telemetry tick to falsified divergence signal `< 1,800ms`; correlated single-modality sensor dropouts discounted automatically when cross-modal corroboration is absent.

### Lane 5 — Epistemic-Weighted Fractional-Kelly Convex Execution (`packages/convex-execution`)
- **Fixes Bottleneck**: Uncalibrated position sizing ignoring provenance depth and link entropy
- **Governing Spec**: Master Spec v3.4 §6 (`CQ-05`)
- **Single-Engineer Stack**: Deterministic fractional-Kelly allocator attenuated by provenance fidelity score $D_{\text{epistemic}} \in [0, 1]$ and hard cluster drawdown governor ($\le 4.0\%$).
- **Hard Acceptance Gate**: Zero capital allocation if falsification survival probability $< 0.85$ or provenance depth $< 1.0$.

---

## 3. Execution Order for Downstream Build Agent (Cheaper/Faster Model Protocol)

When switching to a faster model to build out each lane:
1. Open `/docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md` and copy the target **Lane Build Prompt & Contract**.
2. Implement the pure domain kernel and data schema for that lane first, with zero UI coupling.
3. Run `npx --yes tsx --test` on the lane's unit test suite before wiring API routes or UI panels.
