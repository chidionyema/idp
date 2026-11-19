import express from 'express';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import {
  AutonomousReactivityEngine,
  ExperimentId,
} from './src/engine/autonomousReactivity';
import {
  CertificationScenarioId,
  evaluateMandatoryResilienceMatrix,
  evaluateUniversalKarmicSettlement,
  evaluateZeroGaslightAdmission,
  ExternalComponentProbeInput,
  getAllSeeingEyeAuditSnapshot,
  getGeminiSyncMission7760Status,
  getRecoveryMandateSettlementSnapshot,
  LiveGitHubInventoryRefreshResult,
  reconcileBrowserWorkforceRefinement,
  refreshAllSeeingEyeLiveInventory,
  runBoundaryEliminationProofSuite,
  validateUnsealedChangeManifest,
} from './src/engine/meridianCapabilityCalculus';
import { DagsterOrchestrator } from './src/engine/dagsterOrchestrator';
import {
  EstateGrandUnionEngine,
  evaluateEnsembleVsFrontier,
} from './src/engine/estateGrandUnion';
import {
  buildLiveEstateWorkstreamTelemetry,
  ESTATE_WORKSTREAMS,
  verifyIntakeBodyIntegrity,
} from './src/engine/estateWorkstreams';
import {
  auditInstallerShortcuts,
  buildFirstUseAuditSnapshot,
  evaluateAgentsMdRatchet,
} from './src/engine/firstUseGovernanceAudit';
import {
  buildGenTttSnapshot,
  RS_N,
  runI8088PanspermiaSimulation,
} from './src/engine/genesisSporeTtt';
import {
  buildMeridianSymphonySnapshot,
  generateSymphonySpecificationMarkdown,
} from './src/engine/meridianSymphony';
import {
  buildAuraManifoldSnapshot,
  createDefaultAuraState,
  executeAuraOmniCommand,
} from './src/engine/auraManifold';
import {
  evaluateZeroPollingGuard,
  probeSurfaceMetaTruthfully,
} from './src/engine/i8095Lockdown';
import { LegionTaskClass, ModelSupplyRegistry } from './src/engine/modelSupply';
import crypto from 'node:crypto';
import {
  CeoFocusPolicy,
  generateOttoNumenBotBlueprintTs,
  OttoNumenConciergeEngine,
  RawEstateEventKind,
} from './src/engine/ottoNumenTelegram';
import {
  classifyCodeForRegoGovernance,
  COMMERCIAL_GAP_CLOSURE_MATRIX,
  computeInvestorUnitEconomics,
  computeSynchronicityMerkleStamp,
  FounderConfigEngine,
  generateCanonicalRegoBundle,
  renderInvestorDiligenceMemoMarkdown,
} from './src/engine/founderRegoChronosPlane';
import {
  compareLegacyVsProspector2100,
  Prospector2100Engine,
} from './src/engine/prospectorResearchMumchimp';
import {
  evaluateUnseenTransferPilot,
  StandoutTrackId,
} from './src/engine/genesisAcademyEngine';
import {
  auditEpistemicClaim,
  UhnwSovereignConciergeEngine,
} from './src/engine/uhnwSovereignCharter';
import {
  MumsConciergeEngine,
  NegativeFixtureId,
  WhatsAppInboundFragment,
} from './src/engine/mumsConcierge';
import { PROVIDER_RATE_CARDS } from './src/engine/pricingCatalog';
import { RouterEngine } from './src/engine/routerCore';
import {
  runChaosBenchmark,
  runFullVerificationSuite,
  runHermesChaosStress,
} from './src/engine/resilienceSuite';
import { ChaosConfig, LaneFaultMode, RoutingStrategy } from './src/engine/types';
import {
  findCanonEquivalences,
  inspectDualModeEnglishDiff,
  readingsForText,
  renderLegacySummaryCardText,
  sanitizeHermesInput,
} from './src/engine/hermesCipherEngine';
import {
  evaluateDailyChallengeGuess,
  getDailyChallengeForDate,
  getUtcDateString,
} from './src/engine/hermesTreeCatalog';
import {
  fetchWorldResonanceSnapshot,
  validateCoordinates,
} from './src/engine/hermesWorldConnector';
import { renderCrescendoSignOffMarkdown } from './src/engine/crescendoThreeWayUnion';
import {
  buildDebugPackSnapshot,
  buildLiveCrescendoSignOff,
  buildWorkspaceSourceArchive,
  BUNDLE_RELATIVE_PATH,
  ensureGitRepoAndBundle,
  evaluateProductionGuarantees,
  getAutonomousSyncStatus,
  pushBundleToIngest,
  readSyncTelemetrySnapshot,
  registerCustomIngestTarget,
  removeCustomIngestTarget,
  renderDebugPackMarkdown,
  renderTeamHandoffRunbookMarkdown,
  runAutonomousSyncCycle,
  startAutonomousBundleSyncDaemon,
  subscribeSyncTelemetry,
  validateIngestUrl,
} from './src/engine/debugPackBuilder';
import {
  createIngestReceiverState,
  handleIngestBundleRequest,
  markSessionIdle,
} from './src/engine/ingestReceiver';
import {
  DEFAULT_EXTERNAL_SPINE_URL,
  OmniflowLiveBusEngine,
} from './src/engine/omniflowLiveBus';
import {
  BootStageId,
  PhoenixDailyBootEngine,
  PhoenixProbeMode,
} from './src/engine/phoenixDailyBoot';
import { verifyAllEstateFsmsClosedLoop } from './src/engine/estateClosedLoopFsm';
import {
  buildSystemFirstIocSnapshot,
  evaluateSystemFirstIocGate,
  InterchangeableActuatorId,
} from './src/engine/systemFirstIocReconciler';
import {
  ApplianceProfileId,
  ApplianceTurnkeyEngine,
  ForeignLocationPresetId,
  RecoveryFactorId,
  TurnkeyStageId,
} from './src/engine/applianceTurnkeySetup';
import {
  renderFleetThreeDayManifestMarkdown,
  verifyThreeDayFleetSyncCompleteness,
} from './src/engine/fleetThreeDaySyncGuard';
import {
  buildSelfExtractingClipboardCapsule,
  disconnectGitHubDeviceSession,
  getGitHubDeviceSyncSnapshot,
  PRODUCER_7760_SYNC_REF,
  pushThreeDayRepoToGitHubRemotes,
  startGitHubDeviceFlow,
  subscribeGitHubDeviceSync,
} from './src/engine/githubDirectDeviceSync';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = 3000;

const app = express();
app.use(express.json());

// Live stateful gateway & Dagster control plane instance
const routerEngine = new RouterEngine({ initialReceipts: 2382 });
const dagster = new DagsterOrchestrator();
const supplyRegistry = new ModelSupplyRegistry();
const fleetIngestState = createIngestReceiverState();
const auraState = createDefaultAuraState();
const grandUnion = new EstateGrandUnionEngine({
  router: routerEngine,
  dagster,
  supply: supplyRegistry,
  cadenceMs: 6000,
});
const ottoNumen = new OttoNumenConciergeEngine();
const prospectorEngine = new Prospector2100Engine();
const founderConfigEngine = new FounderConfigEngine();
const uhnwConcierge = new UhnwSovereignConciergeEngine();
const mumsConcierge = new MumsConciergeEngine();
const reactivityEngine = new AutonomousReactivityEngine();
const omniflowLiveBus = new OmniflowLiveBusEngine({ repoRoot: __dirname });
const phoenixBootEngine = new PhoenixDailyBootEngine({ repoRoot: __dirname });
const applianceTurnkeyEngine = new ApplianceTurnkeyEngine({ repoRoot: __dirname });
phoenixBootEngine.registerSafeHealHook(() => {
  const actions: string[] = [];
  omniflowLiveBus.sweepExpiredParticipants();
  actions.push('OMNIFLOW Bus: Swept expired leases & participant TTL heartbeats.');
  dagster.evaluateSensors(routerEngine);
  actions.push('Dagster Assets: Evaluated vault, ledger & lane matrix sensors.');
  return actions;
});
phoenixBootEngine.registerDecisionHook((decision, seal, reason) => {
  omniflowLiveBus.publishMessage({
    fromAgent: 'founder-genesis-cockpit',
    fromSurface: 'FOUNDER_COCKPIT',
    target: '@all',
    verb: decision === 'GO' ? 'STATUS' : 'BLOCKED',
    body:
      decision === 'GO'
        ? `AUTHORIZED_DAILY_OPERATIONS: ${seal?.sealId ?? 'SEAL'} (${seal?.sealKind ?? ''}) minted until ${seal?.expiresAtUtc ?? '24h'}. ${reason}`
        : `EMERGENCY_QUARANTINE_ABORT: Founder halted autonomous fleet dispatch. Reason: ${reason}`,
    correlationId: `corr-phoenix-${decision.toLowerCase()}-${Date.now()}`,
    idempotencyKey: `idem-phoenix-${decision.toLowerCase()}-${seal?.drillId ?? Date.now()}`,
    requiresClaim: false,
  });
});
const omniflowWatchdog = setInterval(() => {
  omniflowLiveBus.sweepExpiredParticipants();
}, 10_000);
omniflowWatchdog.unref?.();
let currentInvestorEconomics = computeInvestorUnitEconomics();
const diligenceRequestsLog: Array<{
  id: string;
  submittedAtUtc: string;
  investorName: string;
  firm: string;
  email: string;
  focusTrack: string;
  receiptSha256: string;
}> = [];

// Propagate initial Founder first-class config to live engines
routerEngine.setStrategy(founderConfigEngine.getConfig().routingStrategy);
ottoNumen.setFocusPolicy(founderConfigEngine.getConfig().telegramFocusPolicy);
prospectorEngine.setMinCausalConfidenceGatePct(
  founderConfigEngine.getConfig().prospectorMinCausalConfidencePct
);

grandUnion.subscribe((snap) => {
  // Harmonic H1 (1x): Intercept routine heartbeat in OTTO_NUMEN zero-send sink
  ottoNumen.ingestEvent({
    kind: 'chronos_heartbeat',
    sourceSubsystem: 'Chronos / Tempo',
    headline: `Autonomous Chronos beat #${snap.chronos.beatNumber} checkpointed`,
    metrics: { Beat: snap.chronos.beatNumber, SkewMs: snap.chronos.tempoSyncSkewMs },
    autonomousAction: 'Intercepted routine heartbeat before Telegram.',
  });

  // Harmonic H2 (2x): Trigger autonomous Prospector-2100 causal research -> Mumchimp feed
  if (snap.chronos.beatNumber % 2 === 0 && prospectorEngine.getSnapshot().autonomousActive) {
    prospectorEngine.runAutonomousCycle({ chronosBeat: snap.chronos.beatNumber });
  }
});

let currentDeadTentacles: number[] = [];
let currentHealedTentacles: number[] = [];
let currentHealingCycles = 0;
let lastTttSnapshot = buildGenTttSnapshot();
let lastPanspermiaSnapshot = runI8088PanspermiaSimulation({
  deadTentacles: currentDeadTentacles,
  healedTentacles: currentHealedTentacles,
  walReceipts: routerEngine.ledger.getStats().totalReceipts,
  authoritativeFenceToken: 46,
});

let cachedGuarantees: {
  atMs: number;
  report: ReturnType<typeof evaluateProductionGuarantees>;
} | null = null;

function getProductionGuarantees(forceRefresh = false) {
  const now = Date.now();
  if (!forceRefresh && cachedGuarantees && now - cachedGuarantees.atMs < 30_000) {
    return cachedGuarantees.report;
  }
  const report = evaluateProductionGuarantees(routerEngine, __dirname);
  cachedGuarantees = { atMs: now, report };
  return report;
}

function buildSurvivalAndTttPayload(forceGuaranteesRefresh = false) {
  const guarantees = getProductionGuarantees(forceGuaranteesRefresh);
  const walStats = routerEngine.ledger.getStats();
  const lanes = routerEngine.getLanes();
  const keys = routerEngine.keyStore.getAllKeys();
  const models = supplyRegistry.getModels();
  const estateRows = buildLiveEstateWorkstreamTelemetry({
    walReceipts: walStats.totalReceipts,
    healthyLanes: lanes.filter((l) => l.circuitState === 'CLOSED').length,
    totalLanes: lanes.length,
    certifiedModels: models.filter((m) => m.certification === 'CERTIFIED').length,
    totalModels: models.length,
    verifiedKeys: keys.filter((k) => k.lastProbeStatus === 'pass').length,
    totalKeys: keys.length,
    sporeBytes: lastPanspermiaSnapshot.sporeBytes,
    survivingTentacles: lastPanspermiaSnapshot.survivingCount,
    tttBlockedDispatch: lastTttSnapshot.dispatchState === 'BLOCKED_DISPATCH',
    all15TttFalsifiersGuarded: lastTttSnapshot.all15FalsifiersGuarded,
    guaranteesVerified: guarantees.verifiedCount,
    guaranteesTotal: guarantees.totalCount,
  });

  return {
    panspermia: lastPanspermiaSnapshot,
    ttt: lastTttSnapshot,
    estateRows,
    guarantees,
    healingCycles: currentHealingCycles,
  };
}

function buildStateSnapshot() {
  return {
    strategy: routerEngine.getStrategy(),
    vaultHydrated: routerEngine.isVaultHydrated(),
    clientKeys: routerEngine.keyStore.getAllKeys(),
    tomlSnapshot: routerEngine.keyStore.getTomlSnapshot(),
    lanes: routerEngine.getLanes(),
    walStats: routerEngine.ledger.getStats(),
    recentReceipts: routerEngine.ledger.getRecentReceipts(20),
    forensicSummary: routerEngine.forensics.getSummary(),
    dagster: {
      assets: dagster.getAssets(),
      sensors: dagster.getSensors(),
      events: dagster.getEvents(16),
    },
  };
}

let latestLiveAuditInventory: LiveGitHubInventoryRefreshResult | null = null;

app.get('/api/health', (_req, res) => {
  const auto = getAutonomousSyncStatus(__dirname);
  const audit = getAllSeeingEyeAuditSnapshot({
    autoSyncExternalAccepted: Boolean(auto.lastAcceptedBundleSha256),
    liveInventory: latestLiveAuditInventory,
  });
  res.json({
    ok: true,
    isLiveState: true,
    telemetryFreshness: 'LIVE_EXPRESS_RUNTIME',
    service: 'pennyd-dagster-gateway',
    port: PORT,
    projectionMode: 'LIVE_EXPRESS_RUNTIME',
    certificationWithheld: true,
    neverShowFalseGreen: true,
    historicalBaselineFailedRuns: audit.historicalBaselineFailedRuns,
    liveFailedWorkflowRunsCount: audit.liveFailedWorkflowRunsCount,
    inventoryFreshness: audit.inventoryFreshness,
    externalRepositoriesAudited: audit.repositoriesInspected,
    geminiSync7760: getGeminiSyncMission7760Status({
      receiverDeployedExternally: Boolean(auto.lastAcceptedBundleSha256),
      latestSourceDelivered: Boolean(auto.lastAcceptedBundleSha256),
    }),
    headSha: auto.currentHeadSha,
    bundleSha256: auto.currentBundleSha256,
    generatedAtUtc: new Date().toISOString(),
  });
});

app.get('/api/state', (_req, res) => {
  res.json(buildStateSnapshot());
});

app.post('/api/strategy', (req, res) => {
  const strategy = req.body?.strategy as RoutingStrategy;
  if (!['priority_failover', 'lowest_latency', 'weighted_cost', 'least_busy'].includes(strategy)) {
    return res.status(400).json({ error: 'Invalid routing strategy' });
  }
  routerEngine.setStrategy(strategy);
  return res.json(buildStateSnapshot());
});

app.post('/api/route', (req, res) => {
  const { clientKey, modelSlug, estimatedTokens, strategy, idempotencyKey } = req.body ?? {};
  const result = routerEngine.route({
    clientKey: typeof clientKey === 'string' ? clientKey : '',
    modelSlug: typeof modelSlug === 'string' ? modelSlug : 'deepseek-chat',
    estimatedTokens: Number(estimatedTokens) || 1024,
    strategy,
    idempotencyKey,
  });
  res.status(result.ok ? 200 : result.httpStatus).json({
    result,
    state: buildStateSnapshot(),
  });
});

app.post('/api/cap-save', (req, res) => {
  const { keyId, dailyBudgetUsd, simulateLegacyClobberBug } = req.body ?? {};
  const saveResult = routerEngine.keyStore.atomicCapSave(
    String(keyId || ''),
    Number(dailyBudgetUsd),
    { simulateLegacyClobberBug: Boolean(simulateLegacyClobberBug) }
  );
  dagster.evaluateSensors(routerEngine);
  res.status(saveResult.ok ? 200 : 400).json({
    saveResult,
    state: buildStateSnapshot(),
  });
});

app.post('/api/lanes/:id/fault', (req, res) => {
  const laneId = req.params.id;
  const faultMode = (req.body?.faultMode ?? 'healthy') as LaneFaultMode;
  const updated = routerEngine.setLaneFault(laneId, faultMode);
  if (!updated) {
    return res.status(404).json({ error: `Unknown lane ${laneId}` });
  }
  return res.json({
    lane: updated,
    state: buildStateSnapshot(),
  });
});

