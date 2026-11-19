# IDP PLATFORM — MASTER ARCHITECTURE ROADMAP, INCIDENT LEDGER & CONSULTANT DOSSIER

**Document ID**: `IDP-ARCH-2026-V3.4`  
**Status**: Canonical Architecture Baseline · Linked Across All 5 Critical Lanes  
**Cross-References**: `/AGENTS.md` · `/docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md`

---

## 1. Founder Vision & Constitutional Epistemic Invariants

The IDP platform is an empirical **Reality Research Platform** engineered to detect, model, falsify, and exploit **systemic asymmetries**—structural lags between primary physical/regulatory ground truth and consensus secondary narratives.

### Non-Negotiable System Invariants
1. **`INV-01` — Strict Bitemporal Epistemic Isolation (`State(Entity, t_valid, t_known)`)**:
   - Every fact, filing, physical sensor reading, and causal graph edge is immutable and dual-indexed by `t_valid` (when true in physical reality) and `t_known` (microsecond ingested by IDP).
   - *Violation Penalty*: +14.2% synthetic alpha inflation in backtests (`INC-2026-089`).
2. **`INV-02` — Primary-Source Telemetry Over Consensus Aggregation (`Divergence = |Telemetry_Primary(t) - Consensus_Implied(t)|`)**:
   - Ingest raw physical and regulatory telemetry (AIS vessel draughts, grid frequency harmonics, customs manifests, court dockets) prior to wire aggregation.
3. **`INV-03` — Automated Adversarial Falsification Harness (`P(Thesis | Counterfactual_Stress) > Threshold_Convex`)**:
   - Candidate divergences must survive 5 automated Bayesian null-hypothesis and sensor-confounding refutation gates before promotion.
4. **`INV-04` — Cryptographic Provenance to Raw Byte (`Signal_ID -> Merkle_Proof -> BLAKE3(Raw_Blob)`)**:
   - Every downstream signal weight resolves deterministically back to content-addressed raw captures within 500ms.

---

## 2. Production Incident Forensics Driving the Roadmap

| Incident ID | Severity | Affected Package | Blast Radius | Root Cause | Remediating RFC & Lane |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`INC-2026-089`** | Critical | `packages/bitemporal-spine` | +14.2% illusory alpha across 18 historical backtests | Restated filings overwrote `(entity_id, period)` in-place without appending new `t_known` slice. | `RFC-01` (Opt B) · **Lane 2** |
| **`INC-2026-094`** | Critical | `packages/causal-ontology` | 42-min stall; 1.8M AIS & customs events queued | Synchronous transitive closure locks during 1,400 vessel re-flaggings in 90s window. | `RFC-02` (Opt B) · **Lane 3** |
| **`INC-2026-102`** | High | `packages/asymmetry-engine` | 6.4-hr signal delay; 68% of move missed | 180ms telemetry intake waited for 6-hr scheduled batch join against consensus curves. | `RFC-03` (Opt A) · **Lane 4** |
| **`INC-2026-107`** | High | `packages/epistemic-intake` | 9 worker OOM restarts in 4 hours | Token-level provenance DAG created 450+ heap objects per parsed PDF page. | `RFC-04` (Opt B) · **Lane 1** |
| **`INC-2026-111`** | Moderate | `packages/falsification-harness` | 2 false-positive Tier-1 alerts escalated | Regional cloud occlusion across 4 smelters misinterpreted as coordinated production halt. | `RFC-05` (Opt A) · **Lane 4** |

---

## 3. Architectural Proposals (RFC Baseline Decisions)

- **`RFC-01` (Lane 2 — Bitemporal Spine)**: **Selected Option B** — Immutable Apache Iceberg / Parquet files partitioned by `(t_known_bucket, entity_shard)` queried via vectorized DuckDB / DataFusion `ASOF` joins (`+210ms` latency, `98%` fidelity, `$2,900/mo`).
- **`RFC-02` (Lane 3 — Causal Ontology)**: **Selected Option B** — Append-only RocksDB MVCC edge log paired with 500ms epoch-compiled Compressed Sparse Row (`CSR`) in-memory snapshots (`+85ms` latency, `97%` fidelity, `$3,100/mo`).
- **`RFC-03` (Lane 4 — Streaming Divergence)**: **Selected Option A** — Stateful streaming bi-stream `ASOF` join with bounded watermark lateness and incremental Wasserstein-1 distance (`+140ms` latency, `96%` fidelity, `$3,400/mo`).
- **`RFC-04` (Lane 1 — Provenance Tree)**: **Selected Option B** — Inline 32-byte BLAKE3 Merkle-Span proofs embedded in Arrow IPC / Parquet metadata footers (`+45ms` latency, `99%` fidelity, `$950/mo`).
- **`RFC-05` (Lane 4 — Falsification Gate)**: **Selected Option A** — Hierarchical Bayesian Observation-Channel Structural Causal Model (SCM) separating sensor dropout from physical state halts (`+280ms` latency, `96%` fidelity, `$3,800/mo`).

---

## 4. Multi-Dimensional Roadmap (Horizons 1–3)

### Horizon 1 (Days 0–90): Stabilization, Bitemporal Spine & Zero-Leakage Provenance
- **`MS-H1-01`**: Immutable Bitemporal Storage Spine (Iceberg + DuckDB Partitioning) — *5w, Core Data Track*
- **`MS-H1-02`**: Historical Restatement Audit & Backtest Replay Re-Certification — *3w, Epistemic QA*
- **`MS-H1-03`**: Lock-Free MVCC Causal Graph Partitioning & Incremental Entity Merge — *6w, Graph Systems*
- **`MS-H1-04`**: Merkle-Tree Compact Epistemic Provenance & CAS Ingestion Hardening — *4w, Sensorium Track*

### Horizon 2 (Days 90–180): Sub-Second Streaming Divergence & Falsification Lab
- **`MS-H2-01`**: Cross-Jurisdictional Dark-Data & Physical Supply-Chain Entity Linker — *6w, Graph Systems*
- **`MS-H2-02`**: Streaming Incremental Divergence Kernel (Stateful Dataflow) — *7w, Asymmetry Core*
- **`MS-H2-03`**: Automated Sensor-Confounding & Null-Hypothesis Falsification Gate — *5w, Epistemic QA*
- **`MS-H2-04`**: Multi-Modal Physical Telemetry Expansion (14 Primary Feeds) — *5w, Sensorium Track*
- **`MS-H2-05`**: Epistemic Confidence-Weighted Convex Sizing & Drawdown Governor — *4w, Convex Execution*

### Horizon 3 (Days 180–365): Autonomous Red-Teaming & Contagion Cascades
- **`MS-H3-01`**: Autonomous Counterfactual Red-Team Simulation Cluster — *8w, Asymmetry Core*
- **`MS-H3-02`**: Second-Order Causal Cascade & Cross-Market Contagion Simulator — *7w, Convex Execution*
- **`MS-H3-03`**: Zero-Trust Cryptographic Audit & Institutional Verification Portal — *5w, Core Data Track*
