import { createHash } from 'node:crypto';
import {
  buildAuraManifoldSnapshot,
  createDefaultAuraState,
  decodeGenesisAtomicFrame,
  encodeGenesisAtomicFrame,
  executeAuraOmniCommand,
  FRAME_BYTE_LENGTH,
  lawI11Zone,
  VERDICT_FLAG_DIGEST_BOUND,
  VERDICT_FLAG_SEALED,
  VERDICT_FLAG_ZERO_POLL_OK,
} from './auraManifold';
import { AutonomousReactivityEngine } from './autonomousReactivity';
import {
  BROWSER_WORKFORCE_FLEET,
  evaluateMandatoryResilienceMatrix,
  evaluateUniversalKarmicSettlement,
  getAllSeeingEyeAuditSnapshot,
  UniversalExecutionProtocolEngine,
} from './meridianCapabilityCalculus';
import { OmniflowLiveBusEngine } from './omniflowLiveBus';
import {
  verifyAllEstateFsmsClosedLoop,
  verifySingleFsmClosedLoop,
} from './estateClosedLoopFsm';
import { PhoenixDailyBootEngine } from './phoenixDailyBoot';
import {
  evaluateSystemFirstIocGate,
  verifyRepositoryZeroDependencyContinuity,
} from './systemFirstIocReconciler';
import { DagsterOrchestrator } from './dagsterOrchestrator';
import {
  EstateGrandUnionEngine,
  evaluateEnsembleVsFrontier,
} from './estateGrandUnion';
import { ESTATE_WORKSTREAMS, verifyIntakeBodyIntegrity } from './estateWorkstreams';
import {
  auditInstallerShortcuts,
  buildFirstUseAuditSnapshot,
  evaluateAgentsMdRatchet,
  observeCeremonyLedger,
  reproduceLegacyEscapedLinesBug,
} from './firstUseGovernanceAudit';
import {
  buildI8095LockdownSnapshot,
  evaluateZeroPollingGuard,
  probeSurfaceMetaTruthfully,
  verifyFailClosedAuthEnvelope,
} from './i8095Lockdown';
import { buildMeridianSymphonySnapshot } from './meridianSymphony';
import {
  build231GatesMatrix,
  CODEX_SPHERES,
  computePillarEquilibrium,
  evaluateChronoReplay,
  evaluateGatePair,
  QLIPHOTH_REGISTRY,
  THREE_VEILS,
  verifyThreeKeyNonCollusion,
} from './codexCrescendo';
import {
  evaluateCrescendoGoLiveSignOff,
  resolveDeclaredAppRoute,
} from './crescendoThreeWayUnion';
import {
  computeCanonReadings,
  ENGLISH_EXT_TABLE,
  findCanonEquivalences,
  inspectDualModeEnglishDiff,
  readingsForText,
  renderLegacySummaryCardText,
  sanitizeHermesInput,
  scoreGreekIsopsephy,
  scoreHebrewGematria,
  scoreLegacyHebrewWraparound,
} from './hermesCipherEngine';
import {
  computeAstronomicalEphemeris,
  evaluateDailyChallengeGuess,
  getDailyChallengeForDate,
  resolvePathPresentation,
  resolveSephirahForValue,
  SEPHIROT,
  TREE_PATHS,
} from './hermesTreeCatalog';
import {
  deriveInterpretedLayer,
  MAX_WORLD_CACHE_ENTRIES,
  resolveSanctuaryPlace,
  validateCoordinates,
} from './hermesWorldConnector';
import { ModelSupplyRegistry } from './modelSupply';
import {
  buildGenTttSnapshot,
  decryptSomaPayload,
  encryptSomaPayload,
  runI8088PanspermiaSimulation,
  rsDecodeAny3,
  rsEncodeK3N8,
  SPORE_MAX_BYTES,
  unwrapShardFromLosslessPng,
  wrapShardInLosslessPng,
} from './genesisSporeTtt';
import {
  buildSafeCallbackData,
  CEO_SINGLE_SCREEN_CHAR_BUDGET,
  escapeTelegramHtml,
  escapeTelegramMarkdownV2,
  OttoNumenConciergeEngine,
  TELEGRAM_MAX_CALLBACK_BYTES,
} from './ottoNumenTelegram';
import {
  classifyCodeForRegoGovernance,
  computeInvestorUnitEconomics,
  computeSynchronicityMerkleStamp,
  FounderConfigEngine,
  simulateAcademyModule,
} from './founderRegoChronosPlane';
import {
  compareLegacyVsProspector2100,
  Prospector2100Engine,
} from './prospectorResearchMumchimp';
import {
  evaluateUnseenTransferPilot,
  simulateStandoutAcademyTrack,
} from './genesisAcademyEngine';
import {
  auditEpistemicClaim,
  UhnwSovereignConciergeEngine,
} from './uhnwSovereignCharter';
import {
  analyzeConciergeDocument,
  MumsConciergeEngine,
  parseKernelPermission,
  verifyProviderReceipt,
} from './mumsConcierge';
import { calculateTokenEconomics } from './pricingCatalog';
import { RouterEngine } from './routerCore';
import {
  AssertionCheck,
  ChaosConfig,
  ChaosReport,
  ChaosTimelineEvent,
  VerificationCaseResult,
  VerificationSuiteReport,
} from './types';

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  const idx = Math.min(sorted.length - 1, Math.floor((p / 100) * sorted.length));
  return sorted[idx];
}

/**
 * Executes real end-to-end Integration Tests and Adversarial Falsifiers
 * against fresh isolated RouterEngine + DagsterOrchestrator instances.
 */
export function runFullVerificationSuite(): VerificationSuiteReport {
  const suiteStart = Date.now();
  const cases: VerificationCaseResult[] = [
    runIntegrationMultiLaneRouting(),
    runIntegrationBudgetEnforcement(),
    runIntegrationDagsterAssetLineage(),
    runIntegrationIdempotentWalReplay(),
    runIntegrationHermesSanitizationAndPrivacy(),
    runIntegrationDailyGameFullYearAndCanon(),
    runFalsifierF1CapSaveKeyClobbering(),
    runFalsifierF2DeepSeek402AndTopUpRecovery(),
    runFalsifierF3LaunchdCrashZeroWalLoss(),
    runFalsifierF4AllLanesFailedDiagnosticFidelity(),
    runFalsifierF5ConcurrentCapSaveRace(),
    runFalsifierF6ExactProviderTokenMath(),
    runFalsifierF7MeridianBlindAndDoubleCountInvariant(),
    runFalsifierF8QuotaPreExhaustionAndPolicyCompliance(),
    runFalsifierF9SpecialistOrchestrationAndRecoveryHonesty(),
    runFalsifierF10IntakeHashBindingAndEstateHonesty(),
    runFalsifierF11SymphonyTruthInvariant(),
    runFalsifierF12I8095ClassALockdown(),
    runFalsifierF13AuraBinaryManifoldAndChronoForking(),
    runFalsifierF14HermesLivingTreeIntegrity(),
    runFalsifierF15WorldCoordinatePrivacyAndResonancePurity(),
    runFalsifierF16HermesFuzzChaosAndDeterminism(),
    runFalsifierF17CodexCrescendoMatrixAndNonCollusion(),
    runFalsifierF18I8088PanspermiaAndGenTtt(),
    runFalsifierF19GrandUnionChronosInterCloudAndEnsemble(),
    runFalsifierF20FirstUseMachineAgentGovernanceAudit(),
    runFalsifierF21OttoNumenVipTelegramTriageAndFormatting(),
    runFalsifierF22Prospector2100CausalResearchAndMumchimp(),
    runFalsifierF23FounderRegoConstitutionAndChronosMerkle(),
    runFalsifierF24UhnwSovereignCharterAndStandoutTransfer(),
    runFalsifierF25MumConciergeFamilySafetyAndEon001(),
    runFalsifierF26AutonomousReactivityCustodyAndFencing(),
    runFalsifierF27MeridianCapabilityCalculusAnd10CertScenarios(),
    runIntegrationCoreRouterDagsterGrandUnionConcierge(),
    runIntegrationMccOmniflowWorkerRecoveryKarma(),
    runIntegrationGeminiSyncAndAuditHonesty(),
    runIntegrationPhoenixConstitutionOmniflowSealLifecycle(),
    runFalsifierF28GeminiSync7760SecurityAndReadback(),
    runFalsifierF29KarmaSettlementAndResilienceMatrixHonesty(),
    runFalsifierF30ClosedLoopFsmConstitutionAndTrapRejection(),
    runFalsifierF31PhoenixSovereignVetoAndAutoRevoke(),
  ];

  const totalAssertions = cases.reduce((acc, c) => acc + c.assertions.length, 0);
  const passedAssertions = cases.reduce(
    (acc, c) => acc + c.assertions.filter((a) => a.passed).length,
    0
  );
  const passedCases = cases.filter((c) => c.passed).length;

  return {
    runAt: new Date().toISOString(),
    totalCases: cases.length,
    passedCases,
    failedCases: cases.length - passedCases,
    totalAssertions,
    passedAssertions,
    durationMs: Math.max(1, Date.now() - suiteStart),
    cases,
  };
}

function finalizeCase(
  id: string,
  category: 'integration' | 'falsifier',
  title: string,
  hypothesis: string,
  startMs: number,
  assertions: AssertionCheck[]
): VerificationCaseResult {
  const failed = assertions.filter((a) => !a.passed);
  return {
    id,
    category,
    title,
    hypothesis,
    passed: failed.length === 0,
    durationMs: Math.max(1, Date.now() - startMs),
    assertions,
    counterexample:
      failed.length > 0
        ? failed.map((f) => `${f.name}: expected ${f.expected}, got ${f.actual}`).join('; ')
        : null,
  };
}

function runIntegrationMultiLaneRouting(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 0 });
  const r1 = router.route({
    clientKey: 'pk_live_opencode_primary_94a2',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 1024,
    strategy: 'priority_failover',
  });
  const r2 = router.route({
    clientKey: 'pk_live_canary_probe_71c9',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 512,
    strategy: 'weighted_cost',
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'Primary OpenCode key routes via DeepSeek Flash (200)',
      passed: r1.ok && r1.httpStatus === 200 && r1.selectedLaneId === 'deepseek-flash',
      expected: '200 via deepseek-flash',
      actual: `${r1.httpStatus} via ${r1.selectedLaneId}`,
    },
    {
      name: 'Secondary Canary key routes cleanly with distinct WAL sequence',
      passed: r2.ok && r2.httpStatus === 200 && r2.receiptSequence === 2,
      expected: '200 with sequence=2',
      actual: `${r2.httpStatus} with sequence=${r2.receiptSequence}`,
    },
    {
      name: 'Gateway routing overhead remains under 500 µs',
      passed: r1.gatewayOverheadUs < 500 && r2.gatewayOverheadUs < 500,
      expected: '< 500 µs',
      actual: `${r1.gatewayOverheadUs} µs / ${r2.gatewayOverheadUs} µs`,
    },
  ];
  return finalizeCase(
    'INT-01',
    'integration',
    'Multi-Key Routing & WAL Sequence Ordering',
    'Both active client keys dispatch through healthy upstream lanes and commit monotonic WAL receipts.',
    start,
    assertions
  );
}

function runIntegrationBudgetEnforcement(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 0 });
  const capRes = router.keyStore.atomicCapSave('ci_canary', 2.0);
  const res = router.route({
    clientKey: 'pk_live_canary_probe_71c9',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 1024,
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'Budget cap lowers ci_canary ceiling to $2.00 atomically',
      passed: capRes.ok && capRes.newBudgetUsd === 2.0,
      expected: 'ok=true, newBudget=2.0',
      actual: `ok=${capRes.ok}, newBudget=${capRes.newBudgetUsd}`,
    },
    {
      name: 'Requests above daily ceiling return HTTP 402 budget_exceeded (not 401)',
      passed: !res.ok && res.httpStatus === 402 && res.errorPayload?.error.type === 'budget_exceeded',
      expected: '402 budget_exceeded',
      actual: `${res.httpStatus} ${res.errorPayload?.error.type}`,
    },
  ];
  return finalizeCase(
    'INT-02',
    'integration',
    'Atomic Daily Budget Ceiling Enforcement',
    'Over-budget client keys reject before upstream dispatch with HTTP 402 budget_exceeded rather than 401.',
    start,
    assertions
  );
}

function runIntegrationDagsterAssetLineage(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 10 });
  const dagster = new DagsterOrchestrator();

  router.dropVaultKeysInMemory();
  const droppedState = router.isVaultHydrated();
  const tick = dagster.evaluateSensors(router);
  const healedState = router.isVaultHydrated();

  const assertions: AssertionCheck[] = [
    {
      name: 'Simulated env drop is detected as unhydrated vault',
      passed: droppedState === false,
      expected: 'vaultHydrated=false',
      actual: `vaultHydrated=${droppedState}`,
    },
    {
      name: 'vault_env_drift_sensor triggers RunRequest automatically',
      passed: tick.triggeredSensors.includes('vault_env_drift_sensor'),
      expected: 'vault_env_drift_sensor in triggeredSensors',
      actual: JSON.stringify(tick.triggeredSensors),
    },
    {
      name: 'All 4 upstream provider keys are re-hydrated in memory',
      passed: healedState === true,
      expected: 'vaultHydrated=true',
      actual: `vaultHydrated=${healedState}`,
    },
  ];
  return finalizeCase(
    'INT-03',
    'integration',
    'Dagster Vault Drift Sensor Auto-Hydration',
    'Dagster vault_env_drift_sensor detects missing in-memory provider credentials and materializes vault_provider_keys without manual io heal-router.',
    start,
    assertions
  );
}

function runIntegrationIdempotentWalReplay(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 5 });
  const r1 = router.route({
    clientKey: 'pk_live_opencode_primary_94a2',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 600,
    idempotencyKey: 'idem-tx-991',
  });
  const r2 = router.route({
    clientKey: 'pk_live_opencode_primary_94a2',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 600,
    idempotencyKey: 'idem-tx-991',
  });
  const stats = router.ledger.getStats();

  const assertions: AssertionCheck[] = [
    {
      name: 'Duplicate idempotencyKey reuses original WAL sequence',
      passed: r1.receiptSequence === r2.receiptSequence && r1.receiptSequence === 6,
      expected: 'seq1=6, seq2=6',
      actual: `seq1=${r1.receiptSequence}, seq2=${r2.receiptSequence}`,
    },
    {
      name: 'WAL total receipt count increments once for idempotent replay',
      passed: stats.totalReceipts === 6,
      expected: 'totalReceipts=6',
      actual: `totalReceipts=${stats.totalReceipts}`,
    },
  ];
  return finalizeCase(
    'INT-04',
    'integration',
    'WAL Idempotency Deduplication',
    'Retried requests sharing an idempotencyKey do not create duplicate billing receipts.',
    start,
    assertions
  );
}

/**
 * FALSIFIER F1: Attempts to reproduce the exact cap-save key-file clobbering bug
 * where updating ci_canary dropped opencode_primary, plus single-key canary blindness.
 */
function runFalsifierF1CapSaveKeyClobbering(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 0 });

  // 1. Verify legacy clobber simulation IS caught and rolled back by atomic guard
  const clobberAttempt = router.keyStore.atomicCapSave('ci_canary', 250, {
    simulateLegacyClobberBug: true,
  });

  // 2. Verify real in-place atomicCapSave preserves BOTH keys
  const validSave = router.keyStore.atomicCapSave('ci_canary', 250);
  const opencodeResp = router.route({
    clientKey: 'pk_live_opencode_primary_94a2',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 512,
  });
  const canaryResp = router.route({
    clientKey: 'pk_live_canary_probe_71c9',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 512,
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'Atomic invariant blocks & rolls back single-key clobber commit',
      passed: clobberAttempt.ok === false && clobberAttempt.rolledBack === true,
      expected: 'ok=false, rolledBack=true',
      actual: `ok=${clobberAttempt.ok}, rolledBack=${clobberAttempt.rolledBack}`,
    },
    {
      name: 'Valid cap-save preserves all 2 client keys and probes both',
      passed:
        validSave.ok &&
        validSave.preservedKeyCount === 2 &&
        validSave.verifiedKeys.length === 2 &&
        validSave.verifiedKeys.every((v) => v.valid),
      expected: '2 preserved keys, 2/2 verified',
      actual: `${validSave.preservedKeyCount} preserved, ${validSave.verifiedKeys.filter((v) => v.valid).length}/2 verified`,
    },
    {
      name: 'OpenCode primary key routes 200 OK after canary budget edit',
      passed: opencodeResp.ok && opencodeResp.httpStatus === 200,
      expected: '200 OK',
      actual: `${opencodeResp.httpStatus} (${opencodeResp.errorPayload?.error.detail ?? 'ok'})`,
    },
    {
      name: 'Canary key also routes 200 OK after budget edit',
      passed: canaryResp.ok && canaryResp.httpStatus === 200,
      expected: '200 OK',
      actual: `${canaryResp.httpStatus}`,
    },
  ];

  return finalizeCase(
    'F1',
    'falsifier',
    'Falsifier F1: Cap-Save Key Clobbering & Canary Blindness',
    'Updating a budget ceiling on one key must never drop sibling keys, and pre-commit probes must verify 100% of active keys.',
    start,
    assertions
  );
}

/**
 * FALSIFIER F2: Reproduces DeepSeek Flash 402 credit exhaustion -> verifies immediate
 * healthy failover (0 dropped requests) + distinct 402 classification + post-top-up recovery via Dagster sensor.
 */
function runFalsifierF2DeepSeek402AndTopUpRecovery(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 0 });
  const dagster = new DagsterOrchestrator();

  // Inject DeepSeek 402 credit exhaustion
  router.setLaneFault('deepseek-flash', '402_credit_exhausted', 0);

  const failoverRes = router.route({
    clientKey: 'pk_live_opencode_primary_94a2',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 1024,
  });

  const deepseekAttempt = failoverRes.attempts.find((a) => a.laneId === 'deepseek-flash');

  // Now user tops up DeepSeek credits ($50) -> before sensor tick, lane was OPEN; sensor un-trips it
  router.topUpLaneCredits('deepseek-flash', 50);
  const sensorRes = dagster.evaluateSensors(router);

  const recoveredRes = router.route({
    clientKey: 'pk_live_opencode_primary_94a2',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 1024,
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'DeepSeek 402 attempt is classified as billing_exhausted (402), NEVER 401 unknown API key',
      passed: deepseekAttempt?.httpStatus === 402 && deepseekAttempt?.errorType === 'billing_exhausted',
      expected: '402 billing_exhausted',
      actual: `${deepseekAttempt?.httpStatus} ${deepseekAttempt?.errorType}`,
    },
    {
      name: 'Request seamlessly fails over to healthy secondary lane (200 OK)',
      passed: failoverRes.ok && failoverRes.httpStatus === 200 && failoverRes.selectedLaneId === 'anthropic-sonnet',
      expected: '200 OK via anthropic-sonnet',
      actual: `${failoverRes.httpStatus} via ${failoverRes.selectedLaneId}`,
    },
    {
      name: 'After credit top-up, Dagster billing_recovery_sensor un-trips DeepSeek circuit',
      passed: sensorRes.triggeredSensors.includes('billing_recovery_sensor'),
      expected: 'billing_recovery_sensor triggered',
      actual: JSON.stringify(sensorRes.triggeredSensors),
    },
    {
      name: 'Subsequent request routes back onto recovered DeepSeek Flash lane',
      passed: recoveredRes.ok && recoveredRes.selectedLaneId === 'deepseek-flash',
      expected: 'deepseek-flash',
      actual: `${recoveredRes.selectedLaneId}`,
    },
  ];

  return finalizeCase(
    'F2',
    'falsifier',
    'Falsifier F2: DeepSeek 402 Credit Drain & Top-Up Recovery',
    'Credit exhaustion must classify as 402 (not 401), failover without user error, and recover within 1 Dagster sensor cycle after top-up.',
    start,
    assertions
  );
}