app.post('/api/lanes/:id/topup', (req, res) => {
  const laneId = req.params.id;
  const amountUsd = Number(req.body?.amountUsd ?? 50);
  if (!Number.isFinite(amountUsd) || amountUsd <= 0) {
    return res.status(400).json({ error: 'Top-up amount must be positive' });
  }
  const updated = routerEngine.topUpLaneCredits(laneId, amountUsd);
  if (!updated) {
    return res.status(404).json({ error: `Unknown lane ${laneId}` });
  }
  const sensorEval = dagster.evaluateSensors(routerEngine);
  return res.json({
    lane: updated,
    sensorEval,
    state: buildStateSnapshot(),
  });
});

app.post('/api/dagster/evaluate', (_req, res) => {
  const evaluation = dagster.evaluateSensors(routerEngine);
  res.json({
    evaluation,
    state: buildStateSnapshot(),
  });
});

app.post('/api/dagster/materialize', (req, res) => {
  const assetKey = String(req.body?.assetKey || '');
  const asset = dagster.materializeAsset(routerEngine, assetKey);
  if (!asset) {
    return res.status(404).json({ error: `Unknown asset ${assetKey}` });
  }
  return res.json({
    asset,
    state: buildStateSnapshot(),
  });
});

app.post('/api/dagster/restart', (req, res) => {
  const mode = req.body?.mode === 'legacy_launchd' ? 'legacy_launchd' : 'dagster_durable';
  const report = dagster.simulateWorkerRestart(routerEngine, mode);
  res.json({
    report,
    state: buildStateSnapshot(),
  });
});

app.post('/api/tests/run', (_req, res) => {
  const report = runFullVerificationSuite();
  res.json(report);
});

app.post('/api/chaos/run', (req, res) => {
  const body = (req.body ?? {}) as Partial<ChaosConfig>;
  const config: ChaosConfig = {
    requestCount: Number(body.requestCount) || 1500,
    concurrency: Number(body.concurrency) || 50,
    strategy: body.strategy || routerEngine.getStrategy(),
    injectDeepSeek402: body.injectDeepSeek402 ?? true,
    injectWorkerCrash: body.injectWorkerCrash ?? true,
    injectCapSaveRace: body.injectCapSaveRace ?? true,
    injectMultiLane503: body.injectMultiLane503 ?? true,
    injectLatencySpike: body.injectLatencySpike ?? true,
  };
  const report = runChaosBenchmark(config);
  res.json(report);
});

app.get('/api/packets', (req, res) => {
  const limit = Math.min(150, Math.max(10, Number(req.query.limit) || 60));
  res.json({
    packets: routerEngine.forensics.getPackets(limit),
    summary: routerEngine.forensics.getSummary(),
    rateCards: Object.values(PROVIDER_RATE_CARDS),
  });
});

app.post('/api/packets/burst', (req, res) => {
  const count = Math.min(30, Math.max(1, Number(req.body?.count) || 8));
  const strategies: RoutingStrategy[] = ['priority_failover', 'lowest_latency', 'weighted_cost', 'least_busy'];
  const missions = [
    { missionId: 'MSN-ESTATE-409', ownerId: 'founder@meridian.estate', adapter: 'OpenCode V2' as const },
    { missionId: 'MSN-DAGSTER-212', ownerId: 'fleet-dagster@meridian.estate', adapter: 'OpenCode V2' as const },
    { missionId: 'MSN-OPTIMUS-088', ownerId: 'optimus-lab@meridian.estate', adapter: 'CI Runner' as const },
  ];
  const models = ['deepseek-chat', 'claude-sonnet-4', 'gemini-2.5-flash', 'gpt-4o-mini'];

  for (let i = 0; i < count; i++) {
    const msn = missions[i % missions.length];
    routerEngine.route({
      clientKey: i % 4 === 0 ? 'pk_live_canary_probe_71c9' : 'pk_live_opencode_primary_94a2',
      modelSlug: models[i % models.length],
      estimatedTokens: 900 + ((i * 317) % 2400),
      cachedInputTokens: 600 + ((i * 211) % 1800),
      outputTokens: 280 + ((i * 97) % 520),
      reasoningTokens: i % 3 === 0 ? 180 : 0,
      contextTrimSavedTokens: 340 + ((i * 83) % 500),
      missionId: msn.missionId,
      ownerId: msn.ownerId,
      sessionId: `SES-${420 + (i % 4)}`,
      adapter: msn.adapter,
      strategy: strategies[i % strategies.length],
    });
  }

  res.json({
    packets: routerEngine.forensics.getPackets(60),
    summary: routerEngine.forensics.getSummary(),
    rateCards: Object.values(PROVIDER_RATE_CARDS),
    state: buildStateSnapshot(),
  });
});

app.get('/api/meridian', (_req, res) => {
  res.json({
    meridian: routerEngine.forensics.getMeridianSnapshot(),
    rateCards: Object.values(PROVIDER_RATE_CARDS),
  });
});

app.post('/api/meridian/baseline', (req, res) => {
  const modelSlug = String(req.body?.baselineModelSlug || 'claude-sonnet-4');
  if (!PROVIDER_RATE_CARDS[modelSlug]) {
    return res.status(400).json({ error: `Unknown baseline model ${modelSlug}` });
  }
  routerEngine.forensics.setBaselineModelSlug(modelSlug);
  return res.json({
    packets: routerEngine.forensics.getPackets(60),
    summary: routerEngine.forensics.getSummary(),
    meridian: routerEngine.forensics.getMeridianSnapshot(),
    rateCards: Object.values(PROVIDER_RATE_CARDS),
    state: buildStateSnapshot(),
  });
});

function buildSupplySnapshot() {
  return {
    discoveryCycle: supplyRegistry.getDiscoveryCycleCount(),
    models: supplyRegistry.getModels(),
    recoveryPackage: supplyRegistry.getRecoveryPackage(),
    routingMatrix: supplyRegistry.getBattalionRoutingMatrix(),
    workstreams: ESTATE_WORKSTREAMS,
  };
}

app.post('/api/supply/verify-intake', (req, res) => {
  const { verifierPublicKeyHex, claimedBodySha256, receivedBodyBytes, storedCopyBytes } =
    req.body ?? {};
  const result = verifyIntakeBodyIntegrity({
    verifierPublicKeyHex:
      verifierPublicKeyHex !== undefined ? String(verifierPublicKeyHex) : undefined,
    claimedBodySha256: String(claimedBodySha256 || ''),
    receivedBodyBytes: String(receivedBodyBytes || ''),
    storedCopyBytes: String(storedCopyBytes || ''),
  });
  res.status(result.ok ? 200 : 401).json(result);
});

app.get('/api/supply', (_req, res) => {
  res.json(buildSupplySnapshot());
});

app.post('/api/supply/discover', (_req, res) => {
  const tick = supplyRegistry.discoverSupplyTick();
  res.json({
    tick,
    ...buildSupplySnapshot(),
  });
});

app.post('/api/supply/certify', (_req, res) => {
  const certificationProbe = supplyRegistry.runIndependentCertification();
  res.json({
    certificationProbe,
    ...buildSupplySnapshot(),
  });
});

app.post('/api/supply/feedback', (req, res) => {
  const { modelId, verified, latencyMs, costUsd } = req.body ?? {};
  const updated = supplyRegistry.recordOptimusOutcome({
    modelId: String(modelId || ''),
    verified: Boolean(verified),
    latencyMs: Number(latencyMs) || 140,
    costUsd: costUsd !== undefined ? Number(costUsd) : undefined,
  });
  if (!updated) {
    return res.status(404).json({ error: `Unknown model ${modelId}` });
  }
  return res.json({
    updated,
    ...buildSupplySnapshot(),
  });
});

app.post('/api/supply/quota', (req, res) => {
  const { modelId, quotaRemainingPct, geoAllowed } = req.body ?? {};
  const updated = supplyRegistry.setModelQuotaAndPolicy(String(modelId || ''), {
    quotaRemainingPct: quotaRemainingPct !== undefined ? Number(quotaRemainingPct) : undefined,
    geoAllowed: geoAllowed !== undefined ? Boolean(geoAllowed) : undefined,
  });
  if (!updated) {
    return res.status(404).json({ error: `Unknown model ${modelId}` });
  }
  return res.json({
    updated,
    ...buildSupplySnapshot(),
  });
});

app.post('/api/supply/admit', (req, res) => {
  const body = req.body ?? {};
  const decision = supplyRegistry.admitTask({
    taskClass: (body.taskClass || 'routine_coding') as LegionTaskClass,
    requiresZeroRetention: Boolean(body.requiresZeroRetention),
    estimatedTokens: Number(body.estimatedTokens) || 2000,
    regionCode: String(body.regionCode || 'us-west'),
  });
  res.json({
    decision,
    ...buildSupplySnapshot(),
  });
});

app.post('/api/supply/benchmark', (req, res) => {
  const workloadTasks = Number(req.body?.workloadTasks) || 200;
  const benchmark = supplyRegistry.runSmallVsFrontierBenchmark(workloadTasks);
  res.json({
    benchmark,
    ...buildSupplySnapshot(),
  });
});

app.get('/api/symphony', (_req, res) => {
  res.json(
    buildMeridianSymphonySnapshot({
      router: routerEngine,
      dagster,
      supply: supplyRegistry,
    })
  );
});

app.post('/api/symphony/action', (req, res) => {
  const actionId = String(req.body?.actionId || '');
  let actionOutcome = 'Executed authorized action';

  if (actionId === 'evaluate_dagster_sensors') {
    const evalRes = dagster.evaluateSensors(routerEngine);
    actionOutcome = `Evaluated ${dagster.getSensors().length} Dagster sensors (${evalRes.triggeredSensors.length} triggered)`;
  } else if (actionId === 'run_supply_sweep') {
    const tick = supplyRegistry.discoverSupplyTick();
    actionOutcome = `Completed discovery sweep #${tick.cycle} (${tick.discoveredCount} models scanned)`;
  } else if (actionId === 'run_capability_cert') {
    const cert = supplyRegistry.runIndependentCertification();
    actionOutcome = `Certified ${cert.certifiedCount}/${cert.testedModels} lanes (quarantined: ${cert.quarantinedCount})`;
  } else if (actionId === 'checkpoint_wal') {
    const cp = routerEngine.ledger.checkpoint();
    actionOutcome = `Checkpointed WAL ledger (${cp.totalWalCount} total receipts, ${cp.flushedCount} flushed)`;
  } else if (actionId === 'run_i8095_lockdown_sweep') {
    const snap = buildMeridianSymphonySnapshot({
      router: routerEngine,
      dagster,
      supply: supplyRegistry,
    });
    actionOutcome = `I-8095 Class-A sweep complete: ${snap.i8095.counts.bddPassed}/4 BDD scenarios PASS, ${snap.i8095.counts.enforcedOrExplicit}/17 enforced or isolated locally (${snap.i8095.counts.externalRepoPending} external repo targets flagged)`;
  } else {
    return res.status(400).json({ error: `Unauthorized or unknown actionId: ${actionId}` });
  }

  return res.json({
    actionOutcome,
    symphony: buildMeridianSymphonySnapshot({
      router: routerEngine,
      dagster,
      supply: supplyRegistry,
    }),
    state: buildStateSnapshot(),
  });
});

app.get('/api/surface/meta', (_req, res) => {
  res.json(probeSurfaceMetaTruthfully(false));
});

app.post('/api/i8095/test-zero-poll', (req, res) => {
  const source = typeof req.body?.source === 'string' ? req.body.source : '';
  res.json(evaluateZeroPollingGuard(source));
});

app.get('/api/symphony/spec', (_req, res) => {
  const snap = buildMeridianSymphonySnapshot({
    router: routerEngine,
    dagster,
    supply: supplyRegistry,
  });
  const md = generateSymphonySpecificationMarkdown(snap);
  res.setHeader('Content-Type', 'text/markdown; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename="meridian-symphony-final-spec.md"');
  res.send(md);
});

app.get('/api/aura/manifold', (_req, res) => {
  res.json(
    buildAuraManifoldSnapshot({
      router: routerEngine,
      dagster,
      supply: supplyRegistry,
      auraState,
    })
  );
});

app.get('/api/aura/frames.bin', (_req, res) => {
  const snap = buildAuraManifoldSnapshot({
    router: routerEngine,
    dagster,
    supply: supplyRegistry,
    auraState,
  });
  const raw = Buffer.from(snap.framesBase64, 'base64');
  res.setHeader('Content-Type', 'application/octet-stream');
  res.setHeader('X-Genesis-Frame-Bytes', '64');
  res.setHeader('X-Genesis-Frame-Count', String(snap.frameCount));
  res.send(raw);
});

app.post('/api/aura/command', (req, res) => {
  const command = typeof req.body?.command === 'string' ? req.body.command : '';
  const outcome = executeAuraOmniCommand(command, auraState);
  res.status(outcome.ok ? 200 : 400).json({
    outcome,
    manifold: buildAuraManifoldSnapshot({
      router: routerEngine,
      dagster,
      supply: supplyRegistry,
      auraState,
    }),
  });
});

// ---------------------------------------------------------------------------
// HERMES — THE LIVING TREE (Hardened Endpoints, Chaos, Debug Pack & Git Bundle)
// ---------------------------------------------------------------------------
const MAX_IDEMPOTENCY_ENTRIES = 512;
const hermesIdempotencyCache = new Map<
  string,
  { guess: string; evaluation: ReturnType<typeof evaluateDailyChallengeGuess> }
>();

function storeIdempotencyBounded(
  key: string,
  guess: string,
  evaluation: ReturnType<typeof evaluateDailyChallengeGuess>
) {
  while (hermesIdempotencyCache.size >= MAX_IDEMPOTENCY_ENTRIES) {
    const oldest = hermesIdempotencyCache.keys().next().value;
    if (oldest === undefined) break;
    hermesIdempotencyCache.delete(oldest);
  }
  hermesIdempotencyCache.set(key, { guess, evaluation });
}

app.get('/api/hermes/world', async (req, res) => {
  const placeId = typeof req.query.placeId === 'string' ? req.query.placeId : 'london';
  const hasLat = typeof req.query.lat === 'string' && req.query.lat.trim() !== '';
  const hasLon = typeof req.query.lon === 'string' && req.query.lon.trim() !== '';
  const latNum = hasLat ? Number(req.query.lat) : undefined;
  const lonNum = hasLon ? Number(req.query.lon) : undefined;

  if (hasLat !== hasLon) {
    return res.status(400).json({ error: 'Provide both lat and lon coordinates together' });
  }
  const coordCheck = validateCoordinates(latNum, lonNum);
  if (!coordCheck.ok) {
    return res.status(400).json({ error: coordCheck.error });
  }

  const forceOffline = req.query.forceOffline === 'true';
  const snapshot = await fetchWorldResonanceSnapshot({
    placeId,
    lat: latNum,
    lon: lonNum,
    forceOffline,
  });
  return res.json(snapshot);
});

app.post('/api/hermes/calculate', (req, res) => {
  const raw = typeof req.body?.text === 'string' ? req.body.text : '';
  if (raw.length > 10_000) {
    return res.status(413).json({ error: 'Payload exceeds 10,000-char ceiling' });
  }
  const sanitized = sanitizeHermesInput(raw);
  if (sanitized.maxCharsExceeded) {
    return res.status(400).json({ error: 'Input exceeds 2,400-character sanctum limit' });
  }
  const includeLegacyLatin = req.body?.includeLegacyLatin !== false;
  const readings = readingsForText(sanitized.cleaned, { includeLegacyLatin });
  const primaryTotal = readings[0]?.total ?? 0;
  const equivalences = findCanonEquivalences(primaryTotal, sanitized.cleaned.trim());
  const dualModeDiff = inspectDualModeEnglishDiff(sanitized.cleaned);
  return res.json({
    text: sanitized.cleaned,
    strippedControlOrBidi: sanitized.strippedControlOrBidi,
    readings,
    equivalences,
    dualModeDiff,
    legacySummaryCard: renderLegacySummaryCardText(sanitized.cleaned),
  });
});

app.post('/api/hermes/puzzle/check', (req, res) => {
  const rawGuess = typeof req.body?.guess === 'string' ? req.body.guess.trim() : '';
  const sanitized = sanitizeHermesInput(rawGuess, 256);
  const guess = sanitized.cleaned.trim();
  const idempotencyKey =
    typeof req.body?.idempotencyKey === 'string' ? req.body.idempotencyKey.trim() : '';

  if (!guess || sanitized.maxCharsExceeded) {
    return res.status(400).json({ error: 'Provide a word or phrase up to 256 characters' });
  }

  if (idempotencyKey && hermesIdempotencyCache.has(idempotencyKey)) {
    const existing = hermesIdempotencyCache.get(idempotencyKey)!;
    if (existing.guess !== guess) {
      return res.status(409).json({
        error: 'idempotency_key_conflict',
        message: 'Idempotency key already bound to a different guess',
      });
    }
    return res.json({
      ...existing.evaluation,
      idempotentReplay: true,
      challenge: getDailyChallengeForDate(existing.evaluation.utcDate),
    });
  }

  const utcDate = getUtcDateString();
  const customTarget =
    typeof req.body?.customTarget === 'number' && req.body.customTarget > 0
      ? Math.round(req.body.customTarget)
      : undefined;
  const evaluation = evaluateDailyChallengeGuess(guess, utcDate, customTarget);
  if (idempotencyKey) {
    storeIdempotencyBounded(idempotencyKey, guess, evaluation);
  }
  const challenge = getDailyChallengeForDate(utcDate);
  return res.json({
    ...evaluation,
    idempotentReplay: false,
    challenge,
  });
});

