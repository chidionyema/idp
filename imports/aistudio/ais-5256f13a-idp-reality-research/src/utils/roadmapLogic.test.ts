import test from 'node:test';
import assert from 'node:assert/strict';
import {
  INITIAL_CONSULTANT_QUESTIONS,
  INITIAL_INCIDENTS,
  INITIAL_MILESTONES,
  INITIAL_RFCS,
} from '../data/idpDomainData';
import {
  computeRoadmapSummary,
  filterMilestones,
  generateConsultantBriefMarkdown,
  simulateArchitectureMetrics,
  validateNewIncidentInput,
} from './roadmapLogic';
import {
  BitemporalFactRow,
  buildMerkleProvenanceFooter,
  compileCsrGraphSnapshot,
  computeEpistemicKellyAllocation,
  evaluateAgentLeagueAndSpendFloor,
  evaluateClaimAndProofSet,
  evaluateCommercialReadinessGate,
  evaluateDiscoveryOracleAndTenets,
  evaluateStreamingDivergenceAndFalsify,
  evaluateVoiceDirectorAndScienceLoop,
  propagateMultiHopShock,
  queryPointInTimeBitemporalState,
} from '../lanes/operationalKernels';

test('filterMilestones filters accurately by horizon, plane, vector, and search query', () => {
  const h1Only = filterMilestones(INITIAL_MILESTONES, {
    horizon: 'H1',
    plane: 'ALL',
    vector: 'ALL',
    searchQuery: '',
  });
  assert.equal(h1Only.length, 4);
  assert.ok(h1Only.every((m) => m.horizon === 'H1'));

  const byIncidentQuery = filterMilestones(INITIAL_MILESTONES, {
    horizon: 'ALL',
    plane: 'ALL',
    vector: 'ALL',
    searchQuery: 'INC-2026-089',
  });
  assert.ok(byIncidentQuery.length >= 2);
  assert.ok(byIncidentQuery.every((m) => m.linkedIncidentIds.includes('INC-2026-089')));
});

test('computeRoadmapSummary aggregates counts and effort weeks across horizons', () => {
  const summary = computeRoadmapSummary(INITIAL_MILESTONES);
  assert.equal(summary.total, INITIAL_MILESTONES.length);
  assert.equal(
    summary.completed + summary.inProgress + summary.blocked + summary.planned,
    INITIAL_MILESTONES.length
  );
  assert.equal(
    summary.byHorizon.H1.weeks + summary.byHorizon.H2.weeks + summary.byHorizon.H3.weeks,
    summary.totalEffortWeeks
  );
});

test('simulateArchitectureMetrics responds deterministically to RFC option changes and sliders', () => {
  const baselineResult = simulateArchitectureMetrics(INITIAL_RFCS, {
    streamingWindowSec: 2,
    bitemporalAuditStrictness: 98,
    falsificationGatesCount: 5,
    entityResolutionConcurrency: 25000,
  });

  const degradedRfcs = INITIAL_RFCS.map((r) =>
    r.id === 'RFC-01' ? { ...r, selectedOptionId: 'A' as const } : r
  );
  const degradedResult = simulateArchitectureMetrics(degradedRfcs, {
    streamingWindowSec: 1800,
    bitemporalAuditStrictness: 75,
    falsificationGatesCount: 2,
    entityResolutionConcurrency: 5000,
  });

  assert.ok(
    baselineResult.endToEndLatencyMs < degradedResult.endToEndLatencyMs,
    'Baseline streaming + Iceberg option should have lower latency than degraded batch option'
  );
  assert.ok(
    baselineResult.bitemporalFidelityPct > degradedResult.bitemporalFidelityPct,
    'Higher bitemporal strictness and Option B should yield higher fidelity'
  );
  assert.ok(
    baselineResult.falsePositiveRatePct < degradedResult.falsePositiveRatePct,
    'More falsification gates should reduce false-positive rate'
  );
});

test('validateNewIncidentInput enforces required fields and minimum length', () => {
  const invalidEmpty = validateNewIncidentInput({
    title: 'Short',
    affectedModule: 'packages/epistemic-intake',
    rootCause: 'Valid root cause description',
    blastRadiusMetric: '10% loss',
  });
  assert.equal(invalidEmpty.valid, false);

  const validCase = validateNewIncidentInput({
    title: 'Delayed AIS Satellite Frame Reconciliation',
    affectedModule: 'packages/epistemic-intake',
    rootCause: 'Out-of-order orbital downlink frames bypassed watermark buffer.',
    blastRadiusMetric: '45-minute blindspot on 12 Strait of Hormuz tankers',
  });
  assert.equal(validCase.valid, true);
});