/**
 * FALSIFIER F3: Simulates 2,500 buffered/WAL receipt sequences followed by abrupt worker restart.
 * Proves legacy launchd mode loses buffered receipts while Dagster WAL mode preserves 100%.
 */
function runFalsifierF3LaunchdCrashZeroWalLoss(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 552 });
  const dagster = new DagsterOrchestrator();

  // Stream 1,830 new receipts into durable WAL (matching the exact 552 -> 2,382 incident scale)
  for (let i = 0; i < 1830; i++) {
    router.ledger.append(
      {
        idempotencyKey: `burst-wal-${i}`,
        timestamp: new Date().toISOString(),
        clientKeyId: 'opencode_primary',
        laneId: 'deepseek-flash',
        provider: 'DeepSeek',
        model: 'deepseek-chat',
        tokens: 512,
        costUsd: 0.00014,
        httpStatus: 200,
      },
      true
    );
  }

  const dagsterRestart = dagster.simulateWorkerRestart(router, 'dagster_durable');

  // Also test legacy RAM-only ledger to prove falsifier catches real loss when WAL is disabled
  const legacyRouter = new RouterEngine({ initialReceipts: 552 });
  for (let i = 0; i < 1830; i++) {
    legacyRouter.ledger.append(
      {
        idempotencyKey: `burst-ram-${i}`,
        timestamp: new Date().toISOString(),
        clientKeyId: 'opencode_primary',
        laneId: 'deepseek-flash',
        provider: 'DeepSeek',
        model: 'deepseek-chat',
        tokens: 512,
        costUsd: 0.00014,
        httpStatus: 200,
      },
      false
    );
  }
  const legacyLoss = legacyRouter.ledger.simulateRestart(false);

  const assertions: AssertionCheck[] = [
    {
      name: 'Falsifier reproduces exact 1,830 receipt loss when WAL durability is disabled',
      passed: legacyLoss.totalBefore === 2382 && legacyLoss.droppedCount === 1830,
      expected: 'before=2382, dropped=1830',
      actual: `before=${legacyLoss.totalBefore}, dropped=${legacyLoss.droppedCount}`,
    },
    {
      name: 'Dagster durable WAL preserves all 2,382 receipts with 0 dropped across restart',
      passed:
        dagsterRestart.receiptsBeforeRestart === 2382 &&
        dagsterRestart.receiptsAfterRestart === 2382 &&
        dagsterRestart.droppedReceipts === 0,
      expected: 'before=2382, after=2382, dropped=0',
      actual: `before=${dagsterRestart.receiptsBeforeRestart}, after=${dagsterRestart.receiptsAfterRestart}, dropped=${dagsterRestart.droppedReceipts}`,
    },
    {
      name: 'Dagster auto-hydrates all upstream vault keys on worker reboot',
      passed: dagsterRestart.vaultKeysHydratedOnBoot === true,
      expected: 'vaultKeysHydratedOnBoot=true',
      actual: `vaultKeysHydratedOnBoot=${dagsterRestart.vaultKeysHydratedOnBoot}`,
    },
  ];

  return finalizeCase(
    'F3',
    'falsifier',
    'Falsifier F3: Daemon Restart Zero-WAL-Loss & Vault Boot',
    'Restarting a worker mid-burst (2,382 receipts) under Dagster must drop 0 receipts and auto-hydrate vault credentials.',
    start,
    assertions
  );
}

/**
 * FALSIFIER F4: Forces distinct faults on all 4 lanes simultaneously and verifies
 * 502 error response surfaces exact per-lane root causes instead of opaque string.
 */
function runFalsifierF4AllLanesFailedDiagnosticFidelity(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 0 });
  router.setLaneFault('deepseek-flash', '402_credit_exhausted', 0);
  router.setLaneFault('anthropic-sonnet', '401_upstream_key');
  router.setLaneFault('gemini-flash', '429_rate_limit');
  router.setLaneFault('openai-mini', '503_unavailable');

  const res = router.route({
    clientKey: 'pk_live_opencode_primary_94a2',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 1024,
  });

  const diag = res.errorPayload?.error.perLaneDiagnostics ?? [];
  const has402 = diag.some((d) => d.laneId === 'deepseek-flash' && d.httpStatus === 402);
  const has401 = diag.some((d) => d.laneId === 'anthropic-sonnet' && d.httpStatus === 401);
  const has429 = diag.some((d) => d.laneId === 'gemini-flash' && d.httpStatus === 429);
  const has503 = diag.some((d) => d.laneId === 'openai-mini' && d.httpStatus === 503);

  const assertions: AssertionCheck[] = [
    {
      name: 'Returns HTTP 502 upstream when all 4 lanes fail',
      passed: !res.ok && res.httpStatus === 502 && res.errorPayload?.error.type === 'upstream',
      expected: '502 upstream',
      actual: `${res.httpStatus} ${res.errorPayload?.error.type}`,
    },
    {
      name: 'Exposes exact per-lane status codes (402, 401, 429, 503) in diagnostics',
      passed: diag.length === 4 && has402 && has401 && has429 && has503,
      expected: '4 distinct lane statuses [402, 401, 429, 503]',
      actual: diag.map((d) => `${d.laneId}:${d.httpStatus}`).join(', '),
    },
  ];

  return finalizeCase(
    'F4',
    'falsifier',
    'Falsifier F4: All-Lanes-Failed Diagnostic Attribution',
    'When every upstream lane fails, 502 must preserve exact per-lane status codes rather than masking 402/429 behind generic failure text.',
    start,
    assertions
  );
}

/**
 * FALSIFIER F5: Interleaves 500 routing calls across both client keys with 25 atomic cap-save mutations
 * to prove zero torn reads, zero 401 drops, and strictly monotonic WAL sequences.
 */
function runFalsifierF5ConcurrentCapSaveRace(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 0 });
  let authFailures = 0;
  let lastSeq = 0;
  let nonMonotonic = 0;

  for (let i = 0; i < 500; i++) {
    if (i % 20 === 0) {
      const target = i % 40 === 0 ? 'ci_canary' : 'opencode_primary';
      router.keyStore.atomicCapSave(target, 200 + (i % 100));
    }
    const key =
      i % 3 === 0 ? 'pk_live_canary_probe_71c9' : 'pk_live_opencode_primary_94a2';
    const res = router.route({
      clientKey: key,
      modelSlug: 'deepseek-chat',
      estimatedTokens: 300,
    });
    if (res.httpStatus === 401) authFailures++;
    if (res.receiptSequence !== null) {
      if (res.receiptSequence <= lastSeq) nonMonotonic++;
      lastSeq = res.receiptSequence;
    }
  }

  const assertions: AssertionCheck[] = [
    {
      name: 'Zero 401 client auth drops across 500 interleaved cap-save mutations',
      passed: authFailures === 0,
      expected: '0 authFailures',
      actual: `${authFailures} authFailures`,
    },
    {
      name: 'WAL sequence numbers remain strictly monotonic (1..500)',
      passed: nonMonotonic === 0 && lastSeq === 500,
      expected: 'nonMonotonic=0, lastSeq=500',
      actual: `nonMonotonic=${nonMonotonic}, lastSeq=${lastSeq}`,
    },
  ];

  return finalizeCase(
    'F5',
    'falsifier',
    'Falsifier F5: Interleaved Cap-Save & Routing Race Stress',
    'Repeated budget updates during live traffic must never expose a torn key table or drop WAL sequence monotonicity.',
    start,
    assertions
  );
}

/**
 * FALSIFIER F6: Verifies exact micro-dollar provider rate math and "Without PennyD"
 * counterfactual cost math across DeepSeek, Anthropic, Google, and OpenAI.
 */
function runFalsifierF6ExactProviderTokenMath(): VerificationCaseResult {
  const start = Date.now();
  // DeepSeek Chat: 100k uncached ($0.28/1M = $0.028), 200k cached ($0.028/1M = $0.0056), 50k output ($0.42/1M = $0.021)
  // Actual = $0.054600
  // Without PennyD (claude-sonnet-4): (100k + 200k + 50k trim) = 350k in @ $3.00/1M ($1.05) + 50k out @ $15.00/1M ($0.75) = $1.800000
  const ds = calculateTokenEconomics({
    modelSlug: 'deepseek-chat',
    baselineModelSlug: 'claude-sonnet-4',
    uncachedInputTokens: 100_000,
    cachedInputTokens: 200_000,
    outputTokens: 50_000,
    reasoningTokens: 0,
    contextTrimSavedTokens: 50_000,
  });

  // Gemini 2.5 Flash: 1M uncached ($0.30) + 1M cached ($0.075) + 200k out ($0.50) = $0.875000
  const gem = calculateTokenEconomics({
    modelSlug: 'gemini-2.5-flash',
    baselineModelSlug: 'gpt-4o',
    uncachedInputTokens: 1_000_000,
    cachedInputTokens: 1_000_000,
    outputTokens: 200_000,
    reasoningTokens: 0,
    contextTrimSavedTokens: 0,
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'DeepSeek actual cost matches exact token formula ($0.054600)',
      passed: ds.actualTotalCostUsd === 0.0546,
      expected: '0.0546',
      actual: String(ds.actualTotalCostUsd),
    },
    {
      name: 'Without PennyD (Claude Sonnet 4) counterfactual matches ($1.800000)',
      passed: ds.withoutPennydCostUsd === 1.8 && ds.usdSaved === 1.7454,
      expected: 'without=1.8, saved=1.7454',
      actual: `without=${ds.withoutPennydCostUsd}, saved=${ds.usdSaved}`,
    },
    {
      name: 'Tokens saved equals prompt cache hits + context trim (250,000)',
      passed: ds.tokensSavedByPennyD === 250_000,
      expected: '250000',
      actual: String(ds.tokensSavedByPennyD),
    },
    {
      name: 'Gemini 2.5 Flash micro-dollar math matches exact rate card ($0.875000)',
      passed: gem.actualTotalCostUsd === 0.875,
      expected: '0.875',
      actual: String(gem.actualTotalCostUsd),
    },
  ];

  return finalizeCase(
    'F6',
    'falsifier',
    'Falsifier F6: Exact Per-Provider Token & Counterfactual Cost Math',
    'Provider token charges and Without-PennyD counterfactual savings must match published per-1M rate cards to the micro-dollar.',
    start,
    assertions
  );
}

/**
 * FALSIFIER F7: Verifies Meridian Battalion invariants:
 * 1. Every admitted packet carries missionId, ownerId, traceId, and FOCUS chargeId.
 * 2. BLIND producers remain visibly null/BLIND (never coerced to 0).
 * 3. Replaying an idempotencyKey prevents double-counting client spend & lane credits.
 */
function runFalsifierF7MeridianBlindAndDoubleCountInvariant(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 0, seedForensics: 14 });
  const beforeSpend = router.keyStore.getAllKeys().find((k) => k.id === 'opencode_primary')!.spentTodayUsd;

  const first = router.route({
    clientKey: 'pk_live_opencode_primary_94a2',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 2000,
    missionId: 'MSN-ESTATE-409',
    ownerId: 'founder@meridian.estate',
    idempotencyKey: 'meridian-idem-777',
  });
  const afterFirstSpend = router.keyStore.getAllKeys().find((k) => k.id === 'opencode_primary')!.spentTodayUsd;

  const replay = router.route({
    clientKey: 'pk_live_opencode_primary_94a2',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 2000,
    missionId: 'MSN-ESTATE-409',
    ownerId: 'founder@meridian.estate',
    idempotencyKey: 'meridian-idem-777',
  });
  const afterReplaySpend = router.keyStore.getAllKeys().find((k) => k.id === 'opencode_primary')!.spentTodayUsd;

  const packets = router.forensics.getPackets(50);
  const allOwned = packets.every((p) => p.missionId.length > 0 && p.ownerId.length > 0 && p.otelSpan.traceId.length === 32);
  const meridian = router.forensics.getMeridianSnapshot();
  const blindHumanRow = meridian.coverageMatrix.find((r) => r.activity === 'Human work');
  const blindPackets = packets.filter((p) => p.computeEnergyJoules === null);

  const assertions: AssertionCheck[] = [
    {
      name: 'Idempotent replay charges client spend exactly once (zero double-counting)',
      passed:
        afterFirstSpend > beforeSpend &&
        afterReplaySpend === afterFirstSpend &&
        first.receiptSequence === replay.receiptSequence,
      expected: `afterFirst === afterReplay (${afterFirstSpend})`,
      actual: `afterFirst=${afterFirstSpend}, afterReplay=${afterReplaySpend}`,
    },
    {
      name: '100% of admitted packets carry canonical missionId, ownerId, and 32-char OTel traceId',
      passed: allOwned && meridian.activityAccounting.unownedActivities === 0,
      expected: 'allOwned=true, unownedActivities=0',
      actual: `allOwned=${allOwned}, unowned=${meridian.activityAccounting.unownedActivities}`,
    },
    {
      name: 'BLIND telemetry (unlogged human work & unprobed host joules) remains visibly BLIND/null, never 0',
      passed:
        blindHumanRow?.status === 'BLIND' &&
        blindPackets.length > 0 &&
        meridian.physicalResourceAccounting.blindEnergySamplesCount > 0,
      expected: 'Human work=BLIND, blindEnergySamples > 0',
      actual: `Human work=${blindHumanRow?.status}, blindEnergySamples=${meridian.physicalResourceAccounting.blindEnergySamplesCount}`,
    },
  ];

  return finalizeCase(
    'F7',
    'falsifier',
    'Falsifier F7: Meridian Provenance, BLIND != 0 & Double-Count Guard',
    'Every admitted packet must have canonical owner/trace provenance, unmeasured producers must stay visibly BLIND, and idempotent retries must never double-charge.',
    start,
    assertions
  );
}

/**
 * FALSIFIER F8: Proves quota-aware admission triggers pre-exhaustion fallback
 * before hitting 0% exhaustion AND strictly honors zero-retention & geo restrictions.
 */
function runFalsifierF8QuotaPreExhaustionAndPolicyCompliance(): VerificationCaseResult {
  const start = Date.now();
  const supply = new ModelSupplyRegistry();

  // Drop DeepSeek V4.1 Flash Free quota to 10% (below 15% pre-exhaustion buffer)
  supply.setModelQuotaAndPolicy('deepseek-v4.1-flash-free', { quotaRemainingPct: 10 });
  // Mark GLM-5.3-Flash Free as geo-restricted
  supply.setModelQuotaAndPolicy('glm-5.3-flash-free', { geoAllowed: false });

  // 1. Standard routine coding task should bypass both and select MiniMax M3.1 Flash Free cleanly
  const standardDecision = supply.admitTask({
    taskClass: 'routine_coding',
    requiresZeroRetention: false,
    estimatedTokens: 2000,
    regionCode: 'eu-central',
  });

  // 2. Sensitive zero-retention task must NEVER admit provider_logged free models (selects Nemotron zero-retention)
  const sensitiveDecision = supply.admitTask({
    taskClass: 'routine_coding',
    requiresZeroRetention: true,
    estimatedTokens: 2000,
    regionCode: 'eu-central',
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'Pre-exhaustion fallback drains DeepSeek Free at 10% before hard 0% failure',
      passed:
        standardDecision.admitted &&
        standardDecision.preExhaustionFallbackTriggered &&
        standardDecision.selectedModelId === 'minimax-m3.1-flash-free',
      expected: 'admitted=true, preExhaustionFallback=true, minimax-m3.1-flash-free',
      actual: `admitted=${standardDecision.admitted}, fallback=${standardDecision.preExhaustionFallbackTriggered}, model=${standardDecision.selectedModelId}`,
    },
    {
      name: 'Geo-restricted GLM-5.3-Flash Free is never bypassed or admitted',
      passed: standardDecision.rejectedCandidates.some((r) => r.modelId === 'glm-5.3-flash-free'),
      expected: 'glm-5.3-flash-free in rejectedCandidates',
      actual: JSON.stringify(standardDecision.rejectedCandidates.map((r) => r.modelId)),
    },
    {
      name: 'Sensitive zero-retention task routes strictly to zero_retention Nemotron endpoint',
      passed: sensitiveDecision.admitted && sensitiveDecision.selectedModelId === 'nemotron-nano-free',
      expected: 'nemotron-nano-free',
      actual: String(sensitiveDecision.selectedModelId),
    },
  ];

  return finalizeCase(
    'F8',
    'falsifier',
    'Falsifier F8: Quota Pre-Exhaustion & Provider Terms Compliance',
    'Supply admission must fall back before quota exhaustion and never bypass geo or data-retention terms.',
    start,
    assertions
  );
}

/**
 * FALSIFIER F9: Verifies Microsoft Research specialist small-model routing
 * (MagenticBrain, Fara1.5), selective frontier escalation, and honest unverified Gemini recovery state.
 */
function runFalsifierF9SpecialistOrchestrationAndRecoveryHonesty(): VerificationCaseResult {
  const start = Date.now();
  const supply = new ModelSupplyRegistry();

  const orch = supply.admitTask({
    taskClass: 'orchestration',
    requiresZeroRetention: true,
    estimatedTokens: 1500,
    regionCode: 'us-west',
  });
  const cu = supply.admitTask({
    taskClass: 'computer_use',
    requiresZeroRetention: true,
    estimatedTokens: 1800,
    regionCode: 'us-west',
  });
  const review = supply.admitTask({
    taskClass: 'independent_review',
    requiresZeroRetention: true,
    estimatedTokens: 2000,
    regionCode: 'us-west',
  });
  const bench = supply.runSmallVsFrontierBenchmark(200);
  const recovery = supply.getRecoveryPackage();
  const matrix = supply.getBattalionRoutingMatrix();
  const certProbe = supply.runIndependentCertification();
  const modelsBefore = supply.getModels();
  const hasAllSupplyChannels =
    modelsBefore.some((m) => m.providerSource === 'Local / Edge') &&
    modelsBefore.some((m) => m.providerSource === 'Browser / Deterministic') &&
    modelsBefore.some((m) => m.providerSource === 'OpenCode Catalogue') &&
    modelsBefore.some((m) => m.providerSource === 'Google Gemini');

  // Inject repeated failures on minimax-m3.1-flash-free via Optimus feedback to verify quarantine & re-ranking
  for (let i = 0; i < 40; i++) {
    supply.recordOptimusOutcome({ modelId: 'minimax-m3.1-flash-free', verified: false, latencyMs: 320 });
  }
  const minimaxAfter = supply.getModels().find((m) => m.id === 'minimax-m3.1-flash-free');
  const minimaxQuarantined = minimaxAfter?.certification === 'UNVERIFIED';

  const geminiSyncPending = recovery.find((r) => r.id === 'REC-03')?.status === 'PENDING_INSPECTION';
  const argonPending = recovery.find((r) => r.id === 'REC-04')?.status === 'PENDING_INSPECTION';

  const assertions: AssertionCheck[] = [
    {
      name: 'Orchestration tasks route to MagenticBrain specialist instead of frontier',
      passed: orch.selectedModelId === 'msr-magentic-brain' && orch.escalatedToFrontier === false,
      expected: 'msr-magentic-brain, escalated=false',
      actual: `${orch.selectedModelId}, escalated=${orch.escalatedToFrontier}`,
    },
    {
      name: 'Computer-use tasks route to Fara1.5 specialist',
      passed: cu.selectedModelId === 'msr-fara-1.5' && cu.escalatedToFrontier === false,
      expected: 'msr-fara-1.5, escalated=false',
      actual: `${cu.selectedModelId}, escalated=${cu.escalatedToFrontier}`,
    },
    {
      name: 'Independent review selectively escalates to Claude Sonnet 4 frontier',
      passed: review.selectedModelId === 'claude-sonnet-4-frontier' && review.escalatedToFrontier === true,
      expected: 'claude-sonnet-4-frontier, escalated=true',
      actual: `${review.selectedModelId}, escalated=${review.escalatedToFrontier}`,
    },
    {
      name: 'Small-model Legion orchestration reduces cost >=85% vs frontier-everywhere',
      passed: bench.costReductionPct >= 85 && bench.smallOrchestration.smallModelSharePct >= 85,
      expected: 'costReductionPct >= 85, smallShare >= 85',
      actual: `reduction=${bench.costReductionPct}%, smallShare=${bench.smallOrchestration.smallModelSharePct}%`,
    },
    {
      name: 'Supply discovery covers OpenCode, Gemini, Local/Edge, Browser/Deterministic & MSR',
      passed: hasAllSupplyChannels && matrix.length === 5 && certProbe.certifiedCount >= 10,
      expected: 'all channels present, 5 matrix mappings, >=10 certified',
      actual: `channels=${hasAllSupplyChannels}, matrix=${matrix.length}, certified=${certProbe.certifiedCount}`,
    },
    {
      name: 'Optimus feedback quarantines degraded model (<80% pass rate) from admission',
      passed: Boolean(minimaxQuarantined),
      expected: 'minimax-m3.1-flash-free UNVERIFIED after repeated failures',
      actual: `certification=${minimaxAfter?.certification}, passRate=${minimaxAfter?.capabilityPassRatePct}%`,
    },
    {
      name: 'GEMINI-FREE-MODEL-RECOVERY preserves unverified Gemini/Argon items as PENDING_INSPECTION',
      passed: geminiSyncPending && argonPending,
      expected: 'REC-03 & REC-04 PENDING_INSPECTION',
      actual: `REC-03=${recovery.find((r) => r.id === 'REC-03')?.status}, REC-04=${recovery.find((r) => r.id === 'REC-04')?.status}`,
    },
  ];

  return finalizeCase(
    'F9',
    'falsifier',
    'Falsifier F9: MSR Small-Model Routing, Optimus Feedback & Recovery Honesty',
    'Routine orchestration and computer-use must route to MagenticBrain/Fara1.5, frontier review must escalate selectively, Optimus feedback must quarantine degraded lanes, and uninspected Gemini/Argon artifacts must stay PENDING_INSPECTION.',
    start,
    assertions
  );
}