app.post('/api/hermes/export-summary', (req, res) => {
  const raw = typeof req.body?.text === 'string' ? req.body.text : '';
  const cleaned = sanitizeHermesInput(raw).cleaned;
  const summaryMarkdown = renderLegacySummaryCardText(cleaned);
  const readings = readingsForText(cleaned, { includeLegacyLatin: true });
  return res.json({
    // Deliberately omits coordinates / location telemetry to protect visitor privacy
    schemaVersion: 'hermes-sanitized-share-v1',
    locationIncluded: false,
    text: cleaned,
    readings: readings.map((r) => ({
      cipherId: r.cipherId,
      system: r.system,
      total: r.total,
      treeRoot: r.treeRoot,
      legacyMasterRoot: r.legacyMasterRoot,
      reproducibilityHash: r.reproducibilityHash,
    })),
    summaryMarkdown,
  });
});

app.post('/api/hermes/chaos', (req, res) => {
  const iterations = Math.min(5000, Math.max(100, Number(req.body?.iterations) || 1000));
  res.json(runHermesChaosStress(iterations));
});

app.get('/api/debug-pack', async (req, res) => {
  const pack = await buildDebugPackSnapshot(routerEngine, __dirname);
  const format = typeof req.query.format === 'string' ? req.query.format : 'json';
  if (format === 'markdown') {
    const md = renderDebugPackMarkdown(pack);
    res.setHeader('Content-Type', 'text/markdown; charset=utf-8');
    res.setHeader(
      'Content-Disposition',
      'attachment; filename="meridian-hermes-debug-pack.md"'
    );
    return res.send(md);
  }
  res.setHeader(
    'Content-Disposition',
    'attachment; filename="meridian-hermes-debug-pack.json"'
  );
  return res.json(pack);
});

app.get(['/api/export/bundle', '/api/export/git-bundle'], (_req, res) => {
  const ensured = ensureGitRepoAndBundle(__dirname);
  const bundleAbs = ensured.bundleAbs || path.join(__dirname, BUNDLE_RELATIVE_PATH);
  if (!fs.existsSync(bundleAbs)) {
    return res.status(500).json({
      error: 'bundle_generation_failed',
      detail: ensured.error ?? 'Unknown error',
      expectedPath: BUNDLE_RELATIVE_PATH,
    });
  }
  const sync = readSyncTelemetrySnapshot(__dirname);
  if (sync.bundleSha256) {
    res.setHeader('X-Bundle-Sha256', sync.bundleSha256);
  }
  res.setHeader('X-Bundle-Head-Sha', sync.headSha);
  res.setHeader('Content-Type', 'application/octet-stream');
  res.setHeader(
    'Content-Disposition',
    'attachment; filename="meridian-hermes-today.bundle"'
  );
  return res.sendFile(bundleAbs);
});

app.get(['/api/export/all-today', '/api/export/all-3days', '/api/export/workspace.tar.gz'], (req, res) => {
  const archive = buildWorkspaceSourceArchive(__dirname);
  if (!archive.ok) {
    return res.status(500).json({
      ok: false,
      error: archive.error ?? 'Unable to generate complete workspace archive',
    });
  }
  if (req.query.format === 'json') {
    return res.json({
      ok: true,
      filename: archive.filename,
      fileCount: archive.fileCount,
      files: archive.files,
      bytes: archive.bytes,
      sha256: archive.sha256,
      headSha: archive.headSha,
      bundleSha256: archive.bundleSha256,
      bundleBytes: archive.bundleBytes,
      ...(req.query.includeBase64 === '1'
        ? { base64: archive.buffer.toString('base64') }
        : {}),
    });
  }
  const downloadFilename = req.path.includes('all-3days')
    ? 'meridian-complete-3days-2026-11-17.tar.gz'
    : archive.filename;
  res.setHeader('Content-Type', 'application/gzip');
  res.setHeader('X-Archive-Sha256', archive.sha256);
  res.setHeader('X-Git-Head-Sha', archive.headSha);
  res.setHeader(
    'Content-Disposition',
    `attachment; filename="${downloadFilename}"`
  );
  return res.send(archive.buffer);
});

const CONCIERGE_PACK_FILES = [
  'FLEET_3DAY_CANONICAL_MANIFEST.md',
  'MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md',
  'TEAM_HANDOFF_TODAY.md',
  'ROUTER.md',
  'GENESIS_SPORE.dna',
  '.github/workflows/fleet-3day-sync-verify.yml',
  '.github/workflows/phoenix-daily-boot.yml',
  'src/engine/fleetThreeDaySyncGuard.ts',
  'src/engine/applianceTurnkeySetup.ts',
  'src/components/ApplianceSetupDrConsole.tsx',
  'src/engine/systemFirstIocReconciler.ts',
  'src/engine/phoenixDailyBoot.ts',
  'src/engine/estateClosedLoopFsm.ts',
  'src/engine/omniflowLiveBus.ts',
  'src/engine/crescendoThreeWayUnion.ts',
  'src/engine/codexCrescendo.ts',
  'src/components/CodexCrescendoPanel.tsx',
  'src/engine/mumsConcierge.ts',
  'src/components/MumConciergeHub.tsx',
  'src/engine/autonomousReactivity.ts',
  'src/engine/meridianCapabilityCalculus.ts',
  'src/components/FounderAutonomousReactivity.tsx',
  'src/components/FounderMccConvergencePanel.tsx',
  'src/components/TeamHandoffExportPanel.tsx',
  'src/components/GlobalGetWorkModal.tsx',
  'src/engine/genesisAcademyEngine.ts',
  'src/components/GenesisAcademy.tsx',
  'src/engine/uhnwSovereignCharter.ts',
  'src/engine/estateGrandUnion.ts',
  'src/engine/founderRegoChronosPlane.ts',
  'src/engine/resilienceSuite.ts',
  'src/engine/debugPackBuilder.ts',
  'src/engine/router.test.ts',
  'src/engine/httpIntegration.test.ts',
  'src/types/api.ts',
  'src/components/SidebarNav.tsx',
  'src/components/SovereignConciergePalette.tsx',
  'src/components/FalsifiersSuite.tsx',
  'src/App.tsx',
  'server.ts',
  'AGENTS.md',
  'GEMINI.md',
] as const;

app.get('/api/export/concierge-pack', (req, res) => {
  try {
    const existing = CONCIERGE_PACK_FILES.filter((rel) =>
      fs.existsSync(path.join(__dirname, rel))
    );
    const tgzBuffer = execFileSync('tar', ['-czf', '-', ...existing], {
      cwd: __dirname,
      maxBuffer: 16 * 1024 * 1024,
    });
    const sha256 = crypto.createHash('sha256').update(tgzBuffer).digest('hex');
    if (req.query.format === 'json') {
      return res.json({
        ok: true,
        filename: 'meridian-concierge-mcc-pack.tar.gz',
        fileCount: existing.length,
        files: existing,
        bytes: tgzBuffer.length,
        sha256,
        base64: tgzBuffer.toString('base64'),
      });
    }
    res.setHeader('Content-Type', 'application/gzip');
    res.setHeader('X-Pack-Sha256', sha256);
    res.setHeader(
      'Content-Disposition',
      'attachment; filename="meridian-concierge-mcc-pack.tar.gz"'
    );
    return res.send(tgzBuffer);
  } catch (err) {
    return res.status(500).json({
      ok: false,
      error: err instanceof Error ? err.message : 'Unable to build concierge source pack',
    });
  }
});

app.post('/api/export/push-bundle', async (req, res) => {
  const ingestUrl =
    typeof req.body?.ingestUrl === 'string' ? req.body.ingestUrl : undefined;
  const method = req.body?.method === 'PUT' ? 'PUT' : 'POST';

  if (method === 'PUT' && ingestUrl) {
    const checked = validateIngestUrl(ingestUrl);
    if (!checked.ok) {
      return res.status(400).json({ ok: false, pushed: false, error: checked.error });
    }
    const ensured = ensureGitRepoAndBundle(__dirname);
    const bundleAbs = ensured.bundleAbs || path.join(__dirname, BUNDLE_RELATIVE_PATH);
    if (!fs.existsSync(bundleAbs)) {
      return res.status(500).json({ ok: false, pushed: false, error: 'Bundle missing on disk' });
    }
    const payload = fs.readFileSync(bundleAbs);
    const bundleSha256 = crypto.createHash('sha256').update(payload).digest('hex');
    const started = Date.now();
    try {
      const upstream = await fetch(checked.url.toString(), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/octet-stream',
          'X-Bundle-Sha256': bundleSha256,
        },
        body: payload,
      });
      return res.status(200).json({
        ok: upstream.ok,
        pushed: upstream.ok,
        method: 'PUT',
        ingestUrlRedacted: `${checked.url.origin}${checked.url.pathname}`,
        httpStatus: upstream.status,
        bundleBytes: payload.length,
        bundleSha256,
        durationMs: Date.now() - started,
      });
    } catch (err) {
      return res.status(200).json({
        ok: false,
        pushed: false,
        method: 'PUT',
        ingestUrlRedacted: `${checked.url.origin}${checked.url.pathname}`,
        httpStatus: null,
        bundleBytes: payload.length,
        bundleSha256,
        durationMs: Date.now() - started,
        error: err instanceof Error ? err.message : 'PUT upload failed',
      });
    }
  }

  if (ingestUrl && ingestUrl.trim()) {
    registerCustomIngestTarget(__dirname, ingestUrl, method);
  }
  const result = await pushBundleToIngest(__dirname, {
    ingestUrl,
    trigger: 'manual_api',
  });
  const badUrlInput =
    ingestUrl !== undefined &&
    (!result.ingestConfigured ||
      result.attempts.some(
        (a) =>
          a.error?.includes('Malformed') ||
          a.error?.includes('https://') ||
          a.error?.includes('blocked')
      ));
  return res.status(badUrlInput ? 400 : 200).json(result);
});

app.get('/api/export/github-device/status', (_req, res) => {
  return res.json({
    ok: true,
    githubDevice: getGitHubDeviceSyncSnapshot(),
  });
});

app.post('/api/export/github-device/start', async (_req, res) => {
  // Request 8-character GitHub Device Code immediately (~180ms); ensureBundleFn runs right before push
  const githubDevice = await startGitHubDeviceFlow(__dirname, {
    ensureBundleFn: ensureGitRepoAndBundle,
  });
  return res.json({
    ok: githubDevice.phase !== 'PUSH_PARTIAL_OR_FAILED',
    githubDevice,
  });
});

app.post('/api/export/github-device/push-now', async (_req, res) => {
  ensureGitRepoAndBundle(__dirname);
  const githubDevice = await pushThreeDayRepoToGitHubRemotes(__dirname, {
    ensureBundleFn: ensureGitRepoAndBundle,
  });
  return res.json({
    ok: githubDevice.anyTargetRepoPushed,
    githubDevice,
  });
});

app.post('/api/export/github-device/disconnect', (_req, res) => {
  const githubDevice = disconnectGitHubDeviceSession();
  return res.json({
    ok: true,
    githubDevice,
  });
});

app.get('/api/export/clipboard-capsule', (req, res) => {
  if (!fs.existsSync(path.join(__dirname, '.git', 'HEAD'))) {
    ensureGitRepoAndBundle(__dirname);
  }
  const mode = req.query.mode === 'full' ? 'full' : 'compact';
  const capsule = buildSelfExtractingClipboardCapsule(__dirname, mode);
  res.setHeader('Cache-Control', 'no-store');
  return res.json(capsule);
});

app.get('/api/export/auto-sync', (_req, res) => {
  ensureGitRepoAndBundle(__dirname);
  const autoStatus = getAutonomousSyncStatus(__dirname);
  const archive = buildWorkspaceSourceArchive(__dirname);
  const sync = readSyncTelemetrySnapshot(__dirname);
  const githubDevice = getGitHubDeviceSyncSnapshot();
  const externalConfirmed = Boolean(
    githubDevice.anyTargetRepoPushed ||
      (autoStatus.lastAcceptedBundleSha256 &&
        autoStatus.lastAcceptedBundleSha256 === autoStatus.currentBundleSha256)
  );
  const threeDay = verifyThreeDayFleetSyncCompleteness(__dirname, {
    externalGitHubPushConfirmed: externalConfirmed,
  });
  res.json({
    ok: true,
    ...autoStatus,
    workspaceArchiveBytes: archive.bytes,
    workspaceArchiveFileCount: archive.fileCount,
    lastReason: sync.lastEvent?.reason ?? null,
    githubDevice,
    threeDaySync: {
      allThreeDaysSealed: threeDay.allThreeDaysSealed,
      verifiedWorkstreamsCount: threeDay.dayBreakdown.verifiedWorkstreamsCount,
      totalWorkstreamsCount: threeDay.dayBreakdown.totalWorkstreamsCount,
      untrackedSourceFilesCount: threeDay.untrackedSourceFiles.length,
      bundleMatchesHead: threeDay.bundleMatchesHead,
      threeDayMerkleRootSha256: threeDay.threeDayMerkleRootSha256,
      githubCiWorkflowPresent: threeDay.githubCiWorkflowPresent,
      externalGitHubPushState: threeDay.externalGitHubPushState,
    },
  });
});

app.post('/api/export/register-target', async (req, res) => {
  const url = typeof req.body?.url === 'string' ? req.body.url : '';
  const method = req.body?.method === 'PUT' ? 'PUT' : 'POST';
  const saved = registerCustomIngestTarget(__dirname, url, method);
  if (!saved.ok) {
    return res.status(400).json({ ok: false, error: saved.error });
  }
  const cycle = await runAutonomousSyncCycle(__dirname, {
    forcePush: true,
    trigger: 'manual_api',
  });
  return res.json({
    ok: true,
    target: saved.target,
    targets: saved.targets,
    pushed: cycle.pushed,
    httpStatus: cycle.pushResult?.httpStatus ?? (cycle.pushed ? 200 : null),
    reason: cycle.pushResult?.reason ?? null,
    headSha: cycle.headSha,
    bundleSha256: cycle.bundleSha256,
  });
});

app.delete('/api/export/register-target', (req, res) => {
  const url = typeof req.body?.url === 'string' ? req.body.url : '';
  const targets = removeCustomIngestTarget(__dirname, url);
  return res.json({ ok: true, targets });
});

app.get('/api/export/manifest', (_req, res) => {
  ensureGitRepoAndBundle(__dirname);
  const archive = buildWorkspaceSourceArchive(__dirname);
  const sync = readSyncTelemetrySnapshot(__dirname);
  const crescendoSignOff = buildLiveCrescendoSignOff(__dirname);
  const githubDevice = getGitHubDeviceSyncSnapshot();
  const threeDay = verifyThreeDayFleetSyncCompleteness(__dirname, {
    externalGitHubPushConfirmed: Boolean(
      githubDevice.anyTargetRepoPushed || (sync.successfulPushes > 0 && sync.events[0]?.pushed)
    ),
  });
  res.json({
    ok: sync.bundleAvailable && archive.ok && threeDay.allThreeDaysSealed,
    schemaVersion: 'meridian-fleet-manifest-v1',
    generatedAtUtc: new Date().toISOString(),
    sessionId: sync.sessionId,
    headSha: sync.headSha,
    workingTreeClean: sync.workingTreeClean,
    bundlePathRelative: sync.bundlePathRelative,
    bundleBytes: sync.bundleBytes,
    bundleSha256: sync.bundleSha256,
    workspaceArchiveFilename: archive.filename,
    workspaceArchiveFileCount: archive.fileCount,
    workspaceArchiveFiles: archive.files,
    workspaceArchiveBytes: archive.bytes,
    workspaceArchiveSha256: archive.sha256,
    crescendoRoute: crescendoSignOff.declaredEndUserRoute,
    crescendoSignOff: crescendoSignOff.specDocumentPath,
    crescendoGoLiveDecision: crescendoSignOff.overallDecision,
    githubDevice,
    threeDaySync: {
      allThreeDaysSealed: threeDay.allThreeDaysSealed,
      windowLabel: threeDay.windowLabel,
      verifiedWorkstreamsCount: threeDay.dayBreakdown.verifiedWorkstreamsCount,
      totalWorkstreamsCount: threeDay.dayBreakdown.totalWorkstreamsCount,
      untrackedSourceFilesCount: threeDay.untrackedSourceFiles.length,
      bundleMatchesHead: threeDay.bundleMatchesHead,
      threeDayMerkleRootSha256: threeDay.threeDayMerkleRootSha256,
      githubCiWorkflowPresent: threeDay.githubCiWorkflowPresent,
      externalGitHubPushState: threeDay.externalGitHubPushState,
    },
    proxyInterstitialNote:
      'Google AI Studio gates ais-dev and ais-pre URLs behind a browser-cookie interstitial for unauthenticated headless curl. Use 1-Click GitHub Device Flow Push, 1-Click Terminal Clipboard Capsule, or fetch-blob browser download.',
    targetRef: 'refs/heads/aistudio/meridian-hermes-live',
    producer7760Ref: PRODUCER_7760_SYNC_REF,
    targetRemotes: ['chidionyema/argon-sync', 'chidionyema/gemini-sync'],
    paths: {
      bundleDownload: '/api/export/bundle',
      gitBundleAlias: '/api/export/git-bundle',
      allTodayArchive: '/api/export/all-today',
      allThreeDaysArchive: '/api/export/all-3days',
      workspaceTarGzAlias: '/api/export/workspace.tar.gz',
      conciergeMccPack: '/api/export/concierge-pack',
      teamHandoff: '/api/export/team-handoff',
      fleetThreeDayManifestJson: '/api/export/fleet-3day-manifest',
      fleetThreeDayManifestMarkdown: '/FLEET_3DAY_CANONICAL_MANIFEST.md',
      crescendoSignOffMarkdown: '/MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md',
      crescendoSignOffExportAlias: '/api/export/crescendo-signoff',
      crescendoSignOffJson: '/api/crescendo/signoff',
      crescendoEndUserRoute: '/crescendo',
      debugPack: '/api/debug-pack',
      telemetry: '/api/sync/telemetry',
      telemetryStream: '/api/sync/stream',
      ingestBundle: '/api/ingest/bundle',
      ingestSessions: '/api/ingest/sessions',
    },
  });
});