test('generateConsultantBriefMarkdown synthesizes complete markdown briefing package', () => {
  const simResult = simulateArchitectureMetrics(INITIAL_RFCS, {
    streamingWindowSec: 2,
    bitemporalAuditStrictness: 98,
    falsificationGatesCount: 5,
    entityResolutionConcurrency: 25000,
  });

  const md = generateConsultantBriefMarkdown({
    rfcs: INITIAL_RFCS,
    incidents: INITIAL_INCIDENTS,
    milestones: INITIAL_MILESTONES,
    questions: INITIAL_CONSULTANT_QUESTIONS,
    simResult,
    consultantRoleTitle: 'Principal Distributed Systems & Quantitative Architecture Consultant',
    engagementWeeks: 6,
    founderNotes: 'Prioritize H1 bitemporal spine sign-off before week 2.',
  });

  assert.ok(md.includes('IDP PLATFORM — EXTERNAL ARCHITECTURE CONSULTANT BRIEFING DOSSIER'));
  assert.ok(md.includes('INC-2026-089'));
  assert.ok(md.includes('RFC-01'));
  assert.ok(md.includes('Prioritize H1 bitemporal spine sign-off before week 2.'));
});

test('Lane 1 Kernel: buildMerkleProvenanceFooter produces compact O(1) span proofs (INC-2026-107)', () => {
  const footer = buildMerkleProvenanceFooter('blake3_raw_doc_001', 'edgar-parser@2.4.0', [
    { claimId: 'C1', byteStart: 120, byteEnd: 240, extractedValue: 94.2 },
    { claimId: 'C2', byteStart: 500, byteEnd: 680, extractedValue: 18.7 },
  ]);

  assert.equal(footer.spanCount, 2);
  assert.ok(footer.merkleRoot.startsWith('blake3_'));
  assert.equal(footer.estimatedHeapBytes, 128 + 2 * 64);
});

test('Lane 2 Kernel: queryPointInTimeBitemporalState prevents look-ahead leakage on restatements (INC-2026-089)', () => {
  const ledger: BitemporalFactRow[] = [
    {
      factId: 'F-ORIG',
      entityId: 'ENT-SMELTER-01',
      metricKey: 'output_tonnes',
      metricValue: 1000,
      tValidFrom: 100, // Q3 period
      tKnownFrom: 200, // Reported Oct 15
      provenanceMerkleRoot: 'blake3_orig',
    },
    {
      factId: 'F-RESTATED',
      entityId: 'ENT-SMELTER-01',
      metricKey: 'output_tonnes',
      metricValue: 620, // Downward restatement!
      tValidFrom: 100, // Still Q3 period
      tKnownFrom: 500, // Filed Nov 20
      provenanceMerkleRoot: 'blake3_restated',
    },
  ];

  // Querying as of tKnown = 300 (before Nov 20 restatement) MUST return 1000, never 620
  const stateAt300 = queryPointInTimeBitemporalState(
    ledger,
    'ENT-SMELTER-01',
    'output_tonnes',
    300,
    150
  );
  assert.ok(stateAt300);
  assert.equal(stateAt300.metricValue, 1000);

  // Querying as of tKnown = 600 (after Nov 20 restatement) returns restated 620
  const stateAt600 = queryPointInTimeBitemporalState(
    ledger,
    'ENT-SMELTER-01',
    'output_tonnes',
    600,
    150
  );
  assert.ok(stateAt600);
  assert.equal(stateAt600.metricValue, 620);
});

