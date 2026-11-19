export type ArchitecturalPlane =
  | 'Ingestion & Sensorium'
  | 'Bitemporal Ontology & Graph'
  | 'Asymmetry & Falsification Engine'
  | 'Convex Execution & Simulation'
  | 'Governance & Epistemic Audit';

export type HorizonId = 'H1' | 'H2' | 'H3';

export type AsymmetryVector =
  | 'Information Latency Arbitrage'
  | 'Cross-Silo Structural Blindspot'
  | 'Narrative-vs-Telemetry Divergence'
  | 'Tail-Risk Convexity';

export type MilestoneStatus = 'Completed' | 'In Progress' | 'Blocked by RFC' | 'Planned';

export interface RepoModuleSpec {
  id: string;
  path: string;
  plane: ArchitecturalPlane;
  title: string;
  stack: string;
  specVersion: string;
  complianceScore: number;
  p99LatencyMs: number;
  summary: string;
  founderMandate: string;
  bottleneck: string;
}

export interface IncidentRecord {
  id: string;
  date: string;
  title: string;
  severity: 'Critical' | 'High' | 'Moderate';
  plane: ArchitecturalPlane;
  affectedModule: string;
  status: 'Mitigated — Architectural Fix Pending' | 'Resolved in H1' | 'Active Bottleneck';
  blastRadiusMetric: string;
  rootCause: string;
  immediateMitigation: string;
  linkedRfcId: string;
  linkedMilestoneIds: string[];
}

export interface RoadmapMilestone {
  id: string;
  title: string;
  horizon: HorizonId;
  plane: ArchitecturalPlane;
  asymmetryVector: AsymmetryVector;
  status: MilestoneStatus;
  effortWeeks: number;
  ownerTrack: string;
  linkedIncidentIds: string[];
  linkedRfcId: string;
  dependencies: string[];
  thesisImpact: string;
  deliverables: string[];
  acceptanceMetric: string;
}

export interface RfcOption {
  id: 'A' | 'B' | 'C';
  label: string;
  architectureSummary: string;
  latencyImpactMs: number;
  monthlyInfraCostUsd: number;
  bitemporalFidelityScore: number; // 0-100
  asymmetryCaptureLiftPct: number;
  implementationWeeks: number;
  pros: string[];
  cons: string[];
  recommended?: boolean;
}

export interface ArchitectureProposalRfc {
  id: string;
  title: string;
  plane: ArchitecturalPlane;
  horizon: HorizonId;
  status: 'Under Consultant Review' | 'Decision Needed' | 'Approved Baseline';
  linkedIncidents: string[];
  problemStatement: string;
  asymmetryExploitationRationale: string;
  consultantPromptQuestion: string;
  selectedOptionId: 'A' | 'B' | 'C';
  options: RfcOption[];
}

export interface ConsultantQuestion {
  id: string;
  domain: string;
  priority: 'P0 — Blocking H1' | 'P1 — Architecture Sign-off' | 'P2 — Optimization';
  question: string;
  contextRef: string;
  expectedDeliverable: string;
  includedInBrief: boolean;
}

export const FOUNDER_VISION_INVARIANTS = [
  {
    id: 'INV-01',
    title: 'Strict Bitemporal Epistemic Isolation',
    formula: 'State(Entity, t_valid, t_known)',
    mandate:
      'Every assertion, filing, physical measurement, and graph edge must be indexed on both valid-time (when true in physical reality) and transaction-time (when ingested and known to IDP). Zero look-ahead leakage is permitted in historical simulation.',
    violationCost: 'Synthetic backtest alpha inflation (+14.2% false edge observed in INC-2026-089).',
  },
  {
    id: 'INV-02',
    title: 'Primary-Source Telemetry Over Consensus Aggregation',
    formula: 'Divergence = |Telemetry_Primary(t) - Consensus_Implied(t)|',
    mandate:
      'Systemic asymmetries live in the structural lag between physical/regulatory primary reality (AIS vessel draughts, grid load harmonics, customs manifests, court dockets) and consensus secondary narratives.',
    violationCost: 'Decay of structural edge into crowded factor beta within <150ms of headline publication.',
  },
  {
    id: 'INV-03',
    title: 'Automated Adversarial Falsification Harness',
    formula: 'P(Thesis | Counterfactual_Stress) > Threshold_Convex',
    mandate:
      'The platform is a falsification engine, not a confirmation engine. Every candidate asymmetry signal must automatically spawn red-team null-hypothesis agents attempting to explain the anomaly via sensor noise, seasonal artifacts, or data corruption.',
    violationCost: 'Allocation to spurious correlations during regime transitions.',
  },
  {
    id: 'INV-04',
    title: 'Cryptographic Provenance to Raw Byte',
    formula: 'Signal_ID -> DAG(Transform_Hash) -> BLAKE3(Raw_Blob)',
    mandate:
      'Every downstream decision weight or causal graph link must be deterministically reconstructible from content-addressed raw captures within 500ms for institutional audit and post-mortem replay.',
    violationCost: 'Opaque black-box failure modes when upstream schema drift occurs (INC-2026-107).',
  },
];