app.get('/api/export/fleet-3day-manifest', (_req, res) => {
  ensureGitRepoAndBundle(__dirname);
  const sync = readSyncTelemetrySnapshot(__dirname);
  const report = verifyThreeDayFleetSyncCompleteness(__dirname, {
    externalGitHubPushConfirmed: Boolean(sync.successfulPushes > 0 && sync.events[0]?.pushed),
  });
  return res.json({
    ok: report.allThreeDaysSealed,
    isLiveState: true,
    telemetryFreshness: 'LIVE_EXPRESS_RUNTIME',
    report,
  });
});

app.get(
  ['/FLEET_3DAY_CANONICAL_MANIFEST.md', '/api/export/fleet-3day-manifest.md'],
  (req, res) => {
    ensureGitRepoAndBundle(__dirname);
    const report = verifyThreeDayFleetSyncCompleteness(__dirname);
    const rootAbs = path.join(__dirname, 'FLEET_3DAY_CANONICAL_MANIFEST.md');
    const md =
      req.query.dynamic === '1' || !fs.existsSync(rootAbs)
        ? renderFleetThreeDayManifestMarkdown(report)
        : fs.readFileSync(rootAbs, 'utf8');
    res.setHeader('Content-Type', 'text/markdown; charset=utf-8');
    res.setHeader('X-Three-Day-Sealed', String(report.allThreeDaysSealed));
    res.setHeader('X-Git-Head-Sha', report.headSha);
    if (report.bundleSha256) {
      res.setHeader('X-Bundle-Sha256', report.bundleSha256);
    }
    res.setHeader(
      'Content-Disposition',
      req.path.endsWith('.md') && req.query.download !== '1'
        ? 'inline; filename="FLEET_3DAY_CANONICAL_MANIFEST.md"'
        : 'attachment; filename="FLEET_3DAY_CANONICAL_MANIFEST.md"'
    );
    return res.send(md);
  }
);

app.get(
  ['/MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md', '/api/export/crescendo-signoff'],
  (_req, res) => {
    const snap = buildLiveCrescendoSignOff(__dirname);
    const md = renderCrescendoSignOffMarkdown(snap);
    res.setHeader('Content-Type', 'text/markdown; charset=utf-8');
    res.setHeader('X-Crescendo-Decision', snap.overallDecision);
    res.setHeader('X-Git-Head-Sha', snap.headSha);
    if (snap.bundleSha256) {
      res.setHeader('X-Bundle-Sha256', snap.bundleSha256);
    }
    res.setHeader(
      'Content-Disposition',
      'inline; filename="MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md"'
    );
    return res.send(md);
  }
);

app.get('/api/crescendo/signoff', (_req, res) => {
  return res.json(buildLiveCrescendoSignOff(__dirname));
});

app.get('/api/export/team-handoff', (_req, res) => {
  const md = renderTeamHandoffRunbookMarkdown(__dirname, getProductionGuarantees());
  res.setHeader('Content-Type', 'text/markdown; charset=utf-8');
  res.setHeader(
    'Content-Disposition',
    'attachment; filename="meridian-estate-team-handoff.md"'
  );
  return res.send(md);
});

app.post(
  '/api/ingest/bundle',
  express.raw({ type: '*/*', limit: '25mb' }),
  async (req, res) => {
    const bodyBytes = Buffer.isBuffer(req.body) ? req.body : Buffer.alloc(0);
    const headerStr = (name: string) => {
      const val = req.headers[name.toLowerCase()];
      return Array.isArray(val) ? val[0] : val;
    };
    const rawRemotes = headerStr('x-target-remotes');
    const out = await handleIngestBundleRequest({
      bodyBytes,
      claimedSha256: headerStr('x-bundle-sha256'),
      authHeader: headerStr('authorization') ?? headerStr('x-ingest-token'),
      sessionId: headerStr('x-estate-session-id'),
      wakePolicy: headerStr('x-wake-policy'),
      wakeAgent: headerStr('x-wake-agent'),
      appUrl: headerStr('x-app-url'),
      targetRef: headerStr('x-bundle-ref'),
      targetRemotes: rawRemotes
        ? rawRemotes.split(',').map((s) => s.trim()).filter(Boolean)
        : undefined,
      headSha: headerStr('x-bundle-head-sha'),
      stagingDir: path.join(__dirname, 'dist-exports', 'staged-bundles'),
      state: fleetIngestState,
    });
    return res.status(out.httpStatus).json(out);
  }
);

app.get('/api/ingest/sessions', (_req, res) => {
  res.json({
    acceptedCount: fleetIngestState.acceptedCount,
    rejectedCount: fleetIngestState.rejectedCount,
    sessions: Array.from(fleetIngestState.sessionsByWorkerId.values()),
    wakeEvents: fleetIngestState.wakeEvents.slice(0, 30),
  });
});

app.post('/api/ingest/sessions/:workerId/idle', (req, res) => {
  const ok = markSessionIdle(fleetIngestState, req.params.workerId);
  if (!ok) {
    return res.status(404).json({ ok: false, error: 'worker_session_not_found' });
  }
  return res.json({ ok: true, workerId: req.params.workerId, status: 'IDLE' });
});

function buildFleetReceiverSummary() {
  const sessions = Array.from(fleetIngestState.sessionsByWorkerId.values());
  return {
    acceptedCount: fleetIngestState.acceptedCount,
    rejectedCount: fleetIngestState.rejectedCount,
    idleCount: sessions.filter((s) => s.status === 'IDLE').length,
    runningCount: sessions.filter((s) => s.status === 'RUNNING').length,
    sessions,
    wakeEvents: fleetIngestState.wakeEvents.slice(0, 20),
  };
}

app.get('/api/sync/telemetry', (_req, res) => {
  res.json({
    sync: readSyncTelemetrySnapshot(__dirname),
    guarantees: getProductionGuarantees(),
    fleetReceiver: buildFleetReceiverSummary(),
  });
});

app.get('/api/sync/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders?.();

  const sendEvent = (eventName: string, data: unknown) => {
    res.write(`event: ${eventName}\ndata: ${JSON.stringify(data)}\n\n`);
  };

  sendEvent('snapshot', {
    sync: readSyncTelemetrySnapshot(__dirname),
    guarantees: getProductionGuarantees(),
    fleetReceiver: buildFleetReceiverSummary(),
    githubDevice: getGitHubDeviceSyncSnapshot(),
  });

  const unsubscribe = subscribeSyncTelemetry((event, sync) => {
    sendEvent('sync_event', {
      event,
      sync,
      fleetReceiver: buildFleetReceiverSummary(),
      githubDevice: getGitHubDeviceSyncSnapshot(),
    });
  });

  const unsubscribeGhDevice = subscribeGitHubDeviceSync((githubDevice) => {
    sendEvent('sync_event', {
      githubDevice,
      sync: readSyncTelemetrySnapshot(__dirname),
      fleetReceiver: buildFleetReceiverSummary(),
    });
  });

  const heartbeat = setInterval(() => {
    res.write(`: keepalive ${Date.now()}\n\n`);
  }, 15_000);

  req.on('close', () => {
    clearInterval(heartbeat);
    unsubscribe();
    unsubscribeGhDevice();
  });
});

// ---------------------------------------------------------------------------
// I-8088 GENESIS_CEPHALOPOD_PANSPERMIA & GEN-TTT-001 FOUNDER ROUTES
// ---------------------------------------------------------------------------
app.get('/api/genesis/survival-ttt', (_req, res) => {
  res.json(buildSurvivalAndTttPayload());
});

app.post('/api/genesis/panspermia/simulate', (req, res) => {
  const rawDead = Array.isArray(req.body?.deadTentacles) ? req.body.deadTentacles : [];
  const sanitizedDead = Array.from(
    new Set(
      rawDead
        .map((n: unknown) => Number(n))
        .filter((n: number) => Number.isInteger(n) && n >= 0 && n < RS_N)
    )
  ) as number[];

  currentDeadTentacles = sanitizedDead;
  currentHealedTentacles = [];
  lastPanspermiaSnapshot = runI8088PanspermiaSimulation({
    deadTentacles: currentDeadTentacles,
    healedTentacles: currentHealedTentacles,
    walReceipts: routerEngine.ledger.getStats().totalReceipts,
    authoritativeFenceToken: 46 + currentHealingCycles,
  });

  res.json(buildSurvivalAndTttPayload());
});

app.post('/api/genesis/panspermia/heal', (_req, res) => {
  if (lastPanspermiaSnapshot.survivingCount < 3) {
    return res.status(409).json({
      error: 'quorum_below_3_cannot_self_heal',
      message: `Need at least 3 surviving tentacles to reconstruct shards; only ${lastPanspermiaSnapshot.survivingCount} alive.`,
      ...buildSurvivalAndTttPayload(),
    });
  }

  const healedNow = lastPanspermiaSnapshot.tentacles
    .filter((t) => t.status === 'DESTROYED')
    .map((t) => t.index);
  currentDeadTentacles = [];
  currentHealedTentacles = healedNow;
  currentHealingCycles++;
  lastPanspermiaSnapshot = runI8088PanspermiaSimulation({
    deadTentacles: currentDeadTentacles,
    healedTentacles: currentHealedTentacles,
    walReceipts: routerEngine.ledger.getStats().totalReceipts,
    authoritativeFenceToken: 46 + currentHealingCycles,
  });

  return res.json(buildSurvivalAndTttPayload());
});

app.post('/api/genesis/ttt/falsify', (_req, res) => {
  lastTttSnapshot = buildGenTttSnapshot();
  const payload = buildSurvivalAndTttPayload(true);
  const suite = runFullVerificationSuite();
  const f18 = suite.cases.find((c) => c.id === 'F18');
  return res.json({
    f18Case: f18 ?? null,
    suitePassed: suite.failedCases === 0,
    ...payload,
  });
});

// ---------------------------------------------------------------------------
// ESTATE GRAND UNION, CHRONOS/TEMPO SSE HEARTBEAT & FIRST-USE AUDIT ROUTES
// ---------------------------------------------------------------------------
app.get('/api/union', (_req, res) => {
  res.json({
    union: grandUnion.getSnapshot(),
    state: buildStateSnapshot(),
    guarantees: cachedGuarantees?.report,
  });
});

app.get('/api/union/guarantees', (_req, res) => {
  res.json(getProductionGuarantees());
});

app.post('/api/union/beat', (_req, res) => {
  const union = grandUnion.executeBeat('manual_pulse');
  res.json({
    union,
    state: buildStateSnapshot(),
  });
});

app.post('/api/union/autonomous', (req, res) => {
  const enabled = Boolean(req.body?.enabled);
  const cadenceMs =
    req.body?.cadenceMs !== undefined ? Number(req.body.cadenceMs) : undefined;
  const union = grandUnion.setAutonomousEnabled(enabled, cadenceMs);
  res.json({
    union,
    state: buildStateSnapshot(),
  });
});

app.post('/api/union/intercloud/preempt', (req, res) => {
  const laneId = typeof req.body?.laneId === 'string' ? req.body.laneId : undefined;
  const preemption = grandUnion.simulateSpotPreemption(laneId);
  res.json({
    ...preemption,
    union: preemption.snapshot,
    state: buildStateSnapshot(),
  });
});

app.post('/api/union/intercloud/heal', (_req, res) => {
  const union = grandUnion.healAllSpotLanes();
  res.json({
    union,
    state: buildStateSnapshot(),
  });
});

app.post('/api/union/ensemble-proof', (req, res) => {
  const episodes = Number(req.body?.episodes) || 500;
  const proof = evaluateEnsembleVsFrontier(episodes);
  res.json({
    proof,
    union: grandUnion.getSnapshot(),
  });
});

app.post('/api/union/audit/ratchet', (req, res) => {
  const currentLinesRaw =
    req.body?.currentLinesRaw !== undefined ? req.body.currentLinesRaw : 348;
  const baselineLinesRaw =
    req.body?.baselineLinesRaw !== undefined ? req.body.baselineLinesRaw : 348;
  const installerScript =
    typeof req.body?.installerScript === 'string'
      ? req.body.installerScript
      : 'bin/idp-machine-submit --lane greenlane --verify-provenance';

  const ratchet = evaluateAgentsMdRatchet({
    currentLinesRaw,
    baselineLinesRaw,
    targetCeiling: 300,
  });
  const shortcutAudit = auditInstallerShortcuts(installerScript);
  res.json({
    ratchet,
    shortcutAudit,
    firstUseAudit: buildFirstUseAuditSnapshot(),
  });
});

app.get('/api/union/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders?.();

  const sendEvent = (eventName: string, data: unknown) => {
    res.write(`event: ${eventName}\ndata: ${JSON.stringify(data)}\n\n`);
  };

  sendEvent('union_snapshot', {
    union: grandUnion.getSnapshot(),
    state: buildStateSnapshot(),
  });

  const unsubscribe = grandUnion.subscribe((unionSnap) => {
    sendEvent('union_snapshot', {
      union: unionSnap,
      state: buildStateSnapshot(),
    });
  });

  const keepalive = setInterval(() => {
    res.write(`: keepalive ${Date.now()}\n\n`);
  }, 15_000);

  req.on('close', () => {
    clearInterval(keepalive);
    unsubscribe();
  });
});

// ---------------------------------------------------------------------------
// HERMES · OTTO_NUMEN (@otto_numen_bot) VIP CEO TELEGRAM CONCIERGE ROUTES
// ---------------------------------------------------------------------------
app.get('/api/telegram/state', (_req, res) => {
  res.json(ottoNumen.getSnapshot());
});

app.post('/api/telegram/storm', (req, res) => {
  const count = Number(req.body?.eventCount) || 50;
  res.json(ottoNumen.simulateEstateStorm(count));
});

app.post('/api/telegram/briefing', (_req, res) => {
  const unionSnap = grandUnion.getSnapshot();
  const guarantees = getProductionGuarantees();
  const card = ottoNumen.synthesizeLiveExecutiveBriefing({
    beatNumber: unionSnap.chronos.beatNumber,
    walReceipts: unionSnap.battalionRollup.walReceipts,
    netSavingsUsd: unionSnap.battalionRollup.netSavingsUsd,
    savingsPct: unionSnap.battalionRollup.savingsPct,
    ensemblePassPct: unionSnap.ensembleProof.ensembleVerifiedPassPct,
    frontierPassPct: unionSnap.ensembleProof.singleFrontierPassPct,
    onlinePools: unionSnap.interCloudSummary.onlineLanes,
    totalPools: unionSnap.interCloudSummary.totalLanes,
    guaranteesVerified: guarantees.verifiedCount,
    guaranteesTotal: guarantees.totalCount,
  });
  res.json({
    card,
    snapshot: ottoNumen.getSnapshot(),
  });
});

app.post('/api/telegram/policy', (req, res) => {
  const focusPolicy = req.body?.focusPolicy as CeoFocusPolicy | undefined;
  if (
    focusPolicy &&
    ['VIP_P0_ONLY', 'VIP_PLUS_BRIEFINGS', 'SILENT_DND_ALL'].includes(focusPolicy)
  ) {
    ottoNumen.setFocusPolicy(focusPolicy);
  }
  if (req.body?.coalesceWindowSec !== undefined) {
    ottoNumen.setCoalesceWindowSec(Number(req.body.coalesceWindowSec));
  }
  res.json(ottoNumen.getSnapshot());
});

app.post('/api/telegram/unmute-all', (_req, res) => {
  res.json(ottoNumen.clearMutedRules());
});

app.post('/api/telegram/callback', (req, res) => {
  const messageId = String(req.body?.messageId || '');
  const action = String(req.body?.action || 'ack') as 'approve' | 'hold' | 'ack' | 'mute4h';
  if (!['approve', 'hold', 'ack', 'mute4h'].includes(action)) {
    return res.status(400).json({ error: 'Invalid Telegram callback action' });
  }
  const out = ottoNumen.executeInlineCallback({ messageId, action });
  return res.status(out.ok ? 200 : 404).json(out);
});