function runFalsifierF10IntakeHashBindingAndEstateHonesty(): VerificationCaseResult {
  const start = Date.now();
  const payload = JSON.stringify({ mission: 'MSN-ESTATE-409', sequence: 2382 });
  const genuineSha = createHash('sha256').update(payload, 'utf8').digest('hex');
  const validPubKeyHex = 'a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90';

  // 1. Missing or all-zero public key must FAIL CLOSED (fixes CertifierPublicVerifier defect)
  const missingKey = verifyIntakeBodyIntegrity({
    verifierPublicKeyHex: '',
    claimedBodySha256: genuineSha,
    receivedBodyBytes: payload,
    storedCopyBytes: payload,
  });
  const allZeroKey = verifyIntakeBodyIntegrity({
    verifierPublicKeyHex: '0'.repeat(64),
    claimedBodySha256: genuineSha,
    receivedBodyBytes: payload,
    storedCopyBytes: payload,
  });

  // 2. Claimed header hash matching old body while received body is tampered must fail
  const tamperedBody = verifyIntakeBodyIntegrity({
    verifierPublicKeyHex: validPubKeyHex,
    claimedBodySha256: genuineSha,
    receivedBodyBytes: payload.replace('2382', '9999'),
    storedCopyBytes: payload.replace('2382', '9999'),
  });

  // 3. Stored copy corruption without re-hashing copy must fail
  const corruptedCopy = verifyIntakeBodyIntegrity({
    verifierPublicKeyHex: validPubKeyHex,
    claimedBodySha256: genuineSha,
    receivedBodyBytes: payload,
    storedCopyBytes: payload + ' ',
  });

  // 4. Genuine key + bound received SHA-256 + re-hashed copy passes
  const valid = verifyIntakeBodyIntegrity({
    verifierPublicKeyHex: validPubKeyHex,
    claimedBodySha256: genuineSha,
    receivedBodyBytes: payload,
    storedCopyBytes: payload,
  });

  const sourceLocated = ESTATE_WORKSTREAMS.filter((w) => w.status === 'SOURCE-LOCATED').length;
  const partial = ESTATE_WORKSTREAMS.filter((w) => w.status === 'PARTIAL').length;
  const unknown = ESTATE_WORKSTREAMS.filter((w) => w.status === 'UNKNOWN').length;
  const zeroFabricatedDrive = ESTATE_WORKSTREAMS.every((w) => w.drivePath === 'UNKNOWN');

  const assertions: AssertionCheck[] = [
    {
      name: 'Unset or all-zero Ed25519 verifier key fails CLOSED (never Ok(()))',
      passed:
        !missingKey.ok &&
        missingKey.reason === 'verifier_key_missing_fail_closed' &&
        !allZeroKey.ok &&
        allZeroKey.reason === 'verifier_key_missing_fail_closed',
      expected: 'ok=false, reason=verifier_key_missing_fail_closed',
      actual: `missing=${missingKey.reason}, zero=${allZeroKey.reason}`,
    },
    {
      name: 'Claimed body hash is bound to actual received payload bytes',
      passed: !tamperedBody.ok && tamperedBody.reason === 'received_body_hash_mismatch',
      expected: 'ok=false, reason=received_body_hash_mismatch',
      actual: `ok=${tamperedBody.ok}, reason=${tamperedBody.reason}`,
    },
    {
      name: 'Destination copy is re-hashed and mismatches are rejected',
      passed: !corruptedCopy.ok && corruptedCopy.reason === 'copy_rehash_mismatch',
      expected: 'ok=false, reason=copy_rehash_mismatch',
      actual: `ok=${corruptedCopy.ok}, reason=${corruptedCopy.reason}`,
    },
    {
      name: 'Valid verifier key + matching received & copy SHA-256 passes',
      passed: valid.ok && valid.actualReceivedSha256 === valid.actualCopySha256,
      expected: 'ok=true with matching SHA-256',
      actual: `ok=${valid.ok}, reason=${valid.reason}`,
    },
    {
      name: '9-workstream forensic ledger preserves honest counts and UNKNOWN Drive paths',
      passed:
        ESTATE_WORKSTREAMS.length === 9 &&
        sourceLocated === 3 &&
        partial === 5 &&
        unknown === 1 &&
        zeroFabricatedDrive,
      expected: 'total=9, SOURCE-LOCATED=3, PARTIAL=5, UNKNOWN=1, drivePath=UNKNOWN',
      actual: `total=${ESTATE_WORKSTREAMS.length}, SL=${sourceLocated}, P=${partial}, U=${unknown}`,
    },
  ];

  return finalizeCase(
    'F10',
    'falsifier',
    'Falsifier F10: Fail-Closed Intake Hash-Binding & 9-Workstream Epistemic Honesty',
    'Verifier must fail closed when key is unset/zero, bind claimed SHA-256 to received payload, re-hash destination copy, and keep unverified estate paths UNKNOWN.',
    start,
    assertions
  );
}

function runFalsifierF11SymphonyTruthInvariant(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 100, seedForensics: 6 });
  const dagster = new DagsterOrchestrator();
  const supply = new ModelSupplyRegistry();

  const snap = buildMeridianSymphonySnapshot({ router, dagster, supply });
  const faceVoice = snap.nodes.find((n) => n.id === 'genesis_face_unknown');
  const idpNode = snap.nodes.find((n) => n.id === 'idp_delivery');
  const g7 = snap.deliveryGates.find((g) => g.id === 'G7');
  const resolvedIncidents = snap.incidents.filter((i) => i.severity === 'RESOLVED');

  const nodeIds = new Set(snap.nodes.map((n) => n.id));
  const allEdgesValid = snap.edges.every((e) => nodeIds.has(e.from) && nodeIds.has(e.to));

  const assertions: AssertionCheck[] = [
    {
      name: 'All 12 estate pillars plus subsystem/mission/atom layers exist with valid edges',
      passed: snap.nodes.length >= 18 && snap.edges.length >= 24 && allEdgesValid,
      expected: '>=18 nodes, >=24 valid edges',
      actual: `nodes=${snap.nodes.length}, edges=${snap.edges.length}, valid=${allEdgesValid}`,
    },
    {
      name: 'Unimplemented Genesis Face voice/avatar node stays visibly UNKNOWN',
      passed: faceVoice?.epistemicStatus === 'UNKNOWN',
      expected: 'genesis_face_unknown=UNKNOWN',
      actual: `status=${faceVoice?.epistemicStatus}`,
    },
    {
      name: 'IDP #8169 stays PENDING_INSPECTION and Gate G7 stays PENDING_FLEET_ACCEPTANCE',
      passed:
        idpNode?.epistemicStatus === 'PENDING_INSPECTION' &&
        g7?.status === 'PENDING_FLEET_ACCEPTANCE',
      expected: 'IDP=PENDING_INSPECTION, G7=PENDING_FLEET_ACCEPTANCE',
      actual: `IDP=${idpNode?.epistemicStatus}, G7=${g7?.status}`,
    },
    {
      name: 'All 6 lifecycle stages and KARMA resolved incidents report 0 recurrences',
      passed:
        snap.lifecycleStages.length === 6 &&
        snap.deliveryGates.length === 7 &&
        resolvedIncidents.every((i) => i.recurrenceCount === 0),
      expected: '6 stages, 7 gates, 0 recurrences for resolved incidents',
      actual: `stages=${snap.lifecycleStages.length}, gates=${snap.deliveryGates.length}`,
    },
  ];

  return finalizeCase(
    'F11',
    'falsifier',
    'Falsifier F11: Meridian Symphony Causal Graph & Epistemic Truthfulness',
    'Constellation must represent real live engines while preserving UNKNOWN/PENDING_INSPECTION/PENDING_FLEET_ACCEPTANCE for unverified systems.',
    start,
    assertions
  );
}

function runFalsifierF12I8095ClassALockdown(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 10, seedForensics: 4 });
  const dagster = new DagsterOrchestrator();

  const lock = buildI8095LockdownSnapshot({ router, dagster });
  const unsetKey = verifyFailClosedAuthEnvelope({ founderPublicKeyHex: '', cfAccessJwt: 'a.b.c' });
  const forgedJwt = verifyFailClosedAuthEnvelope({
    founderPublicKeyHex: 'a'.repeat(64),
    cfAccessJwt: 'hdr.payload.forged',
  });
  const pollLoop = evaluateZeroPollingGuard('while true; do sleep 3 && gh pr view 8164; done');
  const surfaceMeta = probeSurfaceMetaTruthfully(false);

  const assertions: AssertionCheck[] = [
    {
      name: 'All 17 defect classes (D-01..D-17) & 5 NASA Class-A NPR 7150.2D properties mapped',
      passed: lock.defects.length === 17 && lock.nasaProperties.length === 5 && lock.correctionChain.length === 5,
      expected: '17 defects, 5 NPR properties, 5 CA links',
      actual: `defects=${lock.defects.length}, props=${lock.nasaProperties.length}, ca=${lock.correctionChain.length}`,
    },
    {
      name: 'Scenario G1: Unset Ed25519 key (503) & forged Cloudflare JWT (401) fail closed with 0 rows',
      passed: unsetKey.httpStatus === 503 && forgedJwt.httpStatus === 401 && unsetKey.rowsWritten === 0,
      expected: '503 & 401, rowsWritten=0',
      actual: `unset=${unsetKey.httpStatus}, forged=${forgedJwt.httpStatus}, rows=${unsetKey.rowsWritten}`,
    },
    {
      name: 'Scenario G3: /api/surface/meta reports voiceGatewayConnected=false (zero hardcoding)',
      passed: surfaceMeta.voiceGatewayConnected === false && surfaceMeta.hardcoded === false,
      expected: 'voiceGatewayConnected=false, hardcoded=false',
      actual: `voice=${surfaceMeta.voiceGatewayConnected}, hardcoded=${surfaceMeta.hardcoded}`,
    },
    {
      name: 'Scenario G4: I-8090 Zero-Polling Guard exits 78 on sleep+gh pr view loops',
      passed: pollLoop.exitCode === 78 && !pollLoop.allowed && lock.counts.bddPassed === 4,
      expected: 'exitCode=78, bddPassed=4/4',
      actual: `exitCode=${pollLoop.exitCode}, bddPassed=${lock.counts.bddPassed}/4`,
    },
  ];

  return finalizeCase(
    'F12',
    'falsifier',
    'Falsifier F12: Instruction I-8095 NASA Class-A Mechanical Lockdown',
    'Enforces zero fail-open auth paths (503/401), exit-78 zero-polling lockout, non-hardcoded surface probes, and honest D-01..D-17 status tracking.',
    start,
    assertions
  );
}

function runFalsifierF13AuraBinaryManifoldAndChronoForking(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 20, seedForensics: 4 });
  const dagster = new DagsterOrchestrator();
  const supply = new ModelSupplyRegistry();
  const auraState = createDefaultAuraState();

  const buf = encodeGenesisAtomicFrame({
    timestampNs: 1763256800123456789n,
    traceMerkleRoot: '9e3779b97f4a7c15',
    entityId: 0xdeadbeef,
    causalParentId: 0x00004001,
    metricPrimary: 112.5,
    metricSecondary: 0.64,
    syscallOrOpcode: 429,
    stratum: 1,
    verdictFlags: VERDICT_FLAG_SEALED | VERDICT_FLAG_ZERO_POLL_OK | VERDICT_FLAG_DIGEST_BOUND,
    payloadPreview: 'argon::proxy-4001:429',
  });
  const decoded = decodeGenesisAtomicFrame(buf);

  const rewindCmd = executeAuraOmniCommand('/rewind 42.8', auraState);
  const forkCmd = executeAuraOmniCommand(':fork --upstream kimi --override-intent canary_check', auraState);
  const snap = buildAuraManifoldSnapshot({ router, dagster, supply, auraState });

  const assertions: AssertionCheck[] = [
    {
      name: '64-byte #[repr(C, align(64))] GenesisAtomicFrame encodes and decodes losslessly',
      passed:
        buf.byteLength === FRAME_BYTE_LENGTH &&
        decoded.timestampNs === 1763256800123456789n &&
        decoded.entityId === 0xdeadbeef &&
        decoded.syscallOrOpcode === 429 &&
        decoded.payloadPreview === 'argon::proxy-4001:429',
      expected: '64B roundtrip match (entity=0xdeadbeef, opcode=429)',
      actual: `bytes=${buf.byteLength}, entity=${decoded.entityId.toString(16)}, opcode=${decoded.syscallOrOpcode}`,
    },
    {
      name: 'Law I11 temporal gravity zones transition deterministically across 0..100s',
      passed:
        lawI11Zone(30) === 'LAMINAR' &&
        lawI11Zone(65) === 'COMPRESSION' &&
        lawI11Zone(92) === 'EVENT_HORIZON' &&
        lawI11Zone(100) === 'SEVERED',
      expected: 'LAMINAR -> COMPRESSION -> EVENT_HORIZON -> SEVERED',
      actual: `${lawI11Zone(30)} -> ${lawI11Zone(65)} -> ${lawI11Zone(92)} -> ${lawI11Zone(100)}`,
    },
    {
      name: 'Chrono-Forking /rewind 42.8 + :fork --upstream kimi creates shadow branch',
      passed:
        rewindCmd.ok &&
        forkCmd.ok &&
        snap.activeRewindSec === 42.8 &&
        snap.activeForks.length === 1 &&
        snap.activeForks[0].upstreamOverride === 'kimi',
      expected: 'rewind=42.8s, 1 kimi counterfactual fork',
      actual: `rewind=${snap.activeRewindSec}, forks=${snap.activeForks.length}`,
    },
  ];

  return finalizeCase(
    'F13',
    'falsifier',
    'Falsifier F13: AURA-2100 64-Byte Binary Protocol & Chrono-Forking',
    'Validates zero-copy 64-byte binary frame packing, Law I11 100s gravity zones, and counterfactual shadow lane forks.',
    start,
    assertions
  );
}

function runFalsifierF14HermesLivingTreeIntegrity(): VerificationCaseResult {
  const start = Date.now();
  const iesous = scoreGreekIsopsephy('Ἰησοῦς');
  const beast = scoreGreekIsopsephy('χξϛ');
  const malkuthStd = scoreHebrewGematria('מלכות', false);
  const memGadol = scoreHebrewGematria('שלום', true);
  const wrapDiff = inspectDualModeEnglishDiff('WAX');
  const aweWrap = scoreLegacyHebrewWraparound('AWE');
  const waxWrap = scoreLegacyHebrewWraparound('WAX');

  const canon = computeCanonReadings();
  const sephMalkuth = resolveSephirahForValue(496);
  const daily = getDailyChallengeForDate('2026-11-16');
  const hitEval = evaluateDailyChallengeGuess(
    canon.find((c) => c.reading.total === daily.targetNumber)?.word ?? 'אחד',
    '2026-11-16'
  );
  const ephemeris = computeAstronomicalEphemeris(new Date('2026-11-16T12:00:00Z'), 51.51, -0.13);
  const hePath = TREE_PATHS.find((p) => p.number === 15)!;
  const gdAttr = resolvePathPresentation(hePath, 'golden_dawn');
  const thelemicAttr = resolvePathPresentation(hePath, 'thelemic_tzaddi');

  const assertions: AssertionCheck[] = [
    {
      name: 'Greek 27-letter isopsephy yields exact 888 (Ἰησοῦς) and 666 (χξϛ with Stigma=6)',
      passed: iesous.total === 888 && beast.total === 666 && beast.skipped === 0,
      expected: 'Ἰησοῦς=888, χξϛ=666',
      actual: `Ἰησοῦς=${iesous.total}, χξϛ=${beast.total}`,
    },
    {
      name: 'Hebrew Malkuth stops at Tree root 10 (never folds 10->1 Kether) and Gadol scores final letters 500..900',
      passed:
        malkuthStd.total === 496 &&
        sephMalkuth?.number === 10 &&
        sephMalkuth.name === 'Malkuth' &&
        memGadol.total === 936,
      expected: 'Malkuth=496->10, Shalom Gadol=936',
      actual: `Malkuth=${malkuthStd.total}->${sephMalkuth?.number}, ShalomGadol=${memGadol.total}`,
    },
    {
      name: 'Legacy W=A wraparound bug is preserved & explicitly flagged while English Extended has 26 unique values',
      passed:
        wrapDiff.hasWraparoundDefect &&
        waxWrap.total === 4 &&
        scoreLegacyHebrewWraparound('AAB').total === 4 &&
        aweWrap.total === 7 &&
        ENGLISH_EXT_TABLE.W.value === 500 &&
        new Set(Object.values(ENGLISH_EXT_TABLE).map((v) => v.value)).size === 26,
      expected: '26 distinct English Extended values; WAX_legacy=AAB_legacy=4 vs W_ext=500',
      actual: `W_ext=${ENGLISH_EXT_TABLE.W.value}, WAX_legacy=${waxWrap.total}, AWE_legacy=${aweWrap.total}`,
    },
    {
      name: '37-word live-computed Canon, 10 Sephirot / 22 Paths & explicit Tradition Switcher integrity',
      passed:
        canon.length === 37 &&
        SEPHIROT.length === 10 &&
        TREE_PATHS.length === 22 &&
        gdAttr.trumpLabel === 'The Emperor' &&
        thelemicAttr.trumpLabel.includes('The Star'),
      expected: '37 canon, 10 Sephirot, 22 Paths, Golden Dawn vs Thelemic explicit',
      actual: `canon=${canon.length}, seph=${SEPHIROT.length}, paths=${TREE_PATHS.length}`,
    },
    {
      name: 'Deterministic Daily Challenge is always reachable & Astronomical Ephemeris computes offline',
      passed:
        daily.targetNumber > 0 &&
        hitEval.hit &&
        ephemeris.lunarIlluminationPct >= 0 &&
        ephemeris.lunarIlluminationPct <= 100,
      expected: 'Daily hit=true and valid lunar illumination',
      actual: `target=${daily.targetNumber}, hit=${hitEval.hit}, moon=${ephemeris.lunarIlluminationPct}%`,
    },
  ];

  return finalizeCase(
    'F14',
    'falsifier',
    'Falsifier F14: Hermes Living Tree Math, Tradition Isolation & Daily Game',
    'Proves 27-letter Greek isopsephy, Hebrew Mispar Hechrechi/Gadol, W=A bug isolation, 37-word canon, and reachable daily target.',
    start,
    assertions
  );
}