test('Lane 3 Kernel: compileCsrGraphSnapshot and propagateMultiHopShock execute wait-free contagion (INC-2026-094)', () => {
  const edges = [
    { sourceNodeIdx: 0, targetNodeIdx: 1, weight: 0.8, tKnownFrom: 100 },
    { sourceNodeIdx: 1, targetNodeIdx: 2, weight: 0.5, tKnownFrom: 100 },
    { sourceNodeIdx: 2, targetNodeIdx: 3, weight: 0.5, tKnownFrom: 100 },
    // Future edge not yet known at tKnown=150
    { sourceNodeIdx: 0, targetNodeIdx: 3, weight: 0.95, tKnownFrom: 400 },
  ];

  const csrAt150 = compileCsrGraphSnapshot(4, edges, 150);
  const impacts = propagateMultiHopShock(csrAt150, 0, 1.0, 3);

  assert.equal(impacts[0], 1.0);
  assert.equal(Number(impacts[1].toFixed(2)), 0.8);
  assert.equal(Number(impacts[2].toFixed(2)), 0.4);
  assert.equal(Number(impacts[3].toFixed(2)), 0.2);
});

test('Lane 4 & 5 Kernels: Bayesian sensor-confounding gate refutes occluded false positives and sizes valid signals (INC-2026-111)', () => {
  // Case 1: High cloud occlusion (0.9) and weak secondary corroboration (0.3 sigma) -> Falsified!
  const occludedFalsePositive = evaluateStreamingDivergenceAndFalsify({
    telemetryQuantiles: [10, 12, 14, 16, 18],
    consensusQuantiles: [4, 5, 6, 7, 8],
    primarySensorAvailable: true,
    corroboratingModalityZScore: 0.3,
    environmentalOcclusionProb: 0.9,
  });
  assert.equal(occludedFalsePositive.passedFalsificationGates, false);

  // Case 2: Clear sensor + strong secondary corroboration (2.9 sigma) -> Promoted!
  const corroboratedSignal = evaluateStreamingDivergenceAndFalsify({
    telemetryQuantiles: [10, 12, 14, 16, 18],
    consensusQuantiles: [4, 5, 6, 7, 8],
    primarySensorAvailable: true,
    corroboratingModalityZScore: 2.9,
    environmentalOcclusionProb: 0.1,
  });
  assert.equal(corroboratedSignal.passedFalsificationGates, true);

  const kelly = computeEpistemicKellyAllocation({
    winProbability: 0.6,
    payoffAsymmetryRatio: 4.0,
    fractionalKellyMultiplier: 0.35,
    provenanceFidelityScore: 0.99,
    causalGraphConfidence: 0.95,
    sensorHealthPosterior: corroboratedSignal.sensorHealthPosterior,
    maxClusterDrawdownCapPct: 4.0,
  });
  assert.ok(kelly.recommendedAllocationPct > 0);
  assert.ok(kelly.recommendedAllocationPct <= 4.0);
});

test('Multiplier M1 Kernel: evaluateDiscoveryOracleAndTenets separates BLIND/ABSTAIN from FAIL and enforces T6/T8/R0-R8 (#7499, #7506)', () => {
  // Stale reader (> SLA) must return BLIND, never PASS
  const staleRes = evaluateDiscoveryOracleAndTenets({
    intentName: 'estate.fleet.status',
    observationState: 'MEASURED',
    freshnessAgeSeconds: 900,
    maxFreshnessSlaSeconds: 300,
    sourceCitation: 'bin/estate-fleet:142 @ fafb505',
    probeCommand: 'estate-fleet status --json',
    hasTypedArgsSchema: true,
    hostPathExists: true,
    deciderTier: 'machine',
    canMachineDecide: true,
  });
  assert.equal(staleRes.verdict, 'BLIND');
  assert.equal(staleRes.observationState, 'STALE');

  // Escalating to model when machine (<2ms) can decide violates T8 / ADR 0044
  const badDecider = evaluateDiscoveryOracleAndTenets({
    intentName: 'estate.schema.check',
    observationState: 'MEASURED',
    freshnessAgeSeconds: 10,
    maxFreshnessSlaSeconds: 300,
    sourceCitation: 'bin/schema-conformance:44 @ c89e0a6',
    probeCommand: 'bin/schema-conformance --json',
    hasTypedArgsSchema: true,
    hostPathExists: true,
    deciderTier: 'model',
    canMachineDecide: true,
  });
  assert.equal(badDecider.verdict, 'FAIL');
  assert.equal(badDecider.deciderEscalationValid, false);
});