export const REPO_MODULE_SPECS: RepoModuleSpec[] = [
  {
    id: 'MOD-INTAKE',
    path: 'packages/epistemic-intake',
    plane: 'Ingestion & Sensorium',
    title: 'Multi-Modal Primary Sensorium & CAS Ingestion',
    stack: 'Rust / Tokio, Redpanda, Apache Arrow Flight, BLAKE3 CAS',
    specVersion: 'Master Spec v3.4 §2',
    complianceScore: 78,
    p99LatencyMs: 420,
    summary:
      'Ingests heterogeneous unstructured filings, satellite/physical telemetry streams, and regulatory feeds into content-addressed Arrow record batches.',
    founderMandate: 'Sub-500ms primary capture with zero silent schema coercion.',
    bottleneck: 'Unbounded lineage metadata growth during burst scraping (INC-2026-107).',
  },
  {
    id: 'MOD-BITEMPORAL',
    path: 'packages/bitemporal-spine',
    plane: 'Bitemporal Ontology & Graph',
    title: 'Point-in-Time Bitemporal Ledger & Time-Travel Spine',
    stack: 'DuckDB / Iceberg + Custom Rust Temporal Compaction',
    specVersion: 'Master Spec v3.4 §3.1',
    complianceScore: 62,
    p99LatencyMs: 1850,
    summary:
      'Maintains immutable valid-time vs. transaction-time intervals for all entities, enabling exact historical reality reconstruction at any microsecond t_known.',
    founderMandate: 'Deterministic point-in-time queries with zero retroactive overwrite.',
    bottleneck: 'Upsert path in legacy Postgres table mutated t_known on restated filings (INC-2026-089).',
  },
  {
    id: 'MOD-ONTOLOGY',
    path: 'packages/causal-ontology',
    plane: 'Bitemporal Ontology & Graph',
    title: 'Cross-Silo Entity Resolution & Causal Dependency Graph',
    stack: 'Rust Petgraph + RocksDB State Store + Probabilistic Splink',
    specVersion: 'Master Spec v3.4 §3.2',
    complianceScore: 68,
    p99LatencyMs: 3100,
    summary:
      'Resolves obfuscated subsidiaries, supply-chain nodes, and regulatory obligors across jurisdictions into a unified directed causal hypergraph.',
    founderMandate: 'incremental graph merge without global write locks under high-velocity shocks.',
    bottleneck: 'Synchronous graph merge lock contention during macro supply shock (INC-2026-094).',
  },
  {
    id: 'MOD-ASYMMETRY',
    path: 'packages/asymmetry-engine',
    plane: 'Asymmetry & Falsification Engine',
    title: 'Systemic Divergence Detector & Structural Mispricing Kernel',
    stack: 'Python / Polars, JAX, Rust PyO3 Vector Kernels',
    specVersion: 'Master Spec v3.4 §4',
    complianceScore: 74,
    p99LatencyMs: 6400,
    summary:
      'Continuously computes Kullback-Leibler divergence and structural wasserstein distance between empirical physical telemetry and market/consensus implied distributions.',
    founderMandate: 'Continuous streaming divergence detection decoupled from batch EOD windows.',
    bottleneck: '6.4-hour batch coupling delayed physical-to-consensus reconciliation (INC-2026-102).',
  },
  {
    id: 'MOD-FALSIFY',
    path: 'packages/falsification-harness',
    plane: 'Asymmetry & Falsification Engine',
    title: 'Counterfactual Red-Team & Null-Hypothesis Sandbox',
    stack: 'JAX / NumPyro, Deterministic Replay Containers',
    specVersion: 'Master Spec v3.4 §5',
    complianceScore: 59,
    p99LatencyMs: 8900,
    summary:
      'Executes automated Bayesian refutation tests, synthetic instrument dropouts, and regime-shift stress tests against candidate asymmetry theses.',
    founderMandate: 'Every promoted thesis must pass 5 automated falsification gates.',
    bottleneck: 'Sequential Monte Carlo execution starves GPU/CPU pool during concurrent anomalies.',
  },
  {
    id: 'MOD-CONVEX',
    path: 'packages/convex-execution',
    plane: 'Convex Execution & Simulation',
    title: 'Asymmetric Payoff Structuring & Decision Playbook Engine',
    stack: 'Rust / TypeScript Control Plane, Fix/API Execution Adapters',
    specVersion: 'Master Spec v3.4 §6',
    complianceScore: 81,
    p99LatencyMs: 310,
    summary:
      'Translates validated reality divergences into sizing curves, drawdown-bounded convex structures, and human-in-the-loop research dossiers.',
    founderMandate: 'Strict fractional-Kelly sizing weighted by epistemic confidence & provenance depth.',
    bottleneck: 'Lacks real-time correlation decay feedback from live execution slippage.',
  },
];

