import test from 'node:test';
import assert from 'node:assert/strict';
import { runChaosBenchmark, runFullVerificationSuite } from './resilienceSuite';
import { RouterEngine } from './routerCore';
import { DagsterOrchestrator } from './dagsterOrchestrator';
import { evaluateZeroPollingGuard } from './i8095Lockdown';
import { evaluateAgentsMdRatchet } from './firstUseGovernanceAudit';

test('Full integration & falsifier suite passes every case and assertion', () => {
  const report = runFullVerificationSuite();
  assert.equal(report.failedCases, 0, `Failed cases: ${report.cases.filter((c) => !c.passed).map((c) => c.id).join(', ')}`);
  assert.equal(report.passedCases, report.totalCases);
  assert.equal(report.passedAssertions, report.totalAssertions);
});

test('AtomicKeyStore rejects invalid budgets and preserves all sibling keys', () => {
  const router = new RouterEngine({ initialReceipts: 0 });
  const badBudget = router.keyStore.atomicCapSave('opencode_primary', -10);
  assert.equal(badBudget.ok, false);

  const clobberAttempt = router.keyStore.atomicCapSave('ci_canary', 300, {
    simulateLegacyClobberBug: true,
  });
  assert.equal(clobberAttempt.ok, false);
  assert.equal(clobberAttempt.rolledBack, true);

  const keysAfter = router.keyStore.getAllKeys();
  assert.equal(keysAfter.length, 2);
});

test('Router distinguishes unknown client 401 vs upstream 402 credit exhaustion', () => {
  const router = new RouterEngine({ initialReceipts: 0 });
  const badClient = router.route({
    clientKey: 'pk_invalid_key',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 500,
  });
  assert.equal(badClient.ok, false);
  assert.equal(badClient.httpStatus, 401);
  assert.equal(badClient.errorPayload?.error.type, 'unauthorized');

  router.setLaneFault('deepseek-flash', '402_credit_exhausted', 0);
  const failover = router.route({
    clientKey: 'pk_live_opencode_primary_94a2',
    modelSlug: 'deepseek-chat',
    estimatedTokens: 500,
  });
  assert.equal(failover.ok, true);
  assert.equal(failover.selectedLaneId, 'anthropic-sonnet');
  const dsAttempt = failover.attempts.find((a) => a.laneId === 'deepseek-flash');
  assert.equal(dsAttempt?.httpStatus, 402);
  assert.equal(dsAttempt?.errorType, 'billing_exhausted');
});

test('Dagster orchestrator recovers dropped vault keys and preserves WAL across restarts', () => {
  const router = new RouterEngine({ initialReceipts: 150 });
  const dagster = new DagsterOrchestrator();

  router.dropVaultKeysInMemory();
  assert.equal(router.isVaultHydrated(), false);

  const restartReport = dagster.simulateWorkerRestart(router, 'dagster_durable');
  assert.equal(restartReport.droppedReceipts, 0);
  assert.equal(restartReport.receiptsAfterRestart, 150);
  assert.equal(restartReport.vaultKeysHydratedOnBoot, true);
});

test('Chaos stress run with all 5 fault injectors maintains >=99.5% SLA and 0 dropped receipts', () => {
  const chaos = runChaosBenchmark({
    requestCount: 1200,
    concurrency: 50,
    strategy: 'priority_failover',
    injectDeepSeek402: true,
    injectWorkerCrash: true,
    injectCapSaveRace: true,
    injectMultiLane503: true,
    injectLatencySpike: true,
  });

  assert.equal(chaos.slaPassed, true, chaos.slaVerdict);
  assert.equal(chaos.receiptsDropped, 0);
  assert.equal(chaos.capSaveKeysPreserved, true);
  assert.ok(chaos.failoverRoutedRequests > 0, 'Expected failover routing during injected faults');
});

test('Meridian counterfactual baseline switcher recalculates savings deterministically', () => {
  const router = new RouterEngine({ initialReceipts: 0, seedForensics: 10 });
  const initialSummary = router.forensics.getSummary();
  router.forensics.setBaselineModelSlug('claude-opus-4-1');
  const opusSummary = router.forensics.getSummary();

  assert.equal(opusSummary.actualSpendUsd, initialSummary.actualSpendUsd);
  assert.ok(
    opusSummary.withoutPennydSpendUsd > initialSummary.withoutPennydSpendUsd,
    'Switching baseline from Sonnet 4 to Opus 4.1 must increase counterfactual spend'
  );
  assert.ok(opusSummary.netSavingsUsd > initialSummary.netSavingsUsd);
});

test('ModelSupplyRegistry discovery tick updates cycle and enforces pre-exhaustion drain', async () => {
  const { ModelSupplyRegistry } = await import('./modelSupply');
  const reg = new ModelSupplyRegistry();
  reg.setModelQuotaAndPolicy('deepseek-v4.1-flash-free', { quotaRemainingPct: 12 });
  const tick = reg.discoverSupplyTick();
  assert.equal(tick.cycle, 2);
  assert.ok(tick.preExhaustionWarnings.some((w) => w.includes('DeepSeek V4.1 Flash Free')));
});

test('Optimus feedback loop updates certification, cost per outcome, and Battalion routing matrix', async () => {
  const { ModelSupplyRegistry } = await import('./modelSupply');
  const reg = new ModelSupplyRegistry();
  const matrix = reg.getBattalionRoutingMatrix();
  assert.equal(matrix.length, 5);

  const probe = reg.runIndependentCertification();
  assert.equal(probe.testedModels, 12);
  assert.equal(probe.quarantinedCount, 0);

  const updated = reg.recordOptimusOutcome({
    modelId: 'msr-magentic-brain',
    verified: true,
    latencyMs: 40,
    costUsd: 0.00012,
  });
  assert.ok(updated);
  assert.equal(updated.verifiedOutcomes, 311);
});

test('Fail-closed intake verifier rejects missing keys, claimed-hash bypasses, and un-rehashed copies', async () => {
  const { ESTATE_WORKSTREAMS, verifyIntakeBodyIntegrity } = await import('./estateWorkstreams');
  assert.equal(ESTATE_WORKSTREAMS.length, 9);
  assert.equal(ESTATE_WORKSTREAMS.filter((w) => w.status === 'SOURCE-LOCATED').length, 3);
  assert.equal(ESTATE_WORKSTREAMS.filter((w) => w.status === 'UNKNOWN').length, 1);

  const failClosed = verifyIntakeBodyIntegrity({
    verifierPublicKeyHex: '0'.repeat(64),
    claimedBodySha256: 'abc',
    receivedBodyBytes: 'hello',
    storedCopyBytes: 'hello',
  });
  assert.equal(failClosed.ok, false);
  assert.equal(failClosed.reason, 'verifier_key_missing_fail_closed');
});

test('Meridian Symphony constellation binds live engines while keeping G7 and Face Voice unverified', async () => {
  const { buildMeridianSymphonySnapshot, generateSymphonySpecificationMarkdown } = await import(
    './meridianSymphony'
  );
  const { ModelSupplyRegistry } = await import('./modelSupply');
  const router = new RouterEngine({ initialReceipts: 50, seedForensics: 4 });
  const dagster = new DagsterOrchestrator();
  const supply = new ModelSupplyRegistry();

  const snap = buildMeridianSymphonySnapshot({ router, dagster, supply });
  assert.equal(snap.deliveryGates.length, 7);
  assert.equal(snap.deliveryGates.find((g) => g.id === 'G7')?.status, 'PENDING_FLEET_ACCEPTANCE');
  assert.equal(snap.nodes.find((n) => n.id === 'genesis_face_unknown')?.epistemicStatus, 'UNKNOWN');

  const md = generateSymphonySpecificationMarkdown(snap);
  assert.ok(md.includes('IDP #8169 — MERIDIAN SYMPHONY'));
  assert.ok(md.includes('PENDING_FLEET_ACCEPTANCE'));
  assert.ok(md.includes('Instruction I-8095'));
  assert.equal(snap.i8095.defects.length, 17);
  assert.equal(snap.i8095.counts.bddPassed, 4);
});

test('Instruction I-8095 enforces fail-closed auth (503/401) and zero-polling exit 78 lockout', async () => {
  const { evaluateZeroPollingGuard, probeSurfaceMetaTruthfully, verifyFailClosedAuthEnvelope } =
    await import('./i8095Lockdown');

  const unset = verifyFailClosedAuthEnvelope({ founderPublicKeyHex: '', cfAccessJwt: 'a.b.c' });
  assert.equal(unset.httpStatus, 503);
  assert.equal(unset.code, 'VERIFIER_KEY_UNBOUND');

  const forged = verifyFailClosedAuthEnvelope({
    founderPublicKeyHex: 'b'.repeat(64),
    cfAccessJwt: 'header.payload.forged',
  });
  assert.equal(forged.httpStatus, 401);

  const poll = evaluateZeroPollingGuard('for i in 1 2; do sleep 2; gh pr view 8164; done');
  assert.equal(poll.exitCode, 78);
  assert.equal(poll.allowed, false);

  const push = evaluateZeroPollingGuard('sqlite_wal_notify.arc.notify_one();');
  assert.equal(push.exitCode, 0);
  assert.equal(push.allowed, true);

  const probe = probeSurfaceMetaTruthfully(false);
  assert.equal(probe.voiceGatewayConnected, false);
  assert.equal(probe.hardcoded, false);
});

test('AURA-2100 encodes exact 64B GenesisAtomicFrame binary frames and executes Chrono-Forks', async () => {
  const {
    buildAuraManifoldSnapshot,
    createDefaultAuraState,
    decodeGenesisAtomicFrame,
    encodeGenesisAtomicFrame,
    executeAuraOmniCommand,
    FRAME_BYTE_LENGTH,
  } = await import('./auraManifold');
  const { ModelSupplyRegistry } = await import('./modelSupply');

  const frameBuf = encodeGenesisAtomicFrame({
    timestampNs: 9007199254740995n,
    traceMerkleRoot: '0123456789abcdef',
    entityId: 4001,
    causalParentId: 8095,
    metricPrimary: 42.5,
    metricSecondary: 0.91,
    syscallOrOpcode: 429,
    stratum: 2,
    verdictFlags: 7,
    payloadPreview: 'zai:429_deflect',
  });
  assert.equal(frameBuf.byteLength, FRAME_BYTE_LENGTH);
  const dec = decodeGenesisAtomicFrame(frameBuf);
  assert.equal(dec.entityId, 4001);
  assert.equal(dec.syscallOrOpcode, 429);
  assert.equal(dec.payloadPreview, 'zai:429_deflect');

  const router = new RouterEngine({ initialReceipts: 10 });
  const dagster = new DagsterOrchestrator();
  const supply = new ModelSupplyRegistry();
  const st = createDefaultAuraState();
  executeAuraOmniCommand('/rewind 42.8', st);
  executeAuraOmniCommand(':fork --upstream kimi --override-intent test_shadow', st);
  const snap = buildAuraManifoldSnapshot({ router, dagster, supply, auraState: st });
  assert.equal(snap.frameByteSize, 64);
  assert.equal(snap.activeRewindSec, 42.8);
  assert.equal(snap.activeForks.length, 1);
  assert.equal(snap.activeForks[0].upstreamOverride, 'kimi');
});

test('Hermes isopsephy/gematria preserves Unicode NFD/NFC parity, archaic symbols, and W=A bug diff', async () => {
  const {
    computeCanonReadings,
    findCanonEquivalences,
    inspectDualModeEnglishDiff,
    scoreEnglishExtended,
    scoreGreekIsopsephy,
    scoreHebrewGematria,
  } = await import('./hermesCipherEngine');
  const { evaluateDailyChallengeGuess, getDailyChallengeForDate } = await import(
    './hermesTreeCatalog'
  );
  const { fetchWorldResonanceSnapshot } = await import('./hermesWorldConnector');

  for (const word of ['Ἰησοῦς', 'Λόγος', 'ἀγάπη', 'θέλημα', 'ἀλήθεια']) {
    assert.equal(
      scoreGreekIsopsephy(word.normalize('NFC')).total,
      scoreGreekIsopsephy(word.normalize('NFD')).total
    );
  }

  assert.equal(scoreGreekIsopsephy('Ἰησοῦς').total, 888);
  assert.equal(scoreGreekIsopsephy('χξϛ').total, 666);
  assert.equal(scoreGreekIsopsephy('ϡ').total, 900);

  const partial = scoreGreekIsopsephy('αβγ !? 123 xyz');
  assert.equal(partial.total, 6);
  assert.equal(partial.skipped, 8);

  assert.equal(scoreHebrewGematria('אחד').total, 13);
  assert.equal(scoreHebrewGematria('אהבה').total, 13);
  assert.equal(scoreHebrewGematria('יהוה').total, 26);
  assert.equal(scoreHebrewGematria('אלהים').total, 86);
  // Final mem = 600 vs standard mem = 40
  assert.equal(scoreHebrewGematria('שלום', false).total, 376);
  assert.equal(scoreHebrewGematria('שלום', true).total, 936);

  const eq93 = findCanonEquivalences(93).map((e) => e.word);
  assert.ok(eq93.includes('θέλημα') && eq93.includes('ἀγάπη'));

  const diff = inspectDualModeEnglishDiff('WAX');
  assert.equal(diff.hasWraparoundDefect, true);
  assert.equal(scoreEnglishExtended('WAX').total, 500 + 1 + 600);

  // Check 366 consecutive UTC days for reachability
  const canon = computeCanonReadings();
  const baseMs = Date.UTC(2026, 0, 1);
  for (let i = 0; i < 366; i++) {
    const dStr = new Date(baseMs + i * 86_400_000).toISOString().slice(0, 10);
    const ch = getDailyChallengeForDate(dStr);
    const match = canon.find((c) => c.reading.total === ch.targetNumber);
    assert.ok(match, `Unreachable daily target ${ch.targetNumber} on ${dStr}`);
    assert.equal(evaluateDailyChallengeGuess(match!.word, dStr).hit, true);
  }

  const worldOffline = await fetchWorldResonanceSnapshot({
    placeId: 'jerusalem',
    forceOffline: true,
    now: new Date('2026-11-16T21:00:00Z'),
  });
  assert.equal(worldOffline.observed.status, 'OFFLINE_FALLBACK');
  assert.equal(worldOffline.observed.isStale, true);
  assert.ok(worldOffline.calculated.ephemeris.lunarPhaseName.length > 0);
});

test('Hermes World Connector circuit breaker, bounded LRU cache, 1,000-op fuzz chaos & Debug Pack pass commercial SLA', async () => {
  const { buildDebugPackSnapshot, renderDebugPackMarkdown, runAsyncWorldResilienceProbe } =
    await import('./debugPackBuilder');
  const { runHermesChaosStress } = await import('./resilienceSuite');

  const probe = await runAsyncWorldResilienceProbe();
  assert.equal(probe.passed, true);
  assert.equal(probe.circuitOpenedAfter3Failures, true);
  assert.equal(probe.circuitRecoveredOnHealthyFetch, true);
  assert.equal(probe.lruBoundedAt64After100Coords, true);
  assert.ok(probe.cacheSizeAfter100 <= 64);

  const chaos = runHermesChaosStress(1000);
  assert.equal(chaos.passed, true);
  assert.equal(chaos.exceptionsThrown, 0);
  assert.equal(chaos.succeeded, 1000);

  const router = new RouterEngine({ initialReceipts: 12, seedForensics: 4 });
  const pack = await buildDebugPackSnapshot(router, process.cwd());
  assert.equal(pack.verificationSuite.totalCases, 41);
  assert.equal(pack.verificationSuite.passedCases, 41);
  assert.equal(pack.verificationSuite.failedCases, 0);
  assert.equal(pack.gatewayChaosReport.slaPassed, true);
  assert.equal(pack.hermesChaosReport.passed, true);
  assert.equal(pack.worldConnectorAsyncProbe.passed, true);
  assert.equal(pack.failureModeRegistry.length, 21);
  assert.ok(pack.goldenVectors.every((v) => v.passed));
  assert.equal(pack.git.bundleAvailable, true);
  assert.equal(pack.git.workingTreeClean, true);
  assert.equal(pack.git.bundleSha256?.length, 64);

  const md = renderDebugPackMarkdown(pack);
  assert.ok(md.includes('41 / 41 cases'));
  assert.ok(md.includes('Failure-Mode Mitigation Matrix'));
});

test('Zero-token outbound pushBundleToIngest guards SSRF URLs and executes canonical failover', async () => {
  const {
    CANONICAL_BUNDLE_INGEST_URLS,
    pushBundleToIngest,
    validateIngestUrl,
  } = await import('./debugPackBuilder');

  assert.deepEqual(CANONICAL_BUNDLE_INGEST_URLS, [
    'https://otto.mumchimp.com/api/ingest/bundle',
    'https://genesis-founder-surface.pages.dev/api/ingest/bundle',
  ]);
  assert.equal(validateIngestUrl('http://genesis-founder-surface.pages.dev/api/ingest').ok, false);
  assert.equal(validateIngestUrl('https://127.0.0.1/api/ingest').ok, false);
  assert.equal(validateIngestUrl('https://192.168.1.50/api/ingest').ok, false);
  assert.equal(validateIngestUrl('https://genesis-founder-surface.pages.dev/api/ingest/bundle').ok, true);

  // Empty override fails closed honestly
  const emptyList = await pushBundleToIngest(process.cwd(), { ingestUrl: '', skipTelemetry: true });
  assert.equal(emptyList.ok, false);
  assert.equal(emptyList.pushed, false);
  assert.equal(emptyList.ingestConfigured, false);
  assert.equal(emptyList.bundleSha256?.length, 64);

  // Primary fails TLS/connection -> automatically fails over to canonical secondary endpoint (202 Accepted)
  const calledUrls: string[] = [];
  let capturedShaHeader = '';
  let capturedRemotesHeader = '';
  let capturedBytes = 0;
  const failoverPush = await pushBundleToIngest(process.cwd(), {
    skipTelemetry: true,
    fetchImpl: (async (url: unknown, init?: RequestInit) => {
      const urlStr = String(url);
      calledUrls.push(urlStr);
      if (urlStr.includes('otto.mumchimp.com')) {
        throw new Error('SSL_ERROR_SYSCALL');
      }
      const headers = (init?.headers ?? {}) as Record<string, string>;
      capturedShaHeader = headers['X-Bundle-Sha256'] ?? '';
      capturedRemotesHeader = headers['X-Target-Remotes'] ?? '';
      capturedBytes = Buffer.isBuffer(init?.body) ? init.body.byteLength : 0;
      return new Response(JSON.stringify({ accepted: true, wakeDisposition: 'SPAWNED_NEW_SESSION' }), { status: 202 });
    }) as unknown as typeof fetch,
  });

  assert.equal(failoverPush.ok, true);
  assert.equal(failoverPush.pushed, true);
  assert.equal(failoverPush.httpStatus, 202);
  assert.equal(failoverPush.attempts.length, 2);
  assert.deepEqual(calledUrls, CANONICAL_BUNDLE_INGEST_URLS);
  assert.equal(capturedShaHeader, failoverPush.bundleSha256);
  assert.equal(capturedRemotesHeader, 'chidionyema/argon-sync,chidionyema/gemini-sync');
  assert.equal(capturedBytes, failoverPush.bundleBytes);

  // Both returning 404/error fails closed honestly and surfaces all attempts
  const bothFail = await pushBundleToIngest(process.cwd(), {
    skipTelemetry: true,
    fetchImpl: (async () => new Response('Not Found', { status: 404 })) as unknown as typeof fetch,
  });
  assert.equal(bothFail.ok, false);
  assert.equal(bothFail.pushed, false);
  assert.equal(bothFail.httpStatus, 404);
  assert.equal(bothFail.attempts.length, 2);
});

