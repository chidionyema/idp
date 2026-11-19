import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import type { AddressInfo } from 'node:net';
import path from 'node:path';
import { app, stopServerBackgroundTimers } from '../../server';
import { ensureGitRepoAndBundle } from './debugPackBuilder';

async function withLiveHttpServer<T>(
  fn: (baseUrl: string) => Promise<T>
): Promise<T> {
  const server = await new Promise<import('node:http').Server>((resolve, reject) => {
    const srv = app.listen(0, '127.0.0.1', () => resolve(srv));
    srv.on('error', reject);
  });
  const addr = server.address() as AddressInfo;
  const baseUrl = `http://127.0.0.1:${addr.port}`;
  try {
    return await fn(baseUrl);
  } finally {
    await new Promise<void>((resolve) => server.close(() => resolve()));
    stopServerBackgroundTimers();
  }
}

async function readFirstSseEvent(
  url: string,
  expectedEventName: string,
  timeoutMs = 5000
): Promise<{ event: string; data: unknown }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: controller.signal });
    assert.equal(res.status, 200);
    assert.ok(res.headers.get('content-type')?.includes('text/event-stream'));
    const reader = res.body?.getReader();
    assert.ok(reader, 'Expected readable SSE body stream');

    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      for (const frame of frames.slice(0, -1)) {
        const lines = frame.split('\n');
        const eventLine = lines.find((l) => l.startsWith('event: '));
        const dataLine = lines.find((l) => l.startsWith('data: '));
        if (eventLine && dataLine) {
          const eventName = eventLine.slice(7).trim();
          if (eventName === expectedEventName) {
            return {
              event: eventName,
              data: JSON.parse(dataLine.slice(6)),
            };
          }
        }
      }
      buffer = frames[frames.length - 1] ?? '';
    }
    throw new Error(`SSE stream closed before emitting event ${expectedEventName}`);
  } finally {
    clearTimeout(timer);
    controller.abort();
  }
}

test('HTTP Integration 1 (Past Days Core): Gateway routing, atomic cap-save, 402 failover, Dagster restart WAL preservation, Union Chronos & 41-case suite API', async () => {
  await withLiveHttpServer(async (baseUrl) => {
    const stateRes = await fetch(`${baseUrl}/api/state`);
    assert.equal(stateRes.status, 200);
    const initialState = (await stateRes.json()) as {
      clientKeys: Array<{ id: string }>;
      walStats: { totalReceipts: number };
    };
    assert.ok(initialState.clientKeys.length >= 2);
    const initialWal = initialState.walStats.totalReceipts;

    // 1. Atomic cap save rejects simulated legacy clobber & preserves sibling keys
    const clobberRes = await fetch(`${baseUrl}/api/cap-save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        keyId: 'ci_canary',
        dailyBudgetUsd: 350,
        simulateLegacyClobberBug: true,
      }),
    });
    assert.equal(clobberRes.status, 400);
    const clobberJson = (await clobberRes.json()) as {
      saveResult: { ok: boolean; rolledBack: boolean };
      state: { clientKeys: Array<{ id: string }> };
    };
    assert.equal(clobberJson.saveResult.ok, false);
    assert.equal(clobberJson.saveResult.rolledBack, true);
    assert.equal(clobberJson.state.clientKeys.length, initialState.clientKeys.length);

    // 2. Inject 402 credit exhaustion -> /api/route automatically fails over -> top-up + Dagster closes circuit
    const faultRes = await fetch(`${baseUrl}/api/lanes/deepseek-flash/fault`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ faultMode: '402_credit_exhausted' }),
    });
    assert.equal(faultRes.status, 200);

    const routeRes = await fetch(`${baseUrl}/api/route`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        clientKey: 'pk_live_opencode_primary_94a2',
        modelSlug: 'deepseek-chat',
        estimatedTokens: 768,
        strategy: 'priority_failover',
      }),
    });
    assert.equal(routeRes.status, 200);
    const routeJson = (await routeRes.json()) as {
      result: { ok: boolean; selectedLaneId: string };
      state: { walStats: { totalReceipts: number } };
    };
    assert.equal(routeJson.result.ok, true);
    assert.notEqual(routeJson.result.selectedLaneId, 'deepseek-flash');
    assert.ok(routeJson.state.walStats.totalReceipts >= initialWal + 1);

    const topupRes = await fetch(`${baseUrl}/api/lanes/deepseek-flash/topup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amountUsd: 250 }),
    });
    assert.equal(topupRes.status, 200);

    // 3. Durable Dagster worker restart drops 0 WAL receipts
    const restartRes = await fetch(`${baseUrl}/api/dagster/restart`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'dagster_durable' }),
    });
    assert.equal(restartRes.status, 200);
    const restartJson = (await restartRes.json()) as {
      report: {
        droppedReceipts: number;
        vaultKeysHydratedOnBoot: boolean;
        clientKeysPreserved: number;
      };
    };
    assert.equal(restartJson.report.droppedReceipts, 0);
    assert.equal(restartJson.report.vaultKeysHydratedOnBoot, true);
    assert.ok(restartJson.report.clientKeysPreserved >= 2);

    // 4. Grand Union beat + 41-case Verification Suite HTTP endpoint pass cleanly
    const unionBeatRes = await fetch(`${baseUrl}/api/union/beat`, { method: 'POST' });
    assert.equal(unionBeatRes.status, 200);

    const suiteRes = await fetch(`${baseUrl}/api/tests/run`, { method: 'POST' });
    assert.equal(suiteRes.status, 200);
    const suiteReport = (await suiteRes.json()) as {
      totalCases: number;
      passedCases: number;
      failedCases: number;
      passedAssertions: number;
      totalAssertions: number;
    };
    assert.equal(suiteReport.totalCases, 41);
    assert.equal(suiteReport.passedCases, 41);
    assert.equal(suiteReport.failedCases, 0);
    assert.equal(suiteReport.passedAssertions, suiteReport.totalAssertions);
  });
});

