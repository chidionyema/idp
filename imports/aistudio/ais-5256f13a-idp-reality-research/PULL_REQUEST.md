# Pull Request: IDP Master Architecture Roadmap, 5 Critical Lanes Spec & Reference Kernels

## Summary
This PR establishes the canonical **Multi-Dimensional Architecture Roadmap (Master Spec v3.4)**, **Single-Engineer Operational Specification**, **Production Incident Post-Mortem Ledger (`INC-2026-089` to `INC-2026-111`)**, **External Consultant Briefing Dossier**, and **Executable Reference Kernels** across all 5 Critical Engineering Lanes.

---

## Canonical Files Added / Updated

| File Path | Purpose |
| :--- | :--- |
| **`/AGENTS.md`** | Root agent & single-engineer routing manifest linking all 5 Critical Lanes and the 4 Constitutional Epistemic Invariants (`INV-01`–`INV-04`). |
| **`/docs/IDP_MASTER_ARCHITECTURE_AND_ROADMAP.md`** | Saved Founder Vision, Incident Forensics, RFC Baseline Decisions (`RFC-01`–`RFC-05`), and 3-Horizon Roadmap Matrix. |
| **`/docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md`** | Zero-bloat Single-Engineer Vertical Core specification (DuckDB/Iceberg bitemporal spine, RocksDB MVCC + CSR snapshots, BLAKE3 Merkle footers, streaming Wasserstein + Bayesian gate, fractional-Kelly sizing). |
| **`/src/lanes/operationalKernels.ts`** | Deterministic, zero-dependency reference kernels implementing all 5 critical lanes. |
| **`/src/utils/roadmapLogic.test.ts`** | 9 deterministic `node:test` unit tests verifying roadmap filtering, architecture simulation, consultant brief generation, and all 5 lane kernels. |

---

## The 5 Critical Engineering Lanes

- [x] **Lane 1 (`packages/epistemic-intake`)**: Compact BLAKE3 Merkle-Span Provenance Footer (`RFC-04` Opt B · fixes `INC-2026-107`)
- [x] **Lane 2 (`packages/bitemporal-spine`)**: Immutable Bitemporal Reality Spine & ASOF Point-in-Time Query (`RFC-01` Opt B · fixes `INC-2026-089`)
- [x] **Lane 3 (`packages/causal-ontology`)**: Lock-Free MVCC Edge Log & Epoch-CSR Contagion Traversal (`RFC-02` Opt B · fixes `INC-2026-094`)
- [x] **Lane 4 (`packages/asymmetry-engine`)**: Streaming Wasserstein-1 Divergence & Bayesian Sensor-Confounding Gate (`RFC-03` & `RFC-05` Opt A · fixes `INC-2026-102`, `INC-2026-111`)
- [x] **Lane 5 (`packages/convex-execution`)**: Epistemic-Weighted Fractional-Kelly Allocator & 4.0% Cluster Drawdown Governor (`CQ-05`)

---

## Verification & Test Gate
```bash
npx --yes tsx --test src/utils/roadmapLogic.test.ts
npm run build
```