app.post('/api/telegram/ingest', (req, res) => {
  const body = req.body ?? {};
  const kind = (body.kind || 'p0_ceo_signoff') as RawEstateEventKind;
  const headline = typeof body.headline === 'string' ? body.headline.trim() : '';
  if (!headline) {
    return res.status(400).json({ error: 'Headline is required' });
  }
  const ingested = ottoNumen.ingestEvent({
    kind,
    sourceSubsystem: typeof body.sourceSubsystem === 'string' ? body.sourceSubsystem : 'Estate',
    headline,
    metrics: typeof body.metrics === 'object' && body.metrics ? body.metrics : { Status: 'OK' },
    autonomousAction:
      typeof body.autonomousAction === 'string'
        ? body.autonomousAction
        : 'Validated via OTTO_NUMEN router.',
    ceoQuestion: typeof body.ceoQuestion === 'string' ? body.ceoQuestion : undefined,
    dedupeKey: typeof body.dedupeKey === 'string' ? body.dedupeKey : undefined,
  });
  return res.json({
    ...ingested,
    snapshot: ottoNumen.getSnapshot(),
  });
});

app.get('/api/telegram/bot-blueprint', (_req, res) => {
  const code = generateOttoNumenBotBlueprintTs();
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.setHeader(
    'Content-Disposition',
    'attachment; filename="hermes-otto-numen-telegram-bot.ts"'
  );
  res.send(code);
});

// ---------------------------------------------------------------------------
// PROSPECTOR-2100 AUTONOMOUS CAUSAL RESEARCH & MUMCHIMP COMMERCIAL HUB
// ---------------------------------------------------------------------------
function buildCurrentSynchronicityStamp() {
  const unionSnap = grandUnion.getSnapshot();
  const cfg = founderConfigEngine.getConfig();
  const rego = founderConfigEngine.getCurrentRegoReport();
  const wal = routerEngine.ledger.getStats();
  const prosp = prospectorEngine.getSnapshot();
  const tg = ottoNumen.getSnapshot();
  return computeSynchronicityMerkleStamp({
    chronosBeat: unionSnap.chronos.beatNumber,
    founderConfig: cfg,
    regoBundleSha256: rego.bundleSha256,
    walLatestSequence: wal.latestSequence,
    interCloudOnlineCount: unionSnap.interCloudSummary.onlineLanes,
    interCloudTotalCount: unionSnap.interCloudSummary.totalLanes,
    prospectorDigestSha256: prosp.latestDigestSha256,
    mumchimpPublishedCount: prosp.mumchimpPublishedCount,
    telegramFocusPolicy: tg.focusPolicy,
    sporeSurvivingTentacles: lastPanspermiaSnapshot.survivingCount,
  });
}

function buildFounderPlanePayload() {
  return {
    config: founderConfigEngine.getConfig(),
    regoReport: founderConfigEngine.getCurrentRegoReport(),
    synchronicity: buildCurrentSynchronicityStamp(),
    auditTrail: founderConfigEngine.getAuditTrail(),
    uhnwCharter: uhnwConcierge.getSnapshot(),
  };
}

function buildCommercialOverviewPayload() {
  const unionSnap = grandUnion.getSnapshot();
  const guarantees = getProductionGuarantees();
  const prosp = prospectorEngine.getSnapshot();
  return {
    economics: currentInvestorEconomics,
    gapMatrix: COMMERCIAL_GAP_CLOSURE_MATRIX,
    synchronicity: buildCurrentSynchronicityStamp(),
    uhnwCharter: uhnwConcierge.getSnapshot(),
    guaranteesVerified: guarantees.verifiedCount,
    guaranteesTotal: guarantees.totalCount,
    ensemblePassPct: unionSnap.ensembleProof.ensembleVerifiedPassPct,
    frontierPassPct: unionSnap.ensembleProof.singleFrontierPassPct,
    ensembleCostReductionPct: unionSnap.ensembleProof.costReductionPct,
    prospectorSavingsPct: prosp.savingsPct,
    mumchimpPublishedCount: prosp.mumchimpPublishedCount,
    walReceipts: unionSnap.battalionRollup.walReceipts,
    diligenceRequests: diligenceRequestsLog,
  };
}

app.get('/api/prospector/state', (_req, res) => {
  res.json({
    snapshot: prospectorEngine.getSnapshot(),
    comparison: compareLegacyVsProspector2100(),
  });
});

app.post('/api/prospector/cycle', (req, res) => {
  const beat = grandUnion.getSnapshot().chronos.beatNumber;
  const finding = prospectorEngine.runAutonomousCycle({
    chronosBeat: beat,
    customHypothesis: req.body?.customHypothesis,
  });
  res.json({
    finding,
    snapshot: prospectorEngine.getSnapshot(),
  });
});

// ---------------------------------------------------------------------------
// FOUNDER FIRST-CLASS CONFIG, REGO CONSTITUTION & CHRONOS SYNCHRONICITY
// ---------------------------------------------------------------------------
app.get('/api/founder/plane', (_req, res) => {
  res.json(buildFounderPlanePayload());
});

app.post('/api/founder/config', (req, res) => {
  const body = req.body ?? {};
  const patch: Record<string, unknown> = {};
  if (
    typeof body.routingStrategy === 'string' &&
    ['priority_failover', 'lowest_latency', 'weighted_cost', 'least_busy'].includes(
      body.routingStrategy
    )
  ) {
    patch.routingStrategy = body.routingStrategy;
  }
  if (body.sovereignFreeFloorPct !== undefined) {
    patch.sovereignFreeFloorPct = Number(body.sovereignFreeFloorPct);
  }
  if (body.prospectorMinCausalConfidencePct !== undefined) {
    patch.prospectorMinCausalConfidencePct = Number(body.prospectorMinCausalConfidencePct);
  }
  if (body.maxAutonomousCycleSpendUsd !== undefined) {
    patch.maxAutonomousCycleSpendUsd = Number(body.maxAutonomousCycleSpendUsd);
  }
  if (
    typeof body.telegramFocusPolicy === 'string' &&
    ['VIP_P0_ONLY', 'VIP_PLUS_BRIEFINGS', 'SILENT_DND_ALL'].includes(body.telegramFocusPolicy)
  ) {
    patch.telegramFocusPolicy = body.telegramFocusPolicy;
  }
  if (typeof body.allowGitNoVerifyShortcuts === 'boolean') {
    patch.allowGitNoVerifyShortcuts = body.allowGitNoVerifyShortcuts;
  }
  if (typeof body.enforceZeroClientPollingI8090 === 'boolean') {
    patch.enforceZeroClientPollingI8090 = body.enforceZeroClientPollingI8090;
  }
  if (typeof body.enforceFailClosedAuthI8095 === 'boolean') {
    patch.enforceFailClosedAuthI8095 = body.enforceFailClosedAuthI8095;
  }
  if (typeof body.requireRegoForPolicyLogic === 'boolean') {
    patch.requireRegoForPolicyLogic = body.requireRegoForPolicyLogic;
  }
  if (typeof body.enforceUhnwVipCharter === 'boolean') {
    patch.enforceUhnwVipCharter = body.enforceUhnwVipCharter;
  }
  if (body.p0ConciergeLatencyCeilingMs !== undefined) {
    patch.p0ConciergeLatencyCeilingMs = Number(body.p0ConciergeLatencyCeilingMs);
  }
  if (typeof body.enforceEpistemicSeparation === 'boolean') {
    patch.enforceEpistemicSeparation = body.enforceEpistemicSeparation;
  }

  const out = founderConfigEngine.proposeAndApplyPatch(patch);
  if (out.committed) {
    routerEngine.setStrategy(out.config.routingStrategy);
    ottoNumen.setFocusPolicy(out.config.telegramFocusPolicy);
    prospectorEngine.setMinCausalConfidenceGatePct(out.config.prospectorMinCausalConfidencePct);
  }

  res.status(out.httpStatus).json({
    ...out,
    plane: buildFounderPlanePayload(),
  });
});

app.post('/api/founder/rego-classify', (req, res) => {
  const moduleName =
    typeof req.body?.moduleName === 'string' ? req.body.moduleName : 'proposedModule.ts';
  const sourceSnippet =
    typeof req.body?.sourceSnippet === 'string' ? req.body.sourceSnippet : '';
  res.json(classifyCodeForRegoGovernance(moduleName, sourceSnippet));
});

app.post('/api/founder/concierge-dispatch', (req, res) => {
  const presetKey = req.body?.presetKey;
  const founderInstruction =
    typeof req.body?.founderInstruction === 'string' ? req.body.founderInstruction : '';
  const receipt = uhnwConcierge.dispatchDirective({
    presetKey,
    founderInstruction,
  });

  // Log quiet executive trace in Topic #102 Executive Briefings
  ottoNumen.ingestEvent({
    kind: 'executive_briefing',
    sourceSubsystem: 'OTTO UHNW Concierge',
    headline: `VIP Directive Executed (${receipt.assignedLeadAgent}): ${receipt.instruction.slice(0, 64)}`,
    metrics: {
      LatencyMs: receipt.executionLatencyMs,
      Tier: receipt.epistemicTierEarned,
      Receipt: receipt.receiptSha256.slice(0, 10),
    },
    autonomousAction: receipt.agentJudgementBrief,
    dedupeKey: `vip-concierge:${receipt.assignedLeadAgent}`,
  });

  res.json({
    ok: true,
    receipt,
    uhnwCharter: uhnwConcierge.getSnapshot(),
  });
});

app.post('/api/founder/epistemic-audit', (req, res) => {
  const body = req.body ?? {};
  const result = auditEpistemicClaim({
    capabilityName: String(body.capabilityName ?? 'audit/first-use-machine-agent-20261116'),
    claimedMarketingTier:
      body.claimedMarketingTier === 'CERTIFIED_PRODUCTION_YIELD' ||
      body.claimedMarketingTier === 'ENGINEERING_TEST_VERIFIED'
        ? body.claimedMarketingTier
        : 'CANDIDATE_DISCLOSED',
    hasPlanLock: Boolean(body.hasPlanLock),
    localAdversarialTestsPassed: Boolean(body.localAdversarialTestsPassed),
    signedGreenlaneMerged: Boolean(body.signedGreenlaneMerged),
    independentLiveOutcomeJoined: Boolean(body.independentLiveOutcomeJoined),
  });
  res.status(result.httpStatus).json(result);
});

app.post('/api/academy/transfer-submit', (req, res) => {
  const trackId = (req.body?.trackId ?? 'reproducibility_transfer_boundaries') as StandoutTrackId;
  const selectedAnswers =
    req.body?.selectedAnswers && typeof req.body.selectedAnswers === 'object'
      ? (req.body.selectedAnswers as Record<string, number | undefined>)
      : {};
  const evaluation = evaluateUnseenTransferPilot({ trackId, selectedAnswers });
  res.status(evaluation.complete ? 200 : 400).json(evaluation);
});

app.get('/api/founder/rego-bundle', (_req, res) => {
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.setHeader(
    'Content-Disposition',
    'attachment; filename="genesis-constitutional-v1.rego"'
  );
  res.send(generateCanonicalRegoBundle());
});

// ---------------------------------------------------------------------------
// MERIDIAN COMPANY SHOWCASE & INSTITUTIONAL INVESTOR DATA ROOM ROUTES
// ---------------------------------------------------------------------------
app.get('/api/commercial/overview', (_req, res) => {
  res.json(buildCommercialOverviewPayload());
});

app.post('/api/commercial/model', (req, res) => {
  currentInvestorEconomics = computeInvestorUnitEconomics(req.body ?? {});
  res.json({ economics: currentInvestorEconomics });
});

app.post('/api/commercial/diligence-request', (req, res) => {
  const investorName = String(req.body?.investorName ?? '').trim();
  const firm = String(req.body?.firm ?? '').trim();
  const email = String(req.body?.email ?? '').trim();
  const focusTrack = String(req.body?.focusTrack ?? 'Series Diligence').trim();
  if (investorName.length < 2 || firm.length < 2 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return res.status(400).json({ ok: false, error: 'Valid name, firm, and institutional email required.' });
  }
  const nowUtc = new Date().toISOString();
  const receiptSha256 = crypto
    .createHash('sha256')
    .update(`${investorName}|${firm}|${email}|${focusTrack}|${nowUtc}`, 'utf8')
    .digest('hex');
  const entry = {
    id: `dil-${Date.now().toString(36)}`,
    submittedAtUtc: nowUtc,
    investorName,
    firm,
    email,
    focusTrack,
    receiptSha256,
  };
  diligenceRequestsLog.unshift(entry);
  if (diligenceRequestsLog.length > 25) diligenceRequestsLog.pop();

  // Route structured executive notice into Topic #116 (Releases & Diligence Audit) on OTTO_NUMEN
  ottoNumen.ingestEvent({
    kind: 'release_bundle_sync',
    sourceSubsystem: 'Meridian Investor Room',
    headline: `Diligence Access Registered: ${firm} (${investorName})`,
    metrics: { Track: focusTrack, Receipt: receiptSha256.slice(0, 10) },
    autonomousAction: 'Stamped diligence receipt & provisioned PR #7999 data-room snapshot.',
    dedupeKey: `investor:${email.toLowerCase()}`,
  });

  return res.json({
    ok: true,
    entry,
    overview: buildCommercialOverviewPayload(),
  });
});

app.get('/api/commercial/investor-memo', (req, res) => {
  const modeled = computeInvestorUnitEconomics({
    enterpriseCustomers: req.query.enterpriseCustomers
      ? Number(req.query.enterpriseCustomers)
      : currentInvestorEconomics.input.enterpriseCustomers,
    avgMonthlyPlatformFeeUsd: req.query.avgMonthlyPlatformFeeUsd
      ? Number(req.query.avgMonthlyPlatformFeeUsd)
      : currentInvestorEconomics.input.avgMonthlyPlatformFeeUsd,
    monthlyBillionsTokensAcrossFleet: req.query.monthlyBillionsTokensAcrossFleet
      ? Number(req.query.monthlyBillionsTokensAcrossFleet)
      : currentInvestorEconomics.input.monthlyBillionsTokensAcrossFleet,
    sovereignAndSpotSharePct: req.query.sovereignAndSpotSharePct
      ? Number(req.query.sovereignAndSpotSharePct)
      : currentInvestorEconomics.input.sovereignAndSpotSharePct,
  });
  const guarantees = getProductionGuarantees();
  const prosp = prospectorEngine.getSnapshot();
  const md = renderInvestorDiligenceMemoMarkdown({
    economics: modeled,
    synchronicity: buildCurrentSynchronicityStamp(),
    guaranteesVerified: guarantees.verifiedCount,
    guaranteesTotal: guarantees.totalCount,
    prospectorSavingsPct: prosp.savingsPct,
    mumchimpPublishedCount: prosp.mumchimpPublishedCount,
  });
  res.setHeader('Content-Type', 'text/markdown; charset=utf-8');
  res.setHeader(
    'Content-Disposition',
    'attachment; filename="meridian-genesis-investor-diligence-memo.md"'
  );
  res.send(md);
});

// ---------------------------------------------------------------------------
// MUM-CONCIERGE-001 — AUNTIE EZINNE WHATSAPP & FAMILY SAFETY CONTROL PLANE
// ---------------------------------------------------------------------------
app.get('/api/concierge/overview', (_req, res) => {
  res.json(mumsConcierge.getSnapshot());
});

app.post('/api/concierge/whatsapp-burst', (req, res) => {
  const rawList = Array.isArray(req.body?.fragments) ? req.body.fragments : [];
  const baseTs = Date.now();
  const fragments: WhatsAppInboundFragment[] =
    rawList.length > 0
      ? rawList.map((f: Record<string, unknown>, idx: number) => ({
          messageSid: String(f.messageSid || `wa-${baseTs}-${idx}`),
          senderRole: f.senderRole === 'GUARDIAN' ? 'GUARDIAN' : 'MUMMY',
          channel:
            f.channel === 'voice_note' || f.channel === 'guided_button' ? f.channel : 'text',
          timestampMs: Number(f.timestampMs) || baseTs + idx * 1200,
          text: String(f.text || ''),
        }))
      : [
          {
            messageSid: `wa-eon-${baseTs}-1`,
            senderRole: 'MUMMY',
            channel: 'voice_note',
            timestampMs: baseTs,
            text: 'Auntie Ezinne I just got my E.ON bill email',
          },
          {
            messageSid: `wa-eon-${baseTs}-2`,
            senderRole: 'MUMMY',
            channel: 'text',
            timestampMs: baseTs + 1600,
            text: 'wait it says £95.11 and £52.43 direct debit do I owe money?',
          },
        ];

  const out = mumsConcierge.processWhatsAppBurst(fragments);
  if (out.coalesced.groups.some((g) => g.distressDetected || g.scamDetected)) {
    ottoNumen.ingestEvent({
      kind: 'p0_ceo_signoff',
      sourceSubsystem: 'Auntie Ezinne Family Safety',
      headline: 'Family Safety Alert: Distress or Scam Lure Intercepted (PII Redacted)',
      metrics: {
        CoalescedTurns: out.coalesced.totalCoalescedTurns,
        Channel: 'WhatsApp',
      },
      autonomousAction: 'Paused external actions fail-closed & escalated to Chidi.',
      ceoQuestion: 'Confirm Guardian check-in with Mummy complete?',
      dedupeKey: 'mum-concierge:p0-safety',
    });
  }
  res.json(out);
});

