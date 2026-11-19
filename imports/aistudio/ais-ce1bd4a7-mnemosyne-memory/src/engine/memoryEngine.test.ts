import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createInitialMemoryNodes,
  createInitialThreads,
  ingestMemoryEvent,
  executeContextRotPurgeAndReanchor,
  evaluateSystemMetrics,
  mintVerificationBlock,
  verifyLedgerChainIntegrity,
  createInitialGenesisAgents,
  executeGenesisAgentMemoryTick,
  updateGenesisAgentConfig,
} from './memoryEngine';
import { SOVEREIGN_MODULES } from '../data/frontierResearch';

const ALL_MODULE_KEYS = SOVEREIGN_MODULES.map((m) => m.key);

test('bi-temporal contradiction ingestion supersedes old fact edge and promotes new edge', () => {
  const initialNodes = createInitialMemoryNodes();
  // mem-05 is RateLimiter_Gateway | configured_burst_ceiling | 2,500 req/s
  const result = ingestMemoryEvent(
    initialNodes,
    {
      subject: 'RateLimiter_Gateway',
      predicate: 'configured_burst_ceiling',
      object: '10,000 req/s with adaptive eBPF token bucket',
      category: 'runtime_metric',
    },
    ALL_MODULE_KEYS
  );

  assert.deepEqual(result.supersededNodeIds, ['mem-05']);
  const oldNode = result.updatedNodes.find((n) => n.id === 'mem-05');
  assert.ok(oldNode);
  assert.equal(oldNode.tier, 'archived_superseded');
  assert.ok(oldNode.validUntilStep !== null);
  assert.equal(oldNode.supersededById, result.newNode.id);
  assert.equal(result.newNode.tier, 'working_focus');
  assert.equal(result.newNode.validUntilStep, null);
});

test('ingestMemoryEvent validates required fields and rejects empty inputs', () => {
  const initialNodes = createInitialMemoryNodes();
  assert.throws(() => {
    ingestMemoryEvent(
      initialNodes,
      {
        subject: '   ',
        predicate: 'uses_storage_backend',
        object: 'ClickHouse',
        category: 'architecture_invariant',
      },
      ALL_MODULE_KEYS
    );
  }, /required/);
});

test('executeContextRotPurgeAndReanchor evicts distractor noise and rescues middle-trough facts', () => {
  const initialNodes = createInitialMemoryNodes();
  const threads = createInitialThreads();

  const beforeEval = evaluateSystemMetrics(initialNodes, threads, ALL_MODULE_KEYS);
  assert.ok(beforeEval.activeNoiseNodes > 0);
  assert.ok(beforeEval.highSalienceInMiddleTrough > 0);

  const purgeResult = executeContextRotPurgeAndReanchor(initialNodes);
  assert.ok(purgeResult.evictedNoiseCount >= 2);
  assert.ok(purgeResult.reanchoredCount >= 1);
  assert.ok(purgeResult.tokensReclaimed > 0);

  const afterEval = evaluateSystemMetrics(purgeResult.cleanedNodes, threads, ALL_MODULE_KEYS);
  assert.equal(afterEval.activeNoiseNodes, 0);
  assert.equal(afterEval.highSalienceInMiddleTrough, 0);
  assert.ok(afterEval.exactRecallPct > beforeEval.exactRecallPct);
  assert.ok(afterEval.contextRotIndex < beforeEval.contextRotIndex);
});

test('non-fungible verification ledger mints hash-chained blocks and detects tampering', () => {
  const { cleanedNodes } = executeContextRotPurgeAndReanchor(createInitialMemoryNodes());
  const threads = createInitialThreads();

  const b1 = mintVerificationBlock(
    null,
    cleanedNodes,
    threads,
    ALL_MODULE_KEYS,
    'RULER-1M + LoCoMo + Contradiction-Bench',
    '2026-11-03T15:25:00.000Z'
  );
  const b2 = mintVerificationBlock(
    b1,
    cleanedNodes,
    threads,
    ALL_MODULE_KEYS,
    'Parallel-CoW-Isolation-Probe',
    '2026-11-03T15:26:00.000Z'
  );

  assert.equal(b1.blockNumber, 1);
  assert.equal(b2.blockNumber, 2);
  assert.equal(b2.previousHash, b1.blockHash);
  assert.equal(b1.blockHash.length, 64);

  const integrity = verifyLedgerChainIntegrity([b1, b2]);
  assert.equal(integrity.valid, true);
  assert.equal(integrity.verifiedBlocks, 2);

  // Tamper with b1 hash and verify detection
  const tamperedB1 = { ...b1, blockHash: 'f'.repeat(64) };
  const brokenIntegrity = verifyLedgerChainIntegrity([tamperedB1, b2]);
  assert.equal(brokenIntegrity.valid, false);
  assert.equal(brokenIntegrity.brokenAtBlock, 2);
});

test('Genesis per-agent real-time memory pipeline filters noise below surprise threshold and invalidates contradicted blocks', () => {
  const agents = createInitialGenesisAgents();
  const prime = agents[0];

  // 1. Low-surprise stimulus should be filtered out by Titans Surprise Gate
  const afterNoise = executeGenesisAgentMemoryTick(prime, {
    label: 'Routine_Ping',
    content: '200 OK health ping',
    surprise: 0.12,
    salience: 0.15,
  });

  assert.equal(afterNoise.recentTraces[0].stage2SurpriseGate.decision, 'DROPPED_DISTRACTOR');
  assert.equal(
    afterNoise.liveMetrics.filteredNoiseEvents,
    prime.liveMetrics.filteredNoiseEvents + 1
  );

  // 2. High-surprise contradiction on Primary_Inference_Topology should invalidate old block blk-102
  const afterContradiction = executeGenesisAgentMemoryTick(afterNoise, {
    label: 'Primary_Inference_Topology',
    content: 'Switched KV fabric to Optical Interconnect v3',
    surprise: 0.94,
    salience: 0.96,
  });

  assert.equal(afterContradiction.recentTraces[0].stage2SurpriseGate.decision, 'PROMOTED_TO_FOCUS');
  assert.equal(afterContradiction.recentTraces[0].stage3BiTemporalResolution.supersededBlockId, 'blk-102');

  const superseded = afterContradiction.memoryBlocks.find((b) => b.id === 'blk-102');
  assert.ok(superseded);
  assert.equal(superseded.zone, 'paged_archival');

  // 3. Updating agent config in real time recalculates recall and rot metrics
  const legacyModeAgent = updateGenesisAgentConfig(afterContradiction, {
    bitemporalMode: 'append_only_legacy',
  });
  assert.ok(legacyModeAgent.liveMetrics.agentRecallAccuracyPct < afterContradiction.liveMetrics.agentRecallAccuracyPct);
  assert.ok(legacyModeAgent.liveMetrics.agentRotIndex > afterContradiction.liveMetrics.agentRotIndex);
});

