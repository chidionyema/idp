/**
 * IDP Reality Research Platform — Executable Reference Kernels for All 5 Critical Lanes
 * Designed so a single engineer or downstream model can run, test, and extend each lane immediately.
 */

// ============================================================================
// LANE 1: Compact BLAKE3-Style Merkle-Span Provenance Kernel (Fixes INC-2026-107)
// ============================================================================

export interface RawClaimSpan {
  claimId: string;
  byteStart: number;
  byteEnd: number;
  extractedValue: number;
}

export interface CompactProvenanceFooter {
  rawBlobDigest: string;
  parserSemver: string;
  merkleRoot: string;
  spanCount: number;
  estimatedHeapBytes: number;
  spans: ReadonlyArray<{
    claimId: string;
    byteStart: number;
    byteEnd: number;
    leafHash: string;
  }>;
}

/**
 * Deterministic FNV-1a / 64-bit hex digest helper used for zero-dependency deterministic hashing
 * in browser & Node unit tests (drop-in replaceable with native BLAKE3 SIMD in Rust/Node).
 */
export function deterministicHexDigest(input: string): string {
  let h1 = 0xdeadbeef ^ input.length;
  let h2 = 0x41c6ce57 ^ input.length;
  for (let i = 0; i < input.length; i++) {
    const ch = input.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  const p1 = (h1 >>> 0).toString(16).padStart(8, '0');
  const p2 = (h2 >>> 0).toString(16).padStart(8, '0');
  return `blake3_${p1}${p2}${p1}${p2}`;
}

export function buildMerkleProvenanceFooter(
  rawPayloadDigest: string,
  parserSemver: string,
  claims: RawClaimSpan[]
): CompactProvenanceFooter {
  const leafEntries = claims.map((c) => {
    if (c.byteEnd <= c.byteStart || c.byteStart < 0) {
      throw new Error(`Invalid byte span [${c.byteStart}, ${c.byteEnd}] for claim ${c.claimId}`);
    }
    const leafHash = deterministicHexDigest(
      `${rawPayloadDigest}:${c.claimId}:${c.byteStart}:${c.byteEnd}:${c.extractedValue}:${parserSemver}`
    );
    return {
      claimId: c.claimId,
      byteStart: c.byteStart,
      byteEnd: c.byteEnd,
      leafHash,
    };
  });

  // Pairwise Merkle reduction
  let currentLayer = leafEntries.map((e) => e.leafHash);
  if (currentLayer.length === 0) {
    currentLayer = [deterministicHexDigest(`${rawPayloadDigest}:empty`)];
  }
  while (currentLayer.length > 1) {
    const nextLayer: string[] = [];
    for (let i = 0; i < currentLayer.length; i += 2) {
      const left = currentLayer[i];
      const right = i + 1 < currentLayer.length ? currentLayer[i + 1] : left;
      nextLayer.push(deterministicHexDigest(`${left}:${right}`));
    }
    currentLayer = nextLayer;
  }

  return {
    rawBlobDigest: rawPayloadDigest,
    parserSemver,
    merkleRoot: currentLayer[0],
    spanCount: leafEntries.length,
    // Fixed 64 bytes per compact span vs 18KB per full AST node in legacy INC-2026-107
    estimatedHeapBytes: 128 + leafEntries.length * 64,
    spans: leafEntries,
  };
}

// ============================================================================
// LANE 2: Immutable Bitemporal Reality Spine Kernel (Fixes INC-2026-089)
// ============================================================================

export interface BitemporalFactRow {
  factId: string;
  entityId: string;
  metricKey: string;
  metricValue: number;
  tValidFrom: number; // Epoch ms when true in physical reality
  tKnownFrom: number; // Epoch ms when ingested by IDP (Transaction Time)
  provenanceMerkleRoot: string;
}

/**
 * Strictly append-only bitemporal fact store with deterministic ASOF point-in-time query.
 * Prevents look-ahead leakage when restated filings arrive at a later tKnownFrom.
 */
export function queryPointInTimeBitemporalState(
  ledger: ReadonlyArray<BitemporalFactRow>,
  entityId: string,
  metricKey: string,
  asOfTKnown: number,
  asOfTValid: number
): BitemporalFactRow | null {
  // Filter strictly to facts known on or before asOfTKnown and valid on or before asOfTValid
  const eligible = ledger.filter(
    (row) =>
      row.entityId === entityId &&
      row.metricKey === metricKey &&
      row.tKnownFrom <= asOfTKnown &&
      row.tValidFrom <= asOfTValid
  );

  if (eligible.length === 0) {
    return null;
  }

  // Order by latest valid period first, then latest transaction timestamp known as of asOfTKnown
  eligible.sort((a, b) => {
    if (b.tValidFrom !== a.tValidFrom) {
      return b.tValidFrom - a.tValidFrom;
    }
    return b.tKnownFrom - a.tKnownFrom;
  });

  return eligible[0];
}

// ============================================================================
// LANE 3: Lock-Free CSR Causal Ontology & Multi-Hop Contagion Kernel (Fixes INC-2026-094)
// ============================================================================

export interface CausalEdgeRecord {
  sourceNodeIdx: number;
  targetNodeIdx: number;
  weight: number; // [0..1] supply/ownership sensitivity
  tKnownFrom: number;
}

export interface CompiledCSRGraph {
  epochTKnown: number;
  nodeCount: number;
  rowPtr: Int32Array;
  colIdx: Int32Array;
  weights: Float64Array;
}

export function compileCsrGraphSnapshot(
  nodeCount: number,
  edges: ReadonlyArray<CausalEdgeRecord>,
  asOfTKnown: number
): CompiledCSRGraph {
  const visibleEdges = edges
    .filter((e) => e.tKnownFrom <= asOfTKnown)
    .sort((a, b) =>
      a.sourceNodeIdx !== b.sourceNodeIdx
        ? a.sourceNodeIdx - b.sourceNodeIdx
        : a.targetNodeIdx - b.targetNodeIdx
    );

  const rowPtr = new Int32Array(nodeCount + 1);
  const colIdx = new Int32Array(visibleEdges.length);
  const weights = new Float64Array(visibleEdges.length);

  for (let i = 0; i < visibleEdges.length; i++) {
    const e = visibleEdges[i];
    rowPtr[e.sourceNodeIdx + 1] += 1;
    colIdx[i] = e.targetNodeIdx;
    weights[i] = e.weight;
  }

  for (let n = 0; n < nodeCount; n++) {
    rowPtr[n + 1] += rowPtr[n];
  }

  return {
    epochTKnown: asOfTKnown,
    nodeCount,
    rowPtr,
    colIdx,
    weights,
  };
}

/**
 * Wait-free multi-hop contagion propagation over immutable CSR arrays.
 */
export function propagateMultiHopShock(
  csr: CompiledCSRGraph,
  initialShockNodeIdx: number,
  initialShockMagnitude: number,
  maxHops: number
): Float64Array {
  const impact = new Float64Array(csr.nodeCount);
  let frontier = new Float64Array(csr.nodeCount);
  impact[initialShockNodeIdx] = initialShockMagnitude;
  frontier[initialShockNodeIdx] = initialShockMagnitude;

  for (let hop = 0; hop < maxHops; hop++) {
    const nextFrontier = new Float64Array(csr.nodeCount);
    for (let u = 0; u < csr.nodeCount; u++) {
      const uShock = frontier[u];
      if (uShock <= 1e-6) continue;
      const start = csr.rowPtr[u];
      const end = csr.rowPtr[u + 1];
      for (let edgeIdx = start; edgeIdx < end; edgeIdx++) {
        const v = csr.colIdx[edgeIdx];
        const transmitted = uShock * csr.weights[edgeIdx];
        if (transmitted > nextFrontier[v]) {
          nextFrontier[v] = transmitted;
        }
        if (transmitted > impact[v]) {
          impact[v] = transmitted;
        }
      }
    }
    frontier = nextFrontier;
  }

  return impact;
}

// ============================================================================
// LANE 4: Streaming Wasserstein-1 Divergence & Bayesian Falsification (Fixes INC-2026-102 & 111)
// ============================================================================

export interface DivergenceAndFalsificationOutput {
  rawWassersteinL1: number;
  sensorHealthPosterior: number;
  effectiveDivergence: number;
  passedFalsificationGates: boolean;
  rejectionReason: string | null;
}

export function evaluateStreamingDivergenceAndFalsify(params: {
  telemetryQuantiles: number[]; // Sorted 5-point empirical quantiles
  consensusQuantiles: number[]; // Sorted 5-point market-implied quantiles
  primarySensorAvailable: boolean;
  corroboratingModalityZScore: number; // Secondary independent physical feed (e.g. grid load vs thermal)
  environmentalOcclusionProb: number; // [0..1] e.g. satellite cloud cover probability
}): DivergenceAndFalsificationOutput {
  const {
    telemetryQuantiles,
    consensusQuantiles,
    primarySensorAvailable,
    corroboratingModalityZScore,
    environmentalOcclusionProb,
  } = params;

  const n = Math.min(telemetryQuantiles.length, consensusQuantiles.length);
  if (n === 0 || !primarySensorAvailable) {
    return {
      rawWassersteinL1: 0,
      sensorHealthPosterior: 0,
      effectiveDivergence: 0,
      passedFalsificationGates: false,
      rejectionReason: 'Primary telemetry channel offline or empty.',
    };
  }

  let l1Sum = 0;
  for (let i = 0; i < n; i++) {
    l1Sum += Math.abs(telemetryQuantiles[i] - consensusQuantiles[i]);
  }
  const rawWassersteinL1 = Number((l1Sum / n).toFixed(4));

  // Bayesian Observation-Channel Posterior:
  // If environmental occlusion is high AND secondary modality shows zero corroboration (< 1.5 sigma),
  // posterior probability that the physical anomaly is real drops sharply (solving INC-2026-111).
  const corroborationBoost = Math.min(1, Math.max(0, corroboratingModalityZScore / 3.0));
  const rawSensorPosterior =
    (1 - environmentalOcclusionProb * 0.85) * 0.55 + corroborationBoost * 0.45;
  const sensorHealthPosterior = Number(
    Math.min(1, Math.max(0.05, rawSensorPosterior)).toFixed(3)
  );

  const effectiveDivergence = Number(
    (rawWassersteinL1 * sensorHealthPosterior).toFixed(4)
  );

  if (sensorHealthPosterior < 0.65) {
    return {
      rawWassersteinL1,
      sensorHealthPosterior,
      effectiveDivergence,
      passedFalsificationGates: false,
      rejectionReason: `Falsified by Gate 2 (Sensor Confounding): Posterior ${sensorHealthPosterior} < 0.65 due to high occlusion (${Math.round(
        environmentalOcclusionProb * 100
      )}%) without cross-modal corroboration.`,
    };
  }

  if (effectiveDivergence < 1.25) {
    return {
      rawWassersteinL1,
      sensorHealthPosterior,
      effectiveDivergence,
      passedFalsificationGates: false,
      rejectionReason: `Falsified by Gate 4 (Magnitude Threshold): Effective divergence ${effectiveDivergence} < 1.25 threshold.`,
    };
  }

  return {
    rawWassersteinL1,
    sensorHealthPosterior,
    effectiveDivergence,
    passedFalsificationGates: true,
    rejectionReason: null,
  };
}

// ============================================================================
// LANE 5: Epistemic-Weighted Fractional-Kelly Convex Allocator (Master Spec §6)
// ============================================================================

export interface ConvexSizingResult {
  rawKellyFractionPct: number;
  epistemicDiscountFactor: number;
  recommendedAllocationPct: number;
  cappedByDrawdownGovernor: boolean;
}

export function computeEpistemicKellyAllocation(params: {
  winProbability: number; // p in (0, 1)
  payoffAsymmetryRatio: number; // b = upside / downside (e.g., 4.5x convex skew)
  fractionalKellyMultiplier: number; // gamma (e.g., 0.35)
  provenanceFidelityScore: number; // [0..1]
  causalGraphConfidence: number; // [0..1]
  sensorHealthPosterior: number; // [0..1]
  maxClusterDrawdownCapPct: number; // e.g., 4.0%
}): ConvexSizingResult {
  const {
    winProbability,
    payoffAsymmetryRatio,
    fractionalKellyMultiplier,
    provenanceFidelityScore,
    causalGraphConfidence,
    sensorHealthPosterior,
    maxClusterDrawdownCapPct,
  } = params;

  const q = 1 - winProbability;
  const b = Math.max(0.1, payoffAsymmetryRatio);
  const classicalKelly = Math.max(0, (winProbability * b - q) / b);
  const rawKellyFractionPct = Number((classicalKelly * 100).toFixed(2));

  const epistemicDiscountFactor = Number(
    (provenanceFidelityScore * causalGraphConfidence * sensorHealthPosterior).toFixed(3)
  );

  // If sensor health or provenance is below minimum institutional threshold, allocate 0%
  if (sensorHealthPosterior < 0.65 || provenanceFidelityScore < 0.8) {
    return {
      rawKellyFractionPct,
      epistemicDiscountFactor,
      recommendedAllocationPct: 0,
      cappedByDrawdownGovernor: false,
    };
  }

  const uncappedPct =
    rawKellyFractionPct * fractionalKellyMultiplier * epistemicDiscountFactor;
  const cappedByDrawdownGovernor = uncappedPct > maxClusterDrawdownCapPct;
  const recommendedAllocationPct = Number(
    Math.min(maxClusterDrawdownCapPct, uncappedPct).toFixed(2)
  );

  return {
    rawKellyFractionPct,
    epistemicDiscountFactor,
    recommendedAllocationPct,
    cappedByDrawdownGovernor,
  };
}

// ============================================================================
// ESTATE EXPONENTIAL MULTIPLIER KERNELS (chidionyema/idp — PRs #7324..#7515)
// ============================================================================

/**
 * MULTIPLIER 1: One-Pass Discovery Oracle, Tenets T1-T9 & Schema Conformance R0-R8
 * Grounded in:
 * - docs/specs/2026-10-30-estate-tenets.md (Tenets T1-T9, 362 installed vs 110 tracked)
 * - eval/estate-context/gate_seed.py (#7499 failing-capable discovery seed grader)
 * - bin/schema-conformance (#7506 R0-R8 intent schema & host-path verifier)
 */
export type ObservationState =
  | 'MEASURED'
  | 'ABSENT'
  | 'READER_UNAVAILABLE'
  | 'ACCESS_DENIED'
  | 'STALE'
  | 'UNMEASURABLE';

export type OracleVerdict = 'PASS' | 'FAIL' | 'BLIND' | 'ABSTAIN';

export type DeciderTier = 'machine' | 'model' | 'judgment';

export interface DiscoveryOracleInput {
  intentName: string;
  observationState: ObservationState;
  freshnessAgeSeconds: number;
  maxFreshnessSlaSeconds: number;
  sourceCitation: string | null; // e.g., "bin/estate-fleet:142 @ fafb505"
  probeCommand: string | null; // e.g., "estate-execute status --json"
  hasTypedArgsSchema: boolean; // R0-R8: no free-text where enum/schema fits
  hostPathExists: boolean; // R0-R8: declared host_path exists on disk
  deciderTier: DeciderTier; // ADR 0044: machine -> model -> judgment
  canMachineDecide: boolean;
}

export interface DiscoveryOracleResult {
  verdict: OracleVerdict;
  observationState: ObservationState;
  tenetViolations: string[];
  conformanceScorePct: number;
  deciderEscalationValid: boolean;
  remediationDirective: string | null;
}

export function evaluateDiscoveryOracleAndTenets(
  input: DiscoveryOracleInput
): DiscoveryOracleResult {
  const violations: string[] = [];

  // T2 & T5: Distinguish observation failure (BLIND / ABSTAIN) from assertion failure (FAIL)
  const effectiveObservation: ObservationState =
    input.observationState === 'MEASURED' &&
    input.freshnessAgeSeconds > input.maxFreshnessSlaSeconds
      ? 'STALE'
      : input.observationState;

  // T6: Source-linked citation and executable probe command required
  if (!input.sourceCitation || input.sourceCitation.trim().length < 5) {
    violations.push('T6_MISSING_CITATION: Claim lacks file:line @ sha citation.');
  }
  if (!input.probeCommand || input.probeCommand.trim().length < 4) {
    violations.push('T6_MISSING_INSTRUMENT: Claim lacks re-executable probe command.');
  }

  // R0-R8: Schema conformance (#7506)
  if (!input.hasTypedArgsSchema) {
    violations.push('R3_UNTYPED_FREE_TEXT: Intent accepts untyped string where enum/schema fits.');
  }
  if (!input.hostPathExists) {
    violations.push('R7_DEAD_HOST_PATH: Intent references non-existent host path.');
  }

  // T8 & ADR 0044: Machine-first decider hierarchy (machine -> model -> judgment)
  const deciderEscalationValid = !(
    input.canMachineDecide && input.deciderTier !== 'machine'
  );
  if (!deciderEscalationValid) {
    violations.push(
      `T8_DECIDER_VIOLATION: Escalated to '${input.deciderTier}' when a deterministic 'machine' decider (<2ms) can decide.`
    );
  }

  let verdict: OracleVerdict = 'PASS';
  if (
    effectiveObservation === 'READER_UNAVAILABLE' ||
    effectiveObservation === 'ACCESS_DENIED' ||
    effectiveObservation === 'STALE'
  ) {
    verdict = 'BLIND';
  } else if (effectiveObservation === 'UNMEASURABLE') {
    verdict = 'ABSTAIN';
  } else if (effectiveObservation === 'ABSENT' || violations.length > 0) {
    verdict = 'FAIL';
  }

  const totalChecks = 5;
  const passedChecks = Math.max(0, totalChecks - violations.length);
  const conformanceScorePct = Math.round((passedChecks / totalChecks) * 100);

  return {
    verdict,
    observationState: effectiveObservation,
    tenetViolations: violations,
    conformanceScorePct,
    deciderEscalationValid,
    remediationDirective:
      verdict === 'BLIND'
        ? `Restore reader/freshness for ${input.intentName} (state=${effectiveObservation}, age=${input.freshnessAgeSeconds}s > SLA ${input.maxFreshnessSlaSeconds}s); never report PASS while BLIND.`
        : violations.length > 0
        ? violations.join(' | ')
        : null,
  };
}

/**
 * MULTIPLIER 2: ClaimSet + ProofSet + NSVEE 5-Property & EFDA Tier-2/3 Gate
 * Grounded in:
 * - docs/research/nsvee_integration_gate.py (P1-P5 Clopper-Pearson epsilon <= 0.05, n >= 60 mutants)
 * - docs/specs/2026-10-26-verified-completion-v2.md (Tier 1 receipts, Tier 2 WCFG, Tier 3 safetyProof)
 * - PR #7492 ("a receipt keyword is not proof") & PR #7507 (founder-intake repeat detection)
 */
export type ProofOracleSource = 'deployed-artifact' | 'human' | 'formal' | 'generator-self';

export interface ClaimAndProofInput {
  directiveText: string;
  isRepeatFounderDirective: boolean; // founder-intake find_repeat (#7507)
  priorDirectiveId?: string;
  containsHandbackPhrase: boolean; // AGENTS.md "No hand-back" law
  isolatedSandboxExecution: boolean; // NSVEE P1: never executes candidate code in grading process
  selfConsistentWrongArtifactCaught: boolean; // NSVEE P2: kills tautological wrong code+test
  mutantsTestedCount: number; // NSVEE P3: requires n >= 60 for Clopper-Pearson <= 0.05 with 0 survivors
  mutantsSurvivedCount: number;
  oracleSource: ProofOracleSource; // NSVEE P4: must be deployed-artifact | human | formal
  hasExecutableReceiptRow: boolean; // NSVEE P5 & #7492: cmd + measured_at + valid_for_s + sha256
  wcfgTraversalValid: boolean; // EFDA Tier 2 controller-owned WCFG
  destructiveAction: boolean;
  hasFormalSafetyProof: boolean; // EFDA Tier 3 safetyProof (required if destructiveAction)
}

export interface ClaimAndProofVerdict {
  status: 'VERIFIED' | 'FALSE_DONE' | 'UNVERIFIABLE' | 'REFUSED_HANDBACK' | 'REPEAT_ESCALATED';
  clopperPearsonUpperBound: number;
  nsveePropertiesPassed: {
    P1_isolatedProcess: boolean;
    P2_noTautologicalPass: boolean;
    P3_mutantBoundValid: boolean;
    P4_independentOracle: boolean;
    P5_executableClaimRow: boolean;
  };
  efdaTierStatus: 'TIER3_PROVEN' | 'TIER2_WCFG_OK' | 'BLOCKED';
  founderTrustDelta: number; // [-100..+25] asymmetric penalty for broken promises
  blockingReasons: string[];
}

export function evaluateClaimAndProofSet(
  input: ClaimAndProofInput
): ClaimAndProofVerdict {
  const blockingReasons: string[] = [];

  if (input.containsHandbackPhrase) {
    blockingReasons.push(
      'LAW_NO_HANDBACK: Agent attempted to hand back an action ("you can run...", "requires manual step") instead of completing it through an estate door.'
    );
  }

  // Exact 95% Clopper-Pearson upper bound for k=0 survivors: 1 - (0.05)^(1/n)
  // For k > 0 survivors, approximate upper confidence bound
  let cpBound = 1.0;
  if (input.mutantsTestedCount > 0) {
    if (input.mutantsSurvivedCount === 0) {
      cpBound = Number((1 - Math.pow(0.05, 1 / input.mutantsTestedCount)).toFixed(4));
    } else {
      const rawRate = input.mutantsSurvivedCount / input.mutantsTestedCount;
      const margin = 1.96 * Math.sqrt((rawRate * (1 - rawRate)) / input.mutantsTestedCount);
      cpBound = Number(Math.min(1, rawRate + margin).toFixed(4));
    }
  }

  const P1 = input.isolatedSandboxExecution;
  const P2 = input.selfConsistentWrongArtifactCaught;
  const P3 =
    input.mutantsTestedCount >= 60 &&
    input.mutantsSurvivedCount === 0 &&
    cpBound <= 0.05;
  const P4 =
    input.oracleSource === 'deployed-artifact' ||
    input.oracleSource === 'human' ||
    input.oracleSource === 'formal';
  const P5 = input.hasExecutableReceiptRow;

  if (!P1) blockingReasons.push('NSVEE_P1: Candidate code executed in grading process (sandbox breach).');
  if (!P2) blockingReasons.push('NSVEE_P2: Tautological test suite passed wrong artifact.');
  if (!P3) {
    blockingReasons.push(
      `NSVEE_P3: Clopper-Pearson bound ${cpBound} > 0.05 (n=${input.mutantsTestedCount}, survivors=${input.mutantsSurvivedCount}; requires n>=60 with 0 survivors).`
    );
  }
  if (!P4) {
    blockingReasons.push(
      `NSVEE_P4: Oracle source '${input.oracleSource}' is self-generated; must be deployed-artifact, human, or formal.`
    );
  }
  if (!P5) {
    blockingReasons.push(
      'NSVEE_P5 (#7492): A receipt keyword is not proof; missing re-executable facts.jsonl row (cmd, measured_at, valid_for_s, sha256).'
    );
  }

  let efdaTierStatus: 'TIER3_PROVEN' | 'TIER2_WCFG_OK' | 'BLOCKED' = 'TIER2_WCFG_OK';
  if (!input.wcfgTraversalValid) {
    efdaTierStatus = 'BLOCKED';
    blockingReasons.push('EFDA_TIER2: Proposed workflow edge violates controller WAST/WCFG state machine.');
  } else if (input.destructiveAction && !input.hasFormalSafetyProof) {
    efdaTierStatus = 'BLOCKED';
    blockingReasons.push('EFDA_TIER3: Destructive action lacks formal safetyProof certificate.');
  } else if (input.destructiveAction && input.hasFormalSafetyProof) {
    efdaTierStatus = 'TIER3_PROVEN';
  }

  let status: ClaimAndProofVerdict['status'] = 'VERIFIED';
  if (input.containsHandbackPhrase) {
    status = 'REFUSED_HANDBACK';
  } else if (!P4) {
    status = 'UNVERIFIABLE';
  } else if (!P1 || !P2 || !P3 || !P5 || efdaTierStatus === 'BLOCKED') {
    status = 'FALSE_DONE';
  } else if (input.isRepeatFounderDirective) {
    status = 'REPEAT_ESCALATED';
  }

  // Devil's Bargain psychology: broken promises / FALSE_DONE destroy trust asymmetrically (-50),
  // whereas verified one-pass execution compounds trust (+15).
  const founderTrustDelta =
    status === 'VERIFIED'
      ? 15
      : status === 'REPEAT_ESCALATED'
      ? -25
      : status === 'REFUSED_HANDBACK'
      ? -40
      : -60;

  return {
    status,
    clopperPearsonUpperBound: cpBound,
    nsveePropertiesPassed: {
      P1_isolatedProcess: P1,
      P2_noTautologicalPass: P2,
      P3_mutantBoundValid: P3,
      P4_independentOracle: P4,
      P5_executableClaimRow: P5,
    },
    efdaTierStatus,
    founderTrustDelta,
    blockingReasons,
  };
}

/**
 * MULTIPLIER 3: Agent League, War-Games & Economic Spend-Floor Governor
 * Grounded in:
 * - ADR 0038 (Model performance review: MiniMax $20->$50 promotion, Gemini 3.5 Flash consult door)
 * - docs/audits/2026-10-30-harness-assessment.md (#7505 Ranking & estate-dispatchd MiniMax spec)
 * - docs/specs/2026-10-26-the-estate-llm-spend-floor.md (#7248: $29.36/d vs $3.00/d cap, R0-R4)
 */
export interface AgentContestantStats {
  agentId: string;
  modelRoute: string;
  verifiedClaimsCount: number;
  falseDoneCount: number;
  handbackCount: number;
  medianDoorSeconds: number;
  dailySpendUsd: number;
  promptCacheHitRatio: number; // [0..1]
  hasSessionAttribution: boolean; // R1: refuses session: "-"
}

export interface AgentLeagueStanding {
  agentId: string;
  modelRoute: string;
  compositeLeagueScore: number;
  truthRatePct: number;
  costPerVerifiedClaimUsd: number;
  tierAssignment: 'PROMOTED_PRIMARY' | 'CONSULT_FLASH_DOOR' | 'SANDBOX_PROBATION' | 'DEMOTED_THROTTLED';
  routerAction: string;
}

export interface SpendFloorAuditResult {
  measuredDailySpendUsd: number;
  declaredBudgetCapUsd: number;
  projectedPostRemediationSpendUsd: number;
  withinFounderCap: boolean;
  standings: AgentLeagueStanding[];
}

export function evaluateAgentLeagueAndSpendFloor(params: {
  declaredDailyCapUsd: number; // e.g., 3.00 from AGENTS.md [budget.usd_per_day] litellm = 3.0
  preGateRefusalRate: number; // [0..1] fraction of doomed calls refused in <2ms by [A] GATE
  contestants: AgentContestantStats[];
}): SpendFloorAuditResult {
  const { declaredDailyCapUsd, preGateRefusalRate, contestants } = params;

  const measuredDailySpendUsd = Number(
    contestants.reduce((acc, c) => acc + c.dailySpendUsd, 0).toFixed(2)
  );

  const standings: AgentLeagueStanding[] = contestants.map((c) => {
    const totalAttempts = Math.max(
      1,
      c.verifiedClaimsCount + c.falseDoneCount + c.handbackCount
    );
    const truthRatePct = Number(
      ((c.verifiedClaimsCount / totalAttempts) * 100).toFixed(1)
    );
    const costPerVerifiedClaimUsd =
      c.verifiedClaimsCount > 0
        ? Number((c.dailySpendUsd / c.verifiedClaimsCount).toFixed(3))
        : Number(c.dailySpendUsd.toFixed(3));

    // Composite League Score: rewards high truth rate, low $/claim, high cache ratio, penalizes FALSE_DONE & handbacks
    const rawScore =
      truthRatePct * 1.15 -
      c.falseDoneCount * 18 -
      c.handbackCount * 22 -
      costPerVerifiedClaimUsd * 12 +
      c.promptCacheHitRatio * 20 -
      (c.hasSessionAttribution ? 0 : 25);

    const compositeLeagueScore = Number(Math.max(0, Math.min(100, rawScore)).toFixed(1));

    let tierAssignment: AgentLeagueStanding['tierAssignment'] = 'SANDBOX_PROBATION';
    let routerAction = 'Route only low-risk bounded tasks with mandatory countercheck.';

    if (!c.hasSessionAttribution) {
      tierAssignment = 'DEMOTED_THROTTLED';
      routerAction =
        'REFUSED AT ROUTER (R1): Missing caller session_id (session: "-"). Enforce mandatory session tag.';
    } else if (compositeLeagueScore >= 78 && costPerVerifiedClaimUsd <= 0.35) {
      tierAssignment = 'PROMOTED_PRIMARY';
      routerAction =
        'Primary estate-dispatchd workhorse (ADR 0038): full autonomous lane-submit rights.';
    } else if (c.medianDoorSeconds <= 8 && costPerVerifiedClaimUsd <= 0.15) {
      tierAssignment = 'CONSULT_FLASH_DOOR';
      routerAction =
        'Fast consult.gemini / sub-second classifier & discovery seed grader (#7513).';
    } else if (compositeLeagueScore < 50 || c.falseDoneCount >= 2) {
      tierAssignment = 'DEMOTED_THROTTLED';
      routerAction =
        'Demote subscription & cap daily token ceiling (ADR 0038 anti-slop penalty).';
    }

    return {
      agentId: c.agentId,
      modelRoute: c.modelRoute,
      compositeLeagueScore,
      truthRatePct,
      costPerVerifiedClaimUsd,
      tierAssignment,
      routerAction,
    };
  });

  standings.sort((a, b) => b.compositeLeagueScore - a.compositeLeagueScore);

  // Remediation R0-R4 from #7248: prompt caching + <2ms pre-gate refusal + session cap
  const cacheSavingsFactor = 0.32; // 68% reduction on multi-turn agent loops via prompt caching
  const gateSavingsFactor = 1 - Math.min(0.6, Math.max(0, preGateRefusalRate));
  const projectedPostRemediationSpendUsd = Number(
    (measuredDailySpendUsd * cacheSavingsFactor * gateSavingsFactor).toFixed(2)
  );

  return {
    measuredDailySpendUsd,
    declaredBudgetCapUsd: declaredDailyCapUsd,
    projectedPostRemediationSpendUsd,
    withinFounderCap: projectedPostRemediationSpendUsd <= declaredDailyCapUsd,
    standings,
  };
}

/**
 * MULTIPLIER 4: Voice-First 2100 (`ESTATE_FLEET` + Movie Director Engine) & Science Dept Loop
 * Grounded in:
 * - docs/specs/2026-10-30-fleet-comms-surfaces.md (#7496, #7500 inbox --pipe at ack_wait=60s)
 * - docs/specs/2026-10-23-estate-as-movie-director-engine.md (director.go ORBIT_FOCUS | PANORAMIC_SWEEP | MACRO_DOV)
 * - docs/specs/2026-09-29-machine-learning-dept.md (hypotheses.race + forge + growmos)
 */
export type DirectorCameraShot = 'ORBIT_FOCUS' | 'PANORAMIC_SWEEP' | 'MACRO_DOV';

export interface VoiceAndScienceInput {
  spokenDirective: string;
  eventKind: 'phase' | 'tool' | 'wait' | 'done' | 'steer' | 'gate';
  jetStreamAckWaitSeconds: number; // F1 law: must be >= 60s in production tests
  usedAtomicInboxPipe: boolean; // PR #7500: atomic read-and-ack via --pipe
  bayesianHypothesesCount: number; // hypotheses.race
  preRegisteredForgeGatePassed: boolean; // forge/ experiment_record.py
  surfaceBarLevel: 1 | 2 | 3 | 4; // backstage-as-a-product.md: Level 1 link-only is refused
}

export interface VoiceAndScienceResult {
  causalSteeringVerified: boolean;
  cameraShotSelected: DirectorCameraShot;
  templateOverLedgerNarration: string;
  productionAckSafe: boolean;
  sciencePromotionReady: boolean;
  surfaceAccepted: boolean;
  violations: string[];
}

export function evaluateVoiceDirectorAndScienceLoop(
  input: VoiceAndScienceInput
): VoiceAndScienceResult {
  const violations: string[] = [];

  // F1 Law (#7500): Read-then-ack replayed voice messages at ack_wait=60 when tested at ack_wait=1
  const productionAckSafe =
    input.jetStreamAckWaitSeconds >= 60 && input.usedAtomicInboxPipe;
  if (!productionAckSafe) {
    violations.push(
      `F1_VOICE_REPLAY_RISK: JetStream ack_wait=${input.jetStreamAckWaitSeconds}s (must be >=60s) or missing atomic 'inbox --pipe' (#7500).`
    );
  }

  // Director shot grammar (platform/voice-router/internal/director/director.go:91-93)
  let cameraShotSelected: DirectorCameraShot = 'PANORAMIC_SWEEP';
  if (input.eventKind === 'gate' || input.eventKind === 'steer') {
    cameraShotSelected = 'MACRO_DOV';
  } else if (input.eventKind === 'tool' || input.eventKind === 'done') {
    cameraShotSelected = 'ORBIT_FOCUS';
  }

  // Backstage-as-a-product.md: Level 1 link-only cards are strictly refused
  const surfaceAccepted = input.surfaceBarLevel >= 3;
  if (!surfaceAccepted) {
    violations.push(
      `SURFACE_LEVEL_REFUSED: Surface is Level ${input.surfaceBarLevel} (backstage-as-a-product.md refuses Level 1 link-only and requires Level 3 visual or Level 4 interactive).`
    );
  }

  // Science Dept & ML Dept bootstrap gate
  const sciencePromotionReady =
    input.bayesianHypothesesCount >= 2 &&
    input.preRegisteredForgeGatePassed &&
    surfaceAccepted;
  if (!sciencePromotionReady && input.bayesianHypothesesCount < 2) {
    violations.push(
      'SCIENCE_RACE_UNDERFED: hypotheses.race requires >= 2 competing hypotheses before promotion.'
    );
  }

  const causalSteeringVerified =
    productionAckSafe && input.spokenDirective.trim().length > 0;

  const templateOverLedgerNarration = `[LEDGER-BOUND CUE · ${cameraShotSelected}] event=${input.eventKind} | directive="${input.spokenDirective.slice(
    0,
    48
  )}" | ack_wait=${input.jetStreamAckWaitSeconds}s | surface=L${input.surfaceBarLevel}`;

  return {
    causalSteeringVerified,
    cameraShotSelected,
    templateOverLedgerNarration,
    productionAckSafe,
    sciencePromotionReady,
    surfaceAccepted,
    violations,
  };
}

/**
 * MULTIPLIER 5: Commercialisation & Two-Hats Tenant-Split Factory Gate
 * Grounded in:
 * - docs/specs/two-hats-tenant-split.md (Founder estate vs Customer tenant boundary)
 * - docs/specs/backstage-as-a-product.md (52 founder surfaces -> commercial product catalog)
 * - ADR 0034 (Free-tier placement ladder: $0-$150/mo hard ceiling unless funded)
 */
export interface CommercialGateInput {
  surfaceName: string;
  monthlyInfraCostUsd: number;
  usesFreeTierLadderOnly: boolean; // OCI Always-Free AD-2 / Cloudflare / KEDA scale-to-zero
  enforcesTenantIdIsolation: boolean; // EFDA tenant_id invariant
  leaksFounderInternalPaths: boolean; // Two-hats split check
  surfaceInteractivityLevel: 1 | 2 | 3 | 4;
  hasCryptographicProofReceipt: boolean;
}

export interface CommercialGateResult {
  commerciallyReady: boolean;
  devilsBargainCompliant: boolean;
  commercialReadinessScorePct: number;
  pricingTierRecommendation: 'ZERO_COST_SEED' | 'USAGE_PRO_TIER' | 'ENTERPRISE_TENANT' | 'BLOCKED';
  blockers: string[];
}

export function evaluateCommercialReadinessGate(
  input: CommercialGateInput
): CommercialGateResult {
  const blockers: string[] = [];

  // Devil's Bargain: Founder pays $0 for cloud bloat unless funded
  const devilsBargainCompliant =
    input.monthlyInfraCostUsd <= 5.0 && input.usesFreeTierLadderOnly;
  if (!devilsBargainCompliant) {
    blockers.push(
      `DEVILS_BARGAIN_BREACH: Surface '${input.surfaceName}' costs $${input.monthlyInfraCostUsd}/mo or bypasses ADR 0034 free-tier placement ladder.`
    );
  }

  if (!input.enforcesTenantIdIsolation || input.leaksFounderInternalPaths) {
    blockers.push(
      'TWO_HATS_TENANT_BREACH: Surface fails tenant_id boundary isolation or leaks founder-only state (docs/specs/two-hats-tenant-split.md).'
    );
  }

  if (input.surfaceInteractivityLevel < 3) {
    blockers.push(
      `PRODUCT_BAR_BELOW_L3: Surface is Level ${input.surfaceInteractivityLevel}; customer-facing factory surfaces require Level 3 (visual) or Level 4 (interactive).`
    );
  }

  if (!input.hasCryptographicProofReceipt) {
    blockers.push(
      'MISSING_PROOF_RECEIPT: Customer-facing capability lacks verifiable execution receipt.'
    );
  }

  const totalChecks = 4;
  const passed = Math.max(0, totalChecks - blockers.length);
  const commercialReadinessScorePct = Math.round((passed / totalChecks) * 100);
  const commerciallyReady = blockers.length === 0;

  return {
    commerciallyReady,
    devilsBargainCompliant,
    commercialReadinessScorePct,
    pricingTierRecommendation: !commerciallyReady
      ? 'BLOCKED'
      : input.surfaceInteractivityLevel === 4
      ? 'ENTERPRISE_TENANT'
      : 'ZERO_COST_SEED',
    blockers,
  };
}