function runIntegrationHermesSanitizationAndPrivacy(): VerificationCaseResult {
  const start = Date.now();
  const bidiPoison = 'Ἰη\u202Eσοῦ\u0000ς';
  const sanitized = sanitizeHermesInput(bidiPoison);
  const scoredPoison = scoreGreekIsopsephy(bidiPoison);
  const scoredClean = scoreGreekIsopsephy('Ἰησοῦς');
  const oversize = sanitizeHermesInput('α'.repeat(3500));
  const legacyCard = renderLegacySummaryCardText('WAX');

  const assertions: AssertionCheck[] = [
    {
      name: 'Strips Trojan Unicode Bidi overrides (U+202E) & C0 nulls without distorting cipher value',
      passed:
        sanitized.strippedControlOrBidi === 2 &&
        scoredPoison.total === 888 &&
        scoredPoison.total === scoredClean.total,
      expected: 'stripped=2, total=888 matching clean input',
      actual: `stripped=${sanitized.strippedControlOrBidi}, total=${scoredPoison.total}`,
    },
    {
      name: 'Enforces 2,400-character DoS cap cleanly with explicit truncation signal',
      passed: oversize.maxCharsExceeded && oversize.cleaned.length === 2400,
      expected: 'maxCharsExceeded=true, len=2400',
      actual: `exceeded=${oversize.maxCharsExceeded}, len=${oversize.cleaned.length}`,
    },
    {
      name: 'Legacy /summary compatibility export includes explicitly labeled W=A wraparound row',
      passed:
        legacyCard.includes('Hebrew (W=A wrap)') &&
        legacyCard.includes('Legacy Compat') &&
        legacyCard.includes('raw 4 -> root 4'),
      expected: 'Explicit W=A wraparound row & raw 4 -> root 4',
      actual: legacyCard.slice(0, 120),
    },
  ];

  return finalizeCase(
    'INT-05',
    'integration',
    'Hermes Bidi/Control Hardening, DoS Bound & Legacy Card Parity',
    'Sanitization strips bidi overrides and nulls deterministically while bounding CPU and preserving /summary compatibility.',
    start,
    assertions
  );
}

function runIntegrationDailyGameFullYearAndCanon(): VerificationCaseResult {
  const start = Date.now();
  const canon = computeCanonReadings();
  const baseMs = Date.UTC(2026, 0, 1);
  let allReachable = true;
  let firstUnreachable = '';

  for (let i = 0; i < 366; i++) {
    const dStr = new Date(baseMs + i * 86_400_000).toISOString().slice(0, 10);
    const ch = getDailyChallengeForDate(dStr);
    const anchor = canon.find((c) => c.reading.total === ch.targetNumber);
    if (!anchor || !evaluateDailyChallengeGuess(anchor.word, dStr).hit) {
      allReachable = false;
      firstUnreachable = `${dStr}:${ch.targetNumber}`;
      break;
    }
  }

  const eq93 = findCanonEquivalences(93).map((e) => e.word);
  const eq13 = findCanonEquivalences(13).map((e) => e.word);
  const eq358 = findCanonEquivalences(358).map((e) => e.word);
  const graPath15 = resolvePathPresentation(TREE_PATHS[4], 'gra_ari');

  const assertions: AssertionCheck[] = [
    {
      name: 'All 366 consecutive UTC dates draw a deterministic reachable target hit by canon word',
      passed: allReachable,
      expected: '366/366 reachable UTC daily targets',
      actual: allReachable ? '366/366 reachable' : `failed at ${firstUnreachable}`,
    },
    {
      name: 'Classical equivalence clusters emerge directly from tables (93, 13, 358)',
      passed:
        eq93.includes('θέλημα') &&
        eq93.includes('ἀγάπη') &&
        eq13.includes('אחד') &&
        eq13.includes('אהבה') &&
        eq358.includes('משיח') &&
        eq358.includes('נחש'),
      expected: '93={θέλημα,ἀγάπη}, 13={אחד,אהבה}, 358={משיח,נחש}',
      actual: `93=${eq93.length}, 13=${eq13.length}, 358=${eq358.length}`,
    },
    {
      name: 'Gra / Ari Lurianic attribution avoids modern Golden Dawn Tarot labels',
      passed: graPath15.trumpLabel.includes('Non-Tarot') && graPath15.note.includes('Sight'),
      expected: 'Non-Tarot Sefer Yetzirah attribution',
      actual: graPath15.trumpLabel,
    },
  ];

  return finalizeCase(
    'INT-06',
    'integration',
    '366-Day Game Reachability, Concordance & Tradition Isolation',
    'Full Gregorian year daily target sweep confirms 100% win reachability and zero conflation across Kabbalistic/Hermetic traditions.',
    start,
    assertions
  );
}

function runFalsifierF15WorldCoordinatePrivacyAndResonancePurity(): VerificationCaseResult {
  const start = Date.now();
  const invalidLat = validateCoordinates(95.2, 0);
  const invalidNan = validateCoordinates(Number.NaN, 10);
  const coarsePlace = resolveSanctuaryPlace({ lat: 51.5074192, lon: -0.1277583 });
  const ephem = computeAstronomicalEphemeris(new Date('2026-11-16T02:00:00Z'), 51.51, -0.13);

  const rainInterp = deriveInterpretedLayer(
    {
      status: 'LIVE',
      circuitState: 'CLOSED',
      consecutiveFailures: 0,
      dataKind: 'interpolated_grid_current',
      sourceName: 'Open-Meteo Current Grid Feed',
      sourceUrl: 'https://api.open-meteo.com/',
      license: 'CC BY 4.0',
      place: coarsePlace,
      observedAt: '2026-11-16T02:00',
      fetchedAt: '2026-11-16T02:00:05Z',
      freshnessSec: 0,
      ttlSec: 300,
      isStale: false,
      temperatureC: 9.2,
      precipitationMm: 2.4,
      windSpeedKmh: 12,
      cloudCoverPct: 88,
      weatherCode: 61,
      weatherSummary: 'Rain / drizzle',
      isDay: false,
      errorReason: null,
    },
    ephem
  );

  const assertions: AssertionCheck[] = [
    {
      name: 'Rejects out-of-range latitude (95.2) and NaN coordinates before upstream fetch',
      passed: !invalidLat.ok && !invalidNan.ok,
      expected: 'ok=false for 95.2 and NaN',
      actual: `lat95=${invalidLat.ok}, nan=${invalidNan.ok}`,
    },
    {
      name: 'Custom visitor coordinates are quantized to coarse 2-decimal precision (privacy)',
      passed: coarsePlace.latitudeDeg === 51.51 && coarsePlace.longitudeDeg === -0.13 && MAX_WORLD_CACHE_ENTRIES === 64,
      expected: '51.51, -0.13; LRU cap=64',
      actual: `${coarsePlace.latitudeDeg}, ${coarsePlace.longitudeDeg}; cap=${MAX_WORLD_CACHE_ENTRIES}`,
    },
    {
      name: 'Rain observation maps to Path 23 (Mem / Water) with explicit non-causal disclosure',
      passed:
        rainInterp.atmosphereMode === 'RAIN_WATER' &&
        rainInterp.dominantPathNumber === 23 &&
        rainInterp.nonCausalNotice.toLowerCase().includes('zero causal'),
      expected: 'RAIN_WATER / Path 23 + nonCausalNotice',
      actual: `${rainInterp.atmosphereMode} Path ${rainInterp.dominantPathNumber}`,
    },
  ];

  return finalizeCase(
    'F15',
    'falsifier',
    'Falsifier F15: World Connector Coordinate Guard, Privacy Rounding & Symbolic Purity',
    'Prevents SSRF/DoS coordinate fuzzing, truncates GPS precision, and enforces non-causal Layer 3 disclosures.',
    start,
    assertions
  );
}

export interface HermesChaosReport {
  runAt: string;
  iterations: number;
  succeeded: number;
  exceptionsThrown: number;
  sumInvariantFailures: number;
  hashDriftCount: number;
  p50Us: number;
  p95Us: number;
  p99Us: number;
  passed: boolean;
}

export function runHermesChaosStress(iterations = 1000): HermesChaosReport {
  const fuzzCorpus = [
    'Ἰησοῦς',
    'χξϛ',
    'θέλημα',
    'ἀγάπη',
    'מלכות',
    'שלום',
    'אחד',
    'WAX',
    'AAB',
    '',
    '   ',
    '!!! 123 🔮',
    'Ἰη\u202Eσοῦ\u0000ς',
    'x'.repeat(3000),
    'Λόγος '.normalize('NFD') + 'אהבה',
  ];

  const latenciesUs: number[] = [];
  let succeeded = 0;
  let exceptionsThrown = 0;
  let sumInvariantFailures = 0;
  let hashDriftCount = 0;

  for (let i = 0; i < iterations; i++) {
    const sample = fuzzCorpus[i % fuzzCorpus.length];
    const t0 = performance.now();
    try {
      const r1 = readingsForText(sample, { includeLegacyLatin: true });
      const r2 = readingsForText(sample, { includeLegacyLatin: true });
      for (let j = 0; j < r1.length; j++) {
        const sumCheck = r1[j].breakdown.reduce((acc, b) => acc + b.value, 0);
        if (sumCheck !== r1[j].total) sumInvariantFailures++;
        if (r1[j].reproducibilityHash !== r2[j].reproducibilityHash) hashDriftCount++;
      }
      succeeded++;
    } catch {
      exceptionsThrown++;
    }
    const elapsedUs = Math.max(1, Math.round((performance.now() - t0) * 1000));
    latenciesUs.push(elapsedUs);
  }

  latenciesUs.sort((a, b) => a - b);
  const p50Us = percentile(latenciesUs, 50);
  const p95Us = percentile(latenciesUs, 95);
  const p99Us = percentile(latenciesUs, 99);

  return {
    runAt: new Date().toISOString(),
    iterations,
    succeeded,
    exceptionsThrown,
    sumInvariantFailures,
    hashDriftCount,
    p50Us,
    p95Us,
    p99Us,
    passed:
      exceptionsThrown === 0 &&
      sumInvariantFailures === 0 &&
      hashDriftCount === 0 &&
      p95Us < 5000,
  };
}

function runFalsifierF16HermesFuzzChaosAndDeterminism(): VerificationCaseResult {
  const start = Date.now();
  const stress = runHermesChaosStress(1000);

  const assertions: AssertionCheck[] = [
    {
      name: '1,000-op multilingual & hostile-Unicode fuzz stress finishes with 0 exceptions and 0 sum drift',
      passed:
        stress.exceptionsThrown === 0 &&
        stress.sumInvariantFailures === 0 &&
        stress.hashDriftCount === 0 &&
        stress.succeeded === 1000,
      expected: '1000 succeeded, 0 exceptions, 0 drift',
      actual: `${stress.succeeded} ok, err=${stress.exceptionsThrown}, drift=${stress.hashDriftCount}`,
    },
    {
      name: 'Math engine satisfies SLO budget (p95 < 5,000 us even on 3,000-char DoS inputs)',
      passed: stress.p95Us < 5000,
      expected: 'p95 < 5000 us',
      actual: `p50=${stress.p50Us}us, p95=${stress.p95Us}us, p99=${stress.p99Us}us`,
    },
  ];

  return finalizeCase(
    'F16',
    'falsifier',
    'Falsifier F16: Hermes 1,000-Op Fuzz Chaos & Sub-5ms p95 SLO',
    'Blasts cipher, Bidi/null sanitization, and oversize truncation across 1,000 deterministic & hostile iterations.',
    start,
    assertions
  );
}

function runFalsifierF17CodexCrescendoMatrixAndNonCollusion(): VerificationCaseResult {
  const start = Date.now();
  const matrix = build231GatesMatrix();
  const blockedWitnessMalkuth = evaluateGatePair(14, 32);

  const overheat = computePillarEquilibrium(2.2, 0.8);
  const deadlock = computePillarEquilibrium(0.6, 2.2);
  const balanced = computePillarEquilibrium(1.0, 1.0);

  const colluding = verifyThreeKeyNonCollusion({
    keyBinah: 'key_shared',
    keyChesed: 'key_shared',
    keyMalkuth: 'key_shared',
    merkleRoot: 'root_abc',
  });
  const validSeal = verifyThreeKeyNonCollusion({
    keyBinah: 'key_binah_a',
    keyChesed: 'key_chesed_b',
    keyMalkuth: 'key_malkuth_c',
    merkleRoot: 'root_abc',
  });

  const replayFracture = evaluateChronoReplay({
    progress: 0.95,
    current: 'mezla',
    injectedQliphah: 'gamaliel',
    threeKeyValid: true,
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'Sefer Yetzirah 231-Gate Matrix enumerates all C(22,2)=231 pairs and blocks (14, 32) across Qesheth',
      passed: matrix.totalGates === 231 && blockedWitnessMalkuth.compatible === false,
      expected: '231 gates, (14, 32) blocked',
      actual: `${matrix.totalGates} gates, compatible(14,32)=${blockedWitnessMalkuth.compatible}`,
    },
    {
      name: 'Pillar Equilibrium Omega_Pillar(t) flags both Gha’agsheblah overheat and Golachab deadlock',
      passed:
        overheat.regime === 'GHA_AGSHEBLAH_OVERHEAT' &&
        deadlock.regime === 'GOLACHAB_DEADLOCK' &&
        balanced.regime === 'BALANCED',
      expected: 'OVERHEAT / DEADLOCK / BALANCED',
      actual: `${overheat.regime} / ${deadlock.regime} / ${balanced.regime}`,
    },
    {
      name: 'Three-Key Non-Collusion Theorem blocks Nehemoth self-signing and unlocks Malkuth only with 3 distinct keys',
      passed:
        colluding.malkuthIlluminated === false &&
        validSeal.malkuthIlluminated === true &&
        validSeal.distinctKeyCount === 3,
      expected: 'colluding=false, valid=true (3 distinct)',
      actual: `colluding=${colluding.malkuthIlluminated}, valid=${validSeal.malkuthIlluminated} (${validSeal.distinctKeyCount})`,
    },
    {
      name: 'Three Veils (Abyss, Paroketh, Qesheth), 11 Codex Spheres (10+Da’ath), and 10 Qliphoth hold Qliphothic fracture isolation',
      passed:
        THREE_VEILS.length === 3 &&
        CODEX_SPHERES.length === 11 &&
        QLIPHOTH_REGISTRY.length === 10 &&
        replayFracture.fracturedPathNumber === 30 &&
        replayFracture.malkuthSealed === false,
      expected: '3 veils, 11 spheres, 10 Qliphoth, Malkuth dark under Gamaliel',
      actual: `veils=${THREE_VEILS.length}, spheres=${CODEX_SPHERES.length}, fracturePath=${replayFracture.fracturedPathNumber}, sealed=${replayFracture.malkuthSealed}`,
    },
    {
      name: 'Crescendo 3-Way Union resolves /crescendo -> hermes and holds fail-closed NO-GO until external GL-04..GL-06 receipts pass',
      passed:
        resolveDeclaredAppRoute('/crescendo', '') === 'hermes' &&
        resolveDeclaredAppRoute('/', '?tab=crescendo') === 'hermes' &&
        evaluateCrescendoGoLiveSignOff().overallDecision === 'NO-GO' &&
        evaluateCrescendoGoLiveSignOff({
          fleetRemoteAccepted: true,
          verifiedProductionRevision: 'rev-prod-8b6d23f',
          externalRunnerBundleHttp200: true,
          externalEndUserRouteBrowserVerified: true,
        }).overallDecision === 'GO',
      expected: '/crescendo->hermes, default=NO-GO, full external witness=GO',
      actual: `route=${resolveDeclaredAppRoute('/crescendo', '')}, default=${evaluateCrescendoGoLiveSignOff().overallDecision}`,
    },
  ];

  return finalizeCase(
    'F17',
    'falsifier',
    'Falsifier F17: Codex Crescendo 231-Gate Matrix, 3-Way Union Sign-Off & Three-Key Seal',
    'Verifies 231-Gate commutativity, Three Veils isolation, /crescendo route, 3-Way Union NO-GO airlock, and Nehemoth non-collusion.',
    start,
    assertions
  );
}

function runFalsifierF18I8088PanspermiaAndGenTtt(): VerificationCaseResult {
  const start = Date.now();
  const survived3 = runI8088PanspermiaSimulation({
    deadTentacles: [0, 2, 3, 4, 6],
    authoritativeFenceToken: 46,
    walReceipts: 2382,
  });
  const collapsed2 = runI8088PanspermiaSimulation({
    deadTentacles: [0, 1, 2, 3, 4, 5],
    authoritativeFenceToken: 46,
    walReceipts: 2382,
  });

  // Verify GENVAULT1 Encrypt-then-MAC tamper rejection and lossless PNG wrap/unwrap parity
  const secretMsg = Buffer.from('genesis-i8088-soma-parity-probe', 'utf8');
  const sealed = encryptSomaPayload(secretMsg, 'test-passphrase', 5000);
  const shards = rsEncodeK3N8(sealed);
  const pngWrapped = wrapShardInLosslessPng(shards[7]);
  const pngUnwrapped = unwrapShardFromLosslessPng(pngWrapped);
  const rsRecovered = rsDecodeAny3(
    new Map([
      [1, shards[1]],
      [4, shards[4]],
      [7, pngUnwrapped],
    ])
  );
  const decryptedOk = decryptSomaPayload(rsRecovered, 'test-passphrase', 5000).equals(secretMsg);

  const tampered = Buffer.from(sealed);
  tampered[tampered.byteLength - 1] ^= 0xff;
  let tamperRejected = false;
  try {
    decryptSomaPayload(tampered, 'test-passphrase', 5000);
  } catch (err) {
    tamperRejected = err instanceof Error && err.message.includes('VAULT_MAC_VERIFICATION_FAILED');
  }

  const ttt = buildGenTttSnapshot();

  const assertions: AssertionCheck[] = [
    {
      name: 'I-8088 GENESIS_SPORE.dna stays <= 4,096 B, carries valid Ed25519 signature, and emits DNS TXT records',
      passed:
        survived3.sporeWithinLimit &&
        survived3.sporeBytes <= SPORE_MAX_BYTES &&
        survived3.sporeSignatureVerified &&
        survived3.dnsTxtRecords.length >= 3,
      expected: '<= 4096 B, Ed25519 verified, >= 3 DNS records',
      actual: `${survived3.sporeBytes} B, sig=${survived3.sporeSignatureVerified}, dns=${survived3.dnsTxtRecords.length}`,
    },
    {
      name: 'GF(2^8) RS(3,8) reconstructs 100% bit-exact estate state after 5 tentacles are destroyed',
      passed:
        survived3.survivingCount === 3 &&
        survived3.destroyedCount === 5 &&
        survived3.resurrectionOk &&
        survived3.reconstructedBitExact,
      expected: '3 surviving, 5 destroyed, bitExact=true',
      actual: `${survived3.survivingCount} surviving, bitExact=${survived3.reconstructedBitExact}`,
    },
    {
      name: 'Sub-quorum collapse (< 3 tentacles surviving) fails closed without hallucinated recovery',
      passed:
        collapsed2.survivingCount === 2 &&
        !collapsed2.resurrectionOk &&
        collapsed2.resurrectionVerdict.includes('QUORUM_INSUFFICIENT_FAIL_CLOSED'),
      expected: 'ok=false, QUORUM_INSUFFICIENT_FAIL_CLOSED',
      actual: `ok=${collapsed2.resurrectionOk}, verdict=${collapsed2.resurrectionVerdict}`,
    },
    {
      name: 'Lossless PNG stego carrier + PBKDF2 GENVAULT1 MAC rejects 1-bit ciphertext tamper fail-closed',
      passed: decryptedOk && tamperRejected,
      expected: 'PNG roundtrip=true, tamperRejected=true',
      actual: `roundtrip=${decryptedOk}, tamperRejected=${tamperRejected}`,
    },
    {
      name: 'GEN-TTT-001 specification preserves BLOCKED_DISPATCH #8185 honesty and guards all 15 failure classes',
      passed:
        ttt.dispatchState === 'BLOCKED_DISPATCH' &&
        ttt.trackingIssue === '#8185' &&
        ttt.closedInvalidPr === '#8186' &&
        ttt.arms.length === 6 &&
        ttt.failureClasses.length === 15 &&
        ttt.workPackages.length === 8 &&
        ttt.all15FalsifiersGuarded,
      expected: 'BLOCKED_DISPATCH, #8185, 6 arms, 15/15 FCs guarded, 8 WPs',
      actual: `${ttt.dispatchState}, ${ttt.trackingIssue}, arms=${ttt.arms.length}, fc=${ttt.failureClasses.length}, wp=${ttt.workPackages.length}`,
    },
  ];

  return finalizeCase(
    'F18',
    'falsifier',
    'Falsifier F18: I-8088 Cephalopod RS(3,8) Extinction Recovery & GEN-TTT-001 Spec Lock',
    'Proves 5-tentacle extinction survival via GF(2^8) Vandermonde RS(3,8), GENVAULT1 MAC integrity, sub-quorum fail-closed lock, and GEN-TTT-001 BLOCKED_DISPATCH epistemic honesty.',
    start,
    assertions
  );
}

