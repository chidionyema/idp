# IDP PLATFORM — SINGLE-ENGINEER OPERATIONAL SPECIFICATION & CODE BLUEPRINT

**Document ID**: `IDP-SPEC-SINGLE-ENG-2026`  
**Target Executor**: Single Senior Systems Engineer + Fast Downstream Coding Agent (Gemini Flash / Pro)  
**Design Principle**: **Zero Distributed-Systems Bloat**. Replace heavyweight multi-team clusters (Kafka + ZooKeeper + Spark + Neo4j Cluster + Kubernetes service mesh) with a **Single-Node / Embedded Vertical Core** capable of processing 25,000 events/sec on a single 64-core / 256GB RAM bare-metal or cloud instance using **DuckDB, Parquet, RocksDB, CSR Arrays, and BLAKE3**.

---

## 0. Why a Single Engineer Can Run This Entire Stack

| Traditional Multi-Team Stack (Avoid) | IDP Single-Engineer Embedded Equivalent (Use) | Operational Savings |
| :--- | :--- | :--- |
| Kafka + ZooKeeper + Schema Registry | Single-binary **Redpanda** or embedded **SQLite WAL / Arrow Flight ring buffer** | Zero JVM tuning; 1 binary |
| Apache Spark / Flink JVM Cluster | Embedded **DuckDB** + **Polars** + stateful **Rust/TypeScript ring buffers** | 10x lower memory; instant local testability |
| Neo4j / Memgraph Sharded Cluster | Append-only **Edge Log** + in-memory **Compressed Sparse Row (CSR)** typed arrays | Wait-free 5-hop reads in `<5ms`; zero lock cascade |
| Marquez / OpenLineage Postgres Server | Inline **BLAKE3 Merkle Root + Span Footer** inside Parquet/Arrow metadata | $O(1)$ worker heap; zero external DB drift |

---

## LANE 1: Epistemic Intake & BLAKE3 Merkle Provenance (`packages/epistemic-intake`)

### 1.1 Exact Data Contract & Memory-Bounded Merkle Builder
Every raw payload (EDGAR filing, AIS binary frame, grid frequency sample, customs manifest) is hashed once on arrival using `BLAKE3`. Extracted claims store only a 32-byte root hash and `[byteStart, byteEnd]` offsets—never full parent DOM/token trees in RAM.

```typescript
export interface RawCaptureBlob {
  blake3Hash: string;        // 64-char hex BLAKE3 digest of raw bytes
  sourceFeedId: string;      // e.g. "AIS_STRAIT_HORMUZ" | "SEC_EDGAR_8K"
  tKnownMicros: bigint;      // Monotonic ingestion wall-clock (INV-01)
  byteLength: number;
  storageUri: string;        // e.g. "cas://blake3/9f86d081884c7d65..."
}

export interface ProvenanceSpanProof {
  rawBlobHash: string;       // Points to RawCaptureBlob.blake3Hash
  byteStart: number;         // Inclusive byte offset in raw capture
  byteEnd: number;           // Exclusive byte offset in raw capture
  parserVersion: string;     // Deterministic parser semver
  merkleRootHash: string;    // Compact batch Merkle root
}
```

### 1.2 Single-Engineer Verification Check
- Assert that ingesting 10,000 claims from a 200MB filing allocates `< 5MB` of provenance metadata and verifies any claim span in `< 1ms`.

---

## LANE 2: Immutable Bitemporal Reality Spine (`packages/bitemporal-spine`)

### 2.1 DuckDB / Iceberg Bitemporal Schema (Zero Look-Ahead Leakage)
Never run `UPDATE` or `DELETE` on `bitemporal_facts`. Restatements append a new row with the same `t_valid_from` and a newer `t_known_from`.

```sql
CREATE TABLE IF NOT EXISTS bitemporal_facts (
  fact_id VARCHAR NOT NULL,
  entity_id VARCHAR NOT NULL,
  metric_key VARCHAR NOT NULL,
  metric_value DOUBLE NOT NULL,
  -- Valid TimeAxis: When the event occurred in physical reality
  t_valid_from BIGINT NOT NULL,
  t_valid_to BIGINT,
  -- Transaction TimeAxis: When IDP ingested/observed the assertion
  t_known_from BIGINT NOT NULL,
  -- Cryptographic Lineage (INV-04)
  raw_blob_blake3 VARCHAR NOT NULL,
  byte_span_start INTEGER NOT NULL,
  byte_span_end INTEGER NOT NULL
);

-- Canonical Point-in-Time Query (Guaranteed Zero Look-Ahead Leakage)
-- Reconstructs the exact latest state known to IDP at $as_of_t_known
SELECT
  entity_id,
  metric_key,
  arg_max(metric_value, t_known_from) AS known_value,
  max(t_valid_from) AS valid_timestamp,
  arg_max(raw_blob_blake3, t_known_from) AS provenance_hash
FROM bitemporal_facts
WHERE entity_id = $entity_id
  AND t_known_from <= $as_of_t_known
  AND t_valid_from <= $as_of_t_valid
GROUP BY entity_id, metric_key;
```

---

## LANE 3: Lock-Free MVCC & Epoch-CSR Causal Ontology (`packages/causal-ontology`)

### 3.1 Double-Buffered Compressed Sparse Row (`CSR`) Graph Kernel
All incoming ownership/supply-chain links append to a flat log. Every 500ms, a background worker compiles a compact immutable `CSRGraphSnapshot` using flat `Int32Array` and `Float64Array` buffers. Readers acquire an atomic reference to the latest snapshot (`t_known <= query_t_known`) with **zero locks**.

```typescript
export interface CSRGraphSnapshot {
  epochTKnownMicros: bigint;
  nodeCount: number;
  rowPtr: Int32Array;        // Length: nodeCount + 1
  colIdx: Int32Array;        // Target node indices for outgoing edges
  edgeWeights: Float64Array; // Calibrated causal propagation weights [0..1]
  edgeConfidence: Float64Array; // Splink entity-resolution probability
}
```

---

## LANE 4: Streaming Divergence & Bayesian Falsification (`packages/asymmetry-engine`)

### 4.1 Incremental Wasserstein-1 Divergence + Sensor-Confounding Gate
Computes empirical divergence between physical sensor quantiles and consensus implied quantiles, then attenuates the raw divergence by the **Bayesian Sensor-Confounding Posterior** (preventing correlated weather/cloud/API dropouts from triggering false alerts).

```typescript
export interface DivergenceAssessment {
  entityId: string;
  tKnownMicros: bigint;
  wassersteinDistance: number;
  sensorHealthPosterior: number;   // [0..1] P(Sensor_Intact | CrossModal_Corroboration)
  nullHypothesisPValue: number;    // Must be < 0.01 to pass Gate 3
  effectiveAsymmetryScore: number; // wassersteinDistance * sensorHealthPosterior
  promotedToExecution: boolean;
}
```

---

## LANE 5: Epistemic-Weighted Fractional-Kelly Execution (`packages/convex-execution`)

### 5.1 Closed-Form Sizing Law (`CQ-05`)
Position size $f^*$ is bounded by the classical Kelly fraction $f_{\text{Kelly}}$, discounted by provenance fidelity $D_{\text{prov}} \in [0, 1]$, causal graph link certainty $C_{\text{graph}} \in [0, 1]$, and hard cluster drawdown cap $f_{\max} = 0.04$:

$$f^* = \min\left( f_{\max}, \quad \gamma \cdot f_{\text{Kelly}} \cdot D_{\text{prov}} \cdot C_{\text{graph}} \cdot P(\text{Falsification\_Survived}) \right)$$