app.post('/api/concierge/document-analyze', (req, res) => {
  const fixtureId = String(req.body?.fixtureId || 'clean_eon_001') as NegativeFixtureId;
  const out = mumsConcierge.evaluateDocumentFixture(fixtureId);
  if (!out.analysis.safeToAct && (fixtureId === 'spoofed_supplier' || fixtureId === 'false_refund_offer')) {
    ottoNumen.ingestEvent({
      kind: 'p0_ceo_signoff',
      sourceSubsystem: 'MUM-CONCIERGE-001 WP04',
      headline: `Quarantined ${fixtureId.replace(/_/g, ' ')} before reaching Mummy actions`,
      metrics: { Gate: 'WP04', CreditPreserved: '£95.11' },
      autonomousAction: 'Blocked malicious/spoofed vendor flow without exposing personal data.',
      dedupeKey: `mum-concierge:doc:${fixtureId}`,
    });
  }
  res.json(out);
});

app.post('/api/concierge/guardian-action', (req, res) => {
  const action = String(req.body?.action || '');
  if (action === 'kill_switch_on') {
    return res.json({ snapshot: mumsConcierge.setKillSwitch(true) });
  }
  if (action === 'kill_switch_off') {
    return res.json({ snapshot: mumsConcierge.setKillSwitch(false) });
  }
  if (action === 'guardian_offline') {
    return res.json({ snapshot: mumsConcierge.setGuardianAvailable(false) });
  }
  if (action === 'guardian_online') {
    return res.json({ snapshot: mumsConcierge.setGuardianAvailable(true) });
  }
  if (action === 'cancel_all') {
    return res.json({ snapshot: mumsConcierge.cancelAllPending() });
  }
  if (action === 'fulfilment_approve' || action === 'fulfilment_cancel' || action === 'fulfilment_recover') {
    const id = String(req.body?.id || '');
    const mapped =
      action === 'fulfilment_approve'
        ? 'guardian_approve'
        : action === 'fulfilment_recover'
          ? 'recover'
          : 'cancel';
    const out = mumsConcierge.actOnFulfilment({
      id,
      action: mapped,
      guardianName: 'Chidi (Guardian)',
    });
    return res.status(out.ok ? 200 : 409).json(out);
  }
  return res.status(400).json({ error: 'Unsupported guardian action' });
});

app.post('/api/concierge/fulfil', (req, res) => {
  const kind = (['shopping', 'prescription', 'appointment', 'transport'].includes(String(req.body?.kind))
    ? req.body.kind
    : 'shopping') as 'shopping' | 'prescription' | 'appointment' | 'transport';
  const idempotencyKey =
    typeof req.body?.idempotencyKey === 'string' && req.body.idempotencyKey.trim()
      ? req.body.idempotencyKey.trim()
      : `idem-${kind}-${Date.now()}`;
  const out = mumsConcierge.submitFulfilmentRequest({
    idempotencyKey,
    kind,
    title: String(req.body?.title || `${kind} request (Sandbox Adapter)`),
    amountGbp: Number(req.body?.amountGbp ?? 12.5),
    motherConfirmed: req.body?.motherConfirmed !== false,
    simulateInterruption: Boolean(req.body?.simulateInterruption),
  });
  res.json(out);
});

app.post('/api/concierge/falsify-all', (_req, res) => {
  const safetyFalsifiers = mumsConcierge.runSafetyFalsifiers();
  const negativeFixtures = mumsConcierge.runAll11NegativeScenarios();
  res.json({
    safetyPassedCount: safetyFalsifiers.filter((s) => s.passed).length,
    safetyTotalCount: safetyFalsifiers.length,
    negativePassedCount: negativeFixtures.filter((n) => n.passed).length,
    negativeTotalCount: negativeFixtures.length,
    safetyFalsifiers,
    negativeFixtures,
    snapshot: mumsConcierge.getSnapshot(),
  });
});

// ---------------------------------------------------------------------------
// MERIDIAN AUTONOMOUS REACTIVITY & REAL-TIME FOUNDER'S VIEW (#8184 / #8183)
// ---------------------------------------------------------------------------
app.get('/api/reactivity/state', (_req, res) => {
  res.json(reactivityEngine.getSnapshot());
});

app.get('/api/reactivity/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders?.();

  const sendSnapshot = (snap: ReturnType<typeof reactivityEngine.getSnapshot>) => {
    res.write(`event: reactivity_snapshot\ndata: ${JSON.stringify(snap)}\n\n`);
  };

  sendSnapshot(reactivityEngine.getSnapshot());
  const unsubscribe = reactivityEngine.subscribe(sendSnapshot);

  const keepAlive = setInterval(() => {
    res.write(': reactivity-keepalive\n\n');
  }, 15_000);
  keepAlive.unref?.();

  req.on('close', () => {
    clearInterval(keepAlive);
    unsubscribe();
  });
});