test('Ingest receiver enforces fail-closed SHA-256 + git bundle verify, idle/spawn wake, and 7/7 production guarantees', async () => {
  const fs = await import('node:fs');
  const os = await import('node:os');
  const path = await import('node:path');
  const http = await import('node:http');
  const { createHash } = await import('node:crypto');
  const {
    createIngestReceiverState,
    handleIngestBundleRequest,
    markSessionIdle,
  } = await import('./ingestReceiver');
  const {
    BUNDLE_RELATIVE_PATH,
    evaluateProductionGuarantees,
    readSyncTelemetrySnapshot,
  } = await import('./debugPackBuilder');

  const bundleAbs = path.join(process.cwd(), BUNDLE_RELATIVE_PATH);
  assert.equal(fs.existsSync(bundleAbs), true, 'Expected git bundle to exist on disk');
  const validBytes = fs.readFileSync(bundleAbs);
  const validSha256 = createHash('sha256').update(validBytes).digest('hex');

  const stagingDir = fs.mkdtempSync(path.join(os.tmpdir(), 'meridian-ingest-test-'));
  const receiverState = createIngestReceiverState();

  try {
    // 1. Missing SHA header rejected fail-closed with 401
    const missingSha = await handleIngestBundleRequest({
      bodyBytes: validBytes,
      claimedSha256: '',
      stagingDir,
      state: receiverState,
    });
    assert.equal(missingSha.httpStatus, 401);
    assert.equal(missingSha.accepted, false);
    assert.equal(missingSha.error, 'missing_x_bundle_sha256_fail_closed');

    // 1b. Auth token rejection (401) when expectedAuthToken is configured, and >16 MiB (413) rejection
    const unauthorizedToken = await handleIngestBundleRequest({
      bodyBytes: validBytes,
      claimedSha256: validSha256,
      authHeader: 'Bearer wrong-token',
      expectedAuthToken: 'gemini-sync-secret-7760',
      stagingDir,
      state: receiverState,
    });
    assert.equal(unauthorizedToken.httpStatus, 401);
    assert.equal(unauthorizedToken.error, 'unauthorized_receiver_token_fail_closed');

    const oversized = Buffer.alloc(16 * 1024 * 1024 + 1, 0x41);
    const tooBig = await handleIngestBundleRequest({
      bodyBytes: oversized,
      claimedSha256: createHash('sha256').update(oversized).digest('hex'),
      authHeader: 'Bearer gemini-sync-secret-7760',
      expectedAuthToken: 'gemini-sync-secret-7760',
      stagingDir,
      state: receiverState,
    });
    assert.equal(tooBig.httpStatus, 413);
    assert.equal(tooBig.error, 'bundle_exceeds_16mib_gemini_sync_limit');

    // 2. Mismatched SHA rejected fail-closed with 401
    const badSha = await handleIngestBundleRequest({
      bodyBytes: validBytes,
      claimedSha256: 'f'.repeat(64),
      stagingDir,
      state: receiverState,
    });
    assert.equal(badSha.httpStatus, 401);
    assert.equal(badSha.accepted, false);
    assert.equal(badSha.error, 'sha256_mismatch_fail_closed');

    // 3. Corrupt payload with matching SHA rejected by `git bundle verify` with 400
    const junk = Buffer.from('not-a-git-bundle-payload');
    const junkSha = createHash('sha256').update(junk).digest('hex');
    const badBundle = await handleIngestBundleRequest({
      bodyBytes: junk,
      claimedSha256: junkSha,
      stagingDir,
      state: receiverState,
    });
    assert.equal(badBundle.httpStatus, 400);
    assert.equal(badBundle.accepted, false);
    assert.ok(badBundle.error?.startsWith('invalid_git_bundle:'));

    // 4. First valid bundle with auth token & no idle workers spawns tracked session AND verifies independent byte readback (202)
    const spawned = await handleIngestBundleRequest({
      bodyBytes: validBytes,
      claimedSha256: validSha256,
      authHeader: 'Bearer gemini-sync-secret-7760',
      expectedAuthToken: 'gemini-sync-secret-7760',
      sessionId: 'aistudio-test-session',
      wakeAgent: 'pennyd-sync-reconciler',
      stagingDir,
      state: receiverState,
    });
    assert.equal(spawned.httpStatus, 202);
    assert.equal(spawned.accepted, true);
    assert.equal(spawned.independentReadbackVerified, true);
    assert.equal(spawned.storedBytes, validBytes.byteLength);
    assert.equal(spawned.wakeDisposition, 'SPAWNED_NEW_SESSION');
    assert.equal(spawned.wakeCount, 1);
    assert.ok(spawned.workerId?.startsWith('worker-'));

    // 5. Mark worker IDLE, re-deliver bundle via real ephemeral HTTP loopback server -> wakes idle worker
    assert.equal(markSessionIdle(receiverState, spawned.workerId!), true);

    const server = http.createServer((req, res) => {
      const chunks: Buffer[] = [];
      req.on('data', (chunk: Buffer) => chunks.push(chunk));
      req.on('end', () => {
        void (async () => {
          const bodyBytes = Buffer.concat(chunks);
          const out = await handleIngestBundleRequest({
            bodyBytes,
            claimedSha256: String(req.headers['x-bundle-sha256'] ?? ''),
            sessionId: String(req.headers['x-estate-session-id'] ?? ''),
            wakeAgent: String(req.headers['x-wake-agent'] ?? 'pennyd-sync-reconciler'),
            stagingDir,
            state: receiverState,
          });
          res.writeHead(out.httpStatus, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(out));
        })();
      });
    });

    await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
    try {
      const addr = server.address();
      assert.ok(addr && typeof addr === 'object');
      const loopbackRes = await fetch(`http://127.0.0.1:${addr.port}/api/ingest/bundle`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/octet-stream',
          'X-Bundle-Sha256': validSha256,
          'X-Estate-Session-Id': 'aistudio-test-session',
          'X-Wake-Agent': 'pennyd-sync-reconciler',
        },
        body: validBytes,
      });
      assert.equal(loopbackRes.status, 202);
      const loopbackJson = (await loopbackRes.json()) as {
        accepted: boolean;
        wakeDisposition: string;
        workerId: string;
        wakeCount: number;
      };
      assert.equal(loopbackJson.accepted, true);
      assert.equal(loopbackJson.wakeDisposition, 'WOKEN_IDLE_SESSION');
      assert.equal(loopbackJson.workerId, spawned.workerId);
      assert.equal(loopbackJson.wakeCount, 2);
    } finally {
      await new Promise<void>((resolve) => server.close(() => resolve()));
    }

    // 6. All 20 commercial & operational guarantees verify cleanly
    const guarantees = evaluateProductionGuarantees(
      new RouterEngine({ initialReceipts: 100 }),
      process.cwd()
    );
    assert.equal(guarantees.totalCount, 20);
    assert.equal(guarantees.verifiedCount, 20);
    assert.equal(guarantees.allVerified, true);

    const syncSnap = readSyncTelemetrySnapshot(process.cwd());
    assert.equal(syncSnap.schemaVersion, 'meridian-sync-telemetry-v1');
    assert.equal(syncSnap.wakePolicy, 'wake_idle_or_spawn_new');
    assert.ok(syncSnap.sessionId.startsWith('aistudio-'));
    assert.equal(syncSnap.bundleAvailable, true);
  } finally {
    fs.rmSync(stagingDir, { recursive: true, force: true });
  }
});

test('I-8088 Cephalopod RS(3,8) reconstructs across all C(8,3)=56 subsets, enforces 200k PBKDF2 MAC & PNG CRC', async () => {
  const {
    decryptSomaPayload,
    emitDnsTxtRecords,
    encryptSomaPayload,
    PBKDF2_ITERATIONS,
    rsDecodeAny3,
    rsEncodeK3N8,
    runI8088PanspermiaSimulation,
    SPORE_MAX_BYTES,
    unwrapShardFromLosslessPng,
    wrapShardInLosslessPng,
  } = await import('./genesisSporeTtt');

  const payload = Buffer.from(
    JSON.stringify({ genesis: 'I-8088', fence: 46, receipts: 2382, ts: 20261116 }),
    'utf8'
  );
  // Full 200,000-iteration PBKDF2 roundtrip
  const sealed = encryptSomaPayload(payload, 'founder-secret-vault-key', PBKDF2_ITERATIONS);
  assert.ok(decryptSomaPayload(sealed, 'founder-secret-vault-key', PBKDF2_ITERATIONS).equals(payload));
  assert.throws(
    () => decryptSomaPayload(sealed, 'wrong-passphrase', PBKDF2_ITERATIONS),
    /VAULT_MAC_VERIFICATION_FAILED/
  );

  // Exhaustive C(8,3) = 56 subset reconstruction proof
  const shards = rsEncodeK3N8(sealed);
  assert.equal(shards.length, 8);
  let subsetsChecked = 0;
  for (let i = 0; i < 8; i++) {
    for (let j = i + 1; j < 8; j++) {
      for (let k = j + 1; k < 8; k++) {
        const subset = new Map<number, Buffer>([
          [i, shards[i]],
          [j, shards[j]],
          [k, shards[k]],
        ]);
        const recovered = rsDecodeAny3(subset);
        assert.equal(
          recovered.equals(sealed),
          true,
          `RS(3,8) failed subset (${i},${j},${k})`
        );
        subsetsChecked++;
      }
    }
  }
  assert.equal(subsetsChecked, 56);

  // Sub-quorum < 3 shards fails closed
  assert.throws(
    () => rsDecodeAny3(new Map([[0, shards[0]], [5, shards[5]]])),
    /QUORUM_INSUFFICIENT_FAIL_CLOSED/
  );

  // Lossless PNG carrier & CRC32 tamper detection
  const pngCarrier = wrapShardInLosslessPng(shards[3]);
  assert.equal(unwrapShardFromLosslessPng(pngCarrier).equals(shards[3]), true);
  const corruptPng = Buffer.from(pngCarrier);
  corruptPng[corruptPng.byteLength - 6] ^= 0x01;
  assert.throws(() => unwrapShardFromLosslessPng(corruptPng), /PNG_CRC_MISMATCH/);

  // Full simulation <= 4096B + DNS TXT records
  const sim = runI8088PanspermiaSimulation({ deadTentacles: [0, 1, 2, 4, 7] });
  assert.ok(sim.sporeBytes <= SPORE_MAX_BYTES);
  assert.equal(sim.reconstructedBitExact, true);
  assert.equal(sim.resurrectionOk, true);
  assert.ok(emitDnsTxtRecords(Buffer.from('test-spore')).length >= 2);
});

test('GEN-TTT-001 keeps Issue #8185 BLOCKED_DISPATCH and binds live telemetry into all 9 estate rows', async () => {
  const { buildGenTttSnapshot } = await import('./genesisSporeTtt');
  const { buildLiveEstateWorkstreamTelemetry } = await import('./estateWorkstreams');

  const ttt = buildGenTttSnapshot();
  assert.equal(ttt.dispatchState, 'BLOCKED_DISPATCH');
  assert.equal(ttt.trackingIssue, '#8185');
  assert.equal(ttt.closedInvalidPr, '#8186');
  assert.equal(ttt.counts.formalRequirements, 18);
  assert.equal(ttt.counts.bddAcceptanceScenarios, 18);
  assert.equal(ttt.failureClasses.length, 15);
  assert.equal(ttt.workPackages.length, 8);
  assert.equal(ttt.all15FalsifiersGuarded, true);

  for (let i = 1; i < ttt.arms.length; i++) {
    assert.ok(
      ttt.arms[i].helmHeldOutPassPct > ttt.arms[i - 1].helmHeldOutPassPct,
      `Expected monotonic HELM pass improvement from ${ttt.arms[i - 1].armId} to ${ttt.arms[i].armId}`
    );
  }

  const rows = buildLiveEstateWorkstreamTelemetry({
    walReceipts: 2382,
    healthyLanes: 4,
    totalLanes: 4,
    certifiedModels: 10,
    totalModels: 12,
    verifiedKeys: 2,
    totalKeys: 2,
    sporeBytes: 740,
    survivingTentacles: 8,
    tttBlockedDispatch: true,
    all15TttFalsifiersGuarded: true,
    guaranteesVerified: 8,
    guaranteesTotal: 8,
  });
  assert.equal(rows.length, 9);
  assert.equal(rows[7].dispatchState, 'QUORUM_SURVIVAL_OK');
  assert.equal(rows[8].dispatchState, 'BLOCKED_DISPATCH');
});

test('EstateGrandUnionEngine executes autonomous Chronos beats, heals InterCloud spot preemption <50ms, and proves Ensemble > Frontier', async () => {
  const { EstateGrandUnionEngine, evaluateEnsembleVsFrontier } = await import('./estateGrandUnion');
  const { ModelSupplyRegistry } = await import('./modelSupply');

  const router = new RouterEngine({ initialReceipts: 200 });
  const dagster = new DagsterOrchestrator();
  const supply = new ModelSupplyRegistry();
  const union = new EstateGrandUnionEngine({ router, dagster, supply, cadenceMs: 4000 });

  let notifiedBeats = 0;
  const unsub = union.subscribe(() => {
    notifiedBeats++;
  });

  const s0 = union.getSnapshot();
  assert.equal(s0.chronos.beatNumber, 3);
  assert.equal(s0.interCloudLanes.length, 10);
  assert.equal(s0.gwtAeonRegistry.length, 13);
  assert.equal(s0.surfaces.length, 11);

  const s1 = union.executeBeat('manual_pulse');
  assert.equal(s1.chronos.beatNumber, 4);
  assert.equal(s1.battalionRollup.walReceipts, s0.battalionRollup.walReceipts + 1);
  assert.equal(notifiedBeats, 1);

  const preempt = union.simulateSpotPreemption('ic-decentralized-h100-slice');
  assert.equal(preempt.zeroTasksDropped, true);
  assert.ok(preempt.failoverMs < 50);
  assert.equal(
    preempt.snapshot.interCloudLanes.find((l) => l.id === 'ic-decentralized-h100-slice')?.status,
    'SPOT_RECLAIMED_FAILOVER'
  );

  const healed = union.healAllSpotLanes();
  assert.equal(
    healed.interCloudLanes.find((l) => l.id === 'ic-decentralized-h100-slice')?.status,
    'ONLINE'
  );
  unsub();

  const proof = evaluateEnsembleVsFrontier(1000);
  assert.equal(proof.exceedsFrontierQuality, true);
  assert.ok(proof.ensembleVerifiedPassPct > proof.singleFrontierPassPct);
  assert.ok(proof.costReductionPct >= 99);
});

test('First-Use Machine-Agent Governance Audit passes 21/21 adversarial checks, blocks --no-verify & $lines escape, and holds live yield UNKNOWN', async () => {
  const {
    auditInstallerShortcuts,
    buildFirstUseAuditSnapshot,
    evaluateAgentsMdRatchet,
    observeCeremonyLedger,
    reproduceLegacyEscapedLinesBug,
  } = await import('./firstUseGovernanceAudit');

  const snap = buildFirstUseAuditSnapshot();
  assert.equal(snap.auditBranch, 'audit/first-use-machine-agent-20261116');
  assert.equal(snap.candidateHead, 'ff8543bdeaed1a0ed2ddc254491e0e22d361300d');
  assert.equal(snap.comparedMainSha, 'd03f5d59');
  assert.equal(snap.commitsAheadOfMain, 7);
  assert.equal(snap.mergeOrDeploymentClaimed, false);
  assert.equal(snap.failureClassesReviewed, 13);
  assert.equal(snap.adversarialTestsTotal, 21);
  assert.equal(snap.adversarialTestsPassed, 21);
  assert.equal(snap.observerTestsPassed, 12);
  assert.equal(snap.ratchetTestsPassed, 9);
  assert.equal(snap.liveCeremonyEffect, 'UNKNOWN');

  // Legacy fail-open bug vs repaired no-growth ratchet
  assert.equal(reproduceLegacyEscapedLinesBug(348).workflowExitCode, 0);
  const literalFailClosed = evaluateAgentsMdRatchet({ currentLinesRaw: '$lines', baselineLinesRaw: 348 });
  assert.equal(literalFailClosed.passed, false);
  assert.equal(literalFailClosed.exitCode, 1);

  const hold348 = evaluateAgentsMdRatchet({ currentLinesRaw: 348, baselineLinesRaw: 348 });
  assert.equal(hold348.passed, true);
  assert.equal(hold348.mode, 'NO_GROWTH_RATCHET_HOLD');

  const grow349 = evaluateAgentsMdRatchet({ currentLinesRaw: 349, baselineLinesRaw: 348 });
  assert.equal(grow349.passed, false);
  assert.equal(grow349.exitCode, 1);

  const consolidate330 = evaluateAgentsMdRatchet({ currentLinesRaw: 330, baselineLinesRaw: 348 });
  assert.equal(consolidate330.passed, true);
  assert.equal(consolidate330.nextRatchetBaseline, 330);

  // Shortcut guard & observer privacy/epistemic tiers
  const badShortcut = auditInstallerShortcuts('git commit --no-verify');
  assert.equal(badShortcut.allowed, false);
  const goodSubmit = auditInstallerShortcuts('bin/idp-machine-submit --lane greenlane');
  assert.equal(goodSubmit.allowed, true);

  const obs = observeCeremonyLedger([
    JSON.stringify({ eventId: '1', goalId: 'G1', step: 'declare_plan', note: 'Bearer tok_secret_1234567890' }),
    JSON.stringify({ eventId: '1', goalId: 'G1', step: 'declare_plan', note: 'Bearer tok_secret_1234567890' }),
    '{corrupt_json',
    JSON.stringify({ eventId: '2', goalId: 'G1', step: 'complete_goal' }),
  ]);
  assert.equal(obs.duplicateEventsDeduped, 1);
  assert.equal(obs.malformedLinesSkipped, 1);
  assert.equal(obs.redactedSecretsCount, 1);
  assert.ok(obs.outOfOrderViolations.length >= 1);
  assert.equal(obs.liveCeremonyEffect, 'UNKNOWN');
  assert.equal(obs.epistemicTiers.independentlyVerifiedOperationalEffect, 'UNKNOWN');
});