export const INITIAL_INCIDENTS: IncidentRecord[] = [
  {
    id: 'INC-2026-089',
    date: '2026-09-14',
    title: 'Bitemporal Look-Ahead Leakage in Restated Regulatory Filings',
    severity: 'Critical',
    plane: 'Bitemporal Ontology & Graph',
    affectedModule: 'packages/bitemporal-spine',
    status: 'Mitigated — Architectural Fix Pending',
    blastRadiusMetric: '+14.2% illusory alpha inflation across 18 historical asymmetry simulations',
    rootCause:
      'When upstream issuers filed amended restatements, the ingestion upsert key matched on (entity_id, reporting_period) without appending a new transaction_time (t_known) slice, mutating historical state in-place.',
    immediateMitigation:
      'Disabled in-place SQL updates on core fact tables and enforced append-only WAL snapshots, increasing query latency by 3.4x.',
    linkedRfcId: 'RFC-01',
    linkedMilestoneIds: ['MS-H1-01', 'MS-H1-02'],
  },
  {
    id: 'INC-2026-094',
    date: '2026-09-28',
    title: 'Entity Resolution Graph Lock Cascade During Maritime Chokepoint Shock',
    severity: 'Critical',
    plane: 'Bitemporal Ontology & Graph',
    affectedModule: 'packages/causal-ontology',
    status: 'Active Bottleneck',
    blastRadiusMetric: '42-minute pipeline stall; 1.8M primary AIS & customs events queued',
    rootCause:
      'Transitive closure recalculation on corporate beneficial ownership edges acquired coarse partition locks when 1,400 vessel re-flaggings and shell entity updates arrived within a 90-second window.',
    immediateMitigation:
      'Throttled probabilistic entity resolution batch size to 250 entities/tick and deferred multi-hop transitive propagation.',
    linkedRfcId: 'RFC-02',
    linkedMilestoneIds: ['MS-H1-03', 'MS-H2-01'],
  },
  {
    id: 'INC-2026-102',
    date: '2026-10-09',
    title: 'Consensus-vs-Telemetry Divergence Window Missed Due to Batch Coupling',
    severity: 'High',
    plane: 'Asymmetry & Falsification Engine',
    affectedModule: 'packages/asymmetry-engine',
    status: 'Active Bottleneck',
    blastRadiusMetric: '6.4-hour signal delay; 68% of asymmetric payoff captured by market before alert',
    rootCause:
      'Physical grid telemetry was ingested in real time (180ms), but the divergence kernel waited for the 6-hour scheduled normalization join against consensus curve snapshots.',
    immediateMitigation:
      'Added ad-hoc cron triggers every 30 minutes for top-20 watched macro commodities, causing high redundant compute load.',
    linkedRfcId: 'RFC-03',
    linkedMilestoneIds: ['MS-H2-02', 'MS-H2-03'],
  },
  {
    id: 'INC-2026-107',
    date: '2026-10-19',
    title: 'Unbounded Epistemic Lineage DAG OOM on Unstructured Ingestion Workers',
    severity: 'High',
    plane: 'Ingestion & Sensorium',
    affectedModule: 'packages/epistemic-intake',
    status: 'Mitigated — Architectural Fix Pending',
    blastRadiusMetric: '9 ingestion worker OOM restarts over 4 hours; 0 data loss (Redpanda replay)',
    rootCause:
      'Token-level provenance tracking generated 450+ fine-grained DAG edges per parsed PDF page in memory before flushing to the content-addressed store.',
    immediateMitigation:
      'Coarsened lineage granularity from token-span level to document-section chunk level until compact Merkle-proof tree is implemented.',
    linkedRfcId: 'RFC-04',
    linkedMilestoneIds: ['MS-H1-04', 'MS-H2-04'],
  },
  {
    id: 'INC-2026-111',
    date: '2026-10-25',
    title: 'False-Positive Asymmetry Promotion from Correlated Sensor Dropout',
    severity: 'Moderate',
    plane: 'Asymmetry & Falsification Engine',
    affectedModule: 'packages/falsification-harness',
    status: 'Active Bottleneck',
    blastRadiusMetric: '2 false-positive Tier-1 asymmetry alerts escalated to research desk',
    rootCause:
      'Regional cloud-cover occlusion degraded optical satellite thermal readings across 4 smelting facilities simultaneously; the divergence engine interpreted correlated missingness as a coordinated production halt.',
    immediateMitigation:
      'Added manual sensor-health check gate in analyst playbook before capital sizing calculation.',
    linkedRfcId: 'RFC-05',
    linkedMilestoneIds: ['MS-H2-03', 'MS-H3-01'],
  },
];