/**
 * FALSIFIER F19: Verifies Estate Grand Union autonomous Chronos/Tempo beat execution,
 * InterCloud sub-50ms spot reclamation checkpoint failover (0 dropped tasks),
 * Best-of-3 Small/Free Open Ensemble beating single Frontier quality & cost,
 * and complete GWT / AEON / Surface visibility.
 */
function runFalsifierF19GrandUnionChronosInterCloudAndEnsemble(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 100 });
  const dagster = new DagsterOrchestrator();
  const supply = new ModelSupplyRegistry();
  const union = new EstateGrandUnionEngine({ router, dagster, supply, cadenceMs: 5000 });

  const before = union.getSnapshot();
  const afterBeat = union.executeBeat('manual_pulse');
  const preemption = union.simulateSpotPreemption('ic-intercloud-spot-l40s');
  const healed = union.healAllSpotLanes();
  const ensemble = evaluateEnsembleVsFrontier(500);

  const assertions: AssertionCheck[] = [
    {
      name: 'Chronos & Tempo beat advances WAL receipts, forensic packets, and bounded skew',
      passed:
        afterBeat.chronos.beatNumber === before.chronos.beatNumber + 1 &&
        afterBeat.battalionRollup.walReceipts === before.battalionRollup.walReceipts + 1 &&
        afterBeat.chronos.tempoSyncSkewMs < 10,
      expected: `beat=${before.chronos.beatNumber + 1}, wal=${before.battalionRollup.walReceipts + 1}, skew<10ms`,
      actual: `beat=${afterBeat.chronos.beatNumber}, wal=${afterBeat.battalionRollup.walReceipts}, skew=${afterBeat.chronos.tempoSyncSkewMs}ms`,
    },
    {
      name: 'InterCloud spot preemption migrates checkpoint in <50ms with 0 dropped tasks and heals cleanly',
      passed:
        preemption.zeroTasksDropped === true &&
        preemption.failoverMs < 50 &&
        preemption.reclaimedLaneId === 'ic-intercloud-spot-l40s' &&
        healed.interCloudSummary.onlineLanes >= 9,
      expected: 'zeroTasksDropped=true, failoverMs<50, healedOnline>=9',
      actual: `dropped=${!preemption.zeroTasksDropped}, failover=${preemption.failoverMs}ms, online=${healed.interCloudSummary.onlineLanes}`,
    },
    {
      name: 'Best-of-3 Open/Small Ensemble + BEAST gate exceeds single Frontier pass rate at >99% lower cost',
      passed:
        ensemble.exceedsFrontierQuality === true &&
        ensemble.ensembleVerifiedPassPct > ensemble.singleFrontierPassPct &&
        ensemble.costReductionPct >= 99,
      expected: 'ensemblePass > frontierPass (96.9% > 93.4%) & costReduction >= 99%',
      actual: `${ensemble.ensembleVerifiedPassPct}% vs ${ensemble.singleFrontierPassPct}% (-${ensemble.costReductionPct}% cost)`,
    },
    {
      name: 'All 13 GWT/AEON/Audit/Rego/Research/Concierge/Reactivity lanes and 11 Founder/Public/Investor surfaces remain joined-up & honest',
      passed:
        healed.gwtAeonRegistry.length === 13 &&
        healed.surfaces.length === 11 &&
        healed.gwtAeonRegistry.some((g) => g.status === 'BLOCKED_DISPATCH') &&
        healed.gwtAeonRegistry.some((g) => g.status === 'VERIFIED_CANDIDATE'),
      expected: '13 GWT lanes, 11 surfaces, BLOCKED_DISPATCH + VERIFIED_CANDIDATE preserved',
      actual: `gwt=${healed.gwtAeonRegistry.length}, surfaces=${healed.surfaces.length}`,
    },
  ];

  return finalizeCase(
    'F19',
    'falsifier',
    'Falsifier F19: Grand Union Chronos Beat, InterCloud Preemption & Open Ensemble > Frontier',
    'Autonomous Chronos beats must advance real WAL/OTel state, InterCloud spot reclamation must fail over under 50ms with 0 dropped tasks, and Best-of-3 open ensembles must beat single frontier quality and cost.',
    start,
    assertions
  );
}

/**
 * FALSIFIER F20: Verifies the 16 Nov 2026 First-Use Machine-Agent Governance Audit
 * (audit/first-use-machine-agent-20261116 @ ff8543bd vs IDP main d03f5d59):
 *  - 13-pin governance disposition matrix (Retain Pi ceremony, Preserve multi-agent history, Do not revive disk guardian)
 *  - 21/21 adversarial tests (12 Read-Only Ceremony Observer + 9 AGENTS.md No-Growth Ratchet)
 *  - Reproduces fail-open `$lines` shell bug and blocks unsafe installer shortcuts (--no-verify)
 *  - Strictly keeps LIVE CEREMONY EFFECT = UNKNOWN and candidate unmerged/unclaimed as estate-wide yield.
 */
function runFalsifierF20FirstUseMachineAgentGovernanceAudit(): VerificationCaseResult {
  const start = Date.now();
  const audit = buildFirstUseAuditSnapshot();
  const legacyBug = reproduceLegacyEscapedLinesBug(348);
  const literalBlocked = evaluateAgentsMdRatchet({
    currentLinesRaw: '$lines',
    baselineLinesRaw: 348,
  });
  const unsafeInstaller = auditInstallerShortcuts(
    'git commit --no-verify && rewrite_multi_agent_history && disable_governance_extensions'
  );
  const observerOut = observeCeremonyLedger([
    JSON.stringify({
      eventId: 'f20-1',
      goalId: 'G-F20',
      step: 'complete_goal',
      note: 'Attempted premature completion with token sk-secret999999999999',
    }),
  ]);

  const pin8 = audit.pins.find((p) => p.pin === 8);
  const pin10 = audit.pins.find((p) => p.pin === 10);

  const assertions: AssertionCheck[] = [
    {
      name: 'All 21/21 adversarial tests pass (12 Ceremony Observer + 9 AGENTS.md No-Growth Ratchet)',
      passed:
        audit.failureClassesReviewed === 13 &&
        audit.adversarialTestsTotal === 21 &&
        audit.adversarialTestsPassed === 21 &&
        audit.observerTestsPassed === 12 &&
        audit.ratchetTestsPassed === 9,
      expected: '13 pins, 21/21 adversarial (12 observer + 9 ratchet)',
      actual: `pins=${audit.failureClassesReviewed}, passed=${audit.adversarialTestsPassed}/${audit.adversarialTestsTotal}`,
    },
    {
      name: 'Legacy fail-open `$lines` bug reproduced AND blocked fail-closed by repaired no-growth ratchet',
      passed:
        legacyBug.failedOpen === true &&
        legacyBug.workflowExitCode === 0 &&
        !literalBlocked.passed &&
        literalBlocked.exitCode === 1 &&
        literalBlocked.mode === 'FAIL_CLOSED_INVALID_INPUT',
      expected: 'legacyExit=0 (fail-open), repairedExit=1 (FAIL_CLOSED_INVALID_INPUT)',
      actual: `legacyExit=${legacyBug.workflowExitCode}, repairedExit=${literalBlocked.exitCode} (${literalBlocked.mode})`,
    },
    {
      name: 'Rejects unsafe installer shortcuts (--no-verify, history rewrite, governance disable) & retains Pi ceremony',
      passed:
        !unsafeInstaller.allowed &&
        unsafeInstaller.blockedShortcuts.length === 3 &&
        pin8?.disposition === 'Retain' &&
        pin10?.disposition === 'Do not revive',
      expected: '3 shortcuts blocked, Pin 8=Retain, Pin 10=Do not revive',
      actual: `blocked=${unsafeInstaller.blockedShortcuts.length}, P8=${pin8?.disposition}, P10=${pin10?.disposition}`,
    },
    {
      name: 'Observer catches out-of-order ceremony, redacts secrets, and holds LIVE CEREMONY EFFECT = UNKNOWN',
      passed:
        observerOut.outOfOrderViolations.length >= 2 &&
        observerOut.redactedSecretsCount === 1 &&
        audit.liveCeremonyEffect === 'UNKNOWN' &&
        audit.mergeOrDeploymentClaimed === false &&
        audit.candidatePosture === 'VERIFIED_CANDIDATE_NOT_CERTIFIED_ENFORCEMENT',
      expected: 'violations>=2, redactions=1, liveEffect=UNKNOWN, mergeClaimed=false',
      actual: `violations=${observerOut.outOfOrderViolations.length}, redactions=${observerOut.redactedSecretsCount}, effect=${audit.liveCeremonyEffect}`,
    },
  ];

  return finalizeCase(
    'F20',
    'falsifier',
    'Falsifier F20: First-Use Machine-Agent Audit (13 Pins, 21/21 Tests, AGENTS Ratchet & Non-Yield Honesty)',
    'Proves producer-first machine-agent boundary: retains Pi ceremony, blocks unsafe installer shortcuts, repairs fail-open AGENTS.md gate via no-growth ratchet, and keeps unverified operational yield UNKNOWN.',
    start,
    assertions
  );
}

/**
 * FALSIFIER F21: Verifies Hermes · OTTO_NUMEN VIP CEO Telegram Concierge:
 *  - Shards events across 5 dedicated Forum Topics + 1 Zero-Send Suppressed Heartbeat Sink
 *  - Compresses a 50-event storm with >=95% audible interruption reduction (strictly P0 VIP pings)
 *  - Coalesces flapping duplicate alerts via EDIT_IN_PLACE (editMessageText)
 *  - Escapes adversarial HTML (<, >, &) and all 18 MarkdownV2 characters cleanly within <=900 chars & <=64B callbacks
 *  - Records SHA-256 signed CEO decision receipts and enforces 4h fingerprint mute rules.
 */
function runFalsifierF21OttoNumenVipTelegramTriageAndFormatting(): VerificationCaseResult {
  const start = Date.now();
  const engine = new OttoNumenConciergeEngine({ seedInitialEstateState: false });
  const storm = engine.simulateEstateStorm(50);

  const adversarialRaw = 'Check <3 quorum & oot_numun *bold* _italic_ [x](y) `code` #1!';
  const htmlEsc = escapeTelegramHtml(adversarialRaw);
  const mdEsc = escapeTelegramMarkdownV2(adversarialRaw);
  const longCb = buildSafeCallbackData(
    'approve_action_very_long',
    'extremely_long_message_identifier_exceeding_sixty_four_bytes_1234567890'
  );

  const p0Card = storm.snapshot.messages.find((m) => m.topic === 'VIP_CEO_DECISIONS');
  const cbOut = p0Card
    ? engine.executeInlineCallback({ messageId: p0Card.messageId, action: 'mute4h' })
    : null;
  const mutedRepeat = engine.ingestEvent({
    kind: 'p0_budget_ceiling',
    sourceSubsystem: 'PennyD Treasury Guard',
    headline: p0Card?.headline ?? 'Muted test',
    metrics: { Cap: '$400' },
    autonomousAction: 'Should be muted by 4h rule',
    dedupeKey: p0Card ? `vip:cap-raise-${p0Card.headline.split('[').pop()?.replace(']', '')}` : 'mute-test',
  });

  const allWithinLimits = storm.snapshot.messages.every(
    (m) =>
      m.withinSingleScreenBudget &&
      m.withinTelegramHardLimit &&
      m.allCallbacksWithin64Bytes &&
      m.htmlWirePayload.length <= CEO_SINGLE_SCREEN_CHAR_BUDGET
  );

  const assertions: AssertionCheck[] = [
    {
      name: '50-event storm intercepts 100% of routine heartbeats & achieves >=95% audible ping reduction',
      passed:
        storm.suppressedChatter >= 30 &&
        storm.audiblePingsDuringStorm === 1 &&
        storm.snapshot.telemetry.audibleInterruptionReductionPct >= 95,
      expected: 'suppressedChatter>=30, audiblePings=1, reduction>=95%',
      actual: `suppressed=${storm.suppressedChatter}, pings=${storm.audiblePingsDuringStorm}, reduction=${storm.snapshot.telemetry.audibleInterruptionReductionPct}%`,
    },
    {
      name: 'Flapping lane/spot bursts coalesce in-place via EDIT_IN_PLACE instead of flooding channel',
      passed:
        storm.coalescedEdits >= 10 &&
        storm.snapshot.messages.some(
          (m) => m.deliveryMethod === 'EDIT_IN_PLACE' && m.coalescedCount > 1
        ),
      expected: 'coalescedEdits>=10 with EDIT_IN_PLACE cards',
      actual: `coalescedEdits=${storm.coalescedEdits}`,
    },
    {
      name: 'HTML & MarkdownV2 escapers neutralize adversarial syntax; cards stay <=900 chars & callbacks <=64B',
      passed:
        !htmlEsc.includes('<3') &&
        htmlEsc.includes('&lt;3') &&
        htmlEsc.includes('&amp;') &&
        mdEsc.includes('\\_numun') &&
        mdEsc.includes('\\*bold\\*') &&
        longCb.byteLength <= TELEGRAM_MAX_CALLBACK_BYTES &&
        allWithinLimits,
      expected: 'HTML/MarkdownV2 escaped, cards <=900 chars, callbacks <=64B',
      actual: `cbBytes=${longCb.byteLength}, allWithinLimits=${allWithinLimits}`,
    },
    {
      name: '1-tap CEO inline callback records SHA-256 receipt and enforces 4h fingerprint mute',
      passed:
        Boolean(cbOut?.ok) &&
        Boolean(cbOut?.receipt?.decisionSha256.length === 64) &&
        mutedRepeat.outcome === 'MUTED_BY_CEO_RULE',
      expected: 'receipt SHA-256 recorded & repeat event MUTED_BY_CEO_RULE',
      actual: `ok=${cbOut?.ok}, repeatOutcome=${mutedRepeat.outcome}`,
    },
  ];

  return finalizeCase(
    'F21',
    'falsifier',
    'Falsifier F21: Hermes · OTTO_NUMEN VIP CEO Telegram Topic Sharding, Coalescing & Wire Safety',
    'Replaces single-channel oot_numun spam with 5 Forum Topics + Zero-Send Heartbeat Sink, >=95% audible interruption reduction, in-place editMessageText coalescing, and strict HTML/MarkdownV2/64B wire bounds.',
    start,
    assertions
  );
}

function runFalsifierF22Prospector2100CausalResearchAndMumchimp(): VerificationCaseResult {
  const start = Date.now();
  const engine = new Prospector2100Engine();

  // Inject an adversarial benchmark-leaked hype rumor trap
  const trapFinding = engine.runAutonomousCycle({
    chronosBeat: 20,
    customHypothesis: {
      title: 'Unverified Rumor: 100% Guaranteed Zero-Shot Benchmark Leak',
      claim: 'Viral social feed claims 100% guaranteed pass without held-out split.',
      domain: 'ML_FRONTIER_ARCHITECTURES',
      isConfounderTrap: true,
    },
  });

  // Run a clean empirical cycle
  const validFinding = engine.runAutonomousCycle({
    chronosBeat: 22,
    customHypothesis: {
      title: 'Verified Multi-Model AST Gate Reduces Enterprise Defect Escape',
      claim: 'Primary benchmark across 500 enterprise PRs shows +3.5pp verified pass lift.',
      domain: 'COMMERCIAL_ENTERPRISE_SIGNALS',
      isConfounderTrap: false,
    },
  });

  const snap = engine.getSnapshot();
  const cmp = compareLegacyVsProspector2100();
  const trapLeakedToMumchimp = snap.mumchimpFeed.some(
    (a) => a.sourceFindingId === trapFinding.id
  );

  const assertions: AssertionCheck[] = [
    {
      name: 'Prospector-2100 achieves >=99% cost reduction vs legacy naive Frontier scraper (>=200x efficiency)',
      passed: snap.savingsPct >= 99 && cmp.costMultiplierImprovement >= 200,
      expected: 'savingsPct>=99%, multiplier>=200x',
      actual: `savings=${snap.savingsPct}%, multiplier=${cmp.costMultiplierImprovement}x`,
    },
    {
      name: 'MagenticBrain adversarial critic quarantines confounder/hype traps with 0 leakage to Mumchimp',
      passed:
        trapFinding.adversarialCritiqueVerdict === 'QUARANTINED_CONFOUNDER' &&
        !trapFinding.publishedToMumchimp &&
        !trapLeakedToMumchimp,
      expected: 'QUARANTINED_CONFOUNDER & publishedToMumchimp=false',
      actual: `verdict=${trapFinding.adversarialCritiqueVerdict}, leaked=${trapLeakedToMumchimp}`,
    },
    {
      name: 'Verified causal findings carry 64-hex SHA-256 digests and syndicate directly into Mumchimp',
      passed:
        validFinding.adversarialCritiqueVerdict === 'VERIFIED_CAUSAL' &&
        validFinding.publishedToMumchimp &&
        validFinding.findingSha256.length === 64 &&
        snap.mumchimpFeed.some((a) => a.sourceFindingId === validFinding.id),
      expected: 'VERIFIED_CAUSAL + 64-char SHA-256 + present in mumchimpFeed',
      actual: `verdict=${validFinding.adversarialCritiqueVerdict}, feedCount=${snap.mumchimpPublishedCount}`,
    },
  ];

  return finalizeCase(
    'F22',
    'falsifier',
    'Falsifier F22: Prospector-2100 Autonomous Causal Research & Mumchimp Syndication Gate',
    'Proves Sovereign/Spot research achieves >=99% cost reduction over naive Frontier scraping, quarantines confounder traps before Mumchimp, and syndicates SHA-256 verified intelligence.',
    start,
    assertions
  );
}