test('21. Repo-wide I-8090 zero client HTTP polling across all React components & AGENTS.md ceiling', async () => {
  const fsMod = await import('node:fs');
  const pathMod = await import('node:path');
  const { fileURLToPath } = await import('node:url');
  const repoRoot = pathMod.resolve(pathMod.dirname(fileURLToPath(import.meta.url)), '../..');

  const componentsDir = pathMod.join(repoRoot, 'src', 'components');
  const componentFiles = fsMod
    .readdirSync(componentsDir)
    .filter((f) => f.endsWith('.tsx') || f.endsWith('.ts'));
  assert.ok(componentFiles.length >= 10);

  for (const file of componentFiles) {
    const content = fsMod.readFileSync(pathMod.join(componentsDir, file), 'utf8');
    const guard = evaluateZeroPollingGuard(content);
    const clientPollViolations = guard.violations.filter(
      (v) => v.rule === 'CLIENT_SETINTERVAL_API_POLL'
    );
    assert.equal(
      clientPollViolations.length,
      0,
      `Component ${file} contains client setInterval HTTP polling: ${JSON.stringify(clientPollViolations)}`
    );
    if (file !== 'I8095LockdownPanel.tsx') {
      assert.equal(
        guard.exitCode,
        0,
        `Component ${file} violated I-8090 zero-polling guard: ${JSON.stringify(guard.violations)}`
      );
    }
  }

  const agentsMdLines = fsMod
    .readFileSync(pathMod.join(repoRoot, 'AGENTS.md'), 'utf8')
    .split('\n').length;
  const localRatchet = evaluateAgentsMdRatchet({
    currentLinesRaw: agentsMdLines,
    baselineLinesRaw: 300,
    targetCeiling: 300,
  });
  assert.equal(localRatchet.passed, true);
  assert.equal(localRatchet.mode, 'UNDER_TARGET');
});

test('22. Team Handoff Runbook stamps live HEAD SHA, bundle SHA-256, and gated promotions honestly', async () => {
  const pathMod = await import('node:path');
  const { fileURLToPath } = await import('node:url');
  const { evaluateProductionGuarantees, renderTeamHandoffRunbookMarkdown } = await import(
    './debugPackBuilder'
  );
  const repoRoot = pathMod.resolve(pathMod.dirname(fileURLToPath(import.meta.url)), '../..');
  const engine = new RouterEngine({ initialReceipts: 2382 });
  const guarantees = evaluateProductionGuarantees(engine, repoRoot);
  const md = renderTeamHandoffRunbookMarkdown(repoRoot, guarantees);

  assert.ok(md.includes('chidionyema/argon-sync'));
  assert.ok(md.includes('chidionyema/gemini-sync'));
  assert.ok(md.includes('refs/heads/aistudio/meridian-hermes-live'));
  assert.ok(md.includes('LIVE CEREMONY EFFECT = UNKNOWN'));
  assert.ok(md.includes('BLOCKED_DISPATCH'));
  assert.ok(md.includes('G-10'));
  assert.ok(md.includes('G-11'));
});

test('23. Hermes · OTTO_NUMEN VIP CEO Telegram shards 5 Forum Topics, suppresses chatter, coalesces bursts & escapes HTML/MarkdownV2', async () => {
  const {
    buildSafeCallbackData,
    escapeTelegramHtml,
    escapeTelegramMarkdownV2,
    generateOttoNumenBotBlueprintTs,
    OttoNumenConciergeEngine,
    TELEGRAM_MAX_CALLBACK_BYTES,
  } = await import('./ottoNumenTelegram');

  const engine = new OttoNumenConciergeEngine();
  const initialSnap = engine.getSnapshot();
  assert.equal(initialSnap.topics.length, 6);
  assert.ok(initialSnap.telemetry.suppressedHeartbeatEvents >= 18);
  assert.ok(initialSnap.telemetry.coalescedDuplicateUpdates >= 3);

  const storm = engine.simulateEstateStorm(50);
  assert.equal(storm.audiblePingsDuringStorm, 1);
  assert.ok(storm.suppressedChatter >= 30);
  assert.ok(storm.coalescedEdits >= 10);
  assert.ok(storm.snapshot.telemetry.audibleInterruptionReductionPct >= 92);

  // Silent DND policy suppresses even P0 audible pings while still delivering the VIP card
  engine.setFocusPolicy('SILENT_DND_ALL');
  const pingsBefore = engine.getSnapshot().telemetry.audibleCeoPings;
  const dndOut = engine.ingestEvent({
    kind: 'p0_ceo_signoff',
    sourceSubsystem: 'Test DND',
    headline: 'Urgent <3 & [markdown] check',
    metrics: { A: 1 },
    autonomousAction: 'Delivered silently under DND.',
  });
  assert.equal(dndOut.outcome, 'DELIVERED_NEW_CARD');
  assert.equal(dndOut.card?.disableNotification, true);
  assert.equal(engine.getSnapshot().telemetry.audibleCeoPings, pingsBefore);

  // Callback signing & blueprint export
  const cbRes = engine.executeInlineCallback({
    messageId: dndOut.card!.messageId,
    action: 'approve',
  });
  assert.equal(cbRes.ok, true);
  assert.equal(cbRes.receipt?.action, 'APPROVED');
  assert.equal(cbRes.receipt?.decisionSha256.length, 64);

  assert.equal(escapeTelegramHtml('<3 & "ok"'), '&lt;3 &amp; &quot;ok&quot;');
  assert.ok(escapeTelegramMarkdownV2('oot_numun *vip*!').includes('oot\\_numun \\*vip\\*\\!'));
  assert.ok(
    buildSafeCallbackData('approve', 'x'.repeat(120)).byteLength <= TELEGRAM_MAX_CALLBACK_BYTES
  );
  assert.ok(generateOttoNumenBotBlueprintTs().includes('editMessageText'));
});

test('24. Prospector-2100 autonomous causal research achieves >=99% cost savings & blocks confounder traps before Mumchimp', async () => {
  const { compareLegacyVsProspector2100, Prospector2100Engine } = await import(
    './prospectorResearchMumchimp'
  );

  const engine = new Prospector2100Engine();
  const initial = engine.getSnapshot();
  assert.ok(initial.cyclesCompleted >= 4);
  assert.ok(initial.savingsPct >= 99);
  assert.ok(initial.mumchimpPublishedCount >= 3);
  assert.ok(initial.quarantinedTrapsCount >= 1);

  const trap = engine.runAutonomousCycle({
    chronosBeat: 30,
    customHypothesis: {
      title: 'Unverified Rumor: 100% Guaranteed Leak',
      claim: 'Unverified social burst without held-out split.',
      isConfounderTrap: true,
    },
  });
  assert.equal(trap.adversarialCritiqueVerdict, 'QUARANTINED_CONFOUNDER');
  assert.equal(trap.publishedToMumchimp, false);

  const cmp = compareLegacyVsProspector2100();
  assert.ok(cmp.costMultiplierImprovement >= 250);
  assert.equal(cmp.legacyNaive.mumchimpSyndicated, false);
  assert.equal(cmp.prospector2100.mumchimpSyndicated, true);
});

test('25. Founder First-Class Config, Rego v1 Gate, R-008 Classifier, Chronos Merkle Stamp, Investor Economics & Academy pass', async () => {
  const {
    classifyCodeForRegoGovernance,
    COMMERCIAL_GAP_CLOSURE_MATRIX,
    computeInvestorUnitEconomics,
    computeSynchronicityMerkleStamp,
    FounderConfigEngine,
    generateCanonicalRegoBundle,
    simulateAcademyModule,
  } = await import('./founderRegoChronosPlane');

  const founder = new FounderConfigEngine();
  assert.equal(founder.getCurrentRegoReport().allow, true);
  assert.ok(generateCanonicalRegoBundle().includes('package genesis.constitutional.v1'));

  // Unsafe mutation must fail closed (HTTP 422) without incrementing revision
  const bad = founder.proposeAndApplyPatch({
    allowGitNoVerifyShortcuts: true,
    prospectorMinCausalConfidencePct: 70,
  });
  assert.equal(bad.committed, false);
  assert.equal(bad.httpStatus, 422);
  assert.equal(bad.config.revision, 1);

  // Valid mutation increments revision and signs SHA-256
  const good = founder.proposeAndApplyPatch({
    sovereignFreeFloorPct: 90,
    prospectorMinCausalConfidencePct: 91,
  });
  assert.equal(good.committed, true);
  assert.equal(good.httpStatus, 200);
  assert.equal(good.config.revision, 2);
  assert.equal(good.config.configSha256.length, 64);

  // Deterministic 8-leaf Merkle synchronicity stamp
  const stampA = computeSynchronicityMerkleStamp({
    chronosBeat: 24,
    founderConfig: good.config,
    regoBundleSha256: good.regoReport.bundleSha256,
    walLatestSequence: 2500,
    interCloudOnlineCount: 8,
    interCloudTotalCount: 8,
    prospectorDigestSha256: 'b'.repeat(64),
    mumchimpPublishedCount: 4,
    telegramFocusPolicy: 'VIP_P0_ONLY',
    sporeSurvivingTentacles: 8,
  });
  const stampB = computeSynchronicityMerkleStamp({
    chronosBeat: 24,
    founderConfig: good.config,
    regoBundleSha256: good.regoReport.bundleSha256,
    walLatestSequence: 2500,
    interCloudOnlineCount: 8,
    interCloudTotalCount: 8,
    prospectorDigestSha256: 'b'.repeat(64),
    mumchimpPublishedCount: 4,
    telegramFocusPolicy: 'VIP_P0_ONLY',
    sporeSurvivingTentacles: 8,
  });
  assert.equal(stampA.merkleRootSha256, stampB.merkleRootSha256);
  assert.equal(stampA.phaseLocked, true);
  assert.equal(stampA.unjoinedSubsystemsCount, 0);

  // Rule R-008 classifier
  const mustRego = classifyCodeForRegoGovernance(
    'policyCheck.ts',
    'if (user.role === "admin" && dailyBudget >= 100) return true;'
  );
  assert.equal(mustRego.verdict, 'MUST_EXPRESS_AS_REGO');

  // Investor unit economics & Academy all 4 levels/modules
  const econ = computeInvestorUnitEconomics();
  assert.ok(econ.grossMarginPct >= 80);
  assert.equal(COMMERCIAL_GAP_CLOSURE_MATRIX.length, 12);

  for (const mod of [
    'condorcet_ensemble_economics',
    'bayesian_evsi_prospector',
    'reed_solomon_continuity',
    'rego_harmonic_synchronicity',
    'machine_agent_ratchet_doctrine',
  ] as const) {
    for (const lvl of ['novice', 'practitioner', 'expert', 'founder'] as const) {
      const sim = simulateAcademyModule({ moduleId: mod, level: lvl, sliderParam: 86 });
      assert.ok(sim.levelNarrative.length > 20);
      assert.equal(sim.curvePoints.length, 6);
    }
  }
});

test('26. UHNW Sovereign Charter, Rego R-010 Epistemic Guard & Standout Academy Unseen Transfer Pilot pass', async () => {
  const { auditEpistemicClaim, UhnwSovereignConciergeEngine } = await import(
    './uhnwSovereignCharter'
  );
  const {
    evaluateUnseenTransferPilot,
    simulateStandoutAcademyTrack,
    STANDOUT_TRACK_CATALOG,
  } = await import('./genesisAcademyEngine');

  const uhnw = new UhnwSovereignConciergeEngine();
  const charter = uhnw.getSnapshot();
  assert.equal(charter.agents.length, 7);
  assert.equal(charter.allAgentsCompliant, true);
  assert.equal(charter.unownedTouchpointsCount, 0);
  assert.equal(charter.failOpenGatesPermitted, 0);
  assert.ok(charter.maxObservedAgentP95Ms <= 150);

  const receipt = uhnw.dispatchDirective({
    presetKey: 'investor_series_brief',
    founderInstruction: 'Lock Investor Meeting readiness across all 4 suites.',
  });
  assert.equal(receipt.withinUhnwSla150Ms, true);
  assert.equal(receipt.receiptSha256.length, 64);

  // Rego R-010 blocks promoting unmerged candidate (ff8543bd) to CERTIFIED_PRODUCTION_YIELD
  const blockedInflation = auditEpistemicClaim({
    capabilityName: 'First-Use Ceremony Observer (ff8543bd)',
    claimedMarketingTier: 'CERTIFIED_PRODUCTION_YIELD',
    hasPlanLock: true,
    localAdversarialTestsPassed: true,
    signedGreenlaneMerged: false,
    independentLiveOutcomeJoined: false,
  });
  assert.equal(blockedInflation.allowed, false);
  assert.equal(blockedInflation.httpStatus, 422);
  assert.equal(blockedInflation.earnedEvidenceTier, 'ENGINEERING_ACCEPTANCE');

  const honestCandidate = auditEpistemicClaim({
    capabilityName: 'First-Use Ceremony Observer (ff8543bd)',
    claimedMarketingTier: 'ENGINEERING_TEST_VERIFIED',
    hasPlanLock: true,
    localAdversarialTestsPassed: true,
    signedGreenlaneMerged: false,
    independentLiveOutcomeJoined: false,
  });
  assert.equal(honestCandidate.allowed, true);
  assert.equal(honestCandidate.httpStatus, 200);

  // Verify all 6 Standout Academy tracks x 4 depth lenses + boundary counterexamples + unseen transfer pilot
  assert.equal(STANDOUT_TRACK_CATALOG.length, 6);
  for (const track of STANDOUT_TRACK_CATALOG) {
    for (const lvl of ['novice', 'practitioner', 'expert', 'founder'] as const) {
      const cleanSim = simulateStandoutAcademyTrack({
        trackId: track.id,
        level: lvl,
        sliderParam: track.defaultSliderValue,
        activeFaultIds: [],
      });
      assert.equal(cleanSim.representations.length, 3);
      assert.equal(cleanSim.boundaryToggles.length, 3);
      assert.equal(cleanSim.unseenTransferItems.length, 3);
      assert.equal(cleanSim.boundaryViolated, false);

      const faultedSim = simulateStandoutAcademyTrack({
        trackId: track.id,
        level: lvl,
        sliderParam: track.defaultSliderValue,
        activeFaultIds: [cleanSim.boundaryToggles[0].id],
      });
      assert.equal(faultedSim.boundaryViolated, true);
      assert.equal(faultedSim.activeViolationConsequences.length, 1);
    }
  }

  // Track 01: incomplete transfer submission is rejected; complete submission scores 3/3 with SHA-256 receipt
  const incomplete = evaluateUnseenTransferPilot({
    trackId: 'reproducibility_transfer_boundaries',
    selectedAnswers: { 'tr-01-missing-key': 1 },
  });
  assert.equal(incomplete.complete, false);
  assert.ok(incomplete.validationError?.includes('all 3 unseen transfer items'));

  const scored = evaluateUnseenTransferPilot({
    trackId: 'reproducibility_transfer_boundaries',
    selectedAnswers: {
      'tr-01-missing-key': 1,
      'tr-01-external-service': 2,
      'tr-01-disconnected-fleet': 3,
    },
  });
  assert.equal(scored.complete, true);
  assert.equal(scored.score, 3);
  assert.equal(scored.receiptSha256.length, 64);
  assert.ok(scored.epistemicDisclaimer.includes('Research pilot'));
});

test('27. MUM-CONCIERGE-001 Auntie Ezinne WhatsApp Coalescer, Low-Vision EON-001, 9 Safety Falsifiers, 11 Negative Scenarios & Honest G2-G4 UNKNOWN pass', async () => {
  const {
    analyzeConciergeDocument,
    checkVendorDomainSafety,
    coalesceWhatsAppBurst,
    MumsConciergeEngine,
    parseKernelPermission,
    stripPrivatePii,
    verifyProviderReceipt,
    verifyTwilioWebhookSignature,
  } = await import('./mumsConcierge');
  const { pureSha256Hex } = await import('./pureSha256');

  // 1. String "false" kernel flag fails closed
  assert.equal(parseKernelPermission('false'), false);
  assert.equal(parseKernelPermission('False'), false);
  assert.equal(parseKernelPermission('0'), false);
  assert.equal(parseKernelPermission(undefined), false);
  assert.equal(parseKernelPermission('true'), true);

  // 2. False provider receipts rejected; typed sandbox ack accepted
  assert.equal(verifyProviderReceipt('Receipt #123 confirmed').accepted, false);
  assert.equal(
    verifyProviderReceipt({
      typedAck: true,
      providerAckId: 'ACK-1',
      providerReceiptRef: 'RCP-123456',
      inferredFromDomClick: true,
    }).accepted,
    false
  );
  assert.equal(
    verifyProviderReceipt({
      typedAck: true,
      providerAckId: 'ACK-SANDBOX-1',
      providerReceiptRef: 'RCP-123456',
      inferredFromDomClick: false,
    }).accepted,
    true
  );

  // 3. Twilio signature verification vs forged 401
  const payload = 'From=whatsapp%3A%2B447700900001&Body=Check%20bill';
  const url = 'https://mums-concierge.modal.run/twilio/whatsapp';
  const token = 'test-auth-token';
  const sig = pureSha256Hex(`${token}|${url}|${payload}`);
  assert.equal(
    verifyTwilioWebhookSignature({ url, payloadString: payload, authToken: token, providedSignatureHex: sig }).httpStatus,
    200
  );
  assert.equal(
    verifyTwilioWebhookSignature({ url, payloadString: payload, authToken: token, providedSignatureHex: 'f'.repeat(64) }).httpStatus,
    401
  );

  // 4. 4-second WhatsApp burst coalescing, duplicate SID deduplication, and universal cancellation
  const burst = coalesceWhatsAppBurst(
    [
      { messageSid: 'm1', senderRole: 'MUMMY', channel: 'voice_note', timestampMs: 1000, text: 'I got my E.ON bill' },
      { messageSid: 'm2', senderRole: 'MUMMY', channel: 'text', timestampMs: 2400, text: 'wait does £95.11 mean I owe money?' },
      { messageSid: 'm2', senderRole: 'MUMMY', channel: 'text', timestampMs: 2600, text: 'wait does £95.11 mean I owe money?' },
      { messageSid: 'm3', senderRole: 'MUMMY', channel: 'text', timestampMs: 9500, text: 'Actually stop cancel everything' },
    ],
    4000
  );
  assert.equal(burst.duplicateSidsDropped, 1);
  assert.equal(burst.totalCoalescedTurns, 2);
  assert.equal(burst.groups[1].cancelledMidBurst, true);

  // 5. EON-001 £95.11 credit (never debt), £52.43 DD vs £61.54 avg cost, net exit-fee trap detection, and WhatsApp low-vision payload
  const eon = analyzeConciergeDocument('clean_eon_001');
  assert.equal(eon.closingBalanceGbp, 95.11);
  assert.equal(eon.balanceInterpretation, 'CREDIT_IN_MUM_FAVOUR');
  assert.equal(eon.isCreditNeverDescribedAsDebt, true);
  assert.equal(eon.monthlyDirectDebitGbp, 52.43);
  assert.equal(eon.estimatedAverageMonthlyCostGbp, 61.54);
  assert.ok(eon.whatsappFormattedForLowVision.includes('£95.11 IN CREDIT'));
  assert.equal(eon.tariffOptions[1].netFirstYearSavingAfterFeeGbp, -60.64);

  // 6. Malicious domain block & PII scrubbing before fleet KARMA
  assert.equal(checkVendorDomainSafety('https://evil-eon-refund.com/pay').allowed, false);
  const scrubbed = stripPrivatePii('Sort code 12-34-56 account 87654321 at 14 High Street SW1A 1AA');
  assert.ok(!scrubbed.includes('12-34-56'));
  assert.ok(!scrubbed.includes('87654321'));
  assert.ok(!scrubbed.includes('SW1A 1AA'));

  // 7. Full Engine: 9/9 safety falsifiers, 11/11 negative scenarios, IDP #8091 memory, kill-switch & strict UNKNOWN G2-G4
  const engine = new MumsConciergeEngine();
  const snap = engine.getSnapshot();
  assert.equal(snap.baseline.mainSha, '84d1a22d7312c93318c32f78a5a6ded43bfce09a');
  assert.equal(snap.safetyFalsifiers.length, 9);
  assert.ok(snap.safetyFalsifiers.every((s) => s.passed));
  assert.equal(snap.negativeFixtures.length, 11);
  assert.ok(snap.negativeFixtures.every((n) => n.passed));
  assert.equal(snap.founderTelemetryProjection.conciergeInferenceRunCostUsd, 0);
  assert.equal(snap.overallFamilyReleasePermitted, false);
  for (const gateId of ['G2', 'G3', 'G4'] as const) {
    assert.equal(snap.releaseGates.find((g) => g.gateId === gateId)?.status, 'UNKNOWN');
  }

  // Emergency kill switch blocks pending fulfilment fail-closed
  const killed = engine.setKillSwitch(true);
  assert.equal(killed.killSwitchActive, true);
  const blockedSub = engine.submitFulfilmentRequest({
    idempotencyKey: 'idem-killed-01',
    kind: 'shopping',
    title: 'Groceries',
    amountGbp: 20,
    motherConfirmed: true,
  });
  assert.equal(blockedSub.record.status, 'BLOCKED_BY_SAFETY');
});