export const INITIAL_MILESTONES: RoadmapMilestone[] = [
  {
    id: 'MS-H1-01',
    title: 'Immutable Bitemporal Storage Spine (Apache Iceberg + DuckDB Partitioning)',
    horizon: 'H1',
    plane: 'Bitemporal Ontology & Graph',
    asymmetryVector: 'Information Latency Arbitrage',
    status: 'In Progress',
    effortWeeks: 5,
    ownerTrack: 'Core Data & Storage Track',
    linkedIncidentIds: ['INC-2026-089'],
    linkedRfcId: 'RFC-01',
    dependencies: [],
    thesisImpact:
      'Eliminates 100% of retroactive look-ahead bias in backtesting; guarantees microsecond-exact point-in-time state reconstruction.',
    deliverables: [
      'Dual-axis (t_valid_from/to, t_known_from/to) Iceberg table format spec',
      'Automated CI look-ahead leakage detector testing 50 historical restatement scenarios',
      'Zero-copy Arrow Flight reader for point-in-time research notebooks',
    ],
    acceptanceMetric: '0 bytes mutated in-place; P99 point-in-time snapshot query < 250ms over 10TB.',
  },
  {
    id: 'MS-H1-02',
    title: 'Historical Restatement Audit & Backtest Replay Re-Certification',
    horizon: 'H1',
    plane: 'Governance & Epistemic Audit',
    asymmetryVector: 'Narrative-vs-Telemetry Divergence',
    status: 'Planned',
    effortWeeks: 3,
    ownerTrack: 'Epistemic QA & Quant Research',
    linkedIncidentIds: ['INC-2026-089'],
    linkedRfcId: 'RFC-01',
    dependencies: ['MS-H1-01'],
    thesisImpact:
      'Re-establishes institutional ground truth across all 42 active asymmetry strategies post INC-2026-089.',
    deliverables: [
      'Automated diff report comparing pre-fix vs. bitemporal-certified strategy Sharpe and payoff skewness',
      'Immutable cryptographic attestation of historical training splits',
    ],
    acceptanceMetric: '100% of historical thesis models re-certified with zero t_known contamination.',
  },
  {
    id: 'MS-H1-03',
    title: 'Lock-Free MVCC Causal Graph Partitioning & Incremental Entity Merge',
    horizon: 'H1',
    plane: 'Bitemporal Ontology & Graph',
    asymmetryVector: 'Cross-Silo Structural Blindspot',
    status: 'Blocked by RFC',
    effortWeeks: 6,
    ownerTrack: 'Graph & Ontology Systems',
    linkedIncidentIds: ['INC-2026-094'],
    linkedRfcId: 'RFC-02',
    dependencies: ['MS-H1-01'],
    thesisImpact:
      'Enables real-time cross-jurisdictional subsidiary and supply-chain shock propagation without write-lock stalls.',
    deliverables: [
      'CRDT/MVCC edge version log decoupling entity ingestion from transitive closure computation',
      'Subgraph neighborhood isolation for bounded 3-hop causal impact queries',
    ],
    acceptanceMetric: 'Sustain 25,000 entity updates/sec with P99 merge latency < 120ms and zero global locks.',
  },
  {
    id: 'MS-H1-04',
    title: 'Merkle-Tree Compact Epistemic Provenance & CAS Ingestion Hardening',
    horizon: 'H1',
    plane: 'Ingestion & Sensorium',
    asymmetryVector: 'Information Latency Arbitrage',
    status: 'In Progress',
    effortWeeks: 4,
    ownerTrack: 'Sensorium & Intake Engineering',
    linkedIncidentIds: ['INC-2026-107'],
    linkedRfcId: 'RFC-04',
    dependencies: [],
    thesisImpact:
      'Bounds worker memory footprint while preserving cryptographic byte-level lineage from raw document/telemetry capture to thesis assertion.',
    deliverables: [
      'Hierarchical BLAKE3 Merkle proof tree replacing flat in-memory DAG edges',
      'Zero-allocation Rust streaming parser for PDF/EDGAR/customs feeds',
    ],
    acceptanceMetric: 'Worker heap usage capped < 1.5GB under 10x burst load; lineage verification < 15ms.',
  },
  {
    id: 'MS-H2-01',
    title: 'Cross-Jurisdictional Dark-Data & Physical Supply-Chain Entity Linker',
    horizon: 'H2',
    plane: 'Bitemporal Ontology & Graph',
    asymmetryVector: 'Cross-Silo Structural Blindspot',
    status: 'Planned',
    effortWeeks: 6,
    ownerTrack: 'Graph & Ontology Systems',
    linkedIncidentIds: ['INC-2026-094'],
    linkedRfcId: 'RFC-02',
    dependencies: ['MS-H1-03'],
    thesisImpact:
      'Uncovers tier-2 and tier-3 supplier dependencies invisible to consensus equity/credit analysts.',
    deliverables: [
      'Probabilistic entity resolution kernel linking bills of lading, LEI registries, and facility permits',
      'Calibrated epistemic uncertainty scores on every inferred graph edge',
    ],
    acceptanceMetric: 'Precision >= 96.5% and Recall >= 89% on golden tier-3 supply-chain benchmark.',
  },
  {
    id: 'MS-H2-02',
    title: 'Streaming Incremental Divergence Kernel (Stateful Dataflow Engine)',
    horizon: 'H2',
    plane: 'Asymmetry & Falsification Engine',
    asymmetryVector: 'Narrative-vs-Telemetry Divergence',
    status: 'Blocked by RFC',
    effortWeeks: 7,
    ownerTrack: 'Asymmetry Core Kernel',
    linkedIncidentIds: ['INC-2026-102'],
    linkedRfcId: 'RFC-03',
    dependencies: ['MS-H1-01', 'MS-H1-04'],
    thesisImpact:
      'Compresses physical-telemetry-to-consensus divergence detection from 6.4 hours down to sub-2-second streaming windows.',
    deliverables: [
      'Incremental stateful stream processor (Arroyo / Timely Dataflow / Rust) joining primary telemetry with live implied market distributions',
      'Dynamic regime-aware Wasserstein distance thresholds',
    ],
    acceptanceMetric: 'End-to-end telemetry arrival to divergence signal emission P99 < 1,800ms.',
  },
  {
    id: 'MS-H2-03',
    title: 'Automated Sensor-Confounding & Null-Hypothesis Falsification Gate',
    horizon: 'H2',
    plane: 'Asymmetry & Falsification Engine',
    asymmetryVector: 'Narrative-vs-Telemetry Divergence',
    status: 'Planned',
    effortWeeks: 5,
    ownerTrack: 'Epistemic QA & Quant Research',
    linkedIncidentIds: ['INC-2026-111'],
    linkedRfcId: 'RFC-05',
    dependencies: ['MS-H2-02'],
    thesisImpact:
      'Prevents correlated sensor dropouts (weather, satellite occlusion, scraper blocks) from masquerading as real-world economic anomalies.',
    deliverables: [
      'Bayesian confounding model explicitly modeling sensor availability and environmental occlusion',
      'Mandatory 5-stage automated falsification scorecard before any alert reaches Convex Execution plane',
    ],
    acceptanceMetric: 'Reduce false-positive anomaly escalations by >= 85% on historical replay corpus.',
  },
  {
    id: 'MS-H2-04',
    title: 'Multi-Modal Physical Telemetry Expansion (AIS, Grid Harmonics, Customs)',
    horizon: 'H2',
    plane: 'Ingestion & Sensorium',
    asymmetryVector: 'Information Latency Arbitrage',
    status: 'Planned',
    effortWeeks: 5,
    ownerTrack: 'Sensorium & Intake Engineering',
    linkedIncidentIds: ['INC-2026-107'],
    linkedRfcId: 'RFC-04',
    dependencies: ['MS-H1-04'],
    thesisImpact:
      'Expands primary reality coverage across 14 new physical bottleneck indicators with zero consensus overlap.',
    deliverables: [
      'Unified schema registry and dead-letter self-healing adapters for 14 physical feeds',
      'Automated source latency & staleness watermarking',
    ],
    acceptanceMetric: '99.95% feed availability with automated drift quarantine within 30 seconds.',
  },
  {
    id: 'MS-H2-05',
    title: 'Epistemic Confidence-Weighted Convex Sizing & Drawdown Governor',
    horizon: 'H2',
    plane: 'Convex Execution & Simulation',
    asymmetryVector: 'Tail-Risk Convexity',
    status: 'Planned',
    effortWeeks: 4,
    ownerTrack: 'Convex Execution & Risk',
    linkedIncidentIds: ['INC-2026-102'],
    linkedRfcId: 'RFC-06',
    dependencies: ['MS-H2-02', 'MS-H2-03'],
    thesisImpact:
      'Couples position/allocation sizing directly to provenance depth, falsification survival score, and liquidity asymmetry.',
    deliverables: [
      'Continuous fractional-Kelly optimizer parameterized by posterior epistemic uncertainty',
      'Automated tail-hedge structuring calculator for asymmetric payoff profiles',
    ],
    acceptanceMetric: 'Improve Sortino ratio by >= 0.65 and cap max cluster drawdown at 4.0% in stress replay.',
  },
  {
    id: 'MS-H3-01',
    title: 'Autonomous Counterfactual Red-Team Simulation Cluster',
    horizon: 'H3',
    plane: 'Asymmetry & Falsification Engine',
    asymmetryVector: 'Tail-Risk Convexity',
    status: 'Planned',
    effortWeeks: 8,
    ownerTrack: 'Asymmetry Core Kernel',
    linkedIncidentIds: ['INC-2026-111'],
    linkedRfcId: 'RFC-05',
    dependencies: ['MS-H2-03'],
    thesisImpact:
      'Continuously synthesizes adversarial macro/supply-chain shock scenarios to discover hidden fragility in both market consensus and IDP theses.',
    deliverables: [
      'Distributed JAX counterfactual shock generator running 100,000 structural perturbations/hour',
      'Automated fragility surface maps across the causal ontology graph',
    ],
    acceptanceMetric: 'Identify >= 90% of synthetic planted structural vulnerabilities within 15 minutes.',
  },
  {
    id: 'MS-H3-02',
    title: 'Second-Order Causal Cascade & Cross-Market Contagion Simulator',
    horizon: 'H3',
    plane: 'Convex Execution & Simulation',
    asymmetryVector: 'Cross-Silo Structural Blindspot',
    status: 'Planned',
    effortWeeks: 7,
    ownerTrack: 'Convex Execution & Risk',
    linkedIncidentIds: ['INC-2026-094', 'INC-2026-102'],
    linkedRfcId: 'RFC-06',
    dependencies: ['MS-H2-01', 'MS-H2-05'],
    thesisImpact:
      'Exploits 2nd- and 3rd-order contagion lags where primary shock is priced in, but downstream derivative bottlenecks remain unpriced for days.',
    deliverables: [
      'Multi-hop causal impulse-response simulator calibrated on historical supply & liquidity cascades',
      'Automated cross-asset asymmetry basket generator',
    ],
    acceptanceMetric: 'Capture >= 35% incremental asymmetric return from 2nd/3rd-hop nodes in out-of-sample tests.',
  },
  {
    id: 'MS-H3-03',
    title: 'Zero-Trust Cryptographic Audit & External Institutional Verification Portal',
    horizon: 'H3',
    plane: 'Governance & Epistemic Audit',
    asymmetryVector: 'Narrative-vs-Telemetry Divergence',
    status: 'Planned',
    effortWeeks: 5,
    ownerTrack: 'Core Data & Storage Track',
    linkedIncidentIds: ['INC-2026-089', 'INC-2026-107'],
    linkedRfcId: 'RFC-04',
    dependencies: ['MS-H1-02', 'MS-H1-04'],
    thesisImpact:
      'Provides verifiable, institutional-grade proof of non-leakage and primary-source provenance for external partners and auditors.',
    deliverables: [
      'Deterministic replay verifier CLI & read-only audit enclave',
      'Complete cryptographic proof bundle export for any historical thesis decision',
    ],
    acceptanceMetric: '100% deterministic reproduction of any historical signal state within 30 seconds.',
  },
];