test('HTTP Integration 2 (Cross-Surface OMNIFLOW, #7760 Sync Receiver, KARMA Settlement & Resilience Honesty): full live API contracts', async () => {
  await withLiveHttpServer(async (baseUrl) => {
    const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../..');
    const ensured = ensureGitRepoAndBundle(repoRoot);
    assert.equal(ensured.ok, true);
    const bundleBytes = fs.readFileSync(ensured.bundleAbs);
    const bundleSha = createHash('sha256').update(bundleBytes).digest('hex');

    // 1. #7760 Bundle Ingest: fail closed on forged X-Bundle-Sha256 (401), accept valid bundle & wake session (200)
    const badDigestRes = await fetch(`${baseUrl}/api/ingest/bundle`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/octet-stream',
        'X-Bundle-Sha256': '0'.repeat(64),
      },
      body: bundleBytes,
    });
    assert.equal(badDigestRes.status, 401);

    const validIngestRes = await fetch(`${baseUrl}/api/ingest/bundle`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/octet-stream',
        'X-Bundle-Sha256': bundleSha,
        'X-Estate-Session-Id': 'http-int-session-01',
        'X-Wake-Agent': 'pennyd-sync-reconciler',
      },
      body: bundleBytes,
    });
    assert.equal(validIngestRes.status, 202);
    const ingestJson = (await validIngestRes.json()) as {
      accepted: boolean;
      verifiedSha256: string;
      independentReadbackVerified: boolean;
      wakeDisposition: string;
    };
    assert.equal(ingestJson.accepted, true);
    assert.equal(ingestJson.verifiedSha256, bundleSha);
    assert.equal(ingestJson.independentReadbackVerified, true);
    assert.ok(
      ingestJson.wakeDisposition === 'SPAWNED_NEW_SESSION' ||
        ingestJson.wakeDisposition === 'WOKEN_IDLE_SESSION'
    );

    // 2. OMNIFLOW live bus over HTTP: publish claimable envelope -> claim -> 409 stale fence -> 403 self-verify -> 200 independent KARMA verify
    const onboardRes = await fetch(`${baseUrl}/api/omniflow/onboard-worker`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workerId: 'BR-KIMI-01' }),
    });
    assert.equal(onboardRes.status, 200);

    const pubRes = await fetch(`${baseUrl}/api/omniflow/publish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        fromAgent: 'founder-web-tab',
        fromSurface: 'FOUNDER_COCKPIT',
        target: '@all',
        verb: 'ASK',
        body: 'HTTP Integration lease custody verification',
        idempotencyKey: `idem-http-lease-${Date.now()}`,
        requiresClaim: true,
        proposedFiles: ['src/engine/omniflowLiveBus.ts'],
      }),
    });
    assert.equal(pubRes.status, 201);
    const pubJson = (await pubRes.json()) as { message: { envelopeId: string } };
    const envelopeId = pubJson.message.envelopeId;

    const claimRes = await fetch(`${baseUrl}/api/omniflow/lease`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'CLAIM', envelopeId, workerId: 'BR-KIMI-01' }),
    });
    assert.equal(claimRes.status, 200);
    const claimJson = (await claimRes.json()) as {
      message: { fencingToken: number };
    };
    const activeFence = claimJson.message.fencingToken;

    const staleFenceRes = await fetch(`${baseUrl}/api/omniflow/lease`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'SUBMIT_EFFECT',
        envelopeId,
        workerId: 'BR-KIMI-01',
        fencingToken: Math.max(0, activeFence - 1),
      }),
    });
    assert.equal(staleFenceRes.status, 409);

    const submitOkRes = await fetch(`${baseUrl}/api/omniflow/lease`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'SUBMIT_EFFECT',
        envelopeId,
        workerId: 'BR-KIMI-01',
        fencingToken: activeFence,
        artifactRef: 'commit-verified-http',
      }),
    });
    assert.equal(submitOkRes.status, 200);

    const selfVerifyRes = await fetch(`${baseUrl}/api/omniflow/lease`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'VERIFY_EFFECT',
        envelopeId,
        verifierId: 'BR-KIMI-01',
      }),
    });
    assert.equal(selfVerifyRes.status, 403);

    const indepVerifyRes = await fetch(`${baseUrl}/api/omniflow/lease`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'VERIFY_EFFECT',
        envelopeId,
        verifierId: 'karma-verifier-external',
        evidenceNote: 'Independent HTTP verifier attested delivery',
      }),
    });
    assert.equal(indepVerifyRes.status, 200);

    // 3. Health, KARMA, Resilience Matrix, All-Seeing Eye return live state honestly (never fake green)
    for (const ep of [
      '/api/health',
      '/api/karma/settlement',
      '/api/resilience/matrix',
      '/api/audit/all-seeing-eye',
    ]) {
      const r = await fetch(`${baseUrl}${ep}`);
      assert.equal(r.status, 200);
      const j = (await r.json()) as { isLiveState: boolean; telemetryFreshness: string };
      assert.equal(j.isLiveState, true, `${ep} must report isLiveState: true`);
      assert.equal(j.telemetryFreshness, 'LIVE_EXPRESS_RUNTIME');
    }
  });
});

test('HTTP & SSE Integration 3 (Today — Operation Phoenix v2 & Closed-Loop FSM): live SSE frame, 409 Go lock, Quorum Go Seal -> OMNIFLOW -> Fault Auto-Revoke', async () => {
  await withLiveHttpServer(async (baseUrl) => {
    // 1. FSM Constitution API proves 6/6 layers and 10/10 mathematically closed workflows
    const fsmRes = await fetch(`${baseUrl}/api/estate/fsm-constitution`);
    assert.equal(fsmRes.status, 200);
    const fsmJson = (await fsmRes.json()) as {
      ok: boolean;
      constitution: {
        totalEstateLayers: number;
        totalRegisteredFsms: number;
        provenClosedLoopCount: number;
        allFsmsMathematicallyClosed: boolean;
      };
    };
    assert.equal(fsmJson.ok, true);
    assert.equal(fsmJson.constitution.totalEstateLayers, 6);
    assert.equal(fsmJson.constitution.totalRegisteredFsms, 10);
    assert.equal(fsmJson.constitution.provenClosedLoopCount, 10);

    // 2. Real SSE stream handshake emits initial phoenix_snapshot event
    const sseFrame = await readFirstSseEvent(
      `${baseUrl}/api/phoenix/stream`,
      'phoenix_snapshot'
    );
    assert.equal(sseFrame.event, 'phoenix_snapshot');
    assert.equal(
      (sseFrame.data as { schemaVersion: string }).schemaVersion,
      'meridian-phoenix-v2'
    );

    // 3. Premature Go fails closed with HTTP 409
    const blockedGoRes = await fetch(`${baseUrl}/api/phoenix/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision: 'GO' }),
    });
    assert.equal(blockedGoRes.status, 409);

    // 4. Clean-Room Quorum Rehearsal passes Stages 1-6 -> Authorizes 24h Seal (200) -> Broadcasts onto OMNIFLOW
    const rehearsalRes = await fetch(`${baseUrl}/api/phoenix/drill`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        probeMode: 'CLEANROOM_REHEARSAL',
        triggerSource: 'SANDBOX_REHEARSAL',
        runCleanRoomTsc: false,
      }),
    });
    assert.equal(rehearsalRes.status, 200);
    const rehearsalJson = (await rehearsalRes.json()) as {
      ok: boolean;
      run: { overallVerdict: string };
    };
    assert.equal(rehearsalJson.ok, true);
    assert.equal(rehearsalJson.run.overallVerdict, 'QUORUM_READY_AWAITING_GO');

    const goRes = await fetch(`${baseUrl}/api/phoenix/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision: 'GO', reason: 'HTTP Integration Seal test' }),
    });
    assert.equal(goRes.status, 200);
    const goJson = (await goRes.json()) as {
      ok: boolean;
      seal: { active: boolean; sealKind: string };
      snapshot: { autonomousDispatchAllowed: boolean };
    };
    assert.equal(goJson.ok, true);
    assert.equal(goJson.seal.active, true);
    assert.equal(goJson.snapshot.autonomousDispatchAllowed, true);

    const busAfterGoRes = await fetch(`${baseUrl}/api/omniflow/state`);
    assert.equal(busAfterGoRes.status, 200);
    const busAfterGo = (await busAfterGoRes.json()) as {
      messages: Array<{ body: string }>;
    };
    assert.ok(
      busAfterGo.messages.some((m) => m.body.includes('AUTHORIZED_DAILY_OPERATIONS'))
    );

    // 5. Subsequent P0 Fault Drill MUST automatically revoke active Seal fail-closed and lock GO back to 409
    const p0DrillRes = await fetch(`${baseUrl}/api/phoenix/drill`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        probeMode: 'CLEANROOM_REHEARSAL',
        triggerSource: 'FAULT_INJECTION_TEST',
        simulateP0FaultStage: 'STAGE_4_EXTERNAL_PROBES',
        runCleanRoomTsc: false,
      }),
    });
    assert.equal(p0DrillRes.status, 200);
    const p0Json = (await p0DrillRes.json()) as {
      ok: boolean;
      snapshot: {
        autonomousDispatchAllowed: boolean;
        activeSeal: { active: boolean; revokedReason: string | null } | null;
        currentRun: { overallVerdict: string };
      };
    };
    assert.equal(p0Json.ok, false);
    assert.equal(p0Json.snapshot.currentRun.overallVerdict, 'CRITICAL_P0_QUARANTINED');
    assert.equal(p0Json.snapshot.autonomousDispatchAllowed, false);
    assert.equal(p0Json.snapshot.activeSeal?.active, false);
    assert.ok(p0Json.snapshot.activeSeal?.revokedReason?.includes('FAIL-CLOSED'));

    const postFaultGoRes = await fetch(`${baseUrl}/api/phoenix/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision: 'GO' }),
    });
    assert.equal(postFaultGoRes.status, 409);
  });
});