test('Multiplier M2 Kernel: evaluateClaimAndProofSet enforces NSVEE P1-P5 (n>=60 Clopper-Pearson <= 0.05), EFDA WCFG, and No-Handback (#7492)', () => {
  // Under-sampled mutant run (n=20 -> bound > 0.05) or missing receipt row -> FALSE_DONE
  const underSampled = evaluateClaimAndProofSet({
    directiveText: 'Wire estate-dispatchd launchd daemon',
    isRepeatFounderDirective: false,
    containsHandbackPhrase: false,
    isolatedSandboxExecution: true,
    selfConsistentWrongArtifactCaught: true,
    mutantsTestedCount: 20,
    mutantsSurvivedCount: 0,
    oracleSource: 'deployed-artifact',
    hasExecutableReceiptRow: false,
    wcfgTraversalValid: true,
    destructiveAction: false,
    hasFormalSafetyProof: false,
  });
  assert.equal(underSampled.status, 'FALSE_DONE');
  assert.ok(underSampled.clopperPearsonUpperBound > 0.05);

  // Full n=65 zero-survivor NSVEE P1-P5 + Tier 3 safetyProof -> VERIFIED
  const verified = evaluateClaimAndProofSet({
    directiveText: 'Enforce spine firewall brake on destructive path',
    isRepeatFounderDirective: false,
    containsHandbackPhrase: false,
    isolatedSandboxExecution: true,
    selfConsistentWrongArtifactCaught: true,
    mutantsTestedCount: 65,
    mutantsSurvivedCount: 0,
    oracleSource: 'deployed-artifact',
    hasExecutableReceiptRow: true,
    wcfgTraversalValid: true,
    destructiveAction: true,
    hasFormalSafetyProof: true,
  });
  assert.equal(verified.status, 'VERIFIED');
  assert.ok(verified.clopperPearsonUpperBound <= 0.05);
  assert.equal(verified.efdaTierStatus, 'TIER3_PROVEN');
});

test('Multiplier M3, M4, M5 Kernels: Agent League Spend Governor (#7248), Voice Director (#7500), and Commercial Two-Hats Gate', () => {
  const league = evaluateAgentLeagueAndSpendFloor({
    declaredDailyCapUsd: 3.0,
    preGateRefusalRate: 0.35,
    contestants: [
      {
        agentId: 'minimax-dispatchd',
        modelRoute: 'minimax_m27',
        verifiedClaimsCount: 42,
        falseDoneCount: 0,
        handbackCount: 0,
        medianDoorSeconds: 11,
        dailySpendUsd: 8.4,
        promptCacheHitRatio: 0.82,
        hasSessionAttribution: true,
      },
      {
        agentId: 'untagged-loop',
        modelRoute: 'claude-sonnet',
        verifiedClaimsCount: 3,
        falseDoneCount: 2,
        handbackCount: 1,
        medianDoorSeconds: 38,
        dailySpendUsd: 4.5,
        promptCacheHitRatio: 0.1,
        hasSessionAttribution: false,
      },
    ],
  });
  assert.equal(league.standings[0].agentId, 'minimax-dispatchd');
  assert.equal(league.standings[0].tierAssignment, 'PROMOTED_PRIMARY');
  assert.equal(league.standings[1].tierAssignment, 'DEMOTED_THROTTLED');
  assert.equal(league.withinFounderCap, true);

  const voice = evaluateVoiceDirectorAndScienceLoop({
    spokenDirective: 'Cut to the failing gate and dispatch MiniMax on #7497',
    eventKind: 'gate',
    jetStreamAckWaitSeconds: 60,
    usedAtomicInboxPipe: true,
    bayesianHypothesesCount: 3,
    preRegisteredForgeGatePassed: true,
    surfaceBarLevel: 4,
  });
  assert.equal(voice.causalSteeringVerified, true);
  assert.equal(voice.cameraShotSelected, 'MACRO_DOV');
  assert.equal(voice.sciencePromotionReady, true);

  const comm = evaluateCommercialReadinessGate({
    surfaceName: 'factory/surfaces/backstage-portal',
    monthlyInfraCostUsd: 0,
    usesFreeTierLadderOnly: true,
    enforcesTenantIdIsolation: true,
    leaksFounderInternalPaths: false,
    surfaceInteractivityLevel: 4,
    hasCryptographicProofReceipt: true,
  });
  assert.equal(comm.commerciallyReady, true);
  assert.equal(comm.pricingTierRecommendation, 'ENTERPRISE_TENANT');
});