export const INITIAL_RFCS: ArchitectureProposalRfc[] = [
  {
    id: 'RFC-01',
    title: 'Bitemporal Reality Ledger Storage Engine & Point-in-Time Query Spine',
    plane: 'Bitemporal Ontology & Graph',
    horizon: 'H1',
    status: 'Under Consultant Review',
    linkedIncidents: ['INC-2026-089'],
    problemStatement:
      'IDP requires strict separation of valid_time (when an event occurred in physical reality) and transaction_time (when IDP observed/ingested it). Legacy relational upserts caused look-ahead leakage during restated filings, while naive append-only logs degraded point-in-time join latency by 3.4x.',
    asymmetryExploitationRationale:
      'Exploiting information latency asymmetries requires knowing with microsecond precision what the market knew at t_0 versus what physical telemetry revealed at t_0, without contamination from restatements arriving at t_1.',
    consultantPromptQuestion:
      'Given our 15TB/year primary telemetry + filing growth and heavy point-in-time range joins across 5,000+ entities, should we standardize on custom Apache Iceberg bitemporal partitioning with DuckDB/DataFusion workers (Option B), or adopt a dedicated immutable bitemporal database such as XTDB v2 (Option C)?',
    selectedOptionId: 'B',
    options: [
      {
        id: 'A',
        label: 'Option A: Postgres Temporal Tables + TimescaleDB Hypertables',
        architectureSummary:
          'Retain PostgreSQL with range types (tstzrange) for valid_time and transaction_time, accelerated by TimescaleDB compression and GiST exclusion constraints.',
        latencyImpactMs: 920,
        monthlyInfraCostUsd: 4200,
        bitemporalFidelityScore: 88,
        asymmetryCaptureLiftPct: 8,
        implementationWeeks: 3,
        pros: [
          'Minimal migration friction from existing SQL schema',
          'Strong ACID guarantees and native GiST range indexing',
        ],
        cons: [
          'Poor columnar scan performance on wide point-in-time backtest sweeps',
          'Index bloat under high-frequency telemetry restatements',
        ],
      },
      {
        id: 'B',
        label: 'Option B: Apache Iceberg Bitemporal Spine + Rust DataFusion / DuckDB Compute',
        architectureSummary:
          'Immutable Parquet data files managed by Apache Iceberg with explicit (t_known_bucket, entity_shard) partitioning, queried via embedded Rust DataFusion & DuckDB vectorized ASOF/bitemporal joins.',
        latencyImpactMs: 210,
        monthlyInfraCostUsd: 2900,
        bitemporalFidelityScore: 98,
        asymmetryCaptureLiftPct: 24,
        implementationWeeks: 5,
        recommended: true,
        pros: [
          'Zero-copy Arrow Flight integration with JAX/Polars research kernels',
          'Physical immutability guarantees zero in-place mutation by design',
          '10x faster historical simulation sweeps at 30% lower storage cost',
        ],
        cons: [
          'Requires custom compaction coordinator to optimize small streaming micro-batches',
        ],
      },
      {
        id: 'C',
        label: 'Option C: Native Bitemporal Graph-Document Store (XTDB v2 / Arrow Native)',
        architectureSummary:
          'Migrate core fact ledger to XTDB v2 (built natively on Apache Arrow & object storage with first-class SQL/Datalog bitemporal semantics).',
        latencyImpactMs: 340,
        monthlyInfraCostUsd: 3600,
        bitemporalFidelityScore: 100,
        asymmetryCaptureLiftPct: 21,
        implementationWeeks: 7,
        pros: [
          'Out-of-the-box bitemporal SQL semantics without manual interval maintenance',
          'Unified temporal + document/graph query model',
        ],
        cons: [
          'Smaller operational ecosystem and higher learning curve for engineering team',
          'Requires adapter layer for custom Rust vector kernels',
        ],
      },
    ],
  },
  {
    id: 'RFC-02',
    title: 'High-Velocity Causal Ontology & Lock-Free Entity Resolution Architecture',
    plane: 'Bitemporal Ontology & Graph',
    horizon: 'H1',
    status: 'Under Consultant Review',
    linkedIncidents: ['INC-2026-094'],
    problemStatement:
      'During acute geopolitical or supply-chain shocks, thousands of vessel re-flaggings, customs manifest updates, and corporate registry changes arrive simultaneously. Synchronous transitive closure locks in the current graph layer stalled ingestion for 42 minutes.',
    asymmetryExploitationRationale:
      'Cross-silo structural blindspots are most lucrative in the first 5–30 minutes of a physical disruption, when market participants cannot map which public issuers are exposed to a tier-3 bottleneck.',
    consultantPromptQuestion:
      'How should we decouple high-throughput probabilistic entity resolution from multi-hop causal graph traversal so that 25k/sec updates never block read-heavy 3-hop contagion queries?',
    selectedOptionId: 'B',
    options: [
      {
        id: 'A',
        label: 'Option A: Sharded Neo4j / Memgraph Cluster with Read Replicas',
        architectureSummary:
          'Deploy an in-memory property graph cluster (Memgraph) with dedicated read replicas for analytical traversal and micro-batched transactional writes.',
        latencyImpactMs: 480,
        monthlyInfraCostUsd: 6800,
        bitemporalFidelityScore: 82,
        asymmetryCaptureLiftPct: 15,
        implementationWeeks: 4,
        pros: ['Standard Cypher query interface', 'Fast interactive graph visualization support'],
        cons: [
          'High RAM cost for bitemporal edge versioning',
          'Cross-shard multi-hop traversals still suffer tail latency spikes',
        ],
      },
      {
        id: 'B',
        label: 'Option B: Append-Only MVCC Edge Log (RocksDB) + Epoch-Snapshotted CSR In-Memory Graph',
        architectureSummary:
          'Write incoming entity links lock-free to RocksDB versioned column families; compile immutable Compressed Sparse Row (CSR) graph snapshots in Rust every 500ms for wait-free multi-hop reads.',
        latencyImpactMs: 85,
        monthlyInfraCostUsd: 3100,
        bitemporalFidelityScore: 97,
        asymmetryCaptureLiftPct: 31,
        implementationWeeks: 6,
        recommended: true,
        pros: [
          'Wait-free 3-hop and 5-hop causal propagation in <15ms via cache-local CSR arrays',
          'Complete decoupling of write bursts from analytical read queries',
          'Every epoch snapshot is natively indexed by t_known',
        ],
        cons: ['Custom Rust CSR compiler maintenance required'],
      },
      {
        id: 'C',
        label: 'Option C: Batch Graphframes on Spark / Ray Cluster',
        architectureSummary:
          'Execute entity resolution and connected-components every 10 minutes on a distributed Ray/Spark cluster over Parquet tables.',
        latencyImpactMs: 2400,
        monthlyInfraCostUsd: 4500,
        bitemporalFidelityScore: 94,
        asymmetryCaptureLiftPct: 9,
        implementationWeeks: 3,
        pros: ['High throughput for massive offline historical graph rebuilds'],
        cons: ['10-minute batch floor sacrifices acute intraday latency arbitrage windows'],
      },
    ],
  },
  {
    id: 'RFC-03',
    title: 'Streaming Divergence Kernel: Decoupling Reality Telemetry from Batch Windows',
    plane: 'Asymmetry & Falsification Engine',
    horizon: 'H2',
    status: 'Decision Needed',
    linkedIncidents: ['INC-2026-102'],
    problemStatement:
      'INC-2026-102 demonstrated that ingesting primary physical telemetry in 180ms is wasted if the Consensus-vs-Reality divergence kernel waits 6.4 hours for scheduled batch normalization joins.',
    asymmetryExploitationRationale:
      'Information latency arbitrage depends on minimizing total elapsed time from physical state change (e.g. transformer trip, port congestion spike) to divergence quantification against live implied pricing.',
    consultantPromptQuestion:
      'What stateful stream processing architecture best supports incremental rolling Wasserstein / KL-divergence joins between high-jitter physical sensor feeds and high-frequency market implied distributions?',
    selectedOptionId: 'A',
    options: [
      {
        id: 'A',
        label: 'Option A: Rust Stateful Stream Engine (Arroyo / Timely Dataflow) + Arrow State Backend',
        architectureSummary:
          'Continuous bi-stream ASOF join in Rust with bounded watermark lateness handles and incremental rolling window distribution estimators.',
        latencyImpactMs: 140,
        monthlyInfraCostUsd: 3400,
        bitemporalFidelityScore: 96,
        asymmetryCaptureLiftPct: 34,
        implementationWeeks: 6,
        recommended: true,
        pros: [
          'Sub-200ms incremental divergence recalculation on every telemetry tick',
          'Deterministic replay from Redpanda offsets for exact backtest parity',
        ],
        cons: ['Requires careful watermark tuning for out-of-order satellite feeds'],
      },
      {
        id: 'B',
        label: 'Option B: Apache Flink + PyFlink JAX UDFs',
        architectureSummary:
          'Standardize on managed Apache Flink with RocksDB state backend invoking Python/JAX vector UDFs via Arrow IPC.',
        latencyImpactMs: 390,
        monthlyInfraCostUsd: 5200,
        bitemporalFidelityScore: 93,
        asymmetryCaptureLiftPct: 26,
        implementationWeeks: 5,
        pros: ['Mature enterprise checkpointing and exactly-once semantics'],
        cons: ['JVM-to-Python serialization overhead and heavier operational footprint'],
      },
      {
        id: 'C',
        label: 'Option C: High-Frequency Micro-Batch Polling over DuckDB (30-Second Ticks)',
        architectureSummary:
          'Run stateless Polars/DuckDB workers polling recent 30-second Iceberg delta manifests.',
        latencyImpactMs: 1450,
        monthlyInfraCostUsd: 2100,
        bitemporalFidelityScore: 95,
        asymmetryCaptureLiftPct: 18,
        implementationWeeks: 2,
        pros: ['Simplest architecture; identical code path for batch and near-real-time'],
        cons: ['30-second floor still misses ultra-fast automated liquidity dislocations'],
      },
    ],
  },
  {
    id: 'RFC-04',
    title: 'Compact Cryptographic Provenance & Content-Addressed Lineage Tree',
    plane: 'Ingestion & Sensorium',
    horizon: 'H1',
    status: 'Approved Baseline',
    linkedIncidents: ['INC-2026-107'],
    problemStatement:
      'Fine-grained provenance tracking caused OOM crashes on ingestion workers when parsing dense unstructured filings, yet coarsening lineage compromises Master Spec Invariant IV.',
    asymmetryExploitationRationale:
      'High-conviction sizing requires verifiable proof that an anomaly originates from an authentic primary source rather than a parser hallucination or corrupted upstream mirror.',
    consultantPromptQuestion:
      'Validate our proposed compact BLAKE3 Merkle-Range Provenance Tree design to ensure zero heap amplification during 500MB+ multipart filing ingestion.',
    selectedOptionId: 'B',
    options: [
      {
        id: 'A',
        label: 'Option A: External Lineage Graph Database (OpenLineage + Marquez)',
        architectureSummary:
          'Emit asynchronous OpenLineage JSON events per transformation step to a central Postgres-backed Marquez service.',
        latencyImpactMs: 310,
        monthlyInfraCostUsd: 1900,
        bitemporalFidelityScore: 84,
        asymmetryCaptureLiftPct: 6,
        implementationWeeks: 3,
        pros: ['Standardized specification'],
        cons: ['Too coarse for byte-span / claim-level epistemic verification'],
      },
      {
        id: 'B',
        label: 'Option B: Inline BLAKE3 Merkle-Span Proofs in Arrow Metadata Footers',
        architectureSummary:
          'Embed fixed-size 32-byte BLAKE3 Merkle root hashes and byte-offset range tables directly in Arrow IPC / Parquet custom metadata footers.',
        latencyImpactMs: 45,
        monthlyInfraCostUsd: 950,
        bitemporalFidelityScore: 99,
        asymmetryCaptureLiftPct: 14,
        implementationWeeks: 4,
        recommended: true,
        pros: [
          'O(1) memory overhead per batch (<64KB regardless of document length)',
          'Lineage travels atomically with data files; zero external DB synchronization drift',
        ],
        cons: ['Requires custom CLI inspector for human analyst drill-down'],
      },
      {
        id: 'C',
        label: 'Option C: Sampled Audit Logging (10% Deterministic Hash Sampling)',
        architectureSummary:
          'Retain full fine-grained lineage for only 10% of ingested documents and high-severity alerts.',
        latencyImpactMs: 60,
        monthlyInfraCostUsd: 700,
        bitemporalFidelityScore: 65,
        asymmetryCaptureLiftPct: 4,
        implementationWeeks: 1,
        pros: ['Immediate memory relief with minimal code change'],
        cons: ['Violates Master Spec Invariant IV (100% deterministic auditability)'],
      },
    ],
  },
  {
    id: 'RFC-05',
    title: 'Bayesian Sensor-Confounding & Counterfactual Falsification Sandbox',
    plane: 'Asymmetry & Falsification Engine',
    horizon: 'H2',
    status: 'Under Consultant Review',
    linkedIncidents: ['INC-2026-111'],
    problemStatement:
      'Physical telemetry sensors suffer correlated environmental and technical dropouts (cloud cover, AIS spoofing, API throttling) that naive divergence detectors misclassify as real-world supply shocks.',
    asymmetryExploitationRationale:
      'True epistemic edge comes from distinguishing genuine structural breaks in physical reality from observation-channel artifacts before committing capital.',
    consultantPromptQuestion:
      'How should we structure the structural causal model (SCM) in the falsification harness to automatically separate observation-mechanism dropout from underlying physical state changes under a 1.5-second latency budget?',
    selectedOptionId: 'A',
    options: [
      {
        id: 'A',
        label: 'Option A: Hierarchical Bayesian Observation-Channel SCM (JAX / NumPyro Variational Inference)',
        architectureSummary:
          'Jointly model latent physical state and explicit sensor-health/occlusion variables using pre-compiled JAX Stochastic Variational Inference (SVI) kernels.',
        latencyImpactMs: 280,
        monthlyInfraCostUsd: 3800,
        bitemporalFidelityScore: 96,
        asymmetryCaptureLiftPct: 29,
        implementationWeeks: 5,
        recommended: true,
        pros: [
          'Explicitly discounts divergence signals when cross-modality sensor corroboration is absent',
          'GPU-accelerated batch falsification in <300ms',
        ],
        cons: ['Requires domain-specific prior calibration per sensor class'],
      },
      {
        id: 'B',
        label: 'Option B: Rule-Based Multi-Source Quorum Gate',
        architectureSummary:
          'Require at least 2 independent physical modalities (e.g. thermal + grid load, or AIS + customs) to cross z-score thresholds before promoting an anomaly.',
        latencyImpactMs: 50,
        monthlyInfraCostUsd: 1100,
        bitemporalFidelityScore: 85,
        asymmetryCaptureLiftPct: 16,
        implementationWeeks: 2,
        pros: ['Simple, interpretable, ultra-low latency'],
        cons: ['Discards high-value single-modality early signals where secondary sensors lag by days'],
      },
      {
        id: 'C',
        label: 'Option C: Full MCMC Counterfactual Simulation per Alert',
        architectureSummary:
          'Run full Hamiltonian Monte Carlo (NUTS) across 4 chains whenever a raw divergence threshold is breached.',
        latencyImpactMs: 4200,
        monthlyInfraCostUsd: 6400,
        bitemporalFidelityScore: 99,
        asymmetryCaptureLiftPct: 22,
        implementationWeeks: 6,
        pros: ['Exact posterior uncertainty estimation on complex multi-modal distributions'],
        cons: ['4–10 second compute latency creates queueing bottlenecks during volatile macro events'],
      },
    ],
  },
];