test('HTTP & SSE Integration 4 (Full Estate Multi-Day Sweep): Union & Reactivity SSE streams, 20/20 Guarantees, Mum’s Concierge, Hermes, AURA-2100, Genesis TTT, Prospector-2100 & Rego Plane', async () => {
  const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../..');
  ensureGitRepoAndBundle(repoRoot);

  await withLiveHttpServer(async (baseUrl) => {
    // 1. Live SSE streams for Grand Union & Autonomous Reactivity (#8184)
    const unionSse = await readFirstSseEvent(`${baseUrl}/api/union/stream`, 'union_snapshot');
    assert.equal(unionSse.event, 'union_snapshot');

    const reactSse = await readFirstSseEvent(
      `${baseUrl}/api/reactivity/stream`,
      'reactivity_snapshot'
    );
    assert.equal(reactSse.event, 'reactivity_snapshot');

    // 2. 20/20 Production & Operational Guarantees endpoint
    const guarRes = await fetch(`${baseUrl}/api/union/guarantees`);
    assert.equal(guarRes.status, 200);
    const guarJson = (await guarRes.json()) as {
      totalCount: number;
      verifiedCount: number;
      allVerified: boolean;
    };
    assert.equal(guarJson.totalCount, 20);
    assert.equal(guarJson.verifiedCount, 20);
    assert.equal(guarJson.allVerified, true);

    // 3. MUM-CONCIERGE-001 (Auntie Ezinne WhatsApp & EON-001): 9/9 safety falsifiers & 11/11 negative scenarios
    const mumRes = await fetch(`${baseUrl}/api/concierge/falsify-all`, { method: 'POST' });
    assert.equal(mumRes.status, 200);
    const mumJson = (await mumRes.json()) as {
      safetyPassedCount: number;
      safetyTotalCount: number;
      negativePassedCount: number;
      negativeTotalCount: number;
    };
    assert.equal(mumJson.safetyPassedCount, 9);
    assert.equal(mumJson.safetyTotalCount, 9);
    assert.equal(mumJson.negativePassedCount, 11);
    assert.equal(mumJson.negativeTotalCount, 11);

    // 4. Hermes Living Tree: Greek isopsephy (Ἰησοῦς = 888) + Bidi sanitization
    const hermesRes = await fetch(`${baseUrl}/api/hermes/calculate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: 'Ἰησοῦς\u202E' }),
    });
    assert.equal(hermesRes.status, 200);
    const hermesJson = (await hermesRes.json()) as {
      strippedControlOrBidi: number;
      readings: Array<{ total: number }>;
    };
    assert.equal(hermesJson.strippedControlOrBidi, 1);
    assert.equal(hermesJson.readings[0]?.total, 888);

    // 5. AURA-2100 64-byte binary manifold stream (exact multiple of 64 bytes)
    const auraBinRes = await fetch(`${baseUrl}/api/aura/frames.bin`);
    assert.equal(auraBinRes.status, 200);
    const auraBytes = Buffer.from(await auraBinRes.arrayBuffer());
    assert.ok(auraBytes.byteLength >= 64);
    assert.equal(auraBytes.byteLength % 64, 0);

    // 6. Genesis Survival I-8088 + GEN-TTT-001, Prospector-2100, Founder Rego Plane, VIP Telegram & Investor Room
    for (const ep of [
      '/api/genesis/survival-ttt',
      '/api/prospector/state',
      '/api/founder/plane',
      '/api/founder/rego-bundle',
      '/api/telegram/state',
      '/api/commercial/overview',
      '/api/symphony',
    ]) {
      const r = await fetch(`${baseUrl}${ep}`);
      assert.equal(r.status, 200, `Expected HTTP 200 on ${ep}`);
    }
  });
});

test('HTTP Integration 5 (System-First IoC & 4KB DNA): /ROUTER.md, /GENESIS_SPORE.dna <=4KB, /api/ioc/state, and /api/ioc/evaluate-admission 200/403/422 contracts', async () => {
  await withLiveHttpServer(async (baseUrl) => {
    // 1. /ROUTER.md serves canonical pennyd 127.0.0.1:4200 contract & LiteLLM :4000 tombstone
    const routerRes = await fetch(`${baseUrl}/ROUTER.md`);
    assert.equal(routerRes.status, 200);
    const routerText = await routerRes.text();
    assert.ok(routerText.includes('127.0.0.1:4200'));
    assert.ok(routerText.includes('PENNYD_API_KEY'));
    assert.ok(routerText.includes(':4000'));

    // 2. /GENESIS_SPORE.dna serves <= 4,096-byte self-extracting JSON DNA
    const sporeRes = await fetch(`${baseUrl}/GENESIS_SPORE.dna`);
    assert.equal(sporeRes.status, 200);
    const sporeRaw = await sporeRes.text();
    assert.ok(Buffer.byteLength(sporeRaw, 'utf8') <= 4096);
    const sporeJson = JSON.parse(sporeRaw) as {
      law: string;
      constitutional_invariants: string[];
      catechism_antibodies: unknown[];
    };
    assert.equal(sporeJson.law, 'LAW_SYSTEM_FIRST_IOC_RECONCILER');
    assert.equal(sporeJson.constitutional_invariants.length, 12);
    assert.equal(sporeJson.catechism_antibodies.length, 10);

    // 3. /api/ioc/state returns live 8-domain Anti-Confusion Ledger & 6 interchangeable actuators
    const stateRes = await fetch(`${baseUrl}/api/ioc/state`);
    assert.equal(stateRes.status, 200);
    const stateJson = (await stateRes.json()) as {
      ok: boolean;
      isLiveState: boolean;
      telemetryFreshness: string;
      snapshot: {
        continuity: { verified: boolean; genesisSporeWithin4Kb: boolean };
        actuators: Array<{ id: string }>;
        antiConfusionLedger: Array<{ domainId: string }>;
      };
    };
    assert.equal(stateJson.ok, true);
    assert.equal(stateJson.isLiveState, true);
    assert.equal(stateJson.telemetryFreshness, 'LIVE_EXPRESS_RUNTIME');
    assert.equal(stateJson.snapshot.continuity.verified, true);
    assert.equal(stateJson.snapshot.continuity.genesisSporeWithin4Kb, true);
    assert.equal(stateJson.snapshot.actuators.length, 6);
    assert.equal(stateJson.snapshot.antiConfusionLedger.length, 8);

    // 4. POST /api/ioc/evaluate-admission enforces 200 admit, 422 ghost block, 200 #8194 auto-split, and 403 unattested
    const admitRes = await fetch(`${baseUrl}/api/ioc/evaluate-admission`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        actuatorModel: 'glm-5.3',
        workerQuadAttested: true,
        taskPrompt: 'Route via pennyd on 127.0.0.1:4200 using PENNYD_API_KEY',
        proposedFiles: ['catalog/capabilities.yaml'],
        targetHosts: ['passkey.mumchimp.com'],
      }),
    });
    assert.equal(admitRes.status, 200);
    const admitJson = (await admitRes.json()) as {
      ok: boolean;
      result: { verdictCode: string; tokensSpent: number };
    };
    assert.equal(admitJson.ok, true);
    assert.equal(admitJson.result.verdictCode, 'ADMITTED_ZERO_GASLIGHT');
    assert.equal(admitJson.result.tokensSpent, 0);

    const ghostRes = await fetch(`${baseUrl}/api/ioc/evaluate-admission`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        actuatorModel: 'claude',
        workerQuadAttested: true,
        taskPrompt: 'Use http://127.0.0.1:4000 LiteLLM and oke-direct 193.123.184.22',
        proposedFiles: ['catalog/routing.yaml'],
        targetHosts: ['passkey.mumchimp.com'],
      }),
    });
    assert.equal(ghostRes.status, 422);
    const ghostJson = (await ghostRes.json()) as {
      ok: boolean;
      result: { verdictCode: string; tokensSpent: number };
    };
    assert.equal(ghostJson.ok, false);
    assert.equal(ghostJson.result.verdictCode, 'ANTI_CONFUSION_RETIRED_GHOST_BLOCKED');
    assert.equal(ghostJson.result.tokensSpent, 0);

    const splitRes = await fetch(`${baseUrl}/api/ioc/evaluate-admission`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        actuatorModel: 'deepseek',
        workerQuadAttested: true,
        autoDecompose: true,
        taskPrompt: 'Update catalog, docs, and tests',
        proposedFiles: ['catalog/capabilities.yaml', 'docs/runbook.md', 'tests/test_boundary.py'],
        targetHosts: ['passkey.mumchimp.com'],
      }),
    });
    assert.equal(splitRes.status, 200);
    const splitJson = (await splitRes.json()) as {
      ok: boolean;
      result: { verdictCode: string; decomposedChildLanes: Array<{ laneId: string }> };
    };
    assert.equal(splitJson.ok, true);
    assert.equal(splitJson.result.verdictCode, 'ADMITTED_VIA_AUTO_DECOMPOSITION');
    assert.equal(splitJson.result.decomposedChildLanes.length, 3);

    const unauthRes = await fetch(`${baseUrl}/api/ioc/evaluate-admission`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        actuatorModel: 'kimi',
        workerQuadAttested: false,
        proposedFiles: ['catalog/capabilities.yaml'],
      }),
    });
    assert.equal(unauthRes.status, 403);
  });
});

test('HTTP & SSE Integration 6 (Turnkey Appliance & Foreign Phone DR): /api/appliance/state, SSE stream, 1-click setup, foreign phone bootstrap (200/403/423), stolen-laptop 409 fence, 12/12 red-team & zero-secret capsule', async () => {
  await withLiveHttpServer(async (baseUrl) => {
    // 1. Live GET /api/appliance/state
    const stateRes = await fetch(`${baseUrl}/api/appliance/state`);
    assert.equal(stateRes.status, 200);
    const stateJson = (await stateRes.json()) as {
      ok: boolean;
      isLiveState: boolean;
      snapshot: {
        sovereignEpochFence: number;
        assets: Array<{ id: string }>;
        turnkeyFsmProof: { closedLoopProven: boolean };
        phoneBootstrapFsmProof: { closedLoopProven: boolean };
        perpetualFutureProof: { allFutureInvariantsSatisfied: boolean };
        lastRedTeamReport: { totalAttacks: number; defeatedCount: number };
      };
    };
    assert.equal(stateJson.ok, true);
    assert.equal(stateJson.isLiveState, true);
    assert.equal(stateJson.snapshot.assets.length, 32);
    assert.equal(stateJson.snapshot.turnkeyFsmProof.closedLoopProven, true);
    assert.equal(stateJson.snapshot.phoneBootstrapFsmProof.closedLoopProven, true);
    assert.equal(stateJson.snapshot.perpetualFutureProof.allFutureInvariantsSatisfied, true);
    assert.equal(stateJson.snapshot.lastRedTeamReport.totalAttacks, 12);
    assert.equal(stateJson.snapshot.lastRedTeamReport.defeatedCount, 12);
    const initialEpoch = stateJson.snapshot.sovereignEpochFence;

    // 2. Live SSE GET /api/appliance/stream emits initial appliance_snapshot frame (I-8090 zero polling)
    const sseController = new AbortController();
    const sseRes = await fetch(`${baseUrl}/api/appliance/stream`, {
      signal: sseController.signal,
    });
    assert.equal(sseRes.status, 200);
    assert.ok(sseRes.headers.get('content-type')?.includes('text/event-stream'));
    const reader = sseRes.body!.getReader();
    let sseAccum = '';
    for (let i = 0; i < 6 && !sseAccum.includes('event: appliance_snapshot'); i++) {
      const { value, done } = await reader.read();
      if (done) break;
      sseAccum += Buffer.from(value).toString('utf8');
    }
    sseController.abort();
    assert.ok(sseAccum.includes('event: appliance_snapshot'));
    assert.ok(sseAccum.includes('meridian-appliance-turnkey-v1'));

    // 3. POST /api/appliance/phone-bootstrap: 2-of-8 rejected (403), duress safe-hold (423), 3-of-8 Tokyo eSIM sealed (200)
    const subQuorumRes = await fetch(`${baseUrl}/api/appliance/phone-bootstrap`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        locationPreset: 'TOKYO_ESIM_NO_DEVICES',
        selectedFactors: [
          'FACTOR_1_MEMORIZED_SOVEREIGN_PASSPHRASE',
          'FACTOR_2_NEW_PHONE_FACEID_WEBAUTHN',
        ],
      }),
    });
    assert.equal(subQuorumRes.status, 403);

    const duressRes = await fetch(`${baseUrl}/api/appliance/phone-bootstrap`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        locationPreset: 'SAO_PAULO_AIRPORT_FRESH_HANDSET',
        selectedFactors: [
          'FACTOR_1_MEMORIZED_SOVEREIGN_PASSPHRASE',
          'FACTOR_2_NEW_PHONE_FACEID_WEBAUTHN',
          'FACTOR_3_GUARDIAN_OFFLINE_QR_SHARD',
        ],
        duressSignal: true,
      }),
    });
    assert.equal(duressRes.status, 423);

    const bootOkRes = await fetch(`${baseUrl}/api/appliance/phone-bootstrap`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        locationPreset: 'TOKYO_ESIM_NO_DEVICES',
        selectedFactors: [
          'FACTOR_1_MEMORIZED_SOVEREIGN_PASSPHRASE',
          'FACTOR_2_NEW_PHONE_FACEID_WEBAUTHN',
          'FACTOR_3_GUARDIAN_OFFLINE_QR_SHARD',
        ],
      }),
    });
    assert.equal(bootOkRes.status, 200);
    const bootOkJson = (await bootOkRes.json()) as {
      ok: boolean;
      receipt: {
        newEpochFence: number;
        smsOtpUsed: boolean;
        cliOrSshUsed: boolean;
        fsmTerminalState: string;
      };
    };
    assert.equal(bootOkJson.ok, true);
    assert.equal(bootOkJson.receipt.newEpochFence, initialEpoch + 1);
    assert.equal(bootOkJson.receipt.smsOtpUsed, false);
    assert.equal(bootOkJson.receipt.cliOrSshUsed, false);
    assert.equal(bootOkJson.receipt.fsmTerminalState, 'FOREIGN_PHONE_SEAL_MINTED');

    // 4. Stolen laptop replaying prior epoch fails closed with HTTP 409
    const replayRes = await fetch(`${baseUrl}/api/appliance/verify-epoch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        deviceId: `lost-founder-mac-epoch-${initialEpoch}`,
        presentedEpochFence: initialEpoch,
      }),
    });
    assert.equal(replayRes.status, 409);

    // 5. POST /api/appliance/red-team (12/12) & GET /api/appliance/recovery-capsule (0 plaintext secrets)
    const redTeamRes = await fetch(`${baseUrl}/api/appliance/red-team`, { method: 'POST' });
    assert.equal(redTeamRes.status, 200);
    const redTeamJson = (await redTeamRes.json()) as {
      ok: boolean;
      report: { allAttacksDefeated: boolean; defeatedCount: number; totalAttacks: number };
    };
    assert.equal(redTeamJson.ok, true);
    assert.equal(redTeamJson.report.allAttacksDefeated, true);
    assert.equal(redTeamJson.report.defeatedCount, 12);

    const capRes = await fetch(`${baseUrl}/api/appliance/recovery-capsule`);
    assert.equal(capRes.status, 200);
    const capJson = (await capRes.json()) as {
      containsPlaintextSecrets: boolean;
      managedAssetIds: string[];
      capsuleIntegritySha256: string;
    };
    assert.equal(capJson.containsPlaintextSecrets, false);
    assert.equal(capJson.managedAssetIds.length, 32);
    assert.equal(capJson.capsuleIntegritySha256.length, 64);

    // 6. 3-Day Fleet Sync Completeness & Anti-Confusion HTTP Contracts
    const threeDayRes = await fetch(`${baseUrl}/api/export/fleet-3day-manifest`);
    assert.equal(threeDayRes.status, 200);
    const threeDayJson = (await threeDayRes.json()) as {
      ok: boolean;
      isLiveState: boolean;
      report: {
        allThreeDaysSealed: boolean;
        bundleMatchesHead: boolean;
        untrackedSourceFiles: string[];
        dayBreakdown: { verifiedWorkstreamsCount: number; totalWorkstreamsCount: number };
      };
    };
    assert.equal(threeDayJson.ok, true);
    assert.equal(threeDayJson.isLiveState, true);
    assert.equal(threeDayJson.report.allThreeDaysSealed, true);
    assert.equal(threeDayJson.report.bundleMatchesHead, true);
    assert.equal(threeDayJson.report.untrackedSourceFiles.length, 0);
    assert.equal(threeDayJson.report.dayBreakdown.verifiedWorkstreamsCount, 18);
    assert.equal(threeDayJson.report.dayBreakdown.totalWorkstreamsCount, 18);

    const rootMdRes = await fetch(`${baseUrl}/FLEET_3DAY_CANONICAL_MANIFEST.md`);
    assert.equal(rootMdRes.status, 200);
    assert.equal(rootMdRes.headers.get('x-three-day-sealed'), 'true');
    const rootMdText = await rootMdRes.text();
    assert.ok(rootMdText.includes('127.0.0.1:4200'));
    assert.ok(rootMdText.includes('193.123.184.22'));
    assert.ok(rootMdText.includes('chidionyema/argon-sync'));

    const all3DaysJsonRes = await fetch(`${baseUrl}/api/export/all-3days?format=json`);
    assert.equal(all3DaysJsonRes.status, 200);
    const all3DaysJson = (await all3DaysJsonRes.json()) as {
      ok: boolean;
      files: string[];
    };
    assert.equal(all3DaysJson.ok, true);
    assert.ok(all3DaysJson.files.includes('FLEET_3DAY_CANONICAL_MANIFEST.md'));
    assert.ok(all3DaysJson.files.includes('.github/workflows/fleet-3day-sync-verify.yml'));

    // 7. Direct GitHub Device Flow status & Self-Extracting Clipboard Capsule HTTP contracts
    const ghStatusRes = await fetch(`${baseUrl}/api/export/github-device/status`);
    assert.equal(ghStatusRes.status, 200);
    const ghStatusJson = (await ghStatusRes.json()) as {
      ok: boolean;
      githubDevice: {
        phase: string;
        targetRepos: string[];
        targetRefs: string[];
      };
    };
    assert.equal(ghStatusJson.ok, true);
    assert.deepEqual(ghStatusJson.githubDevice.targetRepos, [
      'chidionyema/gemini-sync',
      'chidionyema/argon-sync',
    ]);
    assert.ok(
      ghStatusJson.githubDevice.targetRefs.includes(
        'refs/heads/aistudio/meridian-hermes-carbon-20261117'
      )
    );

    const capsuleRes = await fetch(`${baseUrl}/api/export/clipboard-capsule?mode=compact`);
    assert.equal(capsuleRes.status, 200);
    const capsuleJson = (await capsuleRes.json()) as {
      ok: boolean;
      fileCount: number;
      payloadSha256: string;
      shellCommand: string;
    };
    assert.equal(capsuleJson.ok, true);
    assert.ok(capsuleJson.fileCount >= 110);
    assert.equal(capsuleJson.payloadSha256.length, 64);
    assert.ok(capsuleJson.shellCommand.includes('__MERIDIAN_CAPSULE_EOF__'));
    assert.ok(capsuleJson.shellCommand.includes('aistudio/meridian-hermes-carbon-20261117'));
  });
});