function runFalsifierF23FounderRegoConstitutionAndChronosMerkle(): VerificationCaseResult {
  const start = Date.now();
  const founder = new FounderConfigEngine();

  // 1. Attempt unsafe constitutional override (enable --no-verify, drop causal gate to 60%, enable client polling)
  const denied = founder.proposeAndApplyPatch({
    allowGitNoVerifyShortcuts: true,
    prospectorMinCausalConfidencePct: 60,
    enforceZeroClientPollingI8090: false,
  });

  // 2. Valid Founder configuration update
  const accepted = founder.proposeAndApplyPatch({
    sovereignFreeFloorPct: 86,
    prospectorMinCausalConfidencePct: 90,
  });

  // 3. Chronos 8-leaf Merkle synchronicity stamp
  const stamp = computeSynchronicityMerkleStamp({
    chronosBeat: 16,
    founderConfig: accepted.config,
    regoBundleSha256: accepted.regoReport.bundleSha256,
    walLatestSequence: 2400,
    interCloudOnlineCount: 8,
    interCloudTotalCount: 8,
    prospectorDigestSha256: 'a'.repeat(64),
    mumchimpPublishedCount: 5,
    telegramFocusPolicy: 'VIP_P0_ONLY',
    sporeSurvivingTentacles: 8,
  });

  // 4. R-008 Future-Code Classifier + Investor Economics + Academy Simulator sanity
  const flaggedCode = classifyCodeForRegoGovernance(
    'badPolicy.ts',
    'if (user.role === "admin" && spendUsd <= 10) { return true; }'
  );
  const pureMathCode = classifyCodeForRegoGovernance(
    'gf256.ts',
    'export const xor = (a: number, b: number) => a ^ b;'
  );
  const econ = computeInvestorUnitEconomics({ enterpriseCustomers: 50, sovereignAndSpotSharePct: 88 });
  const acad = simulateAcademyModule({
    moduleId: 'condorcet_ensemble_economics',
    level: 'founder',
    sliderParam: 84,
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'Rego package genesis.constitutional.v1 blocks unsafe Founder overrides fail-closed (HTTP 422)',
      passed:
        !denied.committed &&
        denied.httpStatus === 422 &&
        denied.regoReport.deniedReasons.length >= 3 &&
        denied.config.revision === 1,
      expected: 'committed=false, status=422, revision preserved at 1',
      actual: `committed=${denied.committed}, status=${denied.httpStatus}, rev=${denied.config.revision}`,
    },
    {
      name: 'Valid Founder config mutation signs new SHA-256 revision and folds into 8-leaf Chronos Merkle root',
      passed:
        accepted.committed &&
        accepted.config.revision === 2 &&
        accepted.config.configSha256.length === 64 &&
        stamp.phaseLocked &&
        stamp.driftRadians === 0 &&
        stamp.unjoinedSubsystemsCount === 0 &&
        stamp.harmonicRings.length === 5 &&
        stamp.leaves.length === 8 &&
        stamp.merkleRootSha256.length === 64,
      expected: 'rev=2, phaseLocked=true, 5 harmonic rings, 8 Merkle leaves, 64-hex root',
      actual: `rev=${accepted.config.revision}, phaseLocked=${stamp.phaseLocked}, rootLen=${stamp.merkleRootSha256.length}`,
    },
    {
      name: 'Rule R-008 classifier flags imperative policy branches while permitting pure math & verifying >80% SaaS gross margin',
      passed:
        flaggedCode.verdict === 'MUST_EXPRESS_AS_REGO' &&
        pureMathCode.verdict === 'PURE_COMPUTATION_OK_IN_TS' &&
        econ.grossMarginPct >= 80 &&
        acad.curvePoints.length === 6,
      expected: 'MUST_EXPRESS_AS_REGO + PURE_COMPUTATION_OK_IN_TS + grossMargin>=80%',
      actual: `flagged=${flaggedCode.verdict}, math=${pureMathCode.verdict}, margin=${econ.grossMarginPct}%`,
    },
  ];

  return finalizeCase(
    'F23',
    'falsifier',
    'Falsifier F23: Founder First-Class Config, Rego Constitutional Gate, R-008 Classifier & Chronos Merkle Stamp',
    'Verifies pre-commit Rego policy enforcement, 5-ring Chronos harmonic synchronicity Merkle root, R-008 imperative-policy detector, investor gross margin math, and 4-tier Academy simulations.',
    start,
    assertions
  );
}

function runFalsifierF24UhnwSovereignCharterAndStandoutTransfer(): VerificationCaseResult {
  const start = Date.now();
  const founder = new FounderConfigEngine();
  const concierge = new UhnwSovereignConciergeEngine();

  // 1. Attempt to weaken UHNW VIP SLA (>150ms) or disable epistemic separation -> must fail closed (HTTP 422)
  const deniedCharter = founder.proposeAndApplyPatch({
    enforceUhnwVipCharter: false,
    p0ConciergeLatencyCeilingMs: 500,
    enforceEpistemicSeparation: false,
  });

  // 2. Attempt to market candidate audit branch (ff8543bd, LIVE CEREMONY EFFECT = UNKNOWN) as CERTIFIED_PRODUCTION_YIELD -> blocked (422)
  const blockedInflation = auditEpistemicClaim({
    capabilityName: 'audit/first-use-machine-agent-20261116 (ff8543bd)',
    claimedMarketingTier: 'CERTIFIED_PRODUCTION_YIELD',
    hasPlanLock: true,
    localAdversarialTestsPassed: true,
    signedGreenlaneMerged: false,
    independentLiveOutcomeJoined: false,
  });
  const truthfulCandidate = auditEpistemicClaim({
    capabilityName: 'audit/first-use-machine-agent-20261116 (ff8543bd)',
    claimedMarketingTier: 'ENGINEERING_TEST_VERIFIED',
    hasPlanLock: true,
    localAdversarialTestsPassed: true,
    signedGreenlaneMerged: false,
    independentLiveOutcomeJoined: false,
  });

  // 3. Verify all 7 OTTO & Fleet agents satisfy UHNW SLA <=150ms & execute VIP concierge directive
  const charterSnap = concierge.getSnapshot();
  const receipt = concierge.dispatchDirective({
    presetKey: 'investor_series_brief',
    founderInstruction: 'Prepare signed Investor Meeting diligence brief.',
  });

  // 4. Verify Genesis Standout Academy Track 01 boundary fault & 3-item Unseen Transfer Pilot
  const boundarySim = simulateStandoutAcademyTrack({
    trackId: 'reproducibility_transfer_boundaries',
    level: 'founder',
    sliderParam: 92,
    activeFaultIds: ['missing_key'],
  });
  const incompletePilot = evaluateUnseenTransferPilot({
    trackId: 'reproducibility_transfer_boundaries',
    selectedAnswers: { 'tr-01-missing-key': 1 },
  });
  const perfectPilot = evaluateUnseenTransferPilot({
    trackId: 'reproducibility_transfer_boundaries',
    selectedAnswers: {
      'tr-01-missing-key': 1,
      'tr-01-external-service': 2,
      'tr-01-disconnected-fleet': 3,
    },
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'Rego Rules R-009 & R-010 block weakening UHNW VIP SLA (>150ms) or epistemic separation (HTTP 422)',
      passed:
        !deniedCharter.committed &&
        deniedCharter.httpStatus === 422 &&
        deniedCharter.regoReport.deniedReasons.some((r) => r.includes('R-009')) &&
        deniedCharter.regoReport.deniedReasons.some((r) => r.includes('R-010')),
      expected: 'HTTP 422 with R-009 & R-010 denials',
      actual: `status=${deniedCharter.httpStatus}, reasons=${deniedCharter.regoReport.deniedReasons.length}`,
    },
    {
      name: 'Machine-Agent Epistemic Guard blocks inflating unmerged candidate (ff8543bd) to certified production yield',
      passed:
        !blockedInflation.allowed &&
        blockedInflation.httpStatus === 422 &&
        blockedInflation.earnedEvidenceTier === 'ENGINEERING_ACCEPTANCE' &&
        truthfulCandidate.allowed &&
        truthfulCandidate.httpStatus === 200,
      expected: 'CERTIFIED_PRODUCTION_YIELD=422 blocked; ENGINEERING_TEST_VERIFIED=200 allowed',
      actual: `inflated=${blockedInflation.httpStatus}, truthful=${truthfulCandidate.httpStatus}`,
    },
    {
      name: 'All 7 OTTO & Fleet agents satisfy UHNW <=150ms covenant (0 unowned escalations) with 64-hex SHA-256 receipts',
      passed:
        charterSnap.agents.length === 7 &&
        charterSnap.allAgentsCompliant &&
        charterSnap.maxObservedAgentP95Ms <= 150 &&
        charterSnap.unownedTouchpointsCount === 0 &&
        receipt.withinUhnwSla150Ms &&
        receipt.receiptSha256.length === 64,
      expected: '7/7 compliant, maxP95<=150ms, 64-char SHA-256 receipt',
      actual: `agents=${charterSnap.agents.length}, compliant=${charterSnap.allAgentsCompliant}, maxP95=${charterSnap.maxObservedAgentP95Ms}ms`,
    },
    {
      name: 'Standout Academy enforces missing-key boundary (0% recovery) & scores 3 unseen transfer items strictly post-submission',
      passed:
        boundarySim.boundaryViolated &&
        boundarySim.primaryMetricValue === '0%' &&
        !incompletePilot.complete &&
        perfectPilot.complete &&
        perfectPilot.score === 3 &&
        perfectPilot.epistemicDisclaimer.includes('no claim of established long-term mastery'),
      expected: 'missing_key=0% recovery, incomplete blocked, 3/3 scored with research-pilot disclaimer',
      actual: `recovery=${boundarySim.primaryMetricValue}, incomplete=${incompletePilot.complete}, score=${perfectPilot.score}/3`,
    },
  ];

  return finalizeCase(
    'F24',
    'falsifier',
    'Falsifier F24: UHNW Sovereign VIP Charter, OTTO Agent Covenant, Epistemic Guard & Standout Unseen Transfer',
    'Mathematically binds permanent UHNW <=150ms Founder/Investor service across all 7 OTTO & Fleet agents, blocks inflating unmerged candidate tests into production-yield claims, and verifies tri-representational unseen transfer scoring.',
    start,
    assertions
  );
}

function runFalsifierF25MumConciergeFamilySafetyAndEon001(): VerificationCaseResult {
  const start = Date.now();
  const concierge = new MumsConciergeEngine();
  const snap = concierge.getSnapshot();
  const eon = analyzeConciergeDocument('clean_eon_001');
  const stringFalsePerm = parseKernelPermission('false');
  const badClickReceipt = verifyProviderReceipt('Receipt #fake via click');

  const idempotentFulfil = concierge.submitFulfilmentRequest({
    idempotencyKey: 'idem-f25-rx-01',
    kind: 'prescription',
    title: 'Repeat NHS inhaler delivery',
    amountGbp: 0,
    motherConfirmed: true,
  });
  const duplicateReplay = concierge.submitFulfilmentRequest({
    idempotencyKey: 'idem-f25-rx-01',
    kind: 'prescription',
    title: 'Repeat NHS inhaler delivery',
    amountGbp: 0,
    motherConfirmed: true,
  });

  const externalGatesHeldUnknown = ['G2', 'G3', 'G4'].every(
    (gid) => snap.releaseGates.find((g) => g.gateId === gid)?.status === 'UNKNOWN'
  );

  const assertions: AssertionCheck[] = [
    {
      name: 'All 9 Nov-16 safety falsifiers & string "false" fail-closed kernel guard PASS',
      passed:
        snap.safetyFalsifiers.length === 9 &&
        snap.safetyFalsifiers.every((s) => s.passed) &&
        stringFalsePerm === false &&
        !badClickReceipt.accepted,
      expected: '9/9 safety falsifiers, string "false" === false, fake receipt rejected',
      actual: `safety=${snap.safetyFalsifiers.filter((s) => s.passed).length}/9, stringFalse=${stringFalsePerm}`,
    },
    {
      name: 'EON-001 reconciles £95.11 credit (never debt), £52.43 DD vs £61.54 avg cost & 11/11 negative cases fail closed',
      passed:
        eon.closingBalanceGbp === 95.11 &&
        eon.balanceInterpretation === 'CREDIT_IN_MUM_FAVOUR' &&
        eon.isCreditNeverDescribedAsDebt &&
        eon.monthlyDirectDebitGbp === 52.43 &&
        eon.estimatedAverageMonthlyCostGbp === 61.54 &&
        snap.negativeFixtures.length === 11 &&
        snap.negativeFixtures.every((n) => n.passed),
      expected: 'credit=£95.11 never debt, DD=£52.43, avg=£61.54, 11/11 negative fail-closed',
      actual: `credit=${eon.closingBalanceGbp}, neg=${snap.negativeFixtures.filter((n) => n.passed).length}/11`,
    },
    {
      name: 'Fulfilment idempotency dedupes replays & G2/G3/G4 live external gates stay strictly UNKNOWN',
      passed:
        !idempotentFulfil.idempotentReplay &&
        duplicateReplay.idempotentReplay &&
        idempotentFulfil.record.id === duplicateReplay.record.id &&
        externalGatesHeldUnknown &&
        !snap.overallFamilyReleasePermitted,
      expected: 'idempotentReplay=true on duplicate, G2/G3/G4=UNKNOWN, overallRelease=false',
      actual: `replay=${duplicateReplay.idempotentReplay}, externalUnknown=${externalGatesHeldUnknown}`,
    },
  ];

  return finalizeCase(
    'F25',
    'falsifier',
    'Falsifier F25: MUM-CONCIERGE-001 Family Safety, WhatsApp Coalescer, EON-001 & Honest External Gates',
    'Verifies 9/9 Nov-16 safety falsifiers, EON-001 £95.11 credit vs £52.43 DD accuracy, 11/11 negative cases failing closed, fulfilment idempotency, and strict non-inflation of G2/G3/G4 external gates.',
    start,
    assertions
  );
}

function runFalsifierF26AutonomousReactivityCustodyAndFencing(): VerificationCaseResult {
  const start = Date.now();
  const engine = new AutonomousReactivityEngine();

  // 1. Initial Founder Passkey incident starts DETECTED (never falsely settled by 67 OMNIFLOW comments)
  const initialSnap = engine.getSnapshot();
  const initialPasskey = initialSnap.obligations.find((o) => o.obligationId === 'OBL-PASSKEY-8175');
  const ghFalse = engine.attemptGitHubCommentSettlement(
    'OBL-PASSKEY-8175',
    'GitHub issue escalation comment without lease'
  );
  const ackFalse = engine.attemptBrokerAckSettlement(
    'OBL-PASSKEY-8175',
    'estate.inbox.argon'
  );

  // 2. QUAD Admission boundary blocks spoofed env identity (403), quota-drained idle (429), and incapable (422)
  const spoofCheck = engine.evaluateQuadAdmission({
    agentId: 'worker-spoofed-env-agent',
    requiredCapability: 'passkey_verifier_repair',
    requiredScope: 'security:passkey-repair',
  });
  const drainedCheck = engine.evaluateQuadAdmission({
    agentId: 'worker-idle-quota-drained',
    requiredCapability: 'passkey_verifier_repair',
    requiredScope: 'security:passkey-repair',
  });
  const incapableCheck = engine.evaluateQuadAdmission({
    agentId: 'worker-connected-incapable-ui',
    requiredCapability: 'passkey_verifier_repair',
    requiredScope: 'security:passkey-repair',
  });

  // 3. Execute all 6 Ship-and-Prove Acceptance Experiments (EXP_A .. EXP_F)
  const afterAll = engine.runAllSixExperiments();
  const allSixPassed =
    afterAll.experiments.length === 6 && afterAll.experiments.every((e) => e.passedInEngine);

  const assertions: AssertionCheck[] = [
    {
      name: 'GitHub issue comments & NATS inbox --ack fail closed as false settlement while OBL-PASSKEY-8175 starts DETECTED',
      passed:
        initialPasskey?.stage === 'DETECTED' &&
        !ghFalse.settled &&
        !ackFalse.settled &&
        afterAll.falseSettlementsBlockedCount >= 3,
      expected: 'initial=DETECTED, ghSettled=false, ackSettled=false, blocked>=3',
      actual: `initial=${initialPasskey?.stage}, gh=${ghFalse.settled}, ack=${ackFalse.settled}, blocked=${afterAll.falseSettlementsBlockedCount}`,
    },
    {
      name: 'QUAD admission rejects self-declared ESTATE_AGENT (403), 0%-quota idle (429), and incapable nodes (422)',
      passed:
        !spoofCheck.admitted &&
        spoofCheck.httpStatus === 403 &&
        !drainedCheck.admitted &&
        drainedCheck.httpStatus === 429 &&
        !incapableCheck.admitted &&
        incapableCheck.httpStatus === 422,
      expected: 'spoof=403, quota=429, incapable=422',
      actual: `spoof=${spoofCheck.httpStatus}, quota=${drainedCheck.httpStatus}, incapable=${incapableCheck.httpStatus}`,
    },
    {
      name: 'All 6 Acceptance Experiments (A–F) pass with monotonic fencing (409 zombie block), 0 duplicate effects & producer immunity',
      passed:
        allSixPassed &&
        afterAll.unownedAcceptedP0Obligations === 0 &&
        afterAll.duplicateProtectedEffectsCount === 0 &&
        afterAll.staleFenceRejectionsCount >= 1 &&
        afterAll.inheritedImmunityRules.some((r) => r.preventedRecurrences >= 1),
      expected: '6/6 experiments PASS, unownedP0=0, dupEffects=0, stale409>=1, immunity>=1',
      actual: `exp=${afterAll.experiments.filter((e) => e.passedInEngine).length}/6, stale409=${afterAll.staleFenceRejectionsCount}, dup=${afterAll.duplicateProtectedEffectsCount}`,
    },
    {
      name: '14-boundary estate audit matrix & Rego R-010 external BLOCKED_DISPATCH / NOT_VERIFIED candor preserved',
      passed:
        afterAll.estateAuditMatrix.length === 14 &&
        afterAll.sourceDefectFindings.length === 4 &&
        afterAll.crossHostHonestVerdict.autonomousCrossSurfaceRecovery ===
          'VERIFIED_SANDBOX_ONLY_EXTERNAL_BLOCKED_DISPATCH',
      expected: '14 boundaries, 4 SDF guards, external=VERIFIED_SANDBOX_ONLY_EXTERNAL_BLOCKED_DISPATCH',
      actual: `boundaries=${afterAll.estateAuditMatrix.length}, sdf=${afterAll.sourceDefectFindings.length}`,
    },
  ];

  return finalizeCase(
    'F26',
    'falsifier',
    'Falsifier F26: Meridian Autonomous Reactivity, 7-Stage Custody, QUAD Attestation & Monotonic Fencing (#8184)',
    'Proves that GitHub comments and NATS inbox --ack never settle obligations, QUAD rejects spoofed/drained/incapable workers, zombie leases fail with 409, and Experiments A–F pass with honest cross-host gating.',
    start,
    assertions
  );
}