export const INITIAL_CONSULTANT_QUESTIONS: ConsultantQuestion[] = [
  {
    id: 'CQ-01',
    domain: 'Bitemporal Storage & Compaction (RFC-01)',
    priority: 'P0 — Blocking H1',
    question:
      'Review our dual-axis (t_valid, t_known) Apache Iceberg partitioning strategy: how should we structure compaction and Z-order clustering so point-in-time ASOF joins across 5,000 entities remain sub-250ms without write amplification?',
    contextRef: 'INC-2026-089 · packages/bitemporal-spine',
    expectedDeliverable: 'Written storage layout critique + compaction watermark spec (Week 2).',
    includedInBrief: true,
  },
  {
    id: 'CQ-02',
    domain: 'Lock-Free Causal Graph Snapshot Engine (RFC-02)',
    priority: 'P0 — Blocking H1',
    question:
      'Audit the proposed RocksDB MVCC edge log + 500ms epoch CSR snapshot architecture: what are the failure modes for incremental probabilistic entity merges when retroactive beneficial-ownership links arrive out of order?',
    contextRef: 'INC-2026-094 · packages/causal-ontology',
    expectedDeliverable: 'Concurrency & consistency verification model + Rust CSR memory layout review (Week 3).',
    includedInBrief: true,
  },
  {
    id: 'CQ-03',
    domain: 'Streaming Divergence Watermarking & Late Telemetry (RFC-03)',
    priority: 'P1 — Architecture Sign-off',
    question:
      'Physical satellite and customs feeds exhibit bimodal arrival latency (150ms to 45min). How should our streaming Wasserstein divergence operator handle late-arriving physical observations without violating bitemporal t_known monotonicity?',
    contextRef: 'INC-2026-102 · packages/asymmetry-engine',
    expectedDeliverable: 'Streaming bi-temporal watermark formalization & state-retention bounds (Week 4).',
    includedInBrief: true,
  },
  {
    id: 'CQ-04',
    domain: 'Observation-Channel Confounding vs. True Asymmetry (RFC-05)',
    priority: 'P1 — Architecture Sign-off',
    question:
      'Critique our Structural Causal Model (SCM) topology for separating correlated sensor dropout (e.g., cloud cover, AIS dark-shipping) from genuine supply/production halts under a 1.5s latency budget.',
    contextRef: 'INC-2026-111 · packages/falsification-harness',
    expectedDeliverable: 'Bayesian graphical model review & sensitivity stress-test protocol (Week 5).',
    includedInBrief: true,
  },
  {
    id: 'CQ-05',
    domain: 'Epistemic Uncertainty Propagation into Convex Sizing',
    priority: 'P2 — Optimization',
    question:
      'How should provenance depth and entity-resolution link entropy mathematically attenuate fractional-Kelly sizing weights in packages/convex-execution?',
    contextRef: 'Master Spec v3.4 §6 · packages/convex-execution',
    expectedDeliverable: 'Closed-form epistemic discount factor derivation for payoff optimizer (Week 6).',
    includedInBrief: true,
  },
];