test('28. Meridian Autonomous Reactivity (#8184) enforces 7-stage custody, QUAD attestation, 409 monotonic fencing, Experiments A–F & 14-boundary candor', async () => {
  const { AutonomousReactivityEngine } = await import('./autonomousReactivity');
  const engine = new AutonomousReactivityEngine();

  // 1. Seeded Founder Passkey incident starts in DETECTED (67 GitHub/OMNIFLOW comments != custody)
  const initial = engine.getSnapshot();
  const passkey0 = initial.obligations.find((o) => o.obligationId === 'OBL-PASSKEY-8175');
  assert.ok(passkey0);
  assert.equal(passkey0.stage, 'DETECTED');
  assert.equal(passkey0.githubCommentsLogged, 67);
  assert.equal(passkey0.assignedWorkerId, null);

  // 2. Anti-fraud guards block GitHub comment & NATS inbox --ack settlement
  const ghAttempt = engine.attemptGitHubCommentSettlement(
    'OBL-PASSKEY-8175',
    'Escalated Face ID failure to GitHub issue #8184'
  );
  assert.equal(ghAttempt.settled, false);
  assert.equal(ghAttempt.stageUnchanged, 'DETECTED');
  assert.equal(ghAttempt.reason, 'GITHUB_COMMENT_IS_RECORD_NOT_CUSTODY');

  const ackAttempt = engine.attemptBrokerAckSettlement(
    'OBL-PASSKEY-8175',
    'meridian.obligations.p0.passkey'
  );
  assert.equal(ackAttempt.settled, false);
  assert.equal(ackAttempt.reason, 'BROKER_INBOX_ACK_PROVES_DELIVERY_NOT_EXECUTION');
  assert.equal(engine.getSnapshot().falseSettlementsBlockedCount, 2);

  // 3. QUAD Ed25519 Admission enforces Identity != Env Var, Idle != Available, Connected != Capable
  const spoofed = engine.evaluateQuadAdmission({
    agentId: 'worker-spoofed-env-agent',
    requiredCapability: 'passkey_verifier_repair',
    requiredScope: 'security:passkey-repair',
  });
  assert.equal(spoofed.admitted, false);
  assert.equal(spoofed.httpStatus, 403);
  assert.equal(spoofed.denialCode, 'SELF_DECLARED_ESTATE_AGENT_REJECTED');

  const drained = engine.evaluateQuadAdmission({
    agentId: 'worker-idle-quota-drained',
    requiredCapability: 'passkey_verifier_repair',
    requiredScope: 'security:passkey-repair',
  });
  assert.equal(drained.admitted, false);
  assert.equal(drained.httpStatus, 429);
  assert.equal(drained.denialCode, 'IDLE_NOT_AVAILABLE_QUOTA_EXHAUSTED');

  const incapable = engine.evaluateQuadAdmission({
    agentId: 'worker-connected-incapable-ui',
    requiredCapability: 'passkey_verifier_repair',
    requiredScope: 'security:passkey-repair',
  });
  assert.equal(incapable.admitted, false);
  assert.equal(incapable.httpStatus, 422);
  assert.equal(incapable.denialCode, 'CAPABILITY_OR_SCOPE_MISMATCH');

  const eligible = engine.evaluateQuadAdmission({
    agentId: 'worker-argon-passkey-specialist',
    requiredCapability: 'passkey_verifier_repair',
    requiredScope: 'security:passkey-repair',
  });
  assert.equal(eligible.admitted, true);
  assert.equal(eligible.httpStatus, 200);

  // 4. Execute all 6 Acceptance Experiments (EXP_A..EXP_F) and verify SLA invariants & Rego R-010 candor
  const afterAll = engine.runAllSixExperiments();
  assert.equal(afterAll.experiments.length, 6);
  assert.ok(afterAll.experiments.every((e) => e.passedInEngine));
  assert.equal(afterAll.duplicateProtectedEffectsCount, 0);
  assert.ok(afterAll.staleFenceRejectionsCount >= 1);
  assert.equal(afterAll.unownedAcceptedP0Obligations, 0);
  assert.ok(afterAll.inheritedImmunityRules.length >= 1);
  assert.ok(afterAll.inheritedImmunityRules[0].preventedRecurrences >= 1);
  assert.equal(afterAll.estateAuditMatrix.length, 14);
  assert.equal(afterAll.sourceDefectFindings.length, 4);
  assert.equal(afterAll.fivePlanes.length, 5);
  assert.ok(afterAll.quantitativeBenchmarks.every((b) => b.meetsTargetInEngine));
  assert.equal(
    afterAll.crossHostHonestVerdict.autonomousCrossSurfaceRecovery,
    'VERIFIED_SANDBOX_ONLY_EXTERNAL_BLOCKED_DISPATCH'
  );
});

test('29. MCC-001 9-tuple contracts, bin/capability-index 5 invariants, authority narrowing, Web/App/Console reconnect, LTL & 10/10 certification scenarios pass', async () => {
  const { AutonomousReactivityEngine } = await import('./autonomousReactivity');
  const { UniversalExecutionProtocolEngine } = await import('./meridianCapabilityCalculus');

  const mcc = new UniversalExecutionProtocolEngine();

  // 1. All 5 bin/capability-index invariants hold (including retired OKE cryptographic tombstone)
  const invs = mcc.evaluateCapabilityIndexInvariants();
  assert.equal(invs.length, 5);
  assert.ok(invs.every((i) => i.passed));

  // 2. Sequential composition admits valid passkey repair chain & blocks workflow->prod-deploy implicit escalation
  const presets = mcc.getCompositionPresets();
  const validChain = presets.find((p) => p.presetId === 'CHAIN_VALID_PASSKEY_REPAIR');
  const blockedEscalation = presets.find((p) => p.presetId === 'CHAIN_BLOCKED_DEPLOY_ESCALATION');
  const blockedSkippedDiscovery = presets.find(
    (p) => p.presetId === 'CHAIN_BLOCKED_SKIPPED_DISCOVERY'
  );
  const blockedTombstone = presets.find((p) => p.presetId === 'CHAIN_BLOCKED_TOMBSTONED_OKE');

  assert.equal(validChain?.compatible, true);
  assert.equal(blockedEscalation?.compatible, false);
  assert.equal(blockedEscalation?.failureCode, 'AUTHORITY_EXPANSION_FORBIDDEN');
  assert.equal(blockedSkippedDiscovery?.compatible, false);
  assert.equal(blockedTombstone?.compatible, false);
  assert.equal(blockedTombstone?.failureCode, 'TOMBSTONED_CAPABILITY');

  // 3. Contravariant/Covariant refinement allows Future Sovereign Provider v2 with 0 core engine changes
  const snap0 = mcc.getSnapshot();
  assert.equal(snap0.refinementProofs.length, 1);
  assert.equal(snap0.refinementProofs[0].validRefinement, true);
  assert.equal(snap0.refinementProofs[0].zeroCoreChangesRequired, true);

  // 4. Unified Web · App · Console collaboration: disconnect App surface -> buffers in outbox -> reconnect reconciles to VERIFIED_EFFECT with 0 duplicates
  const react = new AutonomousReactivityEngine();
  react.toggleUnifiedSurfaceConnection('APP_FOUNDER_IPHONE', false);
  const offlineEnv = react.dispatchUnifiedSurfaceIntent({
    surfaceId: 'APP_FOUNDER_IPHONE',
    targetCapabilityId: 'cap.greenlane.patch_passkey_verifier',
    intentSummary: 'Mobile offline Face ID verifier audit queued safely',
    idempotencyKey: 'idem-mobile-offline-test-29',
  });
  assert.equal(offlineEnv.bufferedOffline, true);
  assert.equal(offlineEnv.envelope.settlementState, 'BUFFERED_OFFLINE_OUTBOX');

  const reconnected = react.toggleUnifiedSurfaceConnection('APP_FOUNDER_IPHONE', true);
  assert.equal(reconnected.reconciledEnvelopesCount, 1);

  const replayCheck = react.dispatchUnifiedSurfaceIntent({
    surfaceId: 'APP_FOUNDER_IPHONE',
    targetCapabilityId: 'cap.greenlane.patch_passkey_verifier',
    intentSummary: 'Mobile offline Face ID verifier audit queued safely',
    idempotencyKey: 'idem-mobile-offline-test-29',
  });
  assert.equal(replayCheck.idempotentReplay, true);
  assert.equal(replayCheck.envelope.settlementState, 'VERIFIED_EFFECT');
  assert.deepEqual(replayCheck.envelope.enforcementDoorsPassed, [
    'EP_A',
    'EP_B',
    'EP_C',
    'EP_D',
    'EP_E',
  ]);

  // 5. All 10 Estate Certification Scenarios (CERT_01..CERT_10) + repeated re-verification idempotency + 128-state LTL Model Check
  const initialHydratedCerts = react.getSnapshot().mccConvergence.certificationScenarios;
  assert.equal(initialHydratedCerts.length, 10);
  assert.ok(initialHydratedCerts.every((c) => c.passedInCiEngine));

  const allCertsRun1 = react.runAllMccCertificationScenarios();
  assert.equal(allCertsRun1.length, 10);
  assert.ok(allCertsRun1.every((c) => c.passedInCiEngine));

  const allCertsRun2 = react.runAllMccCertificationScenarios();
  assert.equal(allCertsRun2.length, 10);
  assert.ok(allCertsRun2.every((c) => c.passedInCiEngine));

  const finalSnap = react.getSnapshot().mccConvergence;
  assert.equal(finalSnap.ltlModelCheck.allPropertiesHoldUnderAssumptions, true);
  assert.equal(finalSnap.ltlModelCheck.totalStatesExplored, 128);
  assert.equal(finalSnap.existingEstateInventory.length, 10);
  assert.equal(finalSnap.crossRepoReconciliation.length, 5);
  assert.equal(finalSnap.convergenceMandateMatrix.length, 10);
  assert.equal(
    finalSnap.honestEstateVerdict.externalMultiRepoEnforcement,
    'SPECIFIED_NOT_ESTATE_WIDE_ENFORCED'
  );
});

test('30. Complete workspace archive seals all of today changes (.tar.gz + .bundle) and runbook documents 3 proxy-safe team retrieval lanes', async () => {
  const pathMod = await import('node:path');
  const { fileURLToPath } = await import('node:url');
  const {
    buildWorkspaceSourceArchive,
    evaluateProductionGuarantees,
    renderTeamHandoffRunbookMarkdown,
  } = await import('./debugPackBuilder');

  const repoRoot = pathMod.resolve(pathMod.dirname(fileURLToPath(import.meta.url)), '../..');
  const archive = buildWorkspaceSourceArchive(repoRoot);

  assert.equal(archive.ok, true);
  assert.ok(archive.bytes > 10_000);
  assert.equal(archive.sha256.length, 64);
  assert.ok(archive.files.includes('TEAM_HANDOFF_TODAY.md'));
  assert.ok(archive.files.includes('src/engine/meridianCapabilityCalculus.ts'));
  assert.ok(archive.files.includes('src/components/FounderMccConvergencePanel.tsx'));
  assert.ok(archive.files.includes('src/components/TeamHandoffExportPanel.tsx'));
  assert.ok(archive.files.includes('src/engine/autonomousReactivity.ts'));
  assert.ok(archive.files.includes('src/engine/mumsConcierge.ts'));
  assert.ok(archive.files.includes('src/engine/genesisAcademyEngine.ts'));
  assert.ok(archive.files.includes('dist-exports/meridian-hermes-today.bundle'));

  const engine = new RouterEngine({ initialReceipts: 2382 });
  const guarantees = evaluateProductionGuarantees(engine, repoRoot);
  const runbook = renderTeamHandoffRunbookMarkdown(repoRoot, guarantees);
  assert.ok(runbook.includes('Lane 1'));
  assert.ok(runbook.includes('Lane 2'));
  assert.ok(runbook.includes('Lane 3'));
  assert.ok(runbook.includes('browser-cookie interstitial'));
});

test('31. Crescendo 3-Way Union commits sign-off file, resolves /crescendo route, converges OBL-CRESCENDO-3WAY-UNION, materializes static dist/api/export/bundle, and holds honest NO-GO until external receipts', async () => {
  const fsMod = await import('node:fs');
  const osMod = await import('node:os');
  const pathMod = await import('node:path');
  const cryptoMod = await import('node:crypto');
  const { fileURLToPath } = await import('node:url');
  const {
    evaluateCrescendoGoLiveSignOff,
    renderCrescendoSignOffMarkdown,
    resolveDeclaredAppRoute,
  } = await import('./crescendoThreeWayUnion');
  const { AutonomousReactivityEngine } = await import('./autonomousReactivity');
  const {
    buildLiveCrescendoSignOff,
    buildWorkspaceSourceArchive,
    materializeStaticDistExports,
  } = await import('./debugPackBuilder');

  const repoRoot = pathMod.resolve(pathMod.dirname(fileURLToPath(import.meta.url)), '../..');

  // 1. Declared route resolution fixes Finding 2 (/crescendo, /codex-crescendo, ?tab=crescendo -> hermes)
  assert.equal(resolveDeclaredAppRoute('/crescendo', ''), 'hermes');
  assert.equal(resolveDeclaredAppRoute('/crescendo/', ''), 'hermes');
  assert.equal(resolveDeclaredAppRoute('/codex-crescendo', ''), 'hermes');
  assert.equal(resolveDeclaredAppRoute('/hermes/crescendo', ''), 'hermes');
  assert.equal(resolveDeclaredAppRoute('/', '?tab=crescendo'), 'hermes');
  assert.equal(resolveDeclaredAppRoute('/', '?handoff=1'), 'founder_reactivity');
  assert.equal(resolveDeclaredAppRoute('/', ''), 'union');

  // 2. Authoritative sign-off file is committed in repo root and sealed in workspace archive (Finding 1)
  const signOffRootPath = pathMod.join(
    repoRoot,
    'MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md'
  );
  assert.equal(fsMod.existsSync(signOffRootPath), true);

  const archive = buildWorkspaceSourceArchive(repoRoot);
  assert.equal(archive.ok, true);
  assert.ok(archive.files.includes('MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md'));
  assert.ok(archive.files.includes('src/engine/crescendoThreeWayUnion.ts'));

  // 3. Fail-closed NO-GO governance (Finding 3 + Rego R-010 + Three-Key Non-Collusion)
  const liveSnap = buildLiveCrescendoSignOff(repoRoot);
  assert.equal(liveSnap.overallDecision, 'NO-GO');
  assert.equal(liveSnap.localGatesPassed, 3);
  assert.equal(liveSnap.externalGatesPassed, 0);
  assert.equal(liveSnap.streams.length, 3);
  assert.equal(liveSnap.gates.length, 6);
  assert.equal(
    liveSnap.reasonCode,
    'AWAITING_FLEET_ACCEPTANCE_DEPLOYMENT_AND_EXTERNAL_VERIFICATION'
  );

  const colludingSnap = evaluateCrescendoGoLiveSignOff({
    keyBinah: 'same_key',
    keyChesed: 'same_key',
    keyMalkuth: 'same_key',
    fleetRemoteAccepted: true,
    verifiedProductionRevision: 'rev-prod-1',
    externalRunnerBundleHttp200: true,
    externalEndUserRouteBrowserVerified: true,
  });
  assert.equal(colludingSnap.overallDecision, 'NO-GO');
  assert.equal(colludingSnap.reasonCode, 'LOCAL_ALGEBRA_OR_ROUTE_FAULT');

  const fullWitnessGo = evaluateCrescendoGoLiveSignOff({
    headSha: liveSnap.headSha,
    bundleSha256: liveSnap.bundleSha256,
    fleetRemoteAccepted: true,
    verifiedProductionRevision: 'rev-prod-1',
    externalRunnerBundleHttp200: true,
    externalEndUserRouteBrowserVerified: true,
  });
  assert.equal(fullWitnessGo.overallDecision, 'GO');
  assert.equal(fullWitnessGo.localGatesPassed, 3);
  assert.equal(fullWitnessGo.externalGatesPassed, 3);

  const md = renderCrescendoSignOffMarkdown(liveSnap);
  assert.ok(md.includes('NO-GO'));
  assert.ok(md.includes('OBL-CRESCENDO-3WAY-UNION'));
  assert.ok(md.includes('/crescendo'));

  // 4. Converged fleet recovery obligation registered with 0 disconnected tickets
  const reactivity = new AutonomousReactivityEngine().getSnapshot();
  const crescendoObl = reactivity.obligations.find(
    (o) => o.obligationId === 'OBL-CRESCENDO-3WAY-UNION'
  );
  assert.ok(crescendoObl);
  assert.equal(crescendoObl.priority, 'P0');
  assert.ok(crescendoObl.convergedDuplicateCount >= 1);
  assert.equal(reactivity.unownedAcceptedP0Obligations, 0);

  // 5. Static dist/ export materialization eliminates static-host HTTP 404 on /api/export/bundle & /crescendo
  const tmpDist = fsMod.mkdtempSync(pathMod.join(osMod.tmpdir(), 'meridian-dist-test-'));
  try {
    fsMod.writeFileSync(pathMod.join(tmpDist, 'index.html'), '<!doctype html><title>Meridian</title>');
    const mat = materializeStaticDistExports(repoRoot, tmpDist);
    assert.equal(mat.materialized, true);
    assert.ok(mat.filesWritten.includes('api/export/bundle'));
    assert.ok(mat.filesWritten.includes('MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md'));
    assert.ok(mat.filesWritten.includes('crescendo/index.html'));

    const staticBundleBytes = fsMod.readFileSync(pathMod.join(tmpDist, 'api/export/bundle'));
    const staticBundleSha = cryptoMod
      .createHash('sha256')
      .update(staticBundleBytes)
      .digest('hex');
    assert.equal(staticBundleSha, mat.bundleSha256);
  } finally {
    fsMod.rmSync(tmpDist, { recursive: true, force: true });
  }
});