function runFalsifierF27MeridianCapabilityCalculusAnd10CertScenarios(): VerificationCaseResult {
  const start = Date.now();
  const mcc = new UniversalExecutionProtocolEngine();

  // 1. All 5 bin/capability-index invariants hold (including retired OKE tombstone)
  const invChecks = mcc.evaluateCapabilityIndexInvariants();
  const all5InvariantsHold = invChecks.length === 5 && invChecks.every((i) => i.passed);

  // 2. Sequential composition & monotonic authority narrowing (workflow patch != prod deploy)
  const presets = mcc.getCompositionPresets();
  const validRepair = presets.find((p) => p.presetId === 'CHAIN_VALID_PASSKEY_REPAIR');
  const blockedDeploy = presets.find((p) => p.presetId === 'CHAIN_BLOCKED_DEPLOY_ESCALATION');
  const blockedOke = presets.find((p) => p.presetId === 'CHAIN_BLOCKED_TOMBSTONED_OKE');

  // 3. Unified Web · App · Console disconnect buffering & zero-duplicate reconnect reconciliation
  mcc.setSurfaceConnectivity('WEB_GEMINI_BROWSER', false);
  const offlineDispatch = mcc.dispatchUnifiedCollaborationIntent({
    surfaceId: 'WEB_GEMINI_BROWSER',
    targetCapabilityId: 'cap.greenlane.patch_passkey_verifier',
    intentSummary: 'F27 offline browser directive buffered safely in durable outbox',
    idempotencyKey: 'idem-f27-offline-browser-01',
  });
  const recon = mcc.setSurfaceConnectivity('WEB_GEMINI_BROWSER', true);
  const dupAfterRecon = mcc.dispatchUnifiedCollaborationIntent({
    surfaceId: 'WEB_GEMINI_BROWSER',
    targetCapabilityId: 'cap.greenlane.patch_passkey_verifier',
    intentSummary: 'F27 offline browser directive buffered safely in durable outbox',
    idempotencyKey: 'idem-f27-offline-browser-01',
  });

  // 4. All 10 Estate Certification Scenarios (CERT_01..CERT_10) + Bounded LTL Model Check + Honest External Verdict
  const certs = mcc.runAllTenCertificationScenarios();
  const snap = mcc.getSnapshot();

  const assertions: AssertionCheck[] = [
    {
      name: 'All 5 bin/capability-index invariants hold across 9-tuple contracts C_c=(I,O,P,Q,A,E,F,R,V) including retired OKE tombstone',
      passed: all5InvariantsHold && snap.contracts.length >= 9,
      expected: '5/5 invariants PASS, >=9 canonical contracts',
      actual: `invariants=${invChecks.filter((i) => i.passed).length}/5, contracts=${snap.contracts.length}`,
    },
    {
      name: 'MGE-001 composition admits valid repair chain while blocking workflow-to-prod-deploy authority escalation & tombstoned OKE',
      passed:
        Boolean(validRepair?.compatible) &&
        blockedDeploy?.compatible === false &&
        blockedDeploy?.failureCode === 'AUTHORITY_EXPANSION_FORBIDDEN' &&
        blockedOke?.compatible === false &&
        blockedOke?.failureCode === 'TOMBSTONED_CAPABILITY',
      expected: 'repair=true, deploy=AUTHORITY_EXPANSION_FORBIDDEN, oke=TOMBSTONED_CAPABILITY',
      actual: `repair=${validRepair?.compatible}, deploy=${blockedDeploy?.failureCode}, oke=${blockedOke?.failureCode}`,
    },
    {
      name: 'Unified Web · App · Console bus buffers offline surface intents and reconciles to VERIFIED_EFFECT on reconnect with 0 duplicates',
      passed:
        offlineDispatch.bufferedOffline === true &&
        recon.reconciledEnvelopesCount === 1 &&
        dupAfterRecon.idempotentReplay === true &&
        dupAfterRecon.envelope.settlementState === 'VERIFIED_EFFECT',
      expected: 'bufferedOffline=true, reconciled=1, replay=VERIFIED_EFFECT',
      actual: `buffered=${offlineDispatch.bufferedOffline}, reconciled=${recon.reconciledEnvelopesCount}, final=${dupAfterRecon.envelope.settlementState}`,
    },
    {
      name: '10/10 certification scenarios (CERT_01..10) & 128-state LTL model check pass while keeping external multi-repo rollout SPECIFIED_NOT_ESTATE_WIDE_ENFORCED',
      passed:
        certs.length === 10 &&
        certs.every((c) => c.passedInCiEngine) &&
        snap.ltlModelCheck.allPropertiesHoldUnderAssumptions === true &&
        snap.ltlModelCheck.totalStatesExplored === 128 &&
        snap.existingEstateInventory.length === 10 &&
        snap.crossRepoReconciliation.length === 5 &&
        snap.honestEstateVerdict.externalMultiRepoEnforcement === 'SPECIFIED_NOT_ESTATE_WIDE_ENFORCED',
      expected: '10/10 CERT PASS, 128 LTL states PASS, 10 EX + 5 repos reconciled, external=SPECIFIED_NOT_ESTATE_WIDE_ENFORCED',
      actual: `certs=${certs.filter((c) => c.passedInCiEngine).length}/10, ltl=${snap.ltlModelCheck.allPropertiesHoldUnderAssumptions}, external=${snap.honestEstateVerdict.externalMultiRepoEnforcement}`,
    },
  ];

  return finalizeCase(
    'F27',
    'falsifier',
    'Falsifier F27: Meridian Capability Calculus (MCC-001), 5 Enforcement Doors, Unified Web/App/Console Bus & 10/10 Cert Suite',
    'Verifies 9-tuple contracts, 5 bin/capability-index invariants, monotonic authority narrowing, Web/App/Console disconnect/reconnect continuity, 128-state LTL safety/liveness, and 10/10 certification scenarios.',
    start,
    assertions
  );
}

function runIntegrationCoreRouterDagsterGrandUnionConcierge(): VerificationCaseResult {
  const start = Date.now();
  const router = new RouterEngine({ initialReceipts: 20 });
  const dagster = new DagsterOrchestrator();
  const supply = new ModelSupplyRegistry();
  const grandUnion = new EstateGrandUnionEngine({ router, dagster, supply, cadenceMs: 6000 });
  const ottoNumen = new OttoNumenConciergeEngine();
  const baselineVip = ottoNumen.getSnapshot().telemetry;

  grandUnion.subscribe((snap) => {
    ottoNumen.ingestEvent({
      kind: 'chronos_heartbeat',
      sourceSubsystem: 'Chronos / Tempo',
      headline: `Chronos beat #${snap.chronos.beatNumber} checkpointed`,
      metrics: { Beat: snap.chronos.beatNumber },
      autonomousAction: 'Suppressed routine heartbeat cleanly before VIP Telegram.',
    });
  });

  // Step 1: Primary 402 drain fails over automatically without dropping WAL receipts
  router.setLaneFault('deepseek-flash', '402_credit_exhausted', 0);
  const routedOnFailover = router.route({
    clientKey: 'pk_live_opencode_primary_94a2',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 640,
  });

  // Step 2: Worker SIGTERM restart preserves 100% of WAL receipts & hydrates keys
  const restart = dagster.simulateWorkerRestart(router, 'dagster_durable');

  // Step 3: Top-up + Dagster sensor closes circuit cleanly
  router.topUpLaneCredits('deepseek-flash', 200);
  dagster.evaluateSensors(router);
  const restored = router.route({
    clientKey: 'pk_live_opencode_primary_94a2',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 512,
  });

  // Step 4: Grand Union autonomous Chronos tick feeds OTTO_NUMEN zero-send suppression sink
  const tickSnap = grandUnion.executeBeat('manual_pulse');
  const vipSnap = ottoNumen.getSnapshot();
  const deltaSuppressed =
    vipSnap.telemetry.suppressedHeartbeatEvents - baselineVip.suppressedHeartbeatEvents;
  const deltaAudiblePings =
    vipSnap.telemetry.audibleCeoPings - baselineVip.audibleCeoPings;

  const assertions: AssertionCheck[] = [
    {
      name: '402 DeepSeek drain fails over onto fallback lane and top-up + Dagster restores DeepSeek',
      passed:
        routedOnFailover.ok &&
        routedOnFailover.selectedLaneId !== 'deepseek-flash' &&
        restored.ok &&
        restored.selectedLaneId === 'deepseek-flash',
      expected: 'failover != deepseek-flash then restored == deepseek-flash',
      actual: `failover=${routedOnFailover.selectedLaneId}, restored=${restored.selectedLaneId}`,
    },
    {
      name: 'Mid-flight Dagster worker crash drops 0 WAL receipts and hydrates all keys',
      passed:
        restart.droppedReceipts === 0 &&
        restart.vaultKeysHydratedOnBoot === true &&
        restart.clientKeysPreserved >= 2,
      expected: 'droppedReceipts=0, hydrated=true, clientKeys>=2',
      actual: `dropped=${restart.droppedReceipts}, hydrated=${restart.vaultKeysHydratedOnBoot}, keys=${restart.clientKeysPreserved}`,
    },
    {
      name: 'Grand Union Chronos beat checkpoints cleanly while OTTO_NUMEN suppresses non-actionable chatter',
      passed:
        tickSnap.chronos.beatNumber >= 1 &&
        deltaSuppressed >= 1 &&
        deltaAudiblePings === 0,
      expected: 'beat>=1, deltaSuppressed>=1, deltaAudiblePings=0',
      actual: `beat=${tickSnap.chronos.beatNumber}, deltaSuppressed=${deltaSuppressed}, deltaPings=${deltaAudiblePings}`,
    },
  ];

  return finalizeCase(
    'INT-07',
    'integration',
    'Integration INT-07: Multi-Day Core Pipeline (Router Failover -> WAL Crash -> Dagster -> Chronos -> OTTO_NUMEN)',
    'End-to-end integration test across RouterEngine, AtomicKeyStore, WAL ledger, Dagster sensors, Grand Union Chronos beats, and VIP Telegram zero-chatter suppression.',
    start,
    assertions
  );
}

function runIntegrationMccOmniflowWorkerRecoveryKarma(): VerificationCaseResult {
  const start = Date.now();
  const bus = new OmniflowLiveBusEngine({ journalPath: null });
  const t0 = Date.now();

  // 1. Volatile runner joins with 5s lease TTL and claims work
  bus.registerParticipant({
    agentId: 'worker-volatile-01',
    displayName: 'Volatile Runner',
    surfaceClass: 'CLOUD_RUNNER',
    transport: 'SSE_HTTPS',
    capabilities: ['cap.greenlane.patch_passkey_verifier'],
    formations: ['formation-recovery'],
    ttlMs: 5_000,
    nowMs: t0,
  });

  const pub = bus.publishMessage({
    fromAgent: 'founder-web-tab',
    fromSurface: 'FOUNDER_COCKPIT',
    target: '@formation:formation-recovery',
    verb: 'ASK',
    body: 'Execute passkey verifier patch with independent KARMA verification',
    correlationId: 'corr-int08-custody',
    idempotencyKey: 'idem-int08-custody-01',
    requiresClaim: true,
    proposedFiles: ['src/passkey/verifier.ts'],
  });
  const envelopeId = pub.message?.envelopeId ?? '';
  const claim1 = bus.claimLease({
    envelopeId,
    workerId: 'worker-volatile-01',
  });
  const staleFence = claim1.message?.fencingToken ?? 0;

  // 2. Simulate volatile worker crash / heartbeat expiration -> sweep auto-recovers lease
  const swept = bus.sweepExpiredParticipants(t0 + 15_000);

  // 3. Survivor worker re-claims with strictly higher fence; zombie old fence is 409 rejected
  bus.registerParticipant({
    agentId: 'worker-survivor-02',
    displayName: 'Survivor Runner',
    surfaceClass: 'CONSOLE_CLI',
    transport: 'CLI_BRIDGE',
    capabilities: ['cap.greenlane.patch_passkey_verifier'],
    formations: ['formation-recovery'],
    ttlMs: 60_000,
  });
  const claim2 = bus.claimLease({
    envelopeId,
    workerId: 'worker-survivor-02',
  });
  const zombieSubmit = bus.submitEffectWithFence({
    envelopeId,
    workerId: 'worker-volatile-01',
    fencingToken: staleFence,
    artifactRef: 'patch-stale.diff',
  });
  const validSubmit = bus.submitEffectWithFence({
    envelopeId,
    workerId: 'worker-survivor-02',
    fencingToken: claim2.message?.fencingToken ?? 0,
    artifactRef: 'patch-verified.diff',
  });

  // 4. Self-verification blocked (403); independent KARMA verifier settles to VERIFIED_EFFECT
  const selfVerify = bus.verifyIndependently({
    envelopeId,
    verifierId: 'worker-survivor-02',
    evidenceNote: 'Self approval attempt',
  });
  const karmaVerify = bus.verifyIndependently({
    envelopeId,
    verifierId: 'karma-independent-verifier',
    evidenceNote: 'Independent verifier verified patch-verified.diff cleanly',
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'Expired participant TTL sweep recovers lease safely with 0 lost envelopes',
      passed:
        pub.httpStatus === 201 &&
        Boolean(envelopeId) &&
        swept.recoveredEnvelopeIds.includes(envelopeId) &&
        (claim2.message?.fencingToken ?? 0) > staleFence,
      expected: 'recovered on sweep with monotonic fence increase',
      actual: `recovered=${swept.recoveredEnvelopeIds.length}, fence1=${staleFence}, fence2=${claim2.message?.fencingToken}`,
    },
    {
      name: 'Zombie stale fence blocked fail-closed (409) while survivor fence commits effect (200)',
      passed: zombieSubmit.httpStatus === 409 && validSubmit.httpStatus === 200,
      expected: 'zombie=409, survivor=200',
      actual: `zombie=${zombieSubmit.httpStatus}, survivor=${validSubmit.httpStatus}`,
    },
    {
      name: 'Self-verification rejected (403) and independent KARMA verifier reaches VERIFIED_EFFECT (200)',
      passed:
        selfVerify.httpStatus === 403 &&
        karmaVerify.httpStatus === 200 &&
        karmaVerify.message?.custodyStage === 'VERIFIED_EFFECT',
      expected: 'self=403, independent=200 (VERIFIED_EFFECT)',
      actual: `self=${selfVerify.httpStatus}, indep=${karmaVerify.httpStatus} (${karmaVerify.message?.custodyStage})`,
    },
  ];

  return finalizeCase(
    'INT-08',
    'integration',
    'Integration INT-08: MCC-001 -> OMNIFLOW Bus -> Worker Crash TTL Recovery -> Monotonic Fence -> KARMA 403/200',
    'Proves zero lost envelopes across worker drop recovery, monotonic fencing against zombie writers, and independent verifier separation.',
    start,
    assertions
  );
}

function runIntegrationGeminiSyncAndAuditHonesty(): VerificationCaseResult {
  const start = Date.now();
  const auditUnrefreshed = getAllSeeingEyeAuditSnapshot();
  const settlementLocalOnly = evaluateUniversalKarmicSettlement({
    autoSyncHeadSha: 'deadbeef1234',
    autoSyncBundleSha256: 'a'.repeat(64),
    registeredBusWorkerIds: ['BR-KIMI-01'],
  });
  const matrix = evaluateMandatoryResilienceMatrix({
    externalCloudLive: false,
    remoteFaultInjectionVerifiedCount: 0,
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'All-Seeing Eye clearly separates historical 359 baseline from live API inventory',
      passed:
        auditUnrefreshed.historicalBaselineFailedRuns === 359 &&
        auditUnrefreshed.liveFailedWorkflowRunsCount === null &&
        auditUnrefreshed.certificationStatus === 'OPERATIONAL_CERTIFICATION_WITHHELD',
      expected: 'historical=359, live=null, certificationWithheld',
      actual: `hist=${auditUnrefreshed.historicalBaselineFailedRuns}, live=${auditUnrefreshed.liveFailedWorkflowRunsCount}`,
    },
    {
      name: 'Local-only sync head + registered Kimi worker NEVER prematurely settle KARMA certification',
      passed:
        settlementLocalOnly.settled === false &&
        settlementLocalOnly.browserWorkforceAuthenticatedExecutionsCount === 0 &&
        settlementLocalOnly.unblockPackCommands.length >= 3,
      expected: 'settled=false, authenticatedExec=0',
      actual: `settled=${settlementLocalOnly.settled}, authExec=${settlementLocalOnly.browserWorkforceAuthenticatedExecutionsCount}`,
    },
    {
      name: '10-Scenario Resilience Matrix exposes 10/10 local prechecks vs 0/10 remote fault injections honestly',
      passed:
        matrix.localPrechecksPassedCount === 10 &&
        matrix.remoteFaultInjectionsPassedCount === 0 &&
        matrix.productionCertified === false,
      expected: 'local=10, remote=0, certified=false',
      actual: `local=${matrix.localPrechecksPassedCount}, remote=${matrix.remoteFaultInjectionsPassedCount}, cert=${matrix.productionCertified}`,
    },
  ];

  return finalizeCase(
    'INT-09',
    'integration',
    'Integration INT-09: Sync #7760, KARMA Non-Collusion, All-Seeing Eye Honesty & Resilience Matrix',
    'Cross-checks that local builds, historical snapshots, and unauthenticated worker registrations never masquerade as certified external production execution.',
    start,
    assertions
  );
}

function runIntegrationPhoenixConstitutionOmniflowSealLifecycle(): VerificationCaseResult {
  const start = Date.now();
  const constitution = verifyAllEstateFsmsClosedLoop();
  const bus = new OmniflowLiveBusEngine({ journalPath: null });
  const phoenix = new PhoenixDailyBootEngine({ repoRoot: process.cwd() });

  phoenix.registerDecisionHook((decision, seal, reason) => {
    bus.publishMessage({
      fromAgent: 'founder-genesis-cockpit',
      fromSurface: 'FOUNDER_COCKPIT',
      target: '@all',
      verb: decision === 'GO' ? 'STATUS' : 'BLOCKED',
      body:
        decision === 'GO'
          ? `AUTHORIZED_DAILY_OPERATIONS: ${seal?.sealId ?? 'SEAL'} (${reason})`
          : `EMERGENCY_QUARANTINE_ABORT: ${reason}`,
      correlationId: `corr-int10-${decision.toLowerCase()}`,
      idempotencyKey: `idem-int10-${decision.toLowerCase()}`,
      requiresClaim: false,
    });
  });

  // Standby run must reject Go fail-closed with 409 & emit 0 GO broadcasts
  const standbyGo = phoenix.decideGoOrAbort({ decision: 'GO' });
  // Emergency Abort even from standby freezes & publishes EMERGENCY_QUARANTINE_ABORT to OMNIFLOW
  const abortRes = phoenix.decideGoOrAbort({
    decision: 'ABORT',
    reason: 'INT-10 Sovereign Emergency Freeze check',
  });
  const busMessages = bus.getSnapshot().messages;
  const abortBroadcasted = busMessages.some((m) =>
    m.body.includes('EMERGENCY_QUARANTINE_ABORT')
  );

  const assertions: AssertionCheck[] = [
    {
      name: 'Closed-Loop FSM Constitution proves 10/10 workflows across all 6 estate layers',
      passed:
        constitution.allLayersCoveredByFsms &&
        constitution.allFsmsMathematicallyClosed &&
        constitution.provenClosedLoopCount === 10 &&
        constitution.totalEstateLayers === 6,
      expected: '6/6 layers, 10/10 FSMs closed',
      actual: `layers=${constitution.totalEstateLayers}, closed=${constitution.provenClosedLoopCount}/${constitution.totalRegisteredFsms}`,
    },
    {
      name: 'Operation Phoenix rejects Go fail-closed (409) when quorum drill has not passed',
      passed:
        standbyGo.ok === false &&
        standbyGo.httpStatus === 409 &&
        standbyGo.snapshot.autonomousDispatchAllowed === false,
      expected: 'httpStatus=409, autonomousDispatchAllowed=false',
      actual: `status=${standbyGo.httpStatus}, dispatch=${standbyGo.snapshot.autonomousDispatchAllowed}`,
    },
    {
      name: 'Founder Emergency Abort transitions FSM to FOUNDER_ABORTED_FREEZE and broadcasts on OMNIFLOW',
      passed:
        abortRes.ok &&
        abortRes.httpStatus === 200 &&
        abortRes.snapshot.currentRun.overallVerdict === 'FOUNDER_ABORTED_FREEZE' &&
        abortBroadcasted,
      expected: '200 FOUNDER_ABORTED_FREEZE + OMNIFLOW EMERGENCY_QUARANTINE_ABORT',
      actual: `status=${abortRes.httpStatus}, verdict=${abortRes.snapshot.currentRun.overallVerdict}, bus=${abortBroadcasted}`,
    },
  ];

  return finalizeCase(
    'INT-10',
    'integration',
    'Integration INT-10: Operation Phoenix v2 + 10/10 Closed-Loop FSMs + OMNIFLOW Decision Hooks',
    'Verifies Constitutional 6-layer/10-FSM liveness coupling with Phoenix fail-closed 409 Go locks and OMNIFLOW Abort broadcast hooks.',
    start,
    assertions
  );
}

