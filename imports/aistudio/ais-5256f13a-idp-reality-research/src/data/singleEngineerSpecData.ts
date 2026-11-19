import { ArchitecturalPlane, HorizonId } from './idpDomainData';

export interface CriticalEngineeringLane {
  laneNumber: number;
  laneId: string;
  title: string;
  shortLabel: string;
  plane: ArchitecturalPlane;
  horizon: HorizonId;
  repoPackagePath: string;
  savedSpecDocPath: string;
  kernelFilePath: string;
  linkedIncidentIds: string[];
  linkedRfcId: string;
  singleEngineerStack: string;
  daysToOperational: number;
  objectiveSummary: string;
  dayByDayRunbook: string[];
  productionCodeSnippet: string;
  verificationCommand: string;
  downstreamModelBuildPrompt: string;
}

export const SAVED_REPOSITORY_DOCUMENTS = [
  {
    id: 'DOC-AGENTS',
    title: 'Root Agent & Engineer Command Manifest',
    path: '/AGENTS.md',
    audience: 'All Coding Agents (Gemini Flash/Pro) & Lead Engineers',
    summary:
      'Immediate root routing table mapping the 5 Critical Lanes, 4 Constitutional Epistemic Invariants, and mandatory unit-test gates.',
  },
  {
    id: 'DOC-MASTER-ROADMAP',
    title: 'Master Architecture Roadmap & Consultant Dossier',
    path: '/docs/IDP_MASTER_ARCHITECTURE_AND_ROADMAP.md',
    audience: 'Founder, Principal Architect & External Consultant',
    summary:
      'Complete persistent record of Master Spec v3.4, production incident forensics (INC-2026-089 to 111), RFC baseline selections, and 3-Horizon matrix.',
  },
  {
    id: 'DOC-SINGLE-ENG-SPEC',
    title: 'Single-Engineer Operational Spec & Code Blueprint',
    path: '/docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md',
    audience: 'Single Implementing Engineer & Downstream Build Models',
    summary:
      'Zero-bloat vertical core architecture replacing multi-team distributed clusters with embedded DuckDB/Iceberg, RocksDB CSR snapshots, and BLAKE3 Merkle footers.',
  },
  {
    id: 'DOC-KERNELS',
    title: 'Executable Production Reference Kernels',
    path: '/src/lanes/operationalKernels.ts',
    audience: 'Direct Execution & Automated CI Test Suite',
    summary:
      'Working, unit-tested TypeScript implementations of all 5 critical lane algorithms (Merkle spans, Bitemporal ASOF, CSR Contagion, Wasserstein+Bayesian Gate, Kelly Allocator).',
  },
];