app.post('/api/reactivity/action', (req, res) => {
  const action = String(req.body?.action ?? '');

  if (action === 'run_experiment') {
    const validIds: ExperimentId[] = ['EXP_A', 'EXP_B', 'EXP_C', 'EXP_D', 'EXP_E', 'EXP_F'];
    const expId = validIds.includes(req.body?.experimentId)
      ? (req.body.experimentId as ExperimentId)
      : 'EXP_A';
    const report = reactivityEngine.runExperiment(expId);
    ottoNumen.ingestEvent({
      kind: 'incident_auto_healed',
      sourceSubsystem: 'Living Intelligence Graph #8184',
      headline: `${report.code}: ${report.passedInEngine ? 'VERIFIED IN ENGINE' : 'FAILED'}`,
      metrics: {
        Obligation: report.obligationId,
        DurationMs: report.durationMs,
      },
      autonomousAction: report.summary,
      dedupeKey: `reactivity:${expId}`,
    });
    return res.json({
      ok: report.passedInEngine,
      experiment: report,
      obligationId: report.obligationId,
      message: `${report.code} -> ${report.passedInEngine ? 'PASS' : 'FAIL'}: ${report.summary}`,
      snapshot: reactivityEngine.getSnapshot(),
    });
  }

  if (action === 'run_all_experiments') {
    const snapshot = reactivityEngine.runAllSixExperiments();
    const passed = snapshot.experiments.filter((e) => e.passedInEngine).length;
    ottoNumen.ingestEvent({
      kind: 'release_bundle_sync',
      sourceSubsystem: 'Living Intelligence Graph #8184',
      headline: `Ship-and-Prove Suite Executed: ${passed}/6 Experiments Verified`,
      metrics: {
        FenceEpoch: `f_${snapshot.globalFencingEpoch}`,
        Stale409s: snapshot.staleFenceRejectionsCount,
      },
      autonomousAction: 'Verified 7-stage custody, QUAD attestation, split-brain fencing, and producer immunity.',
      dedupeKey: 'reactivity:all-six',
    });
    return res.json({
      ok: passed === 6,
      message: `Executed all 6 Ship-and-Prove Acceptance Experiments (${passed}/6 PASS). Fence epoch advanced to f_${snapshot.globalFencingEpoch}; external WAN rollout kept honestly BLOCKED_DISPATCH.`,
      snapshot,
    });
  }

  if (action === 'attempt_github_settlement') {
    const obligationId = String(req.body?.obligationId || 'OBL-PASSKEY-8175');
    const out = reactivityEngine.attemptGitHubCommentSettlement(
      obligationId,
      'Posting GitHub escalation comment without authenticated worker lease'
    );
    return res.json({
      ok: true,
      obligationId,
      message: `Blocked false completion (${out.reason}): GitHub comment logged as coordination record; custody remains ${out.stageUnchanged}.`,
      snapshot: reactivityEngine.getSnapshot(),
    });
  }

  if (action === 'attempt_broker_ack_settlement') {
    const obligationId = String(req.body?.obligationId || 'OBL-PASSKEY-8175');
    const out = reactivityEngine.attemptBrokerAckSettlement(
      obligationId,
      'estate.inbox.omniflow-8133'
    );
    return res.json({
      ok: true,
      obligationId,
      message: `Blocked false completion (${out.reason}): NATS inbox --ack proves transport delivery only; custody stage is ${out.stageAfterAck}.`,
      snapshot: reactivityEngine.getSnapshot(),
    });
  }

  if (action === 'toggle_nats') {
    const connected = Boolean(req.body?.connected);
    const out = reactivityEngine.setNatsBrokerConnected(connected);
    return res.json({
      ok: true,
      message: out.natsConnected
        ? `NATS JetStream reconnected; replayed ${out.replayedCount} buffered durable outbox obligation(s) with 0 duplicates.`
        : 'NATS JetStream disconnected: new obligations now buffer safely in explicit TRANSPORT_DEGRADED_BACKLOG (0 silent drops).',
      snapshot: reactivityEngine.getSnapshot(),
    });
  }

  if (action === 'crash_worker') {
    const workerId = String(req.body?.workerId || 'worker-argon-greenlane-01');
    const rec = reactivityEngine.simulateWorkerLossAndRecover(workerId);
    return res.json({
      ok: true,
      obligationId: rec.affectedObligationId ?? undefined,
      message: rec.affectedObligationId
        ? `Detected ${rec.crashedWorkerId} loss at 2 missed heartbeats: revoked f_${rec.revokedFence} and transferred ${rec.affectedObligationId} to ${rec.successorWorkerId} under f_${rec.newFence} in ${rec.recoveryMs}ms.`
        : `Marked ${rec.crashedWorkerId} CRASHED (2 missed heartbeats); excluded from QUAD dispatch until re-attested.`,
      snapshot: reactivityEngine.getSnapshot(),
    });
  }

  if (action === 'restore_workers') {
    const snapshot = reactivityEngine.restoreCrashedWorkers();
    return res.json({
      ok: true,
      message: 'Restored crashed workers with fresh Ed25519 session attestation; prior revoked fencing tokens remain permanently invalid.',
      snapshot,
    });
  }

  if (action === 'observe_custom_escalation') {
    const title = String(req.body?.title || '').trim().slice(0, 180);
    if (!title) {
      return res.status(400).json({ ok: false, error: 'Provide an escalation title.' });
    }
    const obs = reactivityEngine.observeEvent({
      subjectKey: `founder:custom:${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
      priority: 'P0',
      title,
      sourceSurface: 'Genesis Real-Time Founder’s View',
      linkedProgrammes: ['#8184', '#8183'],
      requiredCapability: 'typescript_worker',
      requiredQuadScope: 'code:patch',
      collaborationMode: 'REACTIVE',
      causalHypothesis: `Founder-initiated obligation "${title}" tracked end-to-end by BEAST/SPIDER & FLOW.`,
    });

    let stageSummary = obs.obligation.stage;
    if (!obs.convergedIntoExisting && obs.obligation.stage === 'DETECTED') {
      const disp = reactivityEngine.dispatchObligation(obs.obligation.obligationId);
      if (disp.dispatched && disp.assignedWorkerId && disp.fencingToken) {
        reactivityEngine.commitProtectedEffect({
          obligationId: obs.obligation.obligationId,
          workerId: disp.assignedWorkerId,
          fencingToken: disp.fencingToken,
          idempotencyKey: `idem:${obs.obligation.obligationId}:v1`,
          effectSummary: `Executed Founder directive "${title}" under fenced lease f_${disp.fencingToken}.`,
        });
        reactivityEngine.verifyObligationIndependently({
          obligationId: obs.obligation.obligationId,
          verifierAgentId: 'verifier-karma-optimus-judge',
          evidenceSummary: 'Independent KARMA verification of Founder reactive obligation.',
        });
      }
      stageSummary = obs.obligation.stage;
    }

    return res.json({
      ok: true,
      obligationId: obs.obligation.obligationId,
      message: obs.convergedIntoExisting
        ? `Converged duplicate escalation into ${obs.obligation.obligationId} (count=${obs.obligation.convergedDuplicateCount}) without creating a duplicate mission.`
        : `Created ${obs.obligation.obligationId} and drove custody through ${stageSummary}.`,
      snapshot: reactivityEngine.getSnapshot(),
    });
  }

  if (action === 'run_cert_scenario') {
    const validScenarios: CertificationScenarioId[] = [
      'CERT_01',
      'CERT_02',
      'CERT_03',
      'CERT_04',
      'CERT_05',
      'CERT_06',
      'CERT_07',
      'CERT_08',
      'CERT_09',
      'CERT_10',
    ];
    const scenarioId = validScenarios.includes(req.body?.scenarioId)
      ? (req.body.scenarioId as CertificationScenarioId)
      : 'CERT_01';
    const result = reactivityEngine.runMccCertificationScenario(scenarioId);
    return res.json({
      ok: result.passedInCiEngine,
      scenario: result,
      message: `${result.scenarioId} (${result.title}) -> ${result.passedInCiEngine ? 'PASS' : 'FAIL'} [${result.enforcementPointTriggered}]: ${result.observedOutcome}`,
      snapshot: reactivityEngine.getSnapshot(),
    });
  }

  if (action === 'run_all_cert_scenarios') {
    const results = reactivityEngine.runAllMccCertificationScenarios();
    const passedCount = results.filter((r) => r.passedInCiEngine).length;
    ottoNumen.ingestEvent({
      kind: 'release_bundle_sync',
      sourceSubsystem: 'MCC-001 Universal Execution Protocol',
      headline: `Certified ${passedCount}/10 Estate-Wide Scenarios (EP-A..EP-E + LTL)`,
      metrics: {
        Scenarios: `${passedCount}/10`,
        ExternalStatus: 'SPECIFIED_NOT_ENFORCED',
      },
      autonomousAction:
        'Verified 9-tuple contracts, bin/capability-index 5 invariants, authority narrowing, and Web/App/Console reconnect.',
      dedupeKey: 'mcc-001:cert-10',
    });
    return res.json({
      ok: passedCount === 10,
      message: `Executed all 10 MCC-001 Certification Scenarios (${passedCount}/10 PASS in CI Engine; external multi-repo enforcement remains explicitly SPECIFIED / NOT ESTATE-WIDE ENFORCED).`,
      snapshot: reactivityEngine.getSnapshot(),
    });
  }

  if (action === 'toggle_unified_surface') {
    const surfaceId = String(req.body?.surfaceId || 'WEB_GEMINI_BROWSER');
    const connected = Boolean(req.body?.connected);
    try {
      const out = reactivityEngine.toggleUnifiedSurfaceConnection(surfaceId, connected);
      return res.json({
        ok: true,
        message: connected
          ? `Reconnected ${out.surface.label} (${out.surface.modality}): reconciled ${out.reconciledEnvelopesCount} buffered offline outbox envelope(s) through EP-A..EP-E with 0 duplicates.`
          : `Disconnected ${out.surface.label} (${out.surface.modality}): protected cross-surface intents now buffer in durable offline outbox (only offline-leased scopes permitted).`,
        snapshot: reactivityEngine.getSnapshot(),
      });
    } catch (err) {
      return res.status(400).json({
        ok: false,
        error: err instanceof Error ? err.message : 'Invalid surface toggle',
      });
    }
  }

  if (action === 'dispatch_unified_surface') {
    const surfaceId = String(req.body?.surfaceId || 'WEB_GENESIS_MAC');
    const targetCapabilityId =
      typeof req.body?.targetCapabilityId === 'string' && req.body.targetCapabilityId.trim()
        ? req.body.targetCapabilityId.trim()
        : 'cap.greenlane.patch_passkey_verifier';
    const intentSummary = String(req.body?.intentSummary || '').trim().slice(0, 220);
    if (!intentSummary) {
      return res.status(400).json({ ok: false, error: 'Provide a cross-surface intent summary.' });
    }
    try {
      const out = reactivityEngine.dispatchUnifiedSurfaceIntent({
        surfaceId,
        targetCapabilityId,
        intentSummary,
      });
      return res.json({
        ok: true,
        message: out.idempotentReplay
          ? `Idempotent replay deduplicated (${out.envelope.envelopeId} · ${out.envelope.settlementState}) — 0 duplicate effects.`
          : out.bufferedOffline
            ? `Surface offline: buffered ${out.envelope.envelopeId} in durable outbox (${out.envelope.settlementState}). Reconnect surface to reconcile automatically.`
            : `Dispatched ${out.envelope.envelopeId} (${out.envelope.originModality}) across Web · App · Console -> ${out.envelope.settlementState} (f_${out.envelope.fencingToken ?? 'n/a'}).`,
        snapshot: reactivityEngine.getSnapshot(),
      });
    } catch (err) {
      return res.status(400).json({
        ok: false,
        error: err instanceof Error ? err.message : 'Unable to dispatch unified intent',
      });
    }
  }

  return res.status(400).json({ ok: false, error: `Unsupported reactivity action: ${action}` });
});

// ---------------------------------------------------------------------------
// OMNIFLOW REAL-TIME CROSS-SURFACE COLLABORATION BUS (/api/omniflow/*)
// ---------------------------------------------------------------------------
app.get('/api/omniflow/state', (_req, res) => {
  res.json(omniflowLiveBus.getSnapshot());
});

app.get('/api/omniflow/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders?.();

  const sendSnap = (snap: ReturnType<typeof omniflowLiveBus.getSnapshot>) => {
    res.write(`event: omniflow_snapshot\ndata: ${JSON.stringify(snap)}\n\n`);
  };

  sendSnap(omniflowLiveBus.getSnapshot());
  const unsubscribe = omniflowLiveBus.subscribe(sendSnap);

  const keepAlive = setInterval(() => {
    res.write(': omniflow-keepalive\n\n');
  }, 15_000);
  keepAlive.unref?.();

  req.on('close', () => {
    clearInterval(keepAlive);
    unsubscribe();
  });
});

app.post('/api/omniflow/register', (req, res) => {
  try {
    const participant = omniflowLiveBus.registerParticipant({
      agentId: String(req.body?.agentId ?? ''),
      displayName: typeof req.body?.displayName === 'string' ? req.body.displayName : undefined,
      surfaceClass: req.body?.surfaceClass,
      transport: req.body?.transport,
      capabilities: Array.isArray(req.body?.capabilities) ? req.body.capabilities : undefined,
      formations: Array.isArray(req.body?.formations) ? req.body.formations : undefined,
      ttlMs: typeof req.body?.ttlMs === 'number' ? req.body.ttlMs : undefined,
    });
    return res.json({
      ok: true,
      participant,
      snapshot: omniflowLiveBus.getSnapshot(),
    });
  } catch (err) {
    return res.status(400).json({
      ok: false,
      error: err instanceof Error ? err.message : 'Unable to register participant',
    });
  }
});

app.post('/api/omniflow/heartbeat', (req, res) => {
  const agentId = String(req.body?.agentId ?? '').trim();
  if (!agentId) {
    return res.status(400).json({ ok: false, error: 'agentId required' });
  }
  const participant = omniflowLiveBus.heartbeatParticipant(agentId);
  if (!participant) {
    return res.status(404).json({ ok: false, error: 'participant_not_registered' });
  }
  return res.json({
    ok: true,
    participant,
    snapshot: omniflowLiveBus.getSnapshot(),
  });
});

app.post('/api/omniflow/disconnect', (req, res) => {
  const agentId = String(req.body?.agentId ?? '').trim();
  const out = omniflowLiveBus.disconnectParticipant(agentId);
  return res.json({
    ok: true,
    ...out,
    snapshot: omniflowLiveBus.getSnapshot(),
  });
});

app.post('/api/omniflow/validate-manifest', (req, res) => {
  const proposedFiles = Array.isArray(req.body?.proposedFiles)
    ? req.body.proposedFiles.map((f: unknown) => String(f ?? ''))
    : [];
  const maxFiles = Number(req.body?.maxFiles) || 5;
  const validation = validateUnsealedChangeManifest(proposedFiles, maxFiles);

  const probeSnap = omniflowLiveBus.getSnapshot().externalSpineProbe;
  const requiredComponents: ExternalComponentProbeInput[] = Array.isArray(
    req.body?.requiredComponents
  )
    ? req.body.requiredComponents
    : req.body?.requireExternalSpineLive
      ? [
          {
            componentId: 'estate-bus-external-spine',
            status: probeSnap.status,
            retiredOkeIpDetected: probeSnap.retiredOkeIpDetected,
            targetUrl: probeSnap.targetUrl,
            errorDetail: probeSnap.errorDetail,
          },
        ]
      : [];

  const zeroGaslightDecision = evaluateZeroGaslightAdmission({
    workerId: String(req.body?.workerId ?? 'pre-dispatch-gate'),
    workerQuadAttested: req.body?.workerQuadAttested !== false,
    requiresProtectedMutation: req.body?.requiresProtectedMutation !== false,
    proposedFiles,
    observedDiffFiles: Array.isArray(req.body?.observedDiffFiles)
      ? req.body.observedDiffFiles.map((f: unknown) => String(f ?? ''))
      : undefined,
    requiredComponents,
    maxFiles,
  });

  const statusCode =
    req.body?.enforceZeroGaslight === true && !zeroGaslightDecision.admitted
      ? zeroGaslightDecision.httpStatus
      : 200;

  return res.status(statusCode).json({
    ok: zeroGaslightDecision.admitted,
    ...validation,
    zeroGaslightDecision,
  });
});

app.get('/api/omniflow/mathematical-proof', (_req, res) => {
  const proof = runBoundaryEliminationProofSuite();
  const spineLive =
    omniflowLiveBus.getSnapshot().externalSpineProbe.status === 'LIVE_VERIFIED';
  const settlement = getRecoveryMandateSettlementSnapshot(spineLive);
  return res.json({ ok: proof.mathematicalTheoremProven, proof, settlement });
});

app.post('/api/omniflow/mathematical-proof', (_req, res) => {
  const proof = runBoundaryEliminationProofSuite();
  const spineLive =
    omniflowLiveBus.getSnapshot().externalSpineProbe.status === 'LIVE_VERIFIED';
  const settlement = getRecoveryMandateSettlementSnapshot(spineLive);
  return res.json({ ok: proof.mathematicalTheoremProven, proof, settlement });
});

function buildLiveUniversalSettlement() {
  const autoSync = getAutonomousSyncStatus(__dirname);
  const syncTelemetry = readSyncTelemetrySnapshot(__dirname);
  const busSnap = omniflowLiveBus.getSnapshot();
  const probe = busSnap.externalSpineProbe;
  return evaluateUniversalKarmicSettlement({
    autoSyncExternalAccepted: Boolean(autoSync.lastAcceptedBundleSha256),
    autoSyncHeadSha: autoSync.currentHeadSha,
    autoSyncBundleSha256: autoSync.currentBundleSha256,
    autoSyncLastReason: syncTelemetry.lastEvent?.reason ?? null,
    externalBusLiveVerified: probe.status === 'LIVE_VERIFIED',
    externalBusDetail: probe.errorDetail ?? (probe.httpStatus ? `HTTP ${probe.httpStatus}` : null),
    externalKimiLiveVerified: false,
    externalIdpVerified: false,
    remoteFaultInjectionVerifiedCount: 0,
    registeredBusWorkerIds: busSnap.participants.map((p) => p.agentId),
    liveAuditInventory: latestLiveAuditInventory,
  });
}

app.get('/api/omniflow/universal-settlement', (_req, res) => {
  return res.json({
    ok: true,
    isLiveState: true,
    telemetryFreshness: 'LIVE_EXPRESS_RUNTIME',
    projectionMode: 'LIVE_EXPRESS_RUNTIME',
    settlement: buildLiveUniversalSettlement(),
  });
});

app.get('/api/karma/settlement', (_req, res) => {
  return res.json({
    ok: true,
    isLiveState: true,
    telemetryFreshness: 'LIVE_EXPRESS_RUNTIME',
    projectionMode: 'LIVE_EXPRESS_RUNTIME',
    settlement: buildLiveUniversalSettlement(),
  });
});

app.get('/api/passkey/health', async (_req, res) => {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3000);
    const probeRes = await fetch('https://passkey.mumchimp.com', {
      method: 'HEAD',
      signal: controller.signal,
    }).catch(() => null);
    clearTimeout(timer);
    return res.json({
      ok: true,
      isLiveState: true,
      telemetryFreshness: 'LIVE_EXPRESS_RUNTIME',
      host: 'passkey.mumchimp.com',
      projectionMode: 'LIVE_EXPRESS_RUNTIME',
      liveHeadHttpStatus: probeRes?.status ?? null,
      externalHttpReachable: Boolean(probeRes && probeRes.status < 500),
      externalPasskeyVerifyScriptRun: false,
      verdict: probeRes && probeRes.status < 500
        ? 'HTTP_REACHABLE_EXTERNAL_CEREMONY_STILL_REQUIRES_RUNNER'
        : 'LIVE_PROBE_FAILED_OR_TIMEOUT',
      generatedAtUtc: new Date().toISOString(),
    });
  } catch (err) {
    return res.json({
      ok: true,
      isLiveState: true,
      telemetryFreshness: 'LIVE_EXPRESS_RUNTIME',
      host: 'passkey.mumchimp.com',
      projectionMode: 'LIVE_EXPRESS_RUNTIME',
      liveHeadHttpStatus: null,
      externalHttpReachable: false,
      externalPasskeyVerifyScriptRun: false,
      verdict: err instanceof Error ? err.message : 'PROBE_UNAVAILABLE',
      generatedAtUtc: new Date().toISOString(),
    });
  }
});

app.get('/api/resilience/matrix', (_req, res) => {
  const spineLive =
    omniflowLiveBus.getSnapshot().externalSpineProbe.status === 'LIVE_VERIFIED';
  return res.json({
    ok: true,
    isLiveState: true,
    telemetryFreshness: 'LIVE_EXPRESS_RUNTIME',
    projectionMode: 'LIVE_EXPRESS_RUNTIME',
    matrix: evaluateMandatoryResilienceMatrix({
      externalCloudLive: spineLive,
      remoteFaultInjectionVerifiedCount: 0,
    }),
  });
});

app.post('/api/resilience/matrix', (_req, res) => {
  const spineLive =
    omniflowLiveBus.getSnapshot().externalSpineProbe.status === 'LIVE_VERIFIED';
  return res.json({
    ok: true,
    isLiveState: true,
    telemetryFreshness: 'LIVE_EXPRESS_RUNTIME',
    projectionMode: 'LIVE_EXPRESS_RUNTIME',
    matrix: evaluateMandatoryResilienceMatrix({
      externalCloudLive: spineLive,
      remoteFaultInjectionVerifiedCount: 0,
    }),
  });
});

app.get('/api/audit/all-seeing-eye', (_req, res) => {
  const autoSync = getAutonomousSyncStatus(__dirname);
  const probe = omniflowLiveBus.getSnapshot().externalSpineProbe;
  return res.json({
    ok: true,
    isLiveState: true,
    telemetryFreshness: 'LIVE_EXPRESS_RUNTIME',
    projectionMode: 'LIVE_EXPRESS_RUNTIME',
    audit: getAllSeeingEyeAuditSnapshot({
      autoSyncExternalAccepted: Boolean(autoSync.lastAcceptedBundleSha256),
      externalBusLiveVerified: probe.status === 'LIVE_VERIFIED',
      externalKimiLiveVerified: false,
      externalIdpVerified: false,
      liveInventory: latestLiveAuditInventory,
    }),
  });
});

app.post('/api/audit/refresh-github', async (_req, res) => {
  try {
    latestLiveAuditInventory = await refreshAllSeeingEyeLiveInventory();
    const autoSync = getAutonomousSyncStatus(__dirname);
    const probe = omniflowLiveBus.getSnapshot().externalSpineProbe;
    return res.json({
      ok: true,
      isLiveState: true,
      telemetryFreshness: 'LIVE_EXPRESS_RUNTIME',
      projectionMode: 'LIVE_EXPRESS_RUNTIME',
      refreshResult: latestLiveAuditInventory,
      audit: getAllSeeingEyeAuditSnapshot({
        autoSyncExternalAccepted: Boolean(autoSync.lastAcceptedBundleSha256),
        externalBusLiveVerified: probe.status === 'LIVE_VERIFIED',
        externalKimiLiveVerified: false,
        externalIdpVerified: false,
        liveInventory: latestLiveAuditInventory,
      }),
      settlement: buildLiveUniversalSettlement(),
    });
  } catch (err) {
    return res.status(502).json({
      ok: false,
      error: err instanceof Error ? err.message : 'GitHub inventory refresh failed',
    });
  }
});

app.get('/api/omniflow/pages-function-script', (_req, res) => {
  const fnPath = path.join(__dirname, 'functions/api/[[route]].ts');
  if (!fs.existsSync(fnPath)) {
    return res.status(404).type('text/plain').send('functions/api/[[route]].ts not found');
  }
  res.setHeader('Content-Type', 'text/typescript; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename="pages-api-route.ts"');
  return res.sendFile(fnPath);
});

app.post('/api/omniflow/onboard-worker', (req, res) => {
  try {
    const workerId = String(req.body?.workerId ?? 'BR-KIMI-01').trim() || 'BR-KIMI-01';
    const onboarding = reconcileBrowserWorkforceRefinement(workerId);
    if (!onboarding.refinement.validRefinement) {
      return res.status(422).json({
        ok: false,
        error: onboarding.refinement.summary,
        onboarding,
      });
    }

    omniflowLiveBus.registerParticipant({
      agentId: onboarding.worker.workerId,
      displayName: onboarding.worker.providerLabel,
      surfaceClass: 'WEB_BROWSER',
      transport: 'SSE_HTTPS',
      capabilities: onboarding.worker.capabilities,
      formations: onboarding.worker.formations,
      ttlMs: 300_000,
    });

    omniflowLiveBus.publishMessage({
      fromAgent: onboarding.worker.workerId,
      fromSurface: 'WEB_BROWSER',
      target: '@all',
      verb: 'STATUS',
      body: `[Schema Registration Only · ${onboarding.worker.capabilityId} v${onboarding.worker.semver}] 9-tuple refinement checked (${onboarding.worker.specialization}). AUTHENTICATED EXECUTION NOT YET VERIFIED (0/7 seats executed remotely; external auth=${onboarding.worker.externalBrowserAuthState}).`,
      correlationId: `corr-onboard-${onboarding.worker.workerId.toLowerCase()}`,
      idempotencyKey: `idem-onboard-${onboarding.worker.workerId.toLowerCase()}-v2`,
      requiresClaim: false,
    });

    return res.json({
      ok: true,
      onboarding,
      settlement: buildLiveUniversalSettlement(),
      snapshot: omniflowLiveBus.getSnapshot(),
    });
  } catch (err) {
    return res.status(400).json({
      ok: false,
      error: err instanceof Error ? err.message : 'Unable to onboard worker',
    });
  }
});

app.post('/api/omniflow/auto-sync-now', async (_req, res) => {
  try {
    const cycle = await runAutonomousSyncCycle(__dirname, {
      forcePush: true,
      trigger: 'manual_api',
    });
    const autoSync = getAutonomousSyncStatus(__dirname);
    const syncTelemetry = readSyncTelemetrySnapshot(__dirname);
    return res.json({
      ok: true,
      ...cycle,
      autoSync,
      lastReason: syncTelemetry.lastEvent?.reason ?? cycle.pushResult?.reason ?? null,
      settlement: buildLiveUniversalSettlement(),
    });
  } catch (err) {
    return res.status(500).json({
      ok: false,
      error: err instanceof Error ? err.message : 'Auto-sync cycle failed',
    });
  }
});

app.post('/api/omniflow/publish', (req, res) => {
  try {
    const proposedFiles = Array.isArray(req.body?.proposedFiles)
      ? req.body.proposedFiles.map((f: unknown) => String(f ?? ''))
      : undefined;
    const autoDecompose = Boolean(req.body?.autoDecompose);

    if (req.body?.requireExternalSpineLive === true) {
      const probeSnap = omniflowLiveBus.getSnapshot().externalSpineProbe;
      const zg = evaluateZeroGaslightAdmission({
        workerId: String(req.body?.fromAgent ?? 'founder-web-tab'),
        workerQuadAttested: req.body?.workerQuadAttested !== false,
        requiresProtectedMutation: Boolean(proposedFiles && proposedFiles.length > 0),
        proposedFiles: proposedFiles ?? [],
        requiredComponents: [
          {
            componentId: 'estate-bus-external-spine',
            status: probeSnap.status,
            retiredOkeIpDetected: probeSnap.retiredOkeIpDetected,
            targetUrl: probeSnap.targetUrl,
            errorDetail: probeSnap.errorDetail,
          },
        ],
      });
      if (!zg.admitted && (!autoDecompose || zg.blockedComponents.length > 0 || !req.body?.workerQuadAttested)) {
        return res.status(zg.httpStatus).json({
          ok: false,
          error: zg.explanation,
          zeroGaslightDecision: zg,
          snapshot: omniflowLiveBus.getSnapshot(),
        });
      }
    }

    const out = omniflowLiveBus.publishMessage({
      fromAgent: String(req.body?.fromAgent ?? 'founder-web-tab'),
      fromSurface: req.body?.fromSurface,
      target: typeof req.body?.target === 'string' ? req.body.target : '@all',
      verb: req.body?.verb,
      body: String(req.body?.body ?? ''),
      artifactRef: typeof req.body?.artifactRef === 'string' ? req.body.artifactRef : null,
      correlationId: typeof req.body?.correlationId === 'string' ? req.body.correlationId : undefined,
      idempotencyKey:
        typeof req.body?.idempotencyKey === 'string' ? req.body.idempotencyKey : undefined,
      requiresClaim:
        typeof req.body?.requiresClaim === 'boolean' ? req.body.requiresClaim : undefined,
      proposedFiles,
      autoDecompose,
    });
    return res.status(out.httpStatus).json({
      ...out,
      snapshot: omniflowLiveBus.getSnapshot(),
    });
  } catch (err) {
    return res.status(400).json({
      ok: false,
      error: err instanceof Error ? err.message : 'Unable to publish message',
    });
  }
});

app.post('/api/omniflow/lease', (req, res) => {
  const action = String(req.body?.action ?? '').toUpperCase();
  const envelopeId = String(req.body?.envelopeId ?? '');

  if (action === 'CLAIM') {
    const out = omniflowLiveBus.claimLease({
      envelopeId,
      workerId: String(req.body?.workerId ?? ''),
      expectedMinFence:
        typeof req.body?.expectedMinFence === 'number' ? req.body.expectedMinFence : undefined,
    });
    return res.status(out.httpStatus).json({
      ...out,
      snapshot: omniflowLiveBus.getSnapshot(),
    });
  }

  if (action === 'SUBMIT_EFFECT') {
    const out = omniflowLiveBus.submitEffectWithFence({
      envelopeId,
      workerId: String(req.body?.workerId ?? ''),
      fencingToken: Number(req.body?.fencingToken ?? 0),
      artifactRef: typeof req.body?.artifactRef === 'string' ? req.body.artifactRef : undefined,
      note: typeof req.body?.note === 'string' ? req.body.note : undefined,
    });
    return res.status(out.httpStatus).json({
      ...out,
      snapshot: omniflowLiveBus.getSnapshot(),
    });
  }

  if (action === 'VERIFY_EFFECT') {
    const out = omniflowLiveBus.verifyIndependently({
      envelopeId,
      verifierId: String(req.body?.verifierId ?? 'karma-independent-verifier'),
      evidenceNote: String(req.body?.evidenceNote ?? 'Independent verifier receipt recorded'),
    });
    return res.status(out.httpStatus).json({
      ...out,
      snapshot: omniflowLiveBus.getSnapshot(),
    });
  }

  return res.status(400).json({ ok: false, error: `Unsupported lease action: ${action}` });
});

app.post('/api/omniflow/probe-external', async (req, res) => {
  const url = String(req.body?.url ?? DEFAULT_EXTERNAL_SPINE_URL);
  const receipt = await omniflowLiveBus.probeExternalSpine(url);
  return res.json({
    ok: receipt.status === 'LIVE_VERIFIED',
    receipt,
    snapshot: omniflowLiveBus.getSnapshot(),
  });
});

app.get('/api/omniflow/cli-script', (_req, res) => {
  const cliPath = path.join(__dirname, 'scripts/estate-bus-cli.mjs');
  if (!fs.existsSync(cliPath)) {
    return res.status(404).type('text/plain').send('estate-bus-cli.mjs not found');
  }
  res.setHeader('Content-Type', 'text/javascript; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename="estate-bus-cli.mjs"');
  return res.sendFile(cliPath);
});

app.get('/api/omniflow/worker-script', (_req, res) => {
  const workerPath = path.join(__dirname, 'scripts/cloudflare-omniflow-bus.ts');
  if (!fs.existsSync(workerPath)) {
    return res.status(404).type('text/plain').send('cloudflare-omniflow-bus.ts not found');
  }
  res.setHeader('Content-Type', 'text/typescript; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename="cloudflare-omniflow-bus.ts"');
  return res.sendFile(workerPath);
});

// ---------------------------------------------------------------------------
// OPERATION PHOENIX v2: DAILY COLD-BOOT, ROUND TABLE & CLOSED-LOOP FSM GATE
// ---------------------------------------------------------------------------
app.get('/api/phoenix/state', (_req, res) => {
  res.json(phoenixBootEngine.getSnapshot());
});

app.get('/api/phoenix/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders?.();

  const sendSnap = (snap: ReturnType<typeof phoenixBootEngine.getSnapshot>) => {
    res.write(`event: phoenix_snapshot\ndata: ${JSON.stringify(snap)}\n\n`);
  };

  sendSnap(phoenixBootEngine.getSnapshot());
  const unsubscribe = phoenixBootEngine.subscribe(sendSnap);

  const keepAlive = setInterval(() => {
    res.write(': phoenix-keepalive\n\n');
  }, 15_000);
  keepAlive.unref?.();

  req.on('close', () => {
    clearInterval(keepAlive);
    unsubscribe();
  });
});

app.post('/api/phoenix/drill', async (req, res) => {
  try {
    const rawTrigger = String(req.body?.triggerSource ?? 'FOUNDER_MANUAL');
    const triggerSource =
      rawTrigger === 'DAILY_SCHEDULE' ||
      rawTrigger === 'FAULT_INJECTION_TEST' ||
      rawTrigger === 'SANDBOX_REHEARSAL'
        ? rawTrigger
        : 'FOUNDER_MANUAL';
    const probeMode: PhoenixProbeMode =
      req.body?.probeMode === 'CLEANROOM_REHEARSAL' ? 'CLEANROOM_REHEARSAL' : 'LIVE_ESTATE';
    const rawFault = req.body?.simulateP0FaultStage;
    const simulateP0FaultStage: BootStageId | null =
      typeof rawFault === 'string' && rawFault.startsWith('STAGE_')
        ? (rawFault as BootStageId)
        : null;

    const run = await phoenixBootEngine.runColdBootDrill({
      triggerSource,
      probeMode,
      simulateP0FaultStage,
      runCleanRoomTsc: req.body?.runCleanRoomTsc !== false,
    });
    return res.json({
      ok: run.overallVerdict === 'QUORUM_READY_AWAITING_GO',
      run,
      snapshot: phoenixBootEngine.getSnapshot(),
    });
  } catch (err) {
    return res.status(500).json({
      ok: false,
      error: err instanceof Error ? err.message : 'Phoenix cold-boot drill failed',
    });
  }
});

app.post('/api/phoenix/decision', (req, res) => {
  const decision = String(req.body?.decision ?? '').toUpperCase();
  if (decision !== 'GO' && decision !== 'ABORT') {
    return res.status(400).json({ ok: false, error: 'decision must be GO or ABORT' });
  }
  const result = phoenixBootEngine.decideGoOrAbort({
    decision,
    reason: typeof req.body?.reason === 'string' ? req.body.reason : undefined,
    actor: typeof req.body?.actor === 'string' ? req.body.actor : undefined,
  });
  return res.status(result.httpStatus).json(result);
});

app.get('/api/phoenix/cli-script', (_req, res) => {
  const scriptPath = path.join(__dirname, 'scripts/phoenix-daily-drill.ts');
  if (!fs.existsSync(scriptPath)) {
    return res.status(404).type('text/plain').send('phoenix-daily-drill.ts not found');
  }
  res.setHeader('Content-Type', 'text/typescript; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename="phoenix-daily-drill.ts"');
  return res.sendFile(scriptPath);
});

app.get('/api/estate/fsm-constitution', (_req, res) => {
  const constitution = verifyAllEstateFsmsClosedLoop();
  return res.json({
    ok: constitution.allFsmsMathematicallyClosed && constitution.allLayersCoveredByFsms,
    constitution,
  });
});

app.get('/api/ioc/state', (_req, res) => {
  const snapshot = buildSystemFirstIocSnapshot(__dirname);
  return res.json({
    ok: snapshot.continuity.verified,
    isLiveState: true,
    telemetryFreshness: 'LIVE_EXPRESS_RUNTIME',
    snapshot,
  });
});

app.post('/api/ioc/evaluate-admission', (req, res) => {
  const validActuators: ReadonlyArray<InterchangeableActuatorId> = [
    'gemini',
    'glm-5.3',
    'deepseek',
    'kimi',
    'claude',
    'chatgpt',
  ];
  const rawActuator = String(req.body?.actuatorModel ?? 'glm-5.3') as InterchangeableActuatorId;
  const actuatorModel: InterchangeableActuatorId = validActuators.includes(rawActuator)
    ? rawActuator
    : 'glm-5.3';

  const proposedFiles = Array.isArray(req.body?.proposedFiles)
    ? req.body.proposedFiles.map((f: unknown) => String(f ?? ''))
    : [];
  const targetHosts = Array.isArray(req.body?.targetHosts)
    ? req.body.targetHosts.map((h: unknown) => String(h ?? ''))
    : [];

  const result = evaluateSystemFirstIocGate({
    actuatorModel,
    workerId: typeof req.body?.workerId === 'string' ? req.body.workerId : undefined,
    workerQuadAttested: req.body?.workerQuadAttested !== false,
    taskPrompt: typeof req.body?.taskPrompt === 'string' ? req.body.taskPrompt : '',
    proposedFiles,
    targetHosts,
    autoDecompose: Boolean(req.body?.autoDecompose),
  });
  return res.status(result.httpStatus).json({
    ok: result.admitted,
    result,
  });
});

app.get('/ROUTER.md', (_req, res) => {
  const fileAbs = path.join(__dirname, 'ROUTER.md');
  if (!fs.existsSync(fileAbs)) {
    return res.status(404).type('text/plain').send('ROUTER.md not found');
  }
  return res.type('text/markdown; charset=utf-8').sendFile(fileAbs);
});

app.get('/GENESIS_SPORE.dna', (_req, res) => {
  const fileAbs = path.join(__dirname, 'GENESIS_SPORE.dna');
  if (!fs.existsSync(fileAbs)) {
    return res.status(404).type('text/plain').send('GENESIS_SPORE.dna not found');
  }
  return res.type('application/json; charset=utf-8').sendFile(fileAbs);
});

// ---------------------------------------------------------------------------
// COMMERCIAL TURNKEY APPLIANCE SETUP, FOREIGN PHONE DR & ADVERSARIAL RED-TEAM
// ---------------------------------------------------------------------------
app.get('/api/appliance/state', async (_req, res) => {
  try {
    const snapshot = await applianceTurnkeyEngine.getSnapshot();
    return res.json({
      ok:
        snapshot.turnkeyFsmProof.closedLoopProven &&
        snapshot.phoneBootstrapFsmProof.closedLoopProven &&
        snapshot.perpetualFutureProof.allFutureInvariantsSatisfied,
      isLiveState: true,
      telemetryFreshness: 'LIVE_EXPRESS_RUNTIME',
      snapshot,
    });
  } catch (err) {
    return res.status(500).json({
      ok: false,
      error: err instanceof Error ? err.message : 'Unable to read appliance state',
    });
  }
});

app.get('/api/appliance/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders?.();

  const sendSnap = (snap: Awaited<ReturnType<typeof applianceTurnkeyEngine.getSnapshot>>) => {
    res.write(`event: appliance_snapshot\ndata: ${JSON.stringify(snap)}\n\n`);
  };

  void applianceTurnkeyEngine.getSnapshot().then(sendSnap).catch(() => {});
  const unsubscribe = applianceTurnkeyEngine.subscribe(sendSnap);

  const keepAlive = setInterval(() => {
    res.write(': appliance-keepalive\n\n');
  }, 15_000);
  keepAlive.unref?.();

  req.on('close', () => {
    clearInterval(keepAlive);
    unsubscribe();
  });
});

app.post('/api/appliance/run-setup', async (req, res) => {
  try {
    const validProfiles: ReadonlyArray<ApplianceProfileId> = [
      'PRIMARY_FOUNDER_WORKSTATION',
      'CLOUD_SOVEREIGN_NODE',
      'OFFLINE_ZERO_AGENT_LIFEBOAT',
    ];
    const rawProfile = String(
      req.body?.profile ?? 'PRIMARY_FOUNDER_WORKSTATION'
    ) as ApplianceProfileId;
    const profile: ApplianceProfileId = validProfiles.includes(rawProfile)
      ? rawProfile
      : 'PRIMARY_FOUNDER_WORKSTATION';
    const zeroAgentsOnlineMode = req.body?.zeroAgentsOnlineMode !== false;
    const rawFault = req.body?.injectFaultStage;
    const injectFaultStage: TurnkeyStageId | null =
      typeof rawFault === 'string' && rawFault.startsWith('STAGE_')
        ? (rawFault as TurnkeyStageId)
        : null;

    const receipt = await applianceTurnkeyEngine.runTurnkeySetup({
      profile,
      zeroAgentsOnlineMode,
      injectFaultStage,
    });
    const snapshot = await applianceTurnkeyEngine.getSnapshot();
    const ok = receipt.fsmStateReached === 'TURNKEY_OPERATIONAL_SEALED';
    return res.status(ok ? 200 : 409).json({
      ok,
      receipt,
      snapshot,
    });
  } catch (err) {
    return res.status(500).json({
      ok: false,
      error: err instanceof Error ? err.message : 'Turnkey setup execution failed',
    });
  }
});

app.post('/api/appliance/phone-bootstrap', async (req, res) => {
  try {
    const selectedFactors: RecoveryFactorId[] = Array.isArray(req.body?.selectedFactors)
      ? req.body.selectedFactors.map((f: unknown) => String(f ?? '') as RecoveryFactorId)
      : [];
    const locationPreset =
      typeof req.body?.locationPreset === 'string'
        ? (req.body.locationPreset as ForeignLocationPresetId)
        : 'TOKYO_ESIM_NO_DEVICES';
    const expectedEpochFence =
      typeof req.body?.expectedEpochFence === 'number'
        ? req.body.expectedEpochFence
        : undefined;

    const receipt = applianceTurnkeyEngine.runForeignPhoneBootstrap({
      locationPreset,
      selectedFactors,
      expectedEpochFence,
      simulateCorruptedBundle: Boolean(req.body?.simulateCorruptedBundle),
      duressSignal: Boolean(req.body?.duressSignal),
    });

    if (receipt.httpStatus === 200) {
      omniflowLiveBus.publishMessage({
        fromAgent: 'foreign-phone-sovereign-ignition',
        fromSurface: 'FOUNDER_COCKPIT',
        target: '@all',
        verb: 'STATUS',
        body: `FOREIGN_PHONE_SOVEREIGN_BOOTSTRAP_SEALED: Epoch rotated #${receipt.previousEpochFence} -> #${receipt.newEpochFence}; lost devices fenced out; cloud appliance attested.`,
        correlationId: `corr-phone-dr-${receipt.ceremonyId}`,
        idempotencyKey: `idem-phone-dr-${receipt.ceremonyId}`,
        requiresClaim: false,
      });
    }

    const snapshot = await applianceTurnkeyEngine.getSnapshot();
    return res.status(receipt.httpStatus).json({
      ok: receipt.httpStatus === 200,
      receipt,
      snapshot,
    });
  } catch (err) {
    return res.status(500).json({
      ok: false,
      error: err instanceof Error ? err.message : 'Foreign phone bootstrap failed',
    });
  }
});