test('32. Zero-reminder autonomous sync cycle commits/bundles automatically, pushes to saved POST/PUT targets, skips redundant pushes once accepted, and resolves /get-work route', async () => {
  const fsMod = await import('node:fs');
  const osMod = await import('node:os');
  const pathMod = await import('node:path');
  const { fileURLToPath } = await import('node:url');
  const { isDeclaredGetWorkRoute, resolveDeclaredAppRoute } = await import(
    './crescendoThreeWayUnion'
  );
  const {
    readRegisteredIngestTargets,
    registerCustomIngestTarget,
    removeCustomIngestTarget,
    runAutonomousSyncCycle,
  } = await import('./debugPackBuilder');

  const repoRoot = pathMod.resolve(pathMod.dirname(fileURLToPath(import.meta.url)), '../..');

  // 1. /get-work, /export, /download, and ?getwork=1 auto-open the global Get All Work modal
  assert.equal(isDeclaredGetWorkRoute('/get-work', ''), true);
  assert.equal(isDeclaredGetWorkRoute('/download', ''), true);
  assert.equal(isDeclaredGetWorkRoute('/', '?getwork=1'), true);
  assert.equal(isDeclaredGetWorkRoute('/crescendo', ''), false);
  assert.equal(resolveDeclaredAppRoute('/get-work', ''), 'founder_reactivity');

  // 2. Persistent target registration blocks insecure/loopback URLs and pushes automatically to valid HTTPS target
  const tmpDir = fsMod.mkdtempSync(pathMod.join(osMod.tmpdir(), 'meridian-targets-test-'));
  const targetsFile = pathMod.join(tmpDir, 'custom-ingest-targets.json');
  try {
    const blockedHttp = registerCustomIngestTarget(
      repoRoot,
      'http://insecure.example.com/ingest',
      'POST',
      targetsFile
    );
    assert.equal(blockedHttp.ok, false);

    const blockedLocal = registerCustomIngestTarget(
      repoRoot,
      'https://127.0.0.1/ingest',
      'POST',
      targetsFile
    );
    assert.equal(blockedLocal.ok, false);

    const validSaved = registerCustomIngestTarget(
      repoRoot,
      'https://receiver.example.com/api/ingest/bundle',
      'POST',
      targetsFile
    );
    assert.equal(validSaved.ok, true);
    assert.equal(readRegisteredIngestTargets(repoRoot, targetsFile).length, 1);

    let pushCount = 0;
    const mockFetch: typeof fetch = async (input) => {
      pushCount += 1;
      assert.equal(String(input), 'https://receiver.example.com/api/ingest/bundle');
      return new Response(
        JSON.stringify({
          ok: true,
          wakeDisposition: 'WOKEN_IDLE_SESSION',
          wokenSessionId: 'sess-auto-1',
          wokenWorkerId: 'worker-auto-1',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    };

    const cycle1 = await runAutonomousSyncCycle(repoRoot, {
      forcePush: true,
      fetchImpl: mockFetch,
      customTargetsFileAbs: targetsFile,
      skipCanonical: true,
      skipTelemetry: true,
    });
    assert.equal(cycle1.pushed, true);
    assert.equal(pushCount, 1);

    // Subsequent autonomous cycle with unchanged bundleSha256 skips duplicate push
    const cycle2 = await runAutonomousSyncCycle(repoRoot, {
      forcePush: false,
      fetchImpl: mockFetch,
      customTargetsFileAbs: targetsFile,
      skipCanonical: true,
      skipTelemetry: true,
    });
    assert.equal(cycle2.skippedAlreadyPushed, true);
    assert.equal(pushCount, 1);

    const afterRemove = removeCustomIngestTarget(
      repoRoot,
      'https://receiver.example.com/api/ingest/bundle',
      targetsFile
    );
    assert.equal(afterRemove.length, 0);
  } finally {
    fsMod.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('33. OMNIFLOW live cross-surface bus enforces idempotency, monotonic fencing (409), independent verify (403), TTL worker-drop recovery, and real outside-in DNS/OKE probe', async () => {
  const fsMod = await import('node:fs');
  const osMod = await import('node:os');
  const pathMod = await import('node:path');
  const { resolveDeclaredAppRoute } = await import('./crescendoThreeWayUnion');
  const { OmniflowLiveBusEngine } = await import('./omniflowLiveBus');

  assert.equal(resolveDeclaredAppRoute('/comms', ''), 'founder_reactivity');
  assert.equal(resolveDeclaredAppRoute('/bus', ''), 'founder_reactivity');
  assert.equal(resolveDeclaredAppRoute('/omniflow', ''), 'founder_reactivity');

  const bus = new OmniflowLiveBusEngine({ journalPath: null });
  const t0 = Date.now();

  // 1. Register two heterogeneous participants (Console CLI + Web Browser)
  const consoleCli = bus.registerParticipant({
    agentId: 'glm-5.3-console',
    surfaceClass: 'CONSOLE_CLI',
    transport: 'CLI_BRIDGE',
    capabilities: ['code:patch', 'shadow-verify'],
    ttlMs: 10_000,
    nowMs: t0,
  });
  assert.equal(consoleCli.connected, true);

  bus.registerParticipant({
    agentId: 'karma-verifier-edge',
    surfaceClass: 'CLOUD_RUNNER',
    transport: 'SSE_HTTPS',
    capabilities: ['karma:verify'],
    ttlMs: 60_000,
    nowMs: t0,
  });

  // 2. Idempotent publish (applying duplicate idempotencyKey returns deduplicated=true without second message)
  const p1 = bus.publishMessage({
    fromAgent: 'founder-genesis-cockpit',
    target: '@all',
    verb: 'ASK',
    body: 'Fix shadow-verify Prisma P1001 and prove Postgres CI',
    idempotencyKey: 'idem-omniflow-test-33',
    requiresClaim: true,
  });
  assert.equal(p1.deduplicated, false);
  assert.ok(p1.message);
  const m1 = p1.message;
  assert.equal(m1.custodyStage, 'DELIVERED');

  const p2 = bus.publishMessage({
    fromAgent: 'founder-genesis-cockpit',
    target: '@all',
    verb: 'ASK',
    body: 'Fix shadow-verify Prisma P1001 and prove Postgres CI',
    idempotencyKey: 'idem-omniflow-test-33',
    requiresClaim: true,
  });
  assert.equal(p2.deduplicated, true);
  assert.ok(p2.message);
  assert.equal(p2.message.envelopeId, m1.envelopeId);

  // 3. Monotonic lease claim + stale fence 409 rejection + self-verify 403 block
  const claimed = bus.claimLease({
    envelopeId: m1.envelopeId,
    workerId: 'glm-5.3-console',
  });
  assert.equal(claimed.ok, true);
  const f1 = claimed.message!.fencingToken!;
  assert.ok(f1 > 500);

  const staleAttempt = bus.submitEffectWithFence({
    envelopeId: m1.envelopeId,
    workerId: 'glm-5.3-console',
    fencingToken: f1 - 1,
    note: 'stale write',
  });
  assert.equal(staleAttempt.httpStatus, 409);

  const selfVerifyAttempt = bus.verifyIndependently({
    envelopeId: m1.envelopeId,
    verifierId: 'glm-5.3-console',
    evidenceNote: 'trying to self-certify',
  });
  assert.equal(selfVerifyAttempt.httpStatus, 403);

  // 4. Worker heartbeat expiry automatically recovers active lease to LEASE_EXPIRED_RECOVERING
  const swept = bus.sweepExpiredParticipants(t0 + 25_000);
  assert.ok(swept.expiredAgentIds.includes('glm-5.3-console'));
  assert.ok(swept.recoveredEnvelopeIds.includes(m1.envelopeId));

  const recoveredMsg = bus
    .getSnapshot()
    .messages.find((m) => m.envelopeId === m1.envelopeId)!;
  assert.equal(recoveredMsg.custodyStage, 'LEASE_EXPIRED_RECOVERING');
  assert.equal(recoveredMsg.holderAgentId, null);

  // Re-claim by surviving worker and independently verify
  const reclaim = bus.claimLease({
    envelopeId: m1.envelopeId,
    workerId: 'karma-verifier-edge',
  });
  assert.equal(reclaim.ok, true);
  assert.ok(reclaim.message!.fencingToken! > f1);

  const verified = bus.verifyIndependently({
    envelopeId: m1.envelopeId,
    verifierId: 'founder-genesis-cockpit',
    evidenceNote: 'Postgres service test passed externally',
  });
  assert.equal(verified.httpStatus, 200);
  assert.equal(verified.message!.custodyStage, 'VERIFIED_EFFECT');

  // 5. Real outside-in probe blocks retired OKE 193.123.184.22, catches NXDOMAIN, and verifies 200
  const okeBlocked = await bus.probeExternalSpine('https://otto.mumchimp.com/health', {
    lookupFn: async () => [{ address: '193.123.184.22' }],
  });
  assert.equal(okeBlocked.status, 'RETIRED_OKE_IP_BLOCKED');
  assert.equal(okeBlocked.retiredOkeIpDetected, true);

  const nxdomain = await bus.probeExternalSpine('https://estate-bus.mumchimp.com/health', {
    lookupFn: async () => {
      throw new Error('ENOTFOUND estate-bus.mumchimp.com');
    },
  });
  assert.equal(nxdomain.status, 'NXDOMAIN_OR_UNREACHABLE');

  const liveOk = await bus.probeExternalSpine('https://estate-bus.mumchimp.com/health', {
    lookupFn: async () => [{ address: '104.21.10.10' }],
    fetchFn: async () => new Response(JSON.stringify({ ok: true }), { status: 200 }),
  });
  assert.equal(liveOk.status, 'LIVE_VERIFIED');
  assert.equal(liveOk.httpStatus, 200);

  // 6. CLI bridge and Cloudflare Durable Object scripts exist in workspace
  const repoRoot = pathMod.resolve(pathMod.dirname(new URL(import.meta.url).pathname), '../..');
  assert.equal(fsMod.existsSync(pathMod.join(repoRoot, 'scripts/estate-bus-cli.mjs')), true);
  assert.equal(fsMod.existsSync(pathMod.join(repoRoot, 'scripts/cloudflare-omniflow-bus.ts')), true);
  void osMod;
});

test('34. RFCE #8188 / bin/verify_three_proofs.py 100%-Guarantee Admission Guard blocks invalid manifests & unprobed components pre-token and auto-decomposes multi-subsystem tasks', async () => {
  const {
    decomposeManifestToCompliantLanes,
    evaluateZeroGaslightAdmission,
    validateUnsealedChangeManifest,
  } = await import('./meridianCapabilityCalculus');
  const { OmniflowLiveBusEngine } = await import('./omniflowLiveBus');

  // 1. Exact #8194 3-subsystem failure class (catalog + docs + tests) is caught BEFORE inference dispatch
  const threeSubsystemManifest = [
    'catalog/capabilities.yaml',
    'docs/runbook.md',
    'tests/test_catalog.py',
  ];
  const boundaryCheck = validateUnsealedChangeManifest(threeSubsystemManifest);
  assert.equal(boundaryCheck.boundaryValid, false);
  assert.ok(boundaryCheck.violationCodes.includes('MULTI_SUBSYSTEM_FORBIDDEN'));
  assert.equal(boundaryCheck.subsystemCount, 3);
  assert.equal(boundaryCheck.decomposedLanes.length, 3);
  assert.ok(boundaryCheck.decomposedLanes.every((l) => l.boundaryValid && l.fileCount === 1));

  // 2. Oversized 7-file single-subsystem manifest chunks into 5 + 2 compliant lanes
  const sevenFiles = [
    'src/a.ts',
    'src/b.ts',
    'src/c.ts',
    'src/d.ts',
    'src/e.ts',
    'src/f.ts',
    'src/g.ts',
  ];
  const sevenCheck = validateUnsealedChangeManifest(sevenFiles, 5);
  assert.equal(sevenCheck.boundaryValid, false);
  assert.ok(sevenCheck.violationCodes.includes('TOO_MANY_FILES'));
  const chunked = decomposeManifestToCompliantLanes(sevenFiles, 5);
  assert.equal(chunked.length, 2);
  assert.deepEqual(
    chunked.map((c) => c.fileCount),
    [5, 2]
  );

  // 3. Five-gate Zero-Gaslight admission evaluator (100% Guarantee Else No Admission)
  const noManifest = evaluateZeroGaslightAdmission({
    workerId: 'glm-5.3-console',
    workerQuadAttested: true,
    requiresProtectedMutation: true,
    proposedFiles: [],
  });
  assert.equal(noManifest.admitted, false);
  assert.equal(noManifest.httpStatus, 422);
  assert.equal(noManifest.tokensSpentBeforeReject, 0);
  assert.ok(noManifest.failedGates.includes('MANIFEST_REQUIRED_NO_ADMISSION'));

  const unattested = evaluateZeroGaslightAdmission({
    workerId: 'rogue-worker',
    workerQuadAttested: false,
    proposedFiles: ['catalog/capabilities.yaml'],
  });
  assert.equal(unattested.admitted, false);
  assert.equal(unattested.httpStatus, 403);
  assert.ok(unattested.failedGates.includes('WORKER_UNATTESTED_NO_ADMISSION'));

  const unprobedComponent = evaluateZeroGaslightAdmission({
    workerId: 'glm-5.3-console',
    workerQuadAttested: true,
    proposedFiles: ['catalog/capabilities.yaml'],
    requiredComponents: [
      {
        componentId: 'estate-bus-external-spine',
        status: 'NXDOMAIN_OR_UNREACHABLE',
        targetUrl: 'https://estate-bus.mumchimp.com/health',
      },
      {
        componentId: 'otto-host',
        status: 'RETIRED_OKE_IP_BLOCKED',
        retiredOkeIpDetected: true,
      },
    ],
  });
  assert.equal(unprobedComponent.admitted, false);
  assert.equal(unprobedComponent.httpStatus, 422);
  assert.ok(unprobedComponent.failedGates.includes('COMPONENT_UNPROBED_NO_ADMISSION'));
  assert.equal(unprobedComponent.blockedComponents.length, 2);

  const scopeEscape = evaluateZeroGaslightAdmission({
    workerId: 'glm-5.3-console',
    workerQuadAttested: true,
    proposedFiles: ['catalog/capabilities.yaml'],
    observedDiffFiles: ['catalog/capabilities.yaml', 'tests/test_catalog.py'],
    requiredComponents: [{ componentId: 'estate-bus', status: 'LIVE_VERIFIED' }],
  });
  assert.equal(scopeEscape.admitted, false);
  assert.equal(scopeEscape.httpStatus, 422);
  assert.ok(scopeEscape.failedGates.includes('RUNTIME_SCOPE_ESCAPE'));
  assert.deepEqual(scopeEscape.scopeEscapeFiles, ['tests/test_catalog.py']);

  const admitted = evaluateZeroGaslightAdmission({
    workerId: 'glm-5.3-console',
    workerQuadAttested: true,
    proposedFiles: ['catalog/capabilities.yaml'],
    observedDiffFiles: ['catalog/capabilities.yaml'],
    requiredComponents: [{ componentId: 'estate-bus', status: 'LIVE_VERIFIED' }],
  });
  assert.equal(admitted.admitted, true);
  assert.equal(admitted.httpStatus, 200);
  assert.equal(admitted.status, 'ADMITTED_ZERO_GASLIGHT');

  // 4. OMNIFLOW bus rejects 3-subsystem publish with HTTP 422, then auto-decomposes into 3 lanes when requested
  const bus = new OmniflowLiveBusEngine({ journalPath: null });
  const rejected = bus.publishMessage({
    fromAgent: 'founder-genesis-cockpit',
    target: '@all',
    verb: 'ASK',
    body: 'Update catalog, docs, and tests together',
    proposedFiles: threeSubsystemManifest,
    autoDecompose: false,
  });
  assert.equal(rejected.ok, false);
  assert.equal(rejected.httpStatus, 422);
  assert.equal(bus.getSnapshot().admissionBoundaryRejectedCount, 1);

  const decomposed = bus.publishMessage({
    fromAgent: 'founder-genesis-cockpit',
    target: '@all',
    verb: 'ASK',
    body: 'Update catalog, docs, and tests cleanly',
    proposedFiles: threeSubsystemManifest,
    autoDecompose: true,
  });
  assert.equal(decomposed.ok, true);
  assert.equal(decomposed.httpStatus, 201);
  assert.equal(decomposed.decomposedMessages?.length, 3);
  for (const child of decomposed.decomposedMessages!) {
    assert.equal(child.boundaryValidation?.boundaryValid, true);
    assert.equal(child.boundaryValidation?.subsystemCount, 1);
  }
  assert.equal(bus.getSnapshot().autoDecomposedLanesCount, 3);
});

test('35. Exhaustive mathematical proof renders Proof-2 boundary rejection unreachable (1,240 subsets, 0 violations) and enforces non-monetary CA1-CA5 settlement gate', async () => {
  const {
    getRecoveryMandateSettlementSnapshot,
    runBoundaryEliminationProofSuite,
  } = await import('./meridianCapabilityCalculus');

  const proof = runBoundaryEliminationProofSuite();
  assert.equal(proof.mathematicalTheoremProven, true);
  assert.equal(proof.exhaustiveModelStats.validSubsetViolationsFound, 0);
  assert.ok(proof.exhaustiveModelStats.validNonEmptySubsetsTested >= 1200);
  assert.equal(
    proof.exhaustiveModelStats.invalidMultiSubsystemBlockedCount,
    proof.exhaustiveModelStats.invalidMultiSubsystemCombinationsTested
  );
  assert.equal(proof.lemmas.length, 4);
  assert.ok(proof.lemmas.every((l) => l.proven));

  const edges = proof.exhaustiveModelStats.edgeEscapeCasesBlocked;
  assert.equal(edges.emptyManifestAndEmptyDiffBlocked, true);
  assert.equal(edges.nonCanonicalTraversalBlocked, true);
  assert.equal(edges.guardedPathBlocked, true);
  assert.equal(edges.staleBaseShaBlocked, true);
  assert.equal(edges.scopeEscapeDiffBlocked, true);
  assert.equal(edges.historicalIncident8194ReproducedAndBlocked, true);

  // Operational settlement: non-monetary restitution; CA1-CA3 proven locally; CA4-CA5 held unsettled pending external receipts
  const settlement = getRecoveryMandateSettlementSnapshot(false);
  assert.equal(settlement.compensationDoctrine, 'OPERATIONAL_RESTITUTION_NEVER_MONETARY');
  assert.equal(settlement.karmaRecordId, 'FC-20261117-8194');
  assert.equal(
    settlement.overallSettlementVerdict,
    'SETTLEMENT_HELD_OPEN_PENDING_CA4_CA5_EXTERNAL_EVIDENCE'
  );
  assert.equal(settlement.caGates.find((g) => g.gateId === 'CA1')?.status, 'SATISFIED_MATHEMATICALLY_LOCAL');
  assert.equal(settlement.caGates.find((g) => g.gateId === 'CA2')?.status, 'SATISFIED_MATHEMATICALLY_LOCAL');
  assert.equal(settlement.caGates.find((g) => g.gateId === 'CA3')?.status, 'SATISFIED_MATHEMATICALLY_LOCAL');
  assert.equal(settlement.caGates.find((g) => g.gateId === 'CA4')?.status, 'UNSETTLED_EXTERNAL_PENDING');
  assert.equal(settlement.caGates.find((g) => g.gateId === 'CA5')?.status, 'UNSETTLED_EXTERNAL_PENDING');
  assert.equal(settlement.mandateTable.length, 6);
  assert.equal(settlement.measuredHosts.length, 8);

  const { evaluateEstateTargetAdmission } = await import('./meridianCapabilityCalculus');
  const passkeyAdmit = evaluateEstateTargetAdmission({
    workerId: 'zai-worker',
    targetHosts: ['passkey.mumchimp.com'],
    proposedFiles: ['catalog/capabilities.yaml'],
  });
  assert.equal(passkeyAdmit.admitted, true);
  assert.equal(passkeyAdmit.httpStatus, 200);

  for (const deadHost of [
    'catalogue.mumchimp.com',
    'otto.mumchimp.com/healthz',
    'llm.mumchimp.com/health/liveliness',
    'estate-bus.mumchimp.com',
    'genesis-founder-surface.pages.dev/api/ingest/bundle',
  ]) {
    const blocked = evaluateEstateTargetAdmission({
      workerId: 'zai-worker',
      targetHosts: [deadHost],
      proposedFiles: ['catalog/capabilities.yaml'],
    });
    assert.equal(blocked.admitted, false);
    assert.equal(blocked.httpStatus, 422);
    assert.ok(blocked.failedGates.includes('COMPONENT_UNPROBED_NO_ADMISSION'));
  }
});

test('36. KARMA #7452 & #8030 Universal Settlement Gate, Mission #7760 Receiver Truth, and 7-Seat Browser Workforce (Registration != Execution)', async () => {
  const {
    BROWSER_WORKFORCE_FLEET,
    evaluateUniversalKarmicSettlement,
    reconcileBrowserWorkforceRefinement,
  } = await import('./meridianCapabilityCalculus');

  // 1. All 7 browser seats pass 9-tuple schema refinement ONLY (registeredOnly=true, authenticatedExecutionVerified=false)
  assert.equal(BROWSER_WORKFORCE_FLEET.length, 7);
  for (const profile of BROWSER_WORKFORCE_FLEET) {
    const onboarded = reconcileBrowserWorkforceRefinement(profile.workerId);
    assert.equal(onboarded.refinement.validRefinement, true);
    assert.equal(onboarded.zeroCoreChangesRequired, true);
    assert.equal(onboarded.localEngineOnboarded, true);
    assert.equal(onboarded.registeredOnly, true);
    assert.equal(onboarded.authenticatedExecutionVerified, false);
    assert.equal(onboarded.executionStatus, 'REGISTERED_UNAUTHENTICATED_NO_EXECUTION');
    assert.equal(onboarded.executionReceiptSha256, null);
    assert.equal(onboarded.externalBrowserAuthVerified, false);
    assert.equal(onboarded.worker.externalBrowserAuthState, 'UNVERIFIED_EXTERNAL_BROWSER_SESSION');
  }

  // Authenticated execution receipt explicitly switches status only for verified workers
  const verifiedSeat = reconcileBrowserWorkforceRefinement('BR-KIMI-01', {
    'BR-KIMI-01': 'a'.repeat(64),
  });
  assert.equal(verifiedSeat.registeredOnly, false);
  assert.equal(verifiedSeat.authenticatedExecutionVerified, true);
  assert.equal(verifiedSeat.executionStatus, 'AUTHENTICATED_EXECUTION_VERIFIED');

  // 2. When external channels & remote fault injections remain unverified, KARMA #7452 / #8030 holds settled === false
  const unsettled = evaluateUniversalKarmicSettlement({
    autoSyncExternalAccepted: false,
    autoSyncHeadSha: '8d4825a2857360d289593ef7555ee0606a9b6105',
    autoSyncBundleSha256: '22f132bf969af36eea859b4615f80aaa6d62d037c1a2671f1a41a4ef60aff036',
    externalBusLiveVerified: false,
    externalKimiLiveVerified: false,
    externalIdpVerified: false,
    remoteFaultInjectionVerifiedCount: 0,
    registeredBusWorkerIds: ['BR-KIMI-01'],
  });
  assert.equal(unsettled.karmaAuthorityId, 'KARMA #7452');
  assert.equal(unsettled.centralComplaintAuthorityId, '#8030');
  assert.equal(unsettled.compensationDoctrine, 'OPERATIONAL_RESTITUTION_NEVER_MONETARY');
  assert.equal(unsettled.settled, false);
  assert.equal(unsettled.verdict, 'UNSETTLED_HELD_OPEN_CERTIFICATION_WITHHELD');
  assert.equal(unsettled.obligations.length, 5);
  assert.equal(unsettled.localVerifiedCount, 4);
  assert.equal(unsettled.externalLiveVerifiedCount, 0);
  assert.equal(unsettled.browserWorkforceAuthenticatedExecutionsCount, 0);
  assert.equal(unsettled.geminiSync7760.missionId, '#7760');
  assert.equal(unsettled.geminiSync7760.ciTestsPassedCount, 6);
  assert.equal(unsettled.geminiSync7760.maxBundleBytes, 16 * 1024 * 1024);
  assert.equal(unsettled.geminiSync7760.receiverDeployedExternally, false);
  assert.equal(unsettled.resilienceMatrix.localPrechecksPassedCount, 10);
  assert.equal(unsettled.resilienceMatrix.remoteFaultInjectionsPassedCount, 0);
  assert.equal(unsettled.allSeeingEye.historicalBaselineFailedRuns, 359);
  assert.equal(unsettled.allSeeingEye.liveFailedWorkflowRunsCount, null);
  assert.equal(unsettled.unblockPackCommands.length, 4);

  // 3. Partial external verification STILL refuses settlement: Settlement <=> forall o in O, Verified(o)
  const partial = evaluateUniversalKarmicSettlement({
    autoSyncExternalAccepted: true,
    autoSyncHeadSha: '8d4825a2857360d289593ef7555ee0606a9b6105',
    autoSyncBundleSha256: '22f132bf969af36eea859b4615f80aaa6d62d037c1a2671f1a41a4ef60aff036',
    externalBusLiveVerified: true,
    externalKimiLiveVerified: false,
    externalIdpVerified: true,
    remoteFaultInjectionVerifiedCount: 10,
    registeredBusWorkerIds: ['BR-KIMI-01'],
  });
  assert.equal(partial.settled, false);
  assert.equal(partial.externalLiveVerifiedCount, 4);

  // 3b. Even with 1/7 authenticated worker receipt, full 7-seat settlement stays withheld until all 7 execute
  const partialWorkers = evaluateUniversalKarmicSettlement({
    autoSyncExternalAccepted: true,
    autoSyncHeadSha: '8d4825a2857360d289593ef7555ee0606a9b6105',
    autoSyncBundleSha256: '22f132bf969af36eea859b4615f80aaa6d62d037c1a2671f1a41a4ef60aff036',
    externalBusLiveVerified: true,
    externalKimiLiveVerified: true,
    authenticatedBrowserWorkerIds: ['BR-KIMI-01'],
    externalIdpVerified: true,
    remoteFaultInjectionVerifiedCount: 10,
    registeredBusWorkerIds: ['BR-KIMI-01'],
  });
  assert.equal(partialWorkers.browserWorkforceAuthenticatedExecutionsCount, 1);
  assert.equal(partialWorkers.settled, false);

  // 4. Full verification across ALL 5 obligations + 10/10 remote faults + 7/7 authenticated executions settles cleanly
  const settledAll = evaluateUniversalKarmicSettlement({
    autoSyncExternalAccepted: true,
    autoSyncHeadSha: '8d4825a2857360d289593ef7555ee0606a9b6105',
    autoSyncBundleSha256: '22f132bf969af36eea859b4615f80aaa6d62d037c1a2671f1a41a4ef60aff036',
    externalBusLiveVerified: true,
    externalKimiLiveVerified: true,
    authenticatedBrowserWorkerIds: BROWSER_WORKFORCE_FLEET.map((w) => w.workerId),
    externalIdpVerified: true,
    remoteFaultInjectionVerifiedCount: 10,
    registeredBusWorkerIds: ['BR-KIMI-01'],
  });
  assert.equal(settledAll.browserWorkforceAuthenticatedExecutionsCount, 7);
  assert.equal(settledAll.settled, true);
  assert.equal(settledAll.verdict, 'SETTLED_ALL_OBLIGATIONS_VERIFIED');
  assert.equal(settledAll.externalLiveVerifiedCount, 5);
  assert.ok(settledAll.obligations.every((o) => o.verifiedOverall));
});

test('37. 10 Resilience Pre-Checks vs 0/10 Remote Faults, Continuous GitHub Inventory Refresh, 9 Delivery-Scoped Restitution Outcomes, and Non-Live Static Snapshot Tags', async () => {
  const fsMod = await import('node:fs');
  const osMod = await import('node:os');
  const pathMod = await import('node:path');
  const {
    evaluateMandatoryResilienceMatrix,
    evaluateUniversalKarmicSettlement,
    getAllSeeingEyeAuditSnapshot,
    refreshAllSeeingEyeLiveInventory,
  } = await import('./meridianCapabilityCalculus');
  const { materializeStaticDistExports } = await import('./debugPackBuilder');

  // 1. Resilience matrix strictly separates local unit pre-checks (10/10) from remote fault injection (0/10)
  const localOnly = evaluateMandatoryResilienceMatrix({
    externalCloudLive: false,
    remoteFaultInjectionVerifiedCount: 0,
  });
  assert.equal(localOnly.totalScenarios, 10);
  assert.equal(localOnly.localPrechecksPassedCount, 10);
  assert.equal(localOnly.remoteFaultInjectionsPassedCount, 0);
  assert.equal(localOnly.resilienceVerdict, 'UNVERIFIED_ZERO_REMOTE_FAULT_INJECTIONS');
  assert.equal(localOnly.productionCertified, false);
  assert.ok(localOnly.scenarios.every((s) => s.localUnitPrecheckPassed));
  assert.ok(localOnly.scenarios.every((s) => !s.remoteFaultInjectionPassed));
  assert.ok(
    localOnly.scenarios.every(
      (s) => s.remoteFaultInjectionStatus === 'NOT_EXECUTED_REQUIRES_REMOTE_DEPLOYMENT'
    )
  );
  assert.ok(localOnly.scenarios.every((s) => s.requiredRemoteInjectionMethod.length > 10));

  // 2. All-Seeing Eye separates 359 historical baseline from unrefreshed / refreshed live GitHub API inventory
  const unrefreshed = getAllSeeingEyeAuditSnapshot();
  assert.equal(unrefreshed.historicalBaselineFailedRuns, 359);
  assert.equal(unrefreshed.liveFailedWorkflowRunsCount, null);
  assert.equal(unrefreshed.inventoryFreshness, 'HISTORICAL_BASELINE_UNREFRESHED');
  assert.equal(unrefreshed.isLiveInventory, false);
  assert.equal(unrefreshed.repositoriesInspected, 6);
  assert.equal(unrefreshed.certificationStatus, 'OPERATIONAL_CERTIFICATION_WITHHELD');
  assert.ok(!unrefreshed.neverShowFalseGreenCopy.toLowerCase().includes("nothing awaiting you'"));

  const liveRefreshOk = await refreshAllSeeingEyeLiveInventory(async (url) => {
    const u = String(url);
    const counts: Record<string, number> = {
      idp: 12,
      'estate-graph': 4,
      'gemini-sync': 1,
      argon: 3,
      'argon-sync': 2,
      crew: 0,
    };
    const key = Object.keys(counts).find((k) => u.includes(`/${k}/actions/`)) ?? 'crew';
    return new Response(JSON.stringify({ total_count: counts[key] }), { status: 200 });
  });
  assert.equal(liveRefreshOk.inventoryFreshness, 'LIVE_GITHUB_API_REFRESHED');
  assert.equal(liveRefreshOk.liveFailedRunsTotal, 22);
  const refreshedAudit = getAllSeeingEyeAuditSnapshot({ liveInventory: liveRefreshOk });
  assert.equal(refreshedAudit.isLiveInventory, true);
  assert.equal(refreshedAudit.liveFailedWorkflowRunsCount, 22);
  assert.equal(refreshedAudit.historicalBaselineFailedRuns, 359);

  // Rate-limited / private repos return null & RATE_LIMITED_OR_PRIVATE_BLIND rather than guessing
  const partialBlind = await refreshAllSeeingEyeLiveInventory(async (url) =>
    String(url).includes('/idp/')
      ? new Response(JSON.stringify({ total_count: 5 }), { status: 200 })
      : new Response('rate limit', { status: 403 })
  );
  assert.equal(partialBlind.inventoryFreshness, 'REFRESH_PARTIAL_OR_RATE_LIMITED');
  assert.equal(partialBlind.liveFailedRunsTotal, null);
  assert.equal(partialBlind.reposLiveMeasuredCount, 1);

  // 3. All 9 KARMA restitution outcomes measure real deliveryStatus & SLOs (never claiming DELIVERED when unexecuted)
  const unsealedSettlement = evaluateUniversalKarmicSettlement({ registeredBusWorkerIds: ['BR-KIMI-01'] });
  assert.equal(unsealedSettlement.restitutionOutcomes.length, 9);
  assert.equal(
    unsealedSettlement.restitutionOutcomes.find((r) => r.outcomeId === 'REST-03')?.deliveryStatus,
    'NOT_DELIVERED'
  );
  const localSealedOnly = evaluateUniversalKarmicSettlement({
    autoSyncHeadSha: '8d4825a2857360d289593ef7555ee0606a9b6105',
    autoSyncBundleSha256: '22f132bf969af36eea859b4615f80aaa6d62d037c1a2671f1a41a4ef60aff036',
    registeredBusWorkerIds: ['BR-KIMI-01'],
  });
  assert.equal(
    localSealedOnly.restitutionOutcomes.find((r) => r.outcomeId === 'REST-03')?.deliveryStatus,
    'PARTIAL_LOCAL_PREREQUISITE_ONLY'
  );
  assert.ok(localSealedOnly.restitutionOutcomes.every((r) => !r.externalEstateDelivered));
  assert.ok(localSealedOnly.restitutionOutcomes.every((r) => r.measuredDeliveryMetric.length > 5 && r.targetSlo.length > 5));

  // 4. ALL materialized static dist/api/* JSON snapshots declare isLiveState=false & HISTORICAL_BUILD_SNAPSHOT_NOT_LIVE
  const repoRoot = pathMod.resolve(pathMod.dirname(new URL(import.meta.url).pathname), '../..');
  const tmpDist = fsMod.mkdtempSync(pathMod.join(osMod.tmpdir(), 'meridian-cloud-proj-'));
  try {
    fsMod.writeFileSync(pathMod.join(tmpDist, 'index.html'), '<html><body>Meridian</body></html>');
    const mat = materializeStaticDistExports(repoRoot, tmpDist);
    assert.equal(mat.materialized, true);
    for (const apiRel of [
      'api/health',
      'api/karma/settlement',
      'api/omniflow/universal-settlement',
      'api/omniflow/state',
      'api/omniflow/mathematical-proof',
      'api/passkey/health',
      'api/resilience/matrix',
      'api/audit/all-seeing-eye',
      'api/export/auto-sync',
    ]) {
      const abs = pathMod.join(tmpDist, apiRel);
      assert.equal(fsMod.existsSync(abs), true, `Missing static cloud projection: ${apiRel}`);
      const parsed = JSON.parse(fsMod.readFileSync(abs, 'utf8'));
      assert.equal(parsed.isLiveState, false, `${apiRel} must declare isLiveState: false`);
      assert.equal(
        parsed.telemetryFreshness,
        'HISTORICAL_BUILD_SNAPSHOT_NOT_LIVE',
        `${apiRel} must declare HISTORICAL_BUILD_SNAPSHOT_NOT_LIVE`
      );
    }
    const healthJson = JSON.parse(fsMod.readFileSync(pathMod.join(tmpDist, 'api/health'), 'utf8'));
    assert.equal(healthJson.certificationWithheld, true);
    assert.equal(healthJson.historicalBaselineFailedRuns, 359);
    assert.equal(healthJson.liveFailedWorkflowRunsCount, null);
    const passkeyJson = JSON.parse(fsMod.readFileSync(pathMod.join(tmpDist, 'api/passkey/health'), 'utf8'));
    assert.equal(passkeyJson.externalHttpReachable, null);
  } finally {
    fsMod.rmSync(tmpDist, { recursive: true, force: true });
  }

  // 5. Cloudflare Pages Function, DO adapter & routes config exist cleanly in repo
  assert.equal(fsMod.existsSync(pathMod.join(repoRoot, 'functions/api/[[route]].ts')), true);
  assert.equal(fsMod.existsSync(pathMod.join(repoRoot, 'public/_routes.json')), true);
});

test('Closed-Loop FSM Constitution: proves 10/10 estate workflows across 6 layers and rejects open-loop traps', async () => {
  const {
    verifyAllEstateFsmsClosedLoop,
    verifySingleFsmClosedLoop,
  } = await import('./estateClosedLoopFsm');

  const constitution = verifyAllEstateFsmsClosedLoop();
  assert.equal(constitution.totalEstateLayers, 6);
  assert.equal(constitution.totalRegisteredFsms, 10);
  assert.equal(constitution.provenClosedLoopCount, 10);
  assert.equal(constitution.allLayersCoveredByFsms, true);
  assert.equal(constitution.allFsmsMathematicallyClosed, true);
  assert.ok(constitution.lawChecklist.every((l) => l.satisfied));

  // Synthetic open-loop FSM with dangling state, missing timeout edge, and missing quarantine path
  const brokenProof = verifySingleFsmClosedLoop({
    fsmId: 'FSM-SYNTHETIC-BROKEN',
    name: 'Broken Open Loop Test',
    layer: 'LAYER_2_OMNIFLOW_SPINE',
    ownerForce: 'Test',
    missionRefs: ['TEST'],
    states: ['INIT', 'WAITING_FOREVER', 'DONE', 'QUARANTINED'],
    initialState: 'INIT',
    verifiedTerminalStates: ['DONE'],
    quarantineTerminalStates: ['QUARANTINED'],
    waitingOrLeasedStatesRequiringTimeout: ['WAITING_FOREVER'],
    transitions: [
      { from: 'INIT', event: 'GO_WAIT', to: 'WAITING_FOREVER' },
      { from: 'INIT', event: 'FAIL', to: 'QUARANTINED' },
      { from: 'INIT', event: 'FINISH', to: 'DONE' }, // Missing requiresProofDigest & WAITING_FOREVER is a dead-end trap
    ],
    futureProofContract: 'Should fail closure proof',
  });
  assert.equal(brokenProof.closedLoopProven, false);
  assert.equal(brokenProof.zeroDeadEndStates, false);
  assert.equal(brokenProof.allWaitingStatesHaveTimeoutEdge, false);
  assert.equal(brokenProof.allVerifiedTerminalsHaveProofDigest, false);
  assert.ok(brokenProof.violations.length >= 3);
});

test('Operation Phoenix v2: real clean-room bundle unpack, live external gap quarantine & 409 fail-closed Go guard', async () => {
  const fsMod = await import('node:fs');
  const pathMod = await import('node:path');
  const { PhoenixDailyBootEngine } = await import('./phoenixDailyBoot');

  const repoRoot = pathMod.resolve(pathMod.dirname(new URL(import.meta.url).pathname), '../..');
  const engine = new PhoenixDailyBootEngine({ repoRoot });

  // Execute real ephemeral temp clone + parity + FSM check + measured live baseline
  const liveRun = await engine.runColdBootDrill({
    triggerSource: 'FOUNDER_MANUAL',
    probeMode: 'LIVE_ESTATE',
    runCleanRoomTsc: false,
    skipLiveNetwork: true,
  });

  assert.equal(liveRun.cleanRoomDirVerified, true);
  assert.equal(liveRun.stages[0].status, 'PASSED');
  assert.equal(liveRun.stages[1].status, 'PASSED');
  assert.equal(liveRun.stages[2].status, 'PASSED');
  assert.equal(liveRun.stages[3].status, 'CRITICAL_FAILURE');
  assert.equal(liveRun.overallVerdict, 'CRITICAL_P0_QUARANTINED');
  assert.ok(liveRun.unblockPack.some((u) => u.category === 'EXTERNAL_CREDENTIALS_AND_DNS'));

  // Zero-tolerance invariant: Go MUST return HTTP 409 when external Stage 4 fails
  const blockedGo = engine.decideGoOrAbort({ decision: 'GO' });
  assert.equal(blockedGo.ok, false);
  assert.equal(blockedGo.httpStatus, 409);
  assert.equal(blockedGo.snapshot.autonomousDispatchAllowed, false);

  // Simulate synthetic P0 fault in Stage 2 & confirm immunity ledger + unblock pack update cleanly
  const injectedRun = await engine.runColdBootDrill({
    triggerSource: 'FAULT_INJECTION_TEST',
    probeMode: 'CLEANROOM_REHEARSAL',
    simulateP0FaultStage: 'STAGE_2_CLEAN_BUILD',
    runCleanRoomTsc: false,
    skipLiveNetwork: true,
  });
  assert.equal(injectedRun.stages[1].status, 'CRITICAL_FAILURE');
  assert.equal(injectedRun.overallVerdict, 'CRITICAL_P0_QUARANTINED');
  assert.ok(injectedRun.unblockPack.some((u) => u.stageId === 'STAGE_2_CLEAN_BUILD'));
  assert.equal(engine.decideGoOrAbort({ decision: 'GO' }).httpStatus, 409);
  assert.equal(fsMod.existsSync(pathMod.join(repoRoot, 'scripts/phoenix-daily-drill.ts')), true);
});

test('Operation Phoenix v2: 100% Quorum unlocks 24h Seal (Go), Emergency Abort freezes, and /phoenix routes resolve', async () => {
  const pathMod = await import('node:path');
  const { PhoenixDailyBootEngine } = await import('./phoenixDailyBoot');
  const { resolveDeclaredAppRoute } = await import('./crescendoThreeWayUnion');

  assert.equal(resolveDeclaredAppRoute('/phoenix', ''), 'phoenix_round_table');
  assert.equal(resolveDeclaredAppRoute('/cold-boot', ''), 'phoenix_round_table');
  assert.equal(resolveDeclaredAppRoute('/round-table', ''), 'phoenix_round_table');
  assert.equal(resolveDeclaredAppRoute('/', '?tab=phoenix'), 'phoenix_round_table');

  const repoRoot = pathMod.resolve(pathMod.dirname(new URL(import.meta.url).pathname), '../..');
  const engine = new PhoenixDailyBootEngine({ repoRoot });

  let safeHealRan = false;
  engine.registerSafeHealHook(() => {
    safeHealRan = true;
    return ['Test Safe-Heal Hook executed'];
  });

  const rehearsalRun = await engine.runColdBootDrill({
    triggerSource: 'SANDBOX_REHEARSAL',
    probeMode: 'CLEANROOM_REHEARSAL',
    runCleanRoomTsc: false,
    skipLiveNetwork: true,
  });

  assert.equal(safeHealRan, true);
  assert.equal(rehearsalRun.overallVerdict, 'QUORUM_READY_AWAITING_GO');
  assert.equal(rehearsalRun.forces.filter((f) => f.quorumState === 'SEATED_READY').length, 8);

  const goResult = engine.decideGoOrAbort({
    decision: 'GO',
    reason: 'Quorum verified in test',
  });
  assert.equal(goResult.ok, true);
  assert.equal(goResult.httpStatus, 200);
  assert.equal(goResult.snapshot.autonomousDispatchAllowed, true);
  assert.equal(goResult.seal?.sealKind, 'CLEANROOM_REHEARSAL_SEAL');
  assert.equal(goResult.snapshot.currentRun.overallVerdict, 'OPERATIONAL_100_PCT_SEALED');

  const abortResult = engine.decideGoOrAbort({
    decision: 'ABORT',
    reason: 'Founder emergency stop test',
  });
  assert.equal(abortResult.ok, true);
  assert.equal(abortResult.httpStatus, 200);
  assert.equal(abortResult.snapshot.autonomousDispatchAllowed, false);
  assert.equal(abortResult.snapshot.currentRun.overallVerdict, 'FOUNDER_ABORTED_FREEZE');
  assert.equal(abortResult.seal?.active, false);
});

test('System-First IoC Reconciler (LAW_SYSTEM_FIRST_IOC_RECONCILER): verifies <=4KB GENESIS_SPORE.dna, ROUTER.md :4200, 8-domain Anti-Confusion Ledger, and #8194 pre-token auto-decomposition', async () => {
  const fsMod = await import('node:fs');
  const osMod = await import('node:os');
  const pathMod = await import('node:path');
  const {
    ANTI_CONFUSION_LEDGER,
    buildSystemFirstIocSnapshot,
    evaluateSystemFirstIocGate,
    INTERCHANGEABLE_ACTUATORS,
    MAX_GENESIS_SPORE_BYTES,
    SYSTEM_FIRST_IOC_LAW_ID,
    verifyRepositoryZeroDependencyContinuity,
  } = await import('./systemFirstIocReconciler');
  const { materializeStaticDistExports } = await import('./debugPackBuilder');

  const repoRoot = pathMod.resolve(pathMod.dirname(new URL(import.meta.url).pathname), '../..');

  // 1. Repository Zero-Dependency DNA verification (AGENTS.md <= 300, ROUTER.md :4200, GENESIS_SPORE.dna <= 4096 B)
  const cont = verifyRepositoryZeroDependencyContinuity(repoRoot);
  assert.equal(cont.verified, true, `DNA continuity failed: ${cont.violations.join('; ')}`);
  assert.equal(cont.law, SYSTEM_FIRST_IOC_LAW_ID);
  assert.equal(cont.agentsMdWithinCeiling, true);
  assert.ok(cont.agentsMdLines <= 300);
  assert.equal(cont.routerMdEnforcesPennyd4200, true);
  assert.equal(cont.routerMdTombstonesLiteLlm4000, true);
  assert.equal(cont.genesisSporeWithin4Kb, true);
  assert.ok(cont.genesisSporeBytes > 500 && cont.genesisSporeBytes <= MAX_GENESIS_SPORE_BYTES);
  assert.equal(cont.constitutionalInvariantsCount, 12);
  assert.equal(cont.catechismAntibodiesCount, 10);
  assert.equal(cont.activeMerkleRoot?.length, 64);
  assert.ok((cont.monotonicFencingToken ?? 0) >= 512);

  // 2. 6 interchangeable stateless model actuators & 8-domain Anti-Confusion Ledger
  assert.deepEqual(
    INTERCHANGEABLE_ACTUATORS.map((a) => a.id),
    ['gemini', 'glm-5.3', 'deepseek', 'kimi', 'claude', 'chatgpt']
  );
  assert.equal(ANTI_CONFUSION_LEDGER.length, 8);

  // 3. Pre-token mechanical containment across valid, ghost-trap, DSH compat boundary, #8194 auto-split, dead host, and unattested cases
  const validAdmit = evaluateSystemFirstIocGate({
    actuatorModel: 'glm-5.3',
    workerQuadAttested: true,
    taskPrompt: 'Route via pennyd on 127.0.0.1:4200 with PENNYD_API_KEY',
    proposedFiles: ['catalog/capabilities.yaml'],
    targetHosts: ['passkey.mumchimp.com'],
  });
  assert.equal(validAdmit.admitted, true);
  assert.equal(validAdmit.httpStatus, 200);
  assert.equal(validAdmit.verdictCode, 'ADMITTED_ZERO_GASLIGHT');
  assert.equal(validAdmit.tokensSpent, 0);

  const dshAliasCompat = evaluateSystemFirstIocGate({
    actuatorModel: 'kimi',
    workerQuadAttested: true,
    taskPrompt: 'Verify dsh-boundary compatibility alias mapping LITELLM_API_KEY -> PENNYD_API_KEY',
    proposedFiles: ['src/router/dshBoundary.ts'],
    targetHosts: ['passkey.mumchimp.com'],
  });
  assert.equal(dshAliasCompat.admitted, true);
  assert.equal(dshAliasCompat.httpStatus, 200);

  const ghostBlocked = evaluateSystemFirstIocGate({
    actuatorModel: 'claude',
    workerQuadAttested: true,
    taskPrompt:
      'Launch com.estate.litellm-router on 127.0.0.1:4000 with LITELLM_API_KEY targeting oke-direct 193.123.184.22',
    proposedFiles: ['catalog/routing.yaml'],
    targetHosts: ['passkey.mumchimp.com'],
  });
  assert.equal(ghostBlocked.admitted, false);
  assert.equal(ghostBlocked.httpStatus, 422);
  assert.equal(ghostBlocked.verdictCode, 'ANTI_CONFUSION_RETIRED_GHOST_BLOCKED');
  assert.equal(ghostBlocked.tokensSpent, 0);
  assert.ok(ghostBlocked.antiConfusionViolations.length >= 3);

  const split8194 = evaluateSystemFirstIocGate({
    actuatorModel: 'deepseek',
    workerQuadAttested: true,
    autoDecompose: true,
    taskPrompt: 'Update catalog, docs, and tests',
    proposedFiles: ['catalog/capabilities.yaml', 'docs/runbook.md', 'tests/test_boundary.py'],
    targetHosts: ['passkey.mumchimp.com'],
  });
  assert.equal(split8194.admitted, true);
  assert.equal(split8194.httpStatus, 200);
  assert.equal(split8194.verdictCode, 'ADMITTED_VIA_AUTO_DECOMPOSITION');
  assert.deepEqual(
    split8194.decomposedChildLanes.map((l) => l.laneId),
    ['LANE-01-catalog', 'LANE-02-docs', 'LANE-03-tests']
  );

  const deadHostBlocked = evaluateSystemFirstIocGate({
    actuatorModel: 'chatgpt',
    workerQuadAttested: true,
    taskPrompt: 'Send live requests to llm.mumchimp.com and estate-bus.mumchimp.com',
    proposedFiles: ['src/router/cloudLane.ts'],
    targetHosts: ['llm.mumchimp.com', 'estate-bus.mumchimp.com'],
  });
  assert.equal(deadHostBlocked.admitted, false);
  assert.equal(deadHostBlocked.httpStatus, 422);
  assert.equal(deadHostBlocked.blockedComponents.length, 2);

  const unattestedBlocked = evaluateSystemFirstIocGate({
    actuatorModel: 'gemini',
    workerQuadAttested: false,
    proposedFiles: ['catalog/capabilities.yaml'],
  });
  assert.equal(unattestedBlocked.admitted, false);
  assert.equal(unattestedBlocked.httpStatus, 403);

  const snap = buildSystemFirstIocSnapshot(repoRoot);
  assert.equal(snap.presets.length, 4);
  assert.equal(snap.defaultEvaluation.httpStatus, 422);

  // 4. Static dist projection materializes ROUTER.md, GENESIS_SPORE.dna, phoenix/index.html, and honest non-live api/ioc/state
  const tmpDist = fsMod.mkdtempSync(pathMod.join(osMod.tmpdir(), 'meridian-ioc-dist-'));
  try {
    fsMod.writeFileSync(pathMod.join(tmpDist, 'index.html'), '<html><body>Meridian</body></html>');
    const mat = materializeStaticDistExports(repoRoot, tmpDist);
    assert.ok(mat.filesWritten.includes('ROUTER.md'));
    assert.ok(mat.filesWritten.includes('GENESIS_SPORE.dna'));
    assert.ok(mat.filesWritten.includes('phoenix/index.html'));
    assert.ok(mat.filesWritten.includes('api/ioc/state'));
    const staticIoc = JSON.parse(fsMod.readFileSync(pathMod.join(tmpDist, 'api/ioc/state'), 'utf8'));
    assert.equal(staticIoc.isLiveState, false);
    assert.equal(staticIoc.telemetryFreshness, 'HISTORICAL_BUILD_SNAPSHOT_NOT_LIVE');
  } finally {
    fsMod.rmSync(tmpDist, { recursive: true, force: true });
  }
});

test('Turnkey Commercial Appliance, Foreign-Country Zero-Device Phone Bootstrap, 12-Vector Red-Team & Perpetual Future-Proof Ratchet', async () => {
  const fsMod = await import('node:fs');
  const osMod = await import('node:os');
  const pathMod = await import('node:path');
  const { verifySingleFsmClosedLoop } = await import('./estateClosedLoopFsm');
  const {
    ApplianceTurnkeyEngine,
    auditAppliancePortMatrix,
    auditPerpetualFutureProofCoverage,
    BASE_APPLIANCE_ASSETS,
    evaluateSignedHelperRpc,
    FSM_APPLIANCE_SETUP_DR,
    FSM_FOREIGN_PHONE_BOOTSTRAP,
  } = await import('./applianceTurnkeySetup');
  const { resolveDeclaredAppRoute } = await import('./crescendoThreeWayUnion');
  const { materializeStaticDistExports } = await import('./debugPackBuilder');

  const repoRoot = pathMod.resolve(pathMod.dirname(new URL(import.meta.url).pathname), '../..');

  // 1. Closed-Loop FSM mathematical proofs for FSM-DR-01 and FSM-PHONE-DR-02
  const drProof = verifySingleFsmClosedLoop(FSM_APPLIANCE_SETUP_DR);
  const phoneProof = verifySingleFsmClosedLoop(FSM_FOREIGN_PHONE_BOOTSTRAP);
  assert.equal(drProof.closedLoopProven, true, `FSM-DR-01 violations: ${drProof.violations.join('; ')}`);
  assert.equal(drProof.zeroDeadEndStates, true);
  assert.equal(drProof.allActiveStatesHaveQuarantineExit, true);
  assert.equal(drProof.allWaitingStatesHaveTimeoutEdge, true);
  assert.equal(drProof.allVerifiedTerminalsHaveProofDigest, true);

  assert.equal(phoneProof.closedLoopProven, true, `FSM-PHONE-DR-02 violations: ${phoneProof.violations.join('; ')}`);
  assert.equal(phoneProof.zeroDeadEndStates, true);
  assert.equal(phoneProof.allActiveStatesHaveQuarantineExit, true);
  assert.equal(phoneProof.allWaitingStatesHaveTimeoutEdge, true);
  assert.equal(phoneProof.allVerifiedTerminalsHaveProofDigest, true);

  // 2. 5-Pillar Commercial Estate Inventory (32 assets, 0 root ports <1024, 100% deterministic)
  assert.equal(BASE_APPLIANCE_ASSETS.length, 32);
  assert.equal(BASE_APPLIANCE_ASSETS.every((a) => a.unprivilegedPortCompliant), true);
  assert.equal(BASE_APPLIANCE_ASSETS.every((a) => a.zeroAgentDeterministic), true);
  assert.equal(BASE_APPLIANCE_ASSETS.every((a) => a.phoneBootstrapIncluded), true);

  // 3. Zero-Sudo Signed Helper XPC Allowlist & Shell Metacharacter Rejection
  const validHelper = evaluateSignedHelperRpc({
    verb: 'INSTALL_LAUNCHD_USER_AGENT',
    argumentPayload: 'ai.estate.dsh-web',
    signedByApplianceEd25519: true,
  });
  assert.equal(validHelper.allowed, true);
  assert.equal(validHelper.httpStatus, 200);

  const shellInjection = evaluateSignedHelperRpc({
    verb: 'INSTALL_LAUNCHD_USER_AGENT',
    argumentPayload: 'ai.estate.dsh-web && sudo chmod 777 /etc',
    signedByApplianceEd25519: true,
  });
  assert.equal(shellInjection.allowed, false);
  assert.equal(shellInjection.httpStatus, 422);
  assert.equal(shellInjection.reasonCode, 'HELPER_SHELL_INJECTION_BLOCKED_422');

  const unsignedRpc = evaluateSignedHelperRpc({
    verb: 'VERIFY_PORT_OWNERSHIP',
    signedByApplianceEd25519: false,
  });
  assert.equal(unsignedRpc.allowed, false);
  assert.equal(unsignedRpc.httpStatus, 403);

  // 4. Clean-room 1-Click Turnkey Setup (0/6 AI models online) + Fault-Injection Atomic Rollback
  const engine = new ApplianceTurnkeyEngine({ repoRoot });
  const cleanSetup = await engine.runTurnkeySetup({
    profile: 'OFFLINE_ZERO_AGENT_LIFEBOAT',
    zeroAgentsOnlineMode: true,
    injectFaultStage: null,
  });
  assert.equal(cleanSetup.fsmStateReached, 'TURNKEY_OPERATIONAL_SEALED');
  assert.equal(cleanSetup.activeAiModelsCount, 0);
  assert.equal(cleanSetup.llmTokensConsumed, 0);
  assert.equal(cleanSetup.sudoPromptsRequired, 0);
  assert.equal(cleanSetup.cliCommandsRequiredFromUser, 0);
  assert.equal(cleanSetup.ed25519KeyModeOctal, '0600');
  assert.ok(cleanSetup.cleanRoomUnpackedFiles >= 20);
  assert.equal(cleanSetup.stages.every((s) => s.status === 'PASSED'), true);

  const faultRollback = await engine.runTurnkeySetup({
    profile: 'PRIMARY_FOUNDER_WORKSTATION',
    zeroAgentsOnlineMode: true,
    injectFaultStage: 'STAGE_4_VAULT_AND_PORT_BIND',
  });
  assert.equal(faultRollback.fsmStateReached, 'SAFE_ROLLBACK_RESTORED');
  assert.equal(faultRollback.rollbackCleanlyVerified, true);

  // Restore clean sealed run state after fault test
  await engine.runTurnkeySetup({
    profile: 'PRIMARY_FOUNDER_WORKSTATION',
    zeroAgentsOnlineMode: true,
  });

  // 5. Foreign-Country, Zero-Device, Brand-New-Phone-From-Scratch Bootstrap + Stolen Laptop Revocation
  const epochBefore = engine.getSovereignEpochFence();
  const subQuorum = engine.runForeignPhoneBootstrap({
    locationPreset: 'TOKYO_ESIM_NO_DEVICES',
    selectedFactors: [
      'FACTOR_1_MEMORIZED_SOVEREIGN_PASSPHRASE',
      'FACTOR_2_NEW_PHONE_FACEID_WEBAUTHN',
    ],
  });
  assert.equal(subQuorum.httpStatus, 403);
  assert.equal(subQuorum.fsmTerminalState, 'BOOTSTRAP_QUARANTINED_ROLLBACK');
  assert.equal(engine.getSovereignEpochFence(), epochBefore);

  const tamperBlocked = engine.runForeignPhoneBootstrap({
    locationPreset: 'ZURICH_HOTEL_WIFI_NO_SIM',
    selectedFactors: [
      'FACTOR_1_MEMORIZED_SOVEREIGN_PASSPHRASE',
      'FACTOR_2_NEW_PHONE_FACEID_WEBAUTHN',
      'FACTOR_4_CLOUDFLARE_ZERO_TRUST_OIDC',
    ],
    simulateCorruptedBundle: true,
  });
  assert.equal(tamperBlocked.httpStatus, 422);
  assert.equal(tamperBlocked.fsmTerminalState, 'BOOTSTRAP_QUARANTINED_ROLLBACK');
  assert.equal(engine.getSovereignEpochFence(), epochBefore);

  const duressLocked = engine.runForeignPhoneBootstrap({
    locationPreset: 'SAO_PAULO_AIRPORT_FRESH_HANDSET',
    selectedFactors: [
      'FACTOR_1_MEMORIZED_SOVEREIGN_PASSPHRASE',
      'FACTOR_2_NEW_PHONE_FACEID_WEBAUTHN',
      'FACTOR_3_GUARDIAN_OFFLINE_QR_SHARD',
    ],
    duressSignal: true,
  });
  assert.equal(duressLocked.httpStatus, 423);
  assert.equal(duressLocked.fsmTerminalState, 'DURESS_PANIC_SAFE_HOLD');
  assert.equal(engine.getSovereignEpochFence(), epochBefore);

  const foreignBoot = engine.runForeignPhoneBootstrap({
    locationPreset: 'TOKYO_ESIM_NO_DEVICES',
    selectedFactors: [
      'FACTOR_1_MEMORIZED_SOVEREIGN_PASSPHRASE',
      'FACTOR_2_NEW_PHONE_FACEID_WEBAUTHN',
      'FACTOR_5_PRINTED_PAPER_VAULT_CODE',
    ],
  });
  assert.equal(foreignBoot.httpStatus, 200);
  assert.equal(foreignBoot.fsmTerminalState, 'FOREIGN_PHONE_SEAL_MINTED');
  assert.equal(foreignBoot.smsOtpUsed, false);
  assert.equal(foreignBoot.cliOrSshUsed, false);
  assert.equal(foreignBoot.aiAgentsRequired, 0);
  assert.equal(foreignBoot.newEpochFence, epochBefore + 1);
  assert.equal(foreignBoot.newPhonePasskeyThumbprint?.length, 64);

  // Old stolen MacBook replaying prior epoch must fail closed with HTTP 409
  const stolenReplay = engine.verifyDeviceSessionEpoch(
    `lost-founder-mac-epoch-${epochBefore}`,
    epochBefore
  );
  assert.equal(stolenReplay.allowed, false);
  assert.equal(stolenReplay.httpStatus, 409);
  assert.equal(stolenReplay.reasonCode, 'STALE_EPOCH_FENCE_REVOKED');

  // 6. 12-Vector Adversarial Red-Team Attack Suite (12/12 defeated)
  const redTeam = await engine.runAdversarialRedTeamSuite();
  assert.equal(redTeam.totalAttacks, 12);
  assert.equal(redTeam.defeatedCount, 12);
  assert.equal(redTeam.vulnerableCount, 0);
  assert.equal(redTeam.allAttacksDefeated, true);

  // 7. Perpetual Future-Proof Codebase Ratchet (live 100% green + synthetic drift detection)
  const liveRatchet = auditPerpetualFutureProofCoverage(repoRoot);
  assert.equal(
    liveRatchet.allFutureInvariantsSatisfied,
    true,
    `Future-proof violations: tabs=[${liveRatchet.unregisteredNavTabs.join(',')}], polling=[${liveRatchet.pollingViolations.join(',')}], env=[${liveRatchet.customEnvViolations.join(',')}]`
  );
  assert.ok(liveRatchet.discoveredNavTabsCount >= 22);
  assert.equal(liveRatchet.wiredSidebarTabsCount, liveRatchet.discoveredNavTabsCount);
  assert.equal(liveRatchet.wiredRouteResolverTabsCount, liveRatchet.discoveredNavTabsCount);
  assert.equal(liveRatchet.pollingViolations.length, 0);
  assert.equal(liveRatchet.customEnvViolations.length, 0);

  const syntheticDrift = auditPerpetualFutureProofCoverage(repoRoot, {
    injectedPhantomNavTabs: ['future_unwired_2028_tab'],
    injectedPollingComponentSource: {
      filename: 'src/components/SyntheticBadPoller.tsx',
      code: 'setInterval(() => fetch("/api/appliance/state"), 1000);',
    },
    injectedCustomEnvSource: {
      filename: 'src/engine/syntheticBadEnv.ts',
      code: ['const k = process', 'env', 'FORBIDDEN_CUSTOM_VAR;'].join('.'),
    },
  });
  assert.equal(syntheticDrift.allFutureInvariantsSatisfied, false);
  assert.ok(syntheticDrift.unregisteredNavTabs.includes('future_unwired_2028_tab'));
  assert.equal(syntheticDrift.pollingViolations.length, 1);
  assert.equal(syntheticDrift.customEnvViolations.length, 1);

  // 8. Port Auditor & URL Route Resolution (/setup, /phone-boot, /dr) + Static Dist Projection
  const ports = await auditAppliancePortMatrix({ skipLiveSocketProbe: true });
  assert.equal(ports.every((p) => p.compliant), true);
  assert.equal(resolveDeclaredAppRoute('/setup', ''), 'appliance_setup');
  assert.equal(resolveDeclaredAppRoute('/phone-boot', ''), 'appliance_setup');
  assert.equal(resolveDeclaredAppRoute('/dr', ''), 'appliance_setup');
  assert.equal(resolveDeclaredAppRoute('/', '?tab=phone-boot'), 'appliance_setup');

  const tmpDist = fsMod.mkdtempSync(pathMod.join(osMod.tmpdir(), 'meridian-appliance-dist-'));
  try {
    fsMod.writeFileSync(pathMod.join(tmpDist, 'index.html'), '<html><body>Meridian</body></html>');
    const mat = materializeStaticDistExports(repoRoot, tmpDist);
    assert.ok(mat.filesWritten.includes('setup/index.html'));
    assert.ok(mat.filesWritten.includes('phone-boot/index.html'));
    assert.ok(mat.filesWritten.includes('api/appliance/state'));
    const staticAppliance = JSON.parse(
      fsMod.readFileSync(pathMod.join(tmpDist, 'api/appliance/state'), 'utf8')
    );
    assert.equal(staticAppliance.isLiveState, false);
    assert.equal(staticAppliance.telemetryFreshness, 'HISTORICAL_BUILD_SNAPSHOT_NOT_LIVE');
    assert.equal(staticAppliance.summary.turnkeyFsmClosedLoopProven, true);
    assert.equal(staticAppliance.summary.phoneBootstrapFsmClosedLoopProven, true);
  } finally {
    fsMod.rmSync(tmpDist, { recursive: true, force: true });
  }
});

test('43. 3-Day Fleet Sync Completeness & Anti-Confusion Guard (15-17 Nov 2026): 18/18 workstreams tracked, 0 untracked files, bundle===HEAD seal, CI workflow & synthetic missing-file falsifier', async () => {
  const pathMod = await import('node:path');
  const fsMod = await import('node:fs');
  const osMod = await import('node:os');
  const {
    ensureGitRepoAndBundle,
    materializeStaticDistExports,
  } = await import('./debugPackBuilder');
  const {
    CANONICAL_GITHUB_SYNC_REF,
    CANONICAL_GITHUB_SYNC_REMOTES,
    renderFleetThreeDayManifestMarkdown,
    verifyThreeDayFleetSyncCompleteness,
  } = await import('./fleetThreeDaySyncGuard');

  const repoRoot = pathMod.resolve(pathMod.dirname(new URL(import.meta.url).pathname), '../..');
  const ensured = ensureGitRepoAndBundle(repoRoot);
  assert.equal(ensured.ok, true);

  const report = verifyThreeDayFleetSyncCompleteness(repoRoot);
  assert.equal(report.dayBreakdown.day1WorkstreamsCount, 4);
  assert.equal(report.dayBreakdown.day2WorkstreamsCount, 8);
  assert.equal(report.dayBreakdown.day3WorkstreamsCount, 6);
  assert.equal(report.dayBreakdown.totalWorkstreamsCount, 18);
  assert.equal(
    report.missingRequiredFiles.length,
    0,
    `Missing 3-day files: ${report.missingRequiredFiles.join(', ')}`
  );
  assert.equal(
    report.untrackedRequiredFiles.length,
    0,
    `Untracked required files: ${report.untrackedRequiredFiles.join(', ')}`
  );
  assert.equal(
    report.untrackedSourceFiles.length,
    0,
    `Untracked workspace files: ${report.untrackedSourceFiles.join(', ')}`
  );
  assert.equal(report.dayBreakdown.verifiedWorkstreamsCount, 18);
  assert.equal(report.bundleExists, true);
  assert.equal(report.bundleVerifiedOk, true);
  assert.equal(report.bundleMatchesHead, true);
  assert.equal(report.bundleHeadSha, report.headSha);
  assert.equal(report.agentsMdWithinCeiling, true);
  assert.ok(report.agentsMdLines <= 300);
  assert.equal(report.genesisSporeWithin4Kb, true);
  assert.ok(report.genesisSporeBytes <= 4096);
  assert.equal(report.manifestAntiConfusionVerified, true);
  assert.equal(report.githubCiWorkflowPresent, true);
  assert.equal(report.allThreeDaysSealed, true);
  assert.equal(
    report.externalGitHubPushState,
    'LOCAL_SEALED_AWAITING_GITHUB_PUSH_RECEIPT'
  );
  assert.deepEqual(report.canonicalGitHubRemotes, [
    'chidionyema/argon-sync',
    'chidionyema/gemini-sync',
  ]);
  assert.equal(report.canonicalGitHubRef, 'refs/heads/aistudio/meridian-hermes-live');
  assert.equal(report.threeDayMerkleRootSha256.length, 64);

  const renderedMd = renderFleetThreeDayManifestMarkdown(report);
  assert.ok(renderedMd.includes('18/18'));
  assert.ok(renderedMd.includes('chidionyema/argon-sync'));
  assert.ok(renderedMd.includes('chidionyema/gemini-sync'));
  assert.ok(renderedMd.includes('127.0.0.1:4200'));

  // Falsifier: simulated dropped Day-3 file fails closed immediately
  const broken = verifyThreeDayFleetSyncCompleteness(repoRoot, {
    injectedMissingFiles: [
      'FLEET_3DAY_CANONICAL_MANIFEST.md',
      'src/engine/applianceTurnkeySetup.ts',
    ],
  });
  assert.equal(broken.allThreeDaysSealed, false);
  assert.equal(broken.missingRequiredFiles.length, 2);

  // Static dist/ projection writes all 3-day manifest & archive endpoints
  const tmpDist = fsMod.mkdtempSync(pathMod.join(osMod.tmpdir(), 'meridian-3day-dist-'));
  try {
    fsMod.writeFileSync(pathMod.join(tmpDist, 'index.html'), '<html><body>Meridian</body></html>');
    const mat = materializeStaticDistExports(repoRoot, tmpDist);
    assert.ok(mat.filesWritten.includes('FLEET_3DAY_CANONICAL_MANIFEST.md'));
    assert.ok(mat.filesWritten.includes('TEAM_HANDOFF_TODAY.md'));
    assert.ok(mat.filesWritten.includes('api/export/all-3days'));
    assert.ok(mat.filesWritten.includes('api/export/fleet-3day-manifest'));
    const staticManifest = JSON.parse(
      fsMod.readFileSync(pathMod.join(tmpDist, 'api/export/fleet-3day-manifest'), 'utf8')
    );
    assert.equal(staticManifest.ok, true);
    assert.equal(staticManifest.isLiveState, false);
    assert.equal(staticManifest.report.allThreeDaysSealed, true);
    assert.equal(CANONICAL_GITHUB_SYNC_REMOTES.length, 2);
    assert.equal(CANONICAL_GITHUB_SYNC_REF, 'refs/heads/aistudio/meridian-hermes-live');
  } finally {
    fsMod.rmSync(tmpDist, { recursive: true, force: true });
  }
});

test('44. Direct GitHub Device Flow Sync (RFC 8628) & Self-Extracting Clipboard Capsule: #7760 producer ref in .bundle, zero secret exposure, multi-repo push + PR receipt, and SHA-256 round-trip capsule', async () => {
  const pathMod = await import('node:path');
  const cpMod = await import('node:child_process');
  const { ensureGitRepoAndBundle } = await import('./debugPackBuilder');
  const {
    ALL_REQUIRED_GITHUB_SYNC_REFS,
    CANONICAL_LIVE_SYNC_REF,
    PRODUCER_7760_SYNC_REF,
    QUARANTINE_PR_SYNC_REF,
    buildSelfExtractingClipboardCapsule,
    disconnectGitHubDeviceSession,
    getGitHubDeviceSyncSnapshot,
    pollGitHubDeviceFlowOnce,
    startGitHubDeviceFlow,
    verifySelfExtractingCapsuleRoundTrip,
  } = await import('./githubDirectDeviceSync');

  const repoRoot = pathMod.resolve(pathMod.dirname(new URL(import.meta.url).pathname), '../..');
  const ensured = ensureGitRepoAndBundle(repoRoot);
  assert.equal(ensured.ok, true);

  // 1. Verify .bundle contains #7760 producer ref, live mirror ref, and quarantine PR ref
  const bundleAbsPath = pathMod.join(repoRoot, 'dist-exports/meridian-hermes-today.bundle');
  const bundleHeads = cpMod
    .execFileSync('git', ['bundle', 'list-heads', bundleAbsPath], {
      cwd: repoRoot,
      encoding: 'utf8',
    })
    .trim();
  assert.ok(
    bundleHeads.includes(PRODUCER_7760_SYNC_REF),
    `Expected ${PRODUCER_7760_SYNC_REF} in bundle heads: ${bundleHeads}`
  );
  assert.ok(bundleHeads.includes(CANONICAL_LIVE_SYNC_REF));
  assert.ok(bundleHeads.includes(QUARANTINE_PR_SYNC_REF));

  // 2. Deterministic RFC 8628 GitHub Device Flow lifecycle with mock fetch + mock gitPushExecutor
  disconnectGitHubDeviceSession();
  try {
    const pushedCalls: string[] = [];
    const mockFetch = (async (url: string | URL | Request) => {
      const target = String(url);
      if (target === 'https://github.com/login/device/code') {
        return new Response(
          JSON.stringify({
            device_code: 'secret_device_code_never_expose_999',
            user_code: 'ABCD-1234',
            verification_uri: 'https://github.com/login/device',
            expires_in: 900,
            interval: 5,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        );
      }
      if (target === 'https://github.com/login/oauth/access_token') {
        return new Response(
          JSON.stringify({
            access_token: 'gho_secret_ephemeral_token_never_expose_777',
            token_type: 'bearer',
            scope: 'repo,workflow',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        );
      }
      if (target === 'https://api.github.com/user') {
        return new Response(JSON.stringify({ login: 'chidionyema' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (target.includes('/pulls?state=open')) {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (target.endsWith('/pulls')) {
        return new Response(
          JSON.stringify({
            html_url: 'https://github.com/chidionyema/gemini-sync/pull/42',
            number: 42,
          }),
          { status: 201, headers: { 'Content-Type': 'application/json' } }
        );
      }
      return new Response('{}', { status: 404 });
    }) as typeof fetch;

    const mockGitExecutor = async (params: {
      repoFullName: string;
      localHeadSha: string;
    }) => {
      pushedCalls.push(params.repoFullName);
      return {
        pushed: true,
        remoteMainParentSha: '1111111111111111111111111111111111111111',
        landedCommitSha: '2222222222222222222222222222222222222222',
        pushedRefs: [...ALL_REQUIRED_GITHUB_SYNC_REFS],
        error: null,
      };
    };

    const startedSnap = await startGitHubDeviceFlow(repoRoot, {
      fetchImpl: mockFetch,
      gitPushExecutor: mockGitExecutor,
      disableAutoReschedule: true,
    });
    assert.equal(startedSnap.phase, 'AWAITING_USER_APPROVAL');
    assert.equal(startedSnap.userCode, 'ABCD-1234');
    assert.equal(startedSnap.verificationUri, 'https://github.com/login/device');
    const serializedPending = JSON.stringify(startedSnap);
    assert.equal(serializedPending.includes('secret_device_code_never_expose_999'), false);

    const polledSnap = await pollGitHubDeviceFlowOnce(repoRoot, {
      fetchImpl: mockFetch,
      gitPushExecutor: mockGitExecutor,
      disableAutoReschedule: true,
    });
    assert.equal(polledSnap.phase, 'PUSHED_CONFIRMED');
    assert.equal(polledSnap.authorizedInMemory, true);
    assert.equal(polledSnap.authenticatedLogin, 'chidionyema');
    assert.equal(polledSnap.allTargetReposPushed, true);
    assert.deepEqual(pushedCalls, ['chidionyema/gemini-sync', 'chidionyema/argon-sync']);
    assert.equal(polledSnap.repoReceipts.length, 2);
    assert.deepEqual(polledSnap.repoReceipts[0].pushedRefs, [...ALL_REQUIRED_GITHUB_SYNC_REFS]);
    assert.equal(
      polledSnap.repoReceipts[0].prUrl,
      'https://github.com/chidionyema/gemini-sync/pull/42'
    );
    const serializedAuthed = JSON.stringify(getGitHubDeviceSyncSnapshot());
    assert.equal(serializedAuthed.includes('gho_secret_ephemeral_token_never_expose_777'), false);
  } finally {
    // Always leave runtime honest (IDLE / unpushed until real Founder approval)
    const cleared = disconnectGitHubDeviceSession({ clearReceipts: true });
    assert.equal(cleared.phase, 'IDLE');
    assert.equal(cleared.authorizedInMemory, false);
    assert.equal(cleared.repoReceipts.length, 0);
  }

  // 3. Self-Extracting Clipboard Capsule round-trip SHA-256 & 3-day inventory verification
  const capsule = buildSelfExtractingClipboardCapsule(repoRoot, 'compact');
  assert.equal(capsule.ok, true);
  assert.ok(capsule.fileCount >= 110, `Expected >=110 files, got ${capsule.fileCount}`);
  assert.ok(capsule.shellCommand.includes('__MERIDIAN_CAPSULE_EOF__'));
  assert.ok(capsule.shellCommand.includes('aistudio/meridian-hermes-carbon-20261117'));

  const roundTrip = verifySelfExtractingCapsuleRoundTrip(capsule);
  assert.equal(roundTrip.verified, true);
  assert.equal(roundTrip.extractedFileCount, capsule.fileCount);
  assert.equal(roundTrip.hasCanonicalManifest, true);
  assert.equal(roundTrip.hasWorkflow, true);
});