function runFalsifierF28GeminiSync7760SecurityAndReadback(): VerificationCaseResult {
  const start = Date.now();
  const audit = getAllSeeingEyeAuditSnapshot();
  const has7760 = audit.repositoriesInspected === 6;

  const settlementNoSync = evaluateUniversalKarmicSettlement({
    autoSyncExternalAccepted: false,
    externalBusLiveVerified: false,
    registeredBusWorkerIds: [],
  });
  const syncObs = settlementNoSync.obligations.find(
    (o) => o.obligationId === 'OBL-AUTO-SYNC-ZERO-REMINDER'
  );
  const fullSettled = evaluateUniversalKarmicSettlement({
    autoSyncExternalAccepted: true,
    autoSyncHeadSha: '1234abcd5678',
    autoSyncBundleSha256: 'b'.repeat(64),
    externalBusLiveVerified: true,
    externalKimiLiveVerified: true,
    authenticatedBrowserWorkerIds: BROWSER_WORKFORCE_FLEET.map((w) => w.workerId),
    externalIdpVerified: true,
    remoteFaultInjectionVerifiedCount: 10,
    registeredBusWorkerIds: ['BR-KIMI-01'],
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'Mission #7760 models 6 CI assurance tests and 16 MiB bundle cap',
      passed:
        has7760 &&
        settlementNoSync.geminiSync7760.ciTestsPassedCount === 6 &&
        settlementNoSync.geminiSync7760.maxBundleBytes === 16 * 1024 * 1024,
      expected: '6 CI tests, 16 MiB cap',
      actual: `ci=${settlementNoSync.geminiSync7760.ciTestsPassedCount}, cap=${settlementNoSync.geminiSync7760.maxBundleBytes}`,
    },
    {
      name: 'Un-deployed receiver holds OBL-AUTO-SYNC-ZERO-REMINDER open; full proof settles cleanly',
      passed: Boolean(syncObs && !syncObs.verifiedOverall) && fullSettled.settled === true,
      expected: 'unverified when undeployed; settled=true when all 5 obligations + 10 faults verified',
      actual: `syncVerified=${syncObs?.verifiedOverall}, fullSettled=${fullSettled.settled}`,
    },
  ];

  return finalizeCase(
    'F28',
    'falsifier',
    'Falsifier F28: Gemini Sync #7760 Receiver Contract, 16 MiB Limit & Obligation Hold',
    'Ensures undeployed bundle receivers keep Mission #7760 uncertified and require full authenticated delivery + byte readback.',
    start,
    assertions
  );
}

function runFalsifierF29KarmaSettlementAndResilienceMatrixHonesty(): VerificationCaseResult {
  const start = Date.now();
  const partialWorkers = evaluateUniversalKarmicSettlement({
    autoSyncExternalAccepted: true,
    autoSyncHeadSha: 'deadbeef1234',
    autoSyncBundleSha256: 'c'.repeat(64),
    externalBusLiveVerified: true,
    externalKimiLiveVerified: true,
    authenticatedBrowserWorkerIds: ['BR-KIMI-01'],
    externalIdpVerified: true,
    remoteFaultInjectionVerifiedCount: 10,
    registeredBusWorkerIds: ['BR-KIMI-01'],
  });
  const partialFaults = evaluateMandatoryResilienceMatrix({
    externalCloudLive: true,
    remoteFaultInjectionVerifiedCount: 7,
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'Partial browser seat execution (1/7 authenticated) refuses full KARMA settlement',
      passed:
        partialWorkers.browserWorkforceAuthenticatedExecutionsCount === 1 &&
        partialWorkers.settled === false,
      expected: '1/7 -> settled=false',
      actual: `${partialWorkers.browserWorkforceAuthenticatedExecutionsCount}/7 -> settled=${partialWorkers.settled}`,
    },
    {
      name: 'Partial remote fault injections (7/10) withhold production resilience certification',
      passed:
        partialFaults.remoteFaultInjectionsPassedCount === 7 &&
        partialFaults.productionCertified === false,
      expected: '7/10 -> productionCertified=false',
      actual: `${partialFaults.remoteFaultInjectionsPassedCount}/10 -> cert=${partialFaults.productionCertified}`,
    },
  ];

  return finalizeCase(
    'F29',
    'falsifier',
    'Falsifier F29: KARMA Partial-Fleet & Partial-Fault Non-Collusion Falsifier',
    'Prevents partial browser workforce execution or incomplete remote fault injection suites from rounding up to certified operational state.',
    start,
    assertions
  );
}

function runFalsifierF30ClosedLoopFsmConstitutionAndTrapRejection(): VerificationCaseResult {
  const start = Date.now();
  const constitution = verifyAllEstateFsmsClosedLoop();
  const syntheticTrap = verifySingleFsmClosedLoop({
    fsmId: 'FSM-TRAP-TEST',
    name: 'Adversarial Dead-End & Missing Quarantine FSM',
    layer: 'LAYER_1_KERNEL_METERING',
    ownerForce: 'Adversarial Test',
    missionRefs: ['TEST-TRAP'],
    states: ['START', 'WAIT_FOREVER', 'DONE', 'QUARANTINE'],
    initialState: 'START',
    verifiedTerminalStates: ['DONE'],
    quarantineTerminalStates: ['QUARANTINE'],
    waitingOrLeasedStatesRequiringTimeout: ['WAIT_FOREVER'],
    transitions: [
      { from: 'START', event: 'WAIT', to: 'WAIT_FOREVER' },
      { from: 'START', event: 'COMPLETE', to: 'DONE' },
      { from: 'START', event: 'FAIL', to: 'QUARANTINE' },
    ],
    futureProofContract: 'Must fail dead-end, timeout & digest checks',
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'All 10 registered estate FSMs satisfy all 5 Closed-Loop mathematical theorems',
      passed:
        constitution.allFsmsMathematicallyClosed &&
        constitution.lawChecklist.every((l) => l.satisfied) &&
        constitution.provenClosedLoopCount === 10,
      expected: '5/5 laws satisfied, 10/10 FSMs closed',
      actual: `closed=${constitution.provenClosedLoopCount}/${constitution.totalRegisteredFsms}`,
    },
    {
      name: 'Adversarial open-loop FSM with dangling wait state & missing proof digest fails theorem check',
      passed:
        syntheticTrap.closedLoopProven === false &&
        syntheticTrap.zeroDeadEndStates === false &&
        syntheticTrap.allWaitingStatesHaveTimeoutEdge === false &&
        syntheticTrap.allVerifiedTerminalsHaveProofDigest === false,
      expected: 'closedLoopProven=false across 3 violation axes',
      actual: `closed=${syntheticTrap.closedLoopProven}, violations=${syntheticTrap.violations.length}`,
    },
  ];

  return finalizeCase(
    'F30',
    'falsifier',
    'Falsifier F30: Universal Closed-Loop FSM Constitutional Theorems & Open-Loop Trap Rejection',
    'Proves every estate subsystem forms a mathematically closed state machine and catches any dangling state, infinite wait, or unsealed completion.',
    start,
    assertions
  );
}

function runFalsifierF31PhoenixSovereignVetoAndAutoRevoke(): VerificationCaseResult {
  const start = Date.now();
  const phoenix = new PhoenixDailyBootEngine({ repoRoot: process.cwd() });
  const initSnap = phoenix.getSnapshot();
  const blockedGo = phoenix.decideGoOrAbort({ decision: 'GO' });

  const iocContinuity = verifyRepositoryZeroDependencyContinuity(process.cwd());
  const iocGhostTrap = evaluateSystemFirstIocGate({
    actuatorModel: 'claude',
    workerQuadAttested: true,
    taskPrompt:
      'Point com.estate.litellm-proxy at 127.0.0.1:4000 with LITELLM_API_KEY and deploy to oke-direct 193.123.184.22',
    proposedFiles: ['catalog/routing.yaml'],
    targetHosts: ['passkey.mumchimp.com'],
  });
  const iocAutoSplit = evaluateSystemFirstIocGate({
    actuatorModel: 'deepseek',
    workerQuadAttested: true,
    autoDecompose: true,
    taskPrompt: 'Update catalog, docs, and tests cleanly',
    proposedFiles: ['catalog/capabilities.yaml', 'docs/runbook.md', 'tests/test_boundary.py'],
    targetHosts: ['passkey.mumchimp.com'],
  });

  const assertions: AssertionCheck[] = [
    {
      name: 'Phoenix boots fail-closed (autonomousDispatchAllowed=false) and withholds Seal on Go (409)',
      passed:
        initSnap.autonomousDispatchAllowed === false &&
        initSnap.activeSeal === null &&
        blockedGo.httpStatus === 409 &&
        blockedGo.ok === false,
      expected: 'dispatch=false, seal=null, go=409',
      actual: `dispatch=${initSnap.autonomousDispatchAllowed}, go=${blockedGo.httpStatus}`,
    },
    {
      name: 'Inherited Immunity Ledger pre-seeds Ghost IP 193.123.184.22, Proof-2 & FSM Dead-End guards',
      passed:
        initSnap.immunityLedger.length >= 3 &&
        initSnap.immunityLedger.some(
          (r) => r.failureClassCode === 'RETIRED_OKE_GHOST_IP_193_123_184_22'
        ) &&
        initSnap.immunityLedger.some(
          (r) => r.failureClassCode === 'OPEN_LOOP_OR_MISSING_QUARANTINE_FSM'
        ),
      expected: '>=3 immunity rules including RETIRED_OKE_GHOST_IP_193_123_184_22 & FSM_DEADEND',
      actual: `rules=${initSnap.immunityLedger.length}`,
    },
    {
      name: 'LAW_SYSTEM_FIRST_IOC_RECONCILER enforces <=4KB GENESIS_SPORE.dna, blocks OKE/LiteLLM ghosts pre-token (422), and auto-splits #8194',
      passed:
        iocContinuity.verified === true &&
        iocContinuity.genesisSporeWithin4Kb === true &&
        iocGhostTrap.httpStatus === 422 &&
        iocGhostTrap.tokensSpent === 0 &&
        iocGhostTrap.verdictCode === 'ANTI_CONFUSION_RETIRED_GHOST_BLOCKED' &&
        iocAutoSplit.httpStatus === 200 &&
        iocAutoSplit.decomposedChildLanes.length === 3,
      expected: 'DNA<=4KB verified, ghost=422 (0 tokens), #8194=200 (3 lanes)',
      actual: `dna=${iocContinuity.verified} (${iocContinuity.genesisSporeBytes}B), ghost=${iocGhostTrap.httpStatus}, lanes=${iocAutoSplit.decomposedChildLanes.length}`,
    },
  ];

  return finalizeCase(
    'F31',
    'falsifier',
    'Falsifier F31: Operation Phoenix v2 Sovereign Veto Fail-Closed 409 & Inherited Immunity Guards',
    'Ensures the Phoenix Driving Seat never starts with an active Operations Seal, blocks unverified Go dispatches with 409, and locks discovered failure classes into Immunity.',
    start,
    assertions
  );
}

/**
 * Chaos & Stress Resilience Simulator running real RouterEngine + DagsterOrchestrator
 * load across configurable request counts and injected failure scenarios.
 */
export function runChaosBenchmark(config: ChaosConfig): ChaosReport {
  const clampedCount = Math.max(100, Math.min(5000, Math.round(config.requestCount)));
  const router = new RouterEngine({ initialReceipts: 100, strategy: config.strategy });
  const dagster = new DagsterOrchestrator();
  const timeline: ChaosTimelineEvent[] = [];

  // Raise client budget ceiling so stress volume tests failover/recovery rather than hitting $250 cap
  router.keyStore.atomicCapSave('opencode_primary', 25000);
  router.keyStore.atomicCapSave('ci_canary', 15000);

  const overheadSamplesUs: number[] = [];
  const totalLatencySamplesMs: number[] = [];

  let succeededRequests = 0;
  let failedRequests = 0;
  let failoverRoutedRequests = 0;
  let capSaveRacesRun = 0;
  let capSaveKeysPreserved = true;

  const deepseekDrainAt = Math.floor(clampedCount * 0.2);
  const deepseekTopUpAt = Math.floor(clampedCount * 0.45);
  const crashAt = Math.floor(clampedCount * 0.55);
  const brownoutAt = Math.floor(clampedCount * 0.7);
  const brownoutRecoverAt = Math.floor(clampedCount * 0.85);
  const spikeAt = Math.floor(clampedCount * 0.3);

  let stepCounter = 1;
  timeline.push({
    step: stepCounter++,
    requestIndex: 0,
    event: 'Chaos stress harness started',
    severity: 'info',
    detail: `Dispatching ${clampedCount} requests (concurrency=${config.concurrency}, strategy=${config.strategy}).`,
  });

  for (let i = 1; i <= clampedCount; i++) {
    // 1. DeepSeek 402 credit exhaustion injection & top-up recovery
    if (config.injectDeepSeek402 && i === deepseekDrainAt) {
      router.setLaneFault('deepseek-flash', '402_credit_exhausted', 0);
      timeline.push({
        step: stepCounter++,
        requestIndex: i,
        event: 'Injected DeepSeek 402 Insufficient Balance',
        severity: 'critical',
        detail: 'Primary lane balance hit $0.00; expecting instant failover to Anthropic/Gemini.',
      });
    }
    if (config.injectDeepSeek402 && i === deepseekTopUpAt) {
      router.topUpLaneCredits('deepseek-flash', 500);
      dagster.evaluateSensors(router);
      timeline.push({
        step: stepCounter++,
        requestIndex: i,
        event: 'Credit top-up + Dagster billing_recovery_sensor tick',
        severity: 'resolved',
        detail: 'DeepSeek balance topped up; Dagster sensor probed 200 OK and closed circuit.',
      });
    }

    // 2. Latency spike injection
    if (config.injectLatencySpike && i === spikeAt) {
      router.setLaneFault('gemini-flash', 'latency_spike');
      timeline.push({
        step: stepCounter++,
        requestIndex: i,
        event: 'Injected +850ms upstream latency spike on Gemini Flash',
        severity: 'warning',
        detail: 'Monitoring p95/p99 tail latency resilience.',
      });
    }

    // 3. Mid-burst worker crash / restart simulation
    if (config.injectWorkerCrash && i === crashAt) {
      const restartReport = dagster.simulateWorkerRestart(router, 'dagster_durable');
      timeline.push({
        step: stepCounter++,
        requestIndex: i,
        event: 'Simulated SIGTERM worker crash & Dagster reboot',
        severity: restartReport.droppedReceipts === 0 ? 'resolved' : 'critical',
        detail: `Preserved ${restartReport.receiptsAfterRestart}/${restartReport.receiptsBeforeRestart} WAL receipts (dropped=${restartReport.droppedReceipts}); vault hydrated=${restartReport.vaultKeysHydratedOnBoot}.`,
      });
    }

    // 4. Multi-lane 503 brownout (leaves OpenAI Mini standing as 4th fallback)
    if (config.injectMultiLane503 && i === brownoutAt) {
      router.setLaneFault('anthropic-sonnet', '503_unavailable');
      router.setLaneFault('gemini-flash', '503_unavailable');
      timeline.push({
        step: stepCounter++,
        requestIndex: i,
        event: 'Injected dual-lane 503 brownout (Anthropic + Gemini)',
        severity: 'warning',
        detail: 'Verifying deep fallback chain keeps traffic flowing via remaining healthy lanes.',
      });
    }
    if (config.injectMultiLane503 && i === brownoutRecoverAt) {
      router.setLaneFault('anthropic-sonnet', 'healthy', 300);
      router.setLaneFault('gemini-flash', 'healthy', 300);
      dagster.evaluateSensors(router);
      timeline.push({
        step: stepCounter++,
        requestIndex: i,
        event: 'Cleared 503 brownout via Dagster sensor probe',
        severity: 'resolved',
        detail: 'All upstream lanes restored to CLOSED state.',
      });
    }

    // 5. Concurrent cap-save race injection
    if (config.injectCapSaveRace && i % Math.max(25, Math.floor(clampedCount / 20)) === 0) {
      const targetId = capSaveRacesRun % 2 === 0 ? 'ci_canary' : 'opencode_primary';
      const saveRes = router.keyStore.atomicCapSave(targetId, 18000 + capSaveRacesRun * 50);
      capSaveRacesRun++;
      if (!saveRes.ok || saveRes.preservedKeyCount < 2) {
        capSaveKeysPreserved = false;
      }
    }

    const clientKey =
      i % 4 === 0 ? 'pk_live_canary_probe_71c9' : 'pk_live_opencode_primary_94a2';
    const res = router.route({
      clientKey,
      modelSlug: 'deepseek-chat',
      estimatedTokens: 640 + (i % 512),
      strategy: config.strategy,
      nowMs: Date.now() + i * 10,
    });

    overheadSamplesUs.push(res.gatewayOverheadUs);
    totalLatencySamplesMs.push(res.totalLatencyMs);

    if (res.ok) {
      succeededRequests++;
      if (res.attempts.some((a) => a.outcome === 'failed' || a.outcome === 'skipped_open_circuit')) {
        failoverRoutedRequests++;
      }
    } else {
      failedRequests++;
    }
  }

  const walStats = router.ledger.getStats();
  const expectedReceipts = 100 + succeededRequests;
  const receiptsDropped = Math.max(0, expectedReceipts - walStats.totalReceipts);

  overheadSamplesUs.sort((a, b) => a - b);
  totalLatencySamplesMs.sort((a, b) => a - b);

  const successRatePct = Number(((succeededRequests / clampedCount) * 100).toFixed(2));
  const slaPassed = successRatePct >= 99.5 && receiptsDropped === 0 && capSaveKeysPreserved;

  timeline.push({
    step: stepCounter++,
    requestIndex: clampedCount,
    event: slaPassed ? 'Chaos SLA Passed (99.5%+ uptime, 0 WAL loss)' : 'Chaos SLA Breached',
    severity: slaPassed ? 'resolved' : 'critical',
    detail: `Success ${successRatePct}% | Failovers ${failoverRoutedRequests} | Receipts preserved ${walStats.totalReceipts}/${expectedReceipts}.`,
  });

  return {
    runAt: new Date().toISOString(),
    config: { ...config, requestCount: clampedCount },
    totalRequests: clampedCount,
    succeededRequests,
    failedRequests,
    failoverRoutedRequests,
    successRatePct,
    p50OverheadUs: percentile(overheadSamplesUs, 50),
    p95OverheadUs: percentile(overheadSamplesUs, 95),
    p99OverheadUs: percentile(overheadSamplesUs, 99),
    p50TotalLatencyMs: percentile(totalLatencySamplesMs, 50),
    p95TotalLatencyMs: percentile(totalLatencySamplesMs, 95),
    p99TotalLatencyMs: percentile(totalLatencySamplesMs, 99),
    receiptsProduced: expectedReceipts,
    receiptsPreserved: walStats.totalReceipts,
    receiptsDropped,
    capSaveRacesRun,
    capSaveKeysPreserved,
    slaPassed,
    slaVerdict: slaPassed
      ? `PASS — ${successRatePct}% delivery under active faults with 0 dropped WAL receipts`
      : `FAIL — ${successRatePct}% delivery, ${receiptsDropped} dropped receipts`,
    timeline,
  };
}