app.post('/api/appliance/pair-device', async (req, res) => {
  const deviceId = String(req.body?.deviceId ?? '');
  const biometricAttested = req.body?.biometricAttested !== false;
  const out = applianceTurnkeyEngine.pairDeviceEndpoint({ deviceId, biometricAttested });
  const snapshot = await applianceTurnkeyEngine.getSnapshot();
  return res.status(out.httpStatus).json({
    ...out,
    snapshot,
  });
});

app.post('/api/appliance/verify-epoch', (req, res) => {
  const deviceId = String(req.body?.deviceId ?? 'unknown-device');
  const presentedEpochFence = Number(req.body?.presentedEpochFence ?? 0);
  const verdict = applianceTurnkeyEngine.verifyDeviceSessionEpoch(deviceId, presentedEpochFence);
  return res.status(verdict.httpStatus).json({
    ok: verdict.allowed,
    ...verdict,
    activeEpochFence: applianceTurnkeyEngine.getSovereignEpochFence(),
  });
});

app.post('/api/appliance/red-team', async (_req, res) => {
  const report = await applianceTurnkeyEngine.runAdversarialRedTeamSuite();
  const snapshot = await applianceTurnkeyEngine.getSnapshot();
  return res.json({
    ok: report.allAttacksDefeated,
    report,
    snapshot,
  });
});

app.get('/api/appliance/recovery-capsule', (_req, res) => {
  const capsule = applianceTurnkeyEngine.buildRecoveryCapsule();
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('X-Capsule-Sha256', capsule.capsuleIntegritySha256);
  res.setHeader(
    'Content-Disposition',
    'attachment; filename="meridian-zero-secret-recovery-capsule.json"'
  );
  return res.json(capsule);
});

export function stopServerBackgroundTimers(): void {
  clearInterval(omniflowWatchdog);
  if (typeof (grandUnion as unknown as { stopAutonomousLoop?: () => void }).stopAutonomousLoop === 'function') {
    (grandUnion as unknown as { stopAutonomousLoop: () => void }).stopAutonomousLoop();
  }
}

async function startServer() {
  grandUnion.startAutonomousLoop();
  if (process.env.NODE_ENV === 'production') {
    const distPath = path.join(__dirname, 'dist');
    app.use(express.static(distPath));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  } else {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`PennyD Dagster Gateway server listening on http://localhost:${PORT}`);
    const warmTimer = setTimeout(() => {
      startAutonomousBundleSyncDaemon(__dirname, 45_000);
      try {
        getProductionGuarantees();
      } catch {
        // Non-fatal background cache warm
      }
    }, 12_000);
    warmTimer.unref?.();
  });
}

const resolvedEntry = process.argv[1]
  ? (() => {
      try {
        return fs.realpathSync(path.resolve(process.argv[1]));
      } catch {
        return path.resolve(process.argv[1]);
      }
    })()
  : null;

const isMainEntrypoint = resolvedEntry
  ? import.meta.url === pathToFileURL(resolvedEntry).href ||
    import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
  : false;

if (isMainEntrypoint) {
  startServer();
}

export { app };