export const CRITICAL_ENGINEERING_LANES: CriticalEngineeringLane[] = [
  {
    laneNumber: 1,
    laneId: 'LANE-01',
    title: 'Epistemic Intake & BLAKE3 Merkle-Span Provenance',
    shortLabel: 'Lane 1 · Intake & Merkle Provenance',
    plane: 'Ingestion & Sensorium',
    horizon: 'H1',
    repoPackagePath: 'packages/epistemic-intake',
    savedSpecDocPath: '/docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md#lane-1',
    kernelFilePath: '/src/lanes/operationalKernels.ts',
    linkedIncidentIds: ['INC-2026-107'],
    linkedRfcId: 'RFC-04',
    singleEngineerStack: 'Rust / TypeScript Streamer + BLAKE3 CAS + Apache Arrow Footer Metadata',
    daysToOperational: 4,
    objectiveSummary:
      'Eliminate worker OOM crashes (INC-2026-107) while enforcing Invariant IV by embedding O(1) 32-byte BLAKE3 Merkle roots and byte-offset spans directly in Arrow/Parquet footers.',
    dayByDayRunbook: [
      'Day 1: Deploy content-addressed raw blob store (cas://blake3/<digest>) rejecting any unhashed payload.',
      'Day 2: Wire buildMerkleProvenanceFooter() into document/telemetry chunkers so only [byteStart, byteEnd] + leafHash remain in memory.',
      'Day 3: Embed serialized CompactProvenanceFooter JSON into Arrow IPC / Parquet custom_metadata.',
      'Day 4: Add 10x burst replay stress test verifying worker heap stays < 1.5GB.',
    ],
    productionCodeSnippet: `// From /src/lanes/operationalKernels.ts (Lane 1 Reference Kernel)
const footer = buildMerkleProvenanceFooter(
  'blake3_9f86d081884c7d659a2feaa0c55ad015',
  'edgar-parser@2.4.0',
  [
    { claimId: 'CLM-INV-01', byteStart: 1024, byteEnd: 1188, extractedValue: 412.8 },
    { claimId: 'CLM-INV-02', byteStart: 4096, byteEnd: 4310, extractedValue: 19.4 },
  ]
);
// O(1) footer metadata: footer.merkleRoot + 64 bytes/span (Zero AST heap bloat)`,
    verificationCommand: 'npx --yes tsx --test src/utils/roadmapLogic.test.ts',
    downstreamModelBuildPrompt: `You are implementing LANE-01 (Epistemic Intake & BLAKE3 Merkle Provenance) for the IDP Reality Research Platform.
Read /AGENTS.md, /docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md, and /src/lanes/operationalKernels.ts first.
Task:
1. Extend buildMerkleProvenanceFooter() in /src/lanes/operationalKernels.ts to support multipage streaming chunks and cryptographic Merkle inclusion proof verification (verifyClaimInclusionProof).
2. Enforce INV-04: every extracted numeric or entity claim must carry rawBlobDigest, [byteStart, byteEnd], and merkleRoot.
3. Add deterministic unit tests in src/utils/roadmapLogic.test.ts and verify via: npx --yes tsx --test src/utils/roadmapLogic.test.ts.`,
  },
  {
    laneNumber: 2,
    laneId: 'LANE-02',
    title: 'Immutable Bitemporal Reality Spine (DuckDB + Iceberg)',
    shortLabel: 'Lane 2 · Bitemporal Spine',
    plane: 'Bitemporal Ontology & Graph',
    horizon: 'H1',
    repoPackagePath: 'packages/bitemporal-spine',
    savedSpecDocPath: '/docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md#lane-2',
    kernelFilePath: '/src/lanes/operationalKernels.ts',
    linkedIncidentIds: ['INC-2026-089'],
    linkedRfcId: 'RFC-01',
    singleEngineerStack: 'Embedded DuckDB + Immutable Parquet Partitioning on (t_known_date, entity_shard)',
    daysToOperational: 5,
    objectiveSummary:
      'Eradicate retroactive look-ahead bias (INC-2026-089) by enforcing append-only dual-timestamp facts (t_valid_from, t_known_from) with mandatory point-in-time ASOF queries.',
    dayByDayRunbook: [
      'Day 1: Provision append-only Parquet/Iceberg table schema with (t_valid_from, t_known_from, provenance_merkle_root).',
      'Day 2: Ban SQL UPDATE/DELETE at the storage adapter layer; route all amended filings to appendFact().',
      'Day 3: Implement queryPointInTimeBitemporalState(entityId, metricKey, asOfTKnown, asOfTValid) using arg_max(value, t_known_from).',
      'Day 4–5: Run automated backtest replay diff across all 18 historical restatement scenarios.',
    ],
    productionCodeSnippet: `// From /src/lanes/operationalKernels.ts (Lane 2 Bitemporal ASOF Kernel)
// Original Q3 filing ingested Oct 15 (tKnown=1000) reports inventory = 120.0
// Restated Q3 filing ingested Nov 20 (tKnown=2000) amends inventory = 82.5
const stateOnOct20 = queryPointInTimeBitemporalState(
  ledger, 'ENT-SMELTER-04', 'inventory_kt',
  1500, // asOfTKnown (Oct 20): strictly before Nov 20 restatement!
  1000  // asOfTValid
);
// Returns 120.0 (Zero look-ahead leakage from the Nov 20 restatement)`,
    verificationCommand: 'npx --yes tsx --test src/utils/roadmapLogic.test.ts',
    downstreamModelBuildPrompt: `You are implementing LANE-02 (Immutable Bitemporal Reality Spine) for the IDP Reality Research Platform.
Read /AGENTS.md, /docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md, and /src/lanes/operationalKernels.ts first.
Task:
1. Build the BitemporalSpineRepository module wrapping queryPointInTimeBitemporalState() with batch ASOF range-join support across multiple entities and metrics.
2. Add a look-ahead leakage detector function detectBitemporalLeakage() that flags any query or training split where tKnownFrom > simulationTimestamp.
3. Verify with unit tests via: npx --yes tsx --test src/utils/roadmapLogic.test.ts.`,
  },
  {
    laneNumber: 3,
    laneId: 'LANE-03',
    title: 'Lock-Free MVCC & Epoch-CSR Causal Ontology',
    shortLabel: 'Lane 3 · CSR Causal Graph',
    plane: 'Bitemporal Ontology & Graph',
    horizon: 'H1',
    repoPackagePath: 'packages/causal-ontology',
    savedSpecDocPath: '/docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md#lane-3',
    kernelFilePath: '/src/lanes/operationalKernels.ts',
    linkedIncidentIds: ['INC-2026-094'],
    linkedRfcId: 'RFC-02',
    singleEngineerStack: 'Append-Only Edge Log + Double-Buffered TypedArray CSR Graph Snapshots',
    daysToOperational: 5,
    objectiveSummary:
      'Resolve the 42-minute graph lock cascade (INC-2026-094) by decoupling entity-link ingestion from multi-hop contagion reads using immutable Compressed Sparse Row (CSR) snapshots.',
    dayByDayRunbook: [
      'Day 1: Replace synchronous graph DB locks with an append-only CausalEdgeRecord log indexed by tKnownFrom.',
      'Day 2: Implement compileCsrGraphSnapshot() compiling flat Int32Array (rowPtr, colIdx) and Float64Array (weights) every 500ms.',
      'Day 3: Implement wait-free 3-hop and 5-hop supply-chain contagion propagation (propagateMultiHopShock).',
      'Day 4–5: Benchmark 25,000 edge updates/sec concurrent with 5-hop analytical reads (< 15ms P99).',
    ],
    productionCodeSnippet: `// From /src/lanes/operationalKernels.ts (Lane 3 CSR Contagion Kernel)
const csr = compileCsrGraphSnapshot(nodeCount, edgeLog, asOfTKnown);
// Wait-free 3-hop contagion propagation in contiguous TypedArrays (< 2ms):
const downstreamImpacts = propagateMultiHopShock(
  csr,
  0,    // Chokepoint node index (e.g. Strait of Hormuz terminal)
  1.0,  // Initial physical disruption magnitude
  3     // Max causal hops (Tier-1 -> Tier-2 -> Tier-3 obligors)
);`,
    verificationCommand: 'npx --yes tsx --test src/utils/roadmapLogic.test.ts',
    downstreamModelBuildPrompt: `You are implementing LANE-03 (Lock-Free MVCC & Epoch-CSR Causal Ontology) for the IDP Reality Research Platform.
Read /AGENTS.md, /docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md, and /src/lanes/operationalKernels.ts first.
Task:
1. Extend compileCsrGraphSnapshot() and propagateMultiHopShock() in /src/lanes/operationalKernels.ts to track path provenance (which intermediate supplier nodes transmitted the max shock) and bitemporal edge confidence attenuation.
2. Ensure zero lock contention between edge log appends and CSR snapshot reads.
3. Verify with unit tests via: npx --yes tsx --test src/utils/roadmapLogic.test.ts.`,
  },
  {
    laneNumber: 4,
    laneId: 'LANE-04',
    title: 'Streaming Wasserstein Divergence & Bayesian Falsification Gate',
    shortLabel: 'Lane 4 · Divergence & Falsification',
    plane: 'Asymmetry & Falsification Engine',
    horizon: 'H2',
    repoPackagePath: 'packages/asymmetry-engine',
    savedSpecDocPath: '/docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md#lane-4',
    kernelFilePath: '/src/lanes/operationalKernels.ts',
    linkedIncidentIds: ['INC-2026-102', 'INC-2026-111'],
    linkedRfcId: 'RFC-03',
    singleEngineerStack: 'Incremental Streaming Quantile Sketch + Bayesian Sensor-Confounding Filter',
    daysToOperational: 6,
    objectiveSummary:
      'Compress divergence detection from 6.4 hours to < 1.8 seconds (INC-2026-102) while automatically refuting correlated sensor-dropout false positives (INC-2026-111).',
    dayByDayRunbook: [
      'Day 1–2: Replace 6-hour cron batch join with streaming quantile buffers for primary telemetry and consensus curves.',
      'Day 3: Compute continuous L1 Wasserstein distance on every telemetry tick.',
      'Day 4: Wire the Bayesian Sensor-Confounding Gate discounting anomalies when environmental occlusion is high and secondary modality corroboration is absent.',
      'Day 5–6: Replay INC-2026-102 and INC-2026-111 corpuses to certify sub-2s alert emission and 0 false promotions.',
    ],
    productionCodeSnippet: `// From /src/lanes/operationalKernels.ts (Lane 4 Divergence + Bayesian Gate)
const assessment = evaluateStreamingDivergenceAndFalsify({
  telemetryQuantiles: [4.2, 4.8, 5.5, 6.1, 7.0],
  consensusQuantiles: [2.0, 2.3, 2.5, 2.8, 3.1],
  primarySensorAvailable: true,
  corroboratingModalityZScore: 2.8, // Confirmed by independent grid harmonics feed
  environmentalOcclusionProb: 0.12, // Low cloud occlusion
});
// assessment.passedFalsificationGates === true; effectiveDivergence === 2.456`,
    verificationCommand: 'npx --yes tsx --test src/utils/roadmapLogic.test.ts',
    downstreamModelBuildPrompt: `You are implementing LANE-04 (Streaming Wasserstein Divergence & Bayesian Falsification Gate) for the IDP Reality Research Platform.
Read /AGENTS.md, /docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md, and /src/lanes/operationalKernels.ts first.
Task:
1. Expand evaluateStreamingDivergenceAndFalsify() into a complete 5-Gate Adversarial Falsification Pipeline (Gate 1: Bitemporal Monotonicity, Gate 2: Sensor Confounding SCM, Gate 3: Seasonal/Harmonic Null Hypothesis, Gate 4: Wasserstein Effect Size, Gate 5: Liquidity Depth Check).
2. Verify with deterministic unit tests via: npx --yes tsx --test src/utils/roadmapLogic.test.ts.`,
  },
  {
    laneNumber: 5,
    laneId: 'LANE-05',
    title: 'Epistemic-Weighted Fractional-Kelly Convex Execution',
    shortLabel: 'Lane 5 · Convex Execution',
    plane: 'Convex Execution & Simulation',
    horizon: 'H2',
    repoPackagePath: 'packages/convex-execution',
    savedSpecDocPath: '/docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md#lane-5',
    kernelFilePath: '/src/lanes/operationalKernels.ts',
    linkedIncidentIds: ['INC-2026-102'],
    linkedRfcId: 'RFC-05',
    singleEngineerStack: 'Closed-Form Epistemic Kelly Optimizer + 4.0% Cluster Drawdown Governor',
    daysToOperational: 3,
    objectiveSummary:
      'Translate falsification-surviving reality divergences into drawdown-bounded convex allocations weighted directly by provenance fidelity and causal graph certainty.',
    dayByDayRunbook: [
      'Day 1: Implement computeEpistemicKellyAllocation() coupling classical Kelly skew to provenanceFidelityScore * causalGraphConfidence * sensorHealthPosterior.',
      'Day 2: Enforce hard 4.0% cluster drawdown governor and automatic zero-sizing when sensor posterior < 0.65.',
      'Day 3: Wire end-to-end pipeline test from Lane 1 Merkle intake through Lane 5 allocation output.',
    ],
    productionCodeSnippet: `// From /src/lanes/operationalKernels.ts (Lane 5 Convex Kelly Allocator)
const sizing = computeEpistemicKellyAllocation({
  winProbability: 0.62,
  payoffAsymmetryRatio: 4.5, // 4.5x upside-to-downside convexity
  fractionalKellyMultiplier: 0.35,
  provenanceFidelityScore: 0.99,
  causalGraphConfidence: 0.94,
  sensorHealthPosterior: 0.89,
  maxClusterDrawdownCapPct: 4.0,
});`,
    verificationCommand: 'npx --yes tsx --test src/utils/roadmapLogic.test.ts',
    downstreamModelBuildPrompt: `You are implementing LANE-05 (Epistemic-Weighted Fractional-Kelly Convex Execution) for the IDP Reality Research Platform.
Read /AGENTS.md, /docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md, and /src/lanes/operationalKernels.ts first.
Task:
1. Extend computeEpistemicKellyAllocation() to support multi-asset correlated cluster budgets so aggregate portfolio drawdown across linked causal graph nodes never exceeds 4.0%.
2. Verify with unit tests via: npx --yes tsx --test src/utils/roadmapLogic.test.ts.`,
  },
];
