import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CapacityOffer,
  ContinuityError,
  MissionCheckpoint,
  canonicalJson,
  checkpointRequired,
  computeEffectKey,
  hmacSha256,
  isValidTransition,
  selectTakeoverCandidate,
  sha256,
  validateCheckpoint,
} from './missionContinuity.js';

function createMockCheckpoint(overrides: Partial<MissionCheckpoint> = {}): MissionCheckpoint {
  return {
    schema: 'genesis.mission-checkpoint/v1',
    missionId: 'mission_test_001',
    attemptId: 'attempt_001',
    leaseEpoch: 1,
    sequence: 1,
    phase: 'EXECUTING',
    goal: 'Restore estate connectivity',
    subgoals: [
      { id: 'sub_1', text: 'Verify trust pathway', status: 'DONE' },
      { id: 'sub_2', text: 'Establish fencing tokens', status: 'OPEN' },
    ],
    verifiedFacts: [
      { claim: 'Guardian pinned to da1536c7', source: 'git', digest: 'sha256:112233' },
    ],
    decisions: [
      { id: 'dec_1', decision: 'Target Oracle ARM / k3s', rationale: 'Cost & durability invariant' },
    ],
    constraints: ['Max latency <= 15s', 'Cost ceiling <= $200/mo'],
    attemptedActions: ['probe.k3s_health', 'check.fencing_lease'],
    failedEvidenceRefs: [],
    nextAction: 'issue.durable_pvc',
    branch: 'feat/idp-continuity',
    commit: 'da1536c711223344556677889900aabbccddeeff',
    commitVerified: true,
    capabilityScope: ['git.read', 'k3s.apply'],
    contextDigest: 'sha256:ctx_digest_abc123',
    createdAtMs: 1730974550000,
    ...overrides,
  };
}

function createMockOffer(overrides: Partial<CapacityOffer> = {}): CapacityOffer {
  const now = 1730974550000;
  return {
    workerId: 'worker_node_b_arm',
    adapter: 'oci-arm-k3s',
    executionHost: 'oracle-arm-node-02',
    failureDomain: 'oracle_cloud_fra_ad2',
    providers: ['oci_cloud'],
    capabilities: ['git.read', 'k3s.apply', 'sqlite.wal'],
    availability: 'AVAILABLE',
    quotaState: 'AVAILABLE',
    contextState: 'SUFFICIENT',
    concurrencyAvailable: 4,
    costBudgetRemaining: 150.0,
    verifiedSuccessRate: 0.992,
    p95LatencyMs: 120,
    authenticated: true,
    observedAtMs: now - 1000,
    ttlMs: 30000,
    ...overrides,
  };
}

test('1. Canonical JSON produces recursively sorted keys with no whitespace', () => {
  const input = {
    z: 1,
    b: [ { y: 2, a: 1 }, 3 ],
    a: 'test',
  };
  const expected = '{"a":"test","b":[{"a":1,"y":2},3],"z":1}';
  assert.equal(canonicalJson(input), expected);
});

test('2. SHA-256 and HMAC-SHA256 compute deterministic hex outputs', () => {
  const secret = 'super_secret_receipt_key_at_least_32_chars_long';
  const data = 'canonical_payload_string';
  const hash = sha256(data);
  const hmac = hmacSha256(secret, data);

  assert.equal(hash.length, 64);
  assert.equal(hmac.length, 64);
  assert.equal(sha256(data), hash);
  assert.equal(hmacSha256(secret, data), hmac);
});

test('3. Code mission checkpoint requires non-empty branch, full 40-char lowercase hex commit, and commitVerified', () => {
  // Valid code checkpoint
  const validChk = createMockCheckpoint();
  assert.doesNotThrow(() => validateCheckpoint(validChk, 'code'));

  // Missing branch
  assert.throws(
    () => validateCheckpoint(createMockCheckpoint({ branch: '' }), 'code'),
    (err: any) => err instanceof ContinuityError && err.code === 'INVALID_INPUT'
  );

  // Missing or short commit
  assert.throws(
    () => validateCheckpoint(createMockCheckpoint({ commit: 'da1536c' }), 'code'),
    (err: any) => err instanceof ContinuityError && err.code === 'INVALID_INPUT'
  );

  // Uppercase commit
  assert.throws(
    () => validateCheckpoint(createMockCheckpoint({ commit: 'DA1536C711223344556677889900AABBCCDDEEFF' }), 'code'),
    (err: any) => err instanceof ContinuityError && err.code === 'INVALID_INPUT'
  );

  // commitVerified is false
  assert.throws(
    () => validateCheckpoint(createMockCheckpoint({ commitVerified: false }), 'code'),
    (err: any) => err instanceof ContinuityError && err.code === 'INVALID_INPUT'
  );

  // Research or operations mission does not require branch/commit
  assert.doesNotThrow(() =>
    validateCheckpoint(createMockCheckpoint({ branch: null, commit: null, commitVerified: false }), 'research')
  );
  assert.doesNotThrow(() =>
    validateCheckpoint(createMockCheckpoint({ branch: null, commit: null, commitVerified: false }), 'operations')
  );
});

test('4. Secret-shaped values in checkpoints are refused with CHECKPOINT_CONTAINS_SECRET without leaking the secret', () => {
  const secretSamples = [
    'ghp_1234567890abcdefghijklmnopqrstuvwxyz',
    'github_pat_11AAAAAAA0123456789abcdefghijklmnopqrstuvwxyz',
    'AIzaSyD_fakeGoogleApiKeySample123456789',
    'sk-proj-fakeOpenAiKeySample123456789abcdef',
    '-----BEGIN RSA PRIVATE KEY-----\nMIIE...',
    'password=SuperSecretPassword123',
  ];

  for (const secretVal of secretSamples) {
    const taintedChk = createMockCheckpoint({
      constraints: ['standard constraint', secretVal],
    });

    try {
      validateCheckpoint(taintedChk, 'code');
      assert.fail('Expected secret validation to throw');
    } catch (err: any) {
      assert.ok(err instanceof ContinuityError);
      assert.equal(err.code, 'CHECKPOINT_CONTAINS_SECRET');
      // Assert the secret value is NEVER leaked in the error message!
      assert.equal(err.message.includes(secretVal), false, 'Error message must not leak secret string');
    }
  }
});

test('5. Checkpoint budget thresholds determine requirement accurately', () => {
  // Safe baseline: no effect pending, plenty of tokens/context, turns low, elapsed low, zero faults
  const safe = checkpointRequired({
    knownContextRemainingRatio: 0.85,
    knownTokenRemainingRatio: 0.9,
    turnIndex: 2,
    maxTurns: 20,
    elapsedMs: 5000,
    maxElapsedMs: 60000,
    providerFaultCount: 0,
    irreversibleEffectPending: false,
  });
  assert.equal(safe.required, false);
  assert.equal(safe.reasons.length, 0);

  // 1. Irreversible effect pending
  const effectPending = checkpointRequired({
    knownContextRemainingRatio: 0.85,
    knownTokenRemainingRatio: 0.9,
    turnIndex: 2,
    maxTurns: 20,
    elapsedMs: 5000,
    maxElapsedMs: 60000,
    providerFaultCount: 0,
    irreversibleEffectPending: true,
  });
  assert.equal(effectPending.required, true);
  assert.ok(effectPending.reasons.includes('IRREVERSIBLE_EFFECT_PENDING'));

  // 2. Known context ratio <= 0.30
  const lowContext = checkpointRequired({
    knownContextRemainingRatio: 0.28,
    knownTokenRemainingRatio: 0.8,
    turnIndex: 2,
    maxTurns: 20,
    elapsedMs: 5000,
    maxElapsedMs: 60000,
    providerFaultCount: 0,
    irreversibleEffectPending: false,
  });
  assert.equal(lowContext.required, true);
  assert.ok(lowContext.reasons.includes('LOW_CONTEXT_REMAINING'));

  // 3. Known token ratio <= 0.30
  const lowToken = checkpointRequired({
    knownContextRemainingRatio: 0.8,
    knownTokenRemainingRatio: 0.25,
    turnIndex: 2,
    maxTurns: 20,
    elapsedMs: 5000,
    maxElapsedMs: 60000,
    providerFaultCount: 0,
    irreversibleEffectPending: false,
  });
  assert.equal(lowToken.required, true);
  assert.ok(lowToken.reasons.includes('LOW_TOKEN_REMAINING'));

  // 4. Turn use >= 90%
  const highTurns = checkpointRequired({
    knownContextRemainingRatio: 0.8,
    knownTokenRemainingRatio: 0.8,
    turnIndex: 18,
    maxTurns: 20,
    elapsedMs: 5000,
    maxElapsedMs: 60000,
    providerFaultCount: 0,
    irreversibleEffectPending: false,
  });
  assert.equal(highTurns.required, true);
  assert.ok(highTurns.reasons.includes('HIGH_TURN_USAGE'));

  // 5. Elapsed use >= 80%
  const highElapsed = checkpointRequired({
    knownContextRemainingRatio: 0.8,
    knownTokenRemainingRatio: 0.8,
    turnIndex: 5,
    maxTurns: 20,
    elapsedMs: 49000,
    maxElapsedMs: 60000,
    providerFaultCount: 0,
    irreversibleEffectPending: false,
  });
  assert.equal(highElapsed.required, true);
  assert.ok(highElapsed.reasons.includes('HIGH_ELAPSED_USAGE'));

  // 6. Provider fault count >= 1
  const faulted = checkpointRequired({
    knownContextRemainingRatio: 0.8,
    knownTokenRemainingRatio: 0.8,
    turnIndex: 2,
    maxTurns: 20,
    elapsedMs: 5000,
    maxElapsedMs: 60000,
    providerFaultCount: 1,
    irreversibleEffectPending: false,
  });
  assert.equal(faulted.required, true);
  assert.ok(faulted.reasons.includes('PROVIDER_FAULT_OCCURRED'));
});

test('6. Unknown-context 12-turn fallback requires checkpointing at or above turn 12', () => {
  // Both ratios unknown, turn 11 -> not required
  const under12 = checkpointRequired({
    knownContextRemainingRatio: null,
    knownTokenRemainingRatio: null,
    turnIndex: 11,
    maxTurns: 50,
    elapsedMs: 5000,
    maxElapsedMs: 60000,
    providerFaultCount: 0,
    irreversibleEffectPending: false,
  });
  assert.equal(under12.required, false);

  // Both ratios unknown, turn 12 -> required!
  const at12 = checkpointRequired({
    knownContextRemainingRatio: null,
    knownTokenRemainingRatio: null,
    turnIndex: 12,
    maxTurns: 50,
    elapsedMs: 5000,
    maxElapsedMs: 60000,
    providerFaultCount: 0,
    irreversibleEffectPending: false,
  });
  assert.equal(at12.required, true);
  assert.ok(at12.reasons.includes('UNKNOWN_RATIOS_TURN_THRESHOLD_EXCEEDED'));
});

test('7. Capacity candidate hard filters reject ineligible workers', () => {
  const now = 1730974550000;
  const failedAttempt = {
    workerId: 'worker_primary_failed',
    failureDomain: 'domain_failed_us_east',
    provider: 'provider_alpha',
  };
  const requiredCaps = ['git.read', 'k3s.apply'];
  const remainingCost = 50.0;

  // Unauthenticated
  const r1 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: requiredCaps,
    remainingCost,
    offers: [createMockOffer({ workerId: 'w1', authenticated: false })],
    nowMs: now,
  });
  assert.equal(r1.selected, null);
  assert.equal(r1.rejected[0].reason, 'UNAUTHENTICATED');

  // Stale offer (observed + ttl < now)
  const r2 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: requiredCaps,
    remainingCost,
    offers: [createMockOffer({ workerId: 'w2', observedAtMs: now - 40000, ttlMs: 30000 })],
    nowMs: now,
  });
  assert.equal(r2.selected, null);
  assert.equal(r2.rejected[0].reason, 'STALE_OFFER');

  // Future offer (> now + 5000)
  const r3 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: requiredCaps,
    remainingCost,
    offers: [createMockOffer({ workerId: 'w3', observedAtMs: now + 6000 })],
    nowMs: now,
  });
  assert.equal(r3.selected, null);
  assert.equal(r3.rejected[0].reason, 'FUTURE_OFFER');

  // Availability not AVAILABLE
  const r4 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: requiredCaps,
    remainingCost,
    offers: [createMockOffer({ workerId: 'w4', availability: 'DEGRADED' })],
    nowMs: now,
  });
  assert.equal(r4.selected, null);
  assert.equal(r4.rejected[0].reason, 'UNAVAILABLE_DEGRADED');

  // Quota not AVAILABLE
  const r5 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: requiredCaps,
    remainingCost,
    offers: [createMockOffer({ workerId: 'w5', quotaState: 'EXHAUSTED' })],
    nowMs: now,
  });
  assert.equal(r5.selected, null);
  assert.equal(r5.rejected[0].reason, 'QUOTA_EXHAUSTED');

  // Context not SUFFICIENT
  const r6 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: requiredCaps,
    remainingCost,
    offers: [createMockOffer({ workerId: 'w6', contextState: 'LOW' })],
    nowMs: now,
  });
  assert.equal(r6.selected, null);
  assert.equal(r6.rejected[0].reason, 'CONTEXT_LOW');

  // Concurrency <= 0
  const r7 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: requiredCaps,
    remainingCost,
    offers: [createMockOffer({ workerId: 'w7', concurrencyAvailable: 0 })],
    nowMs: now,
  });
  assert.equal(r7.selected, null);
  assert.equal(r7.rejected[0].reason, 'CONCURRENCY_EXHAUSTED');

  // Cost budget insufficient
  const r8 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: requiredCaps,
    remainingCost: 100.0,
    offers: [createMockOffer({ workerId: 'w8', costBudgetRemaining: 40.0 })],
    nowMs: now,
  });
  assert.equal(r8.selected, null);
  assert.equal(r8.rejected[0].reason, 'COST_INSUFFICIENT');

  // Missing required capability
  const r9 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: ['git.read', 'k3s.apply', 'secret.kms_sign'],
    remainingCost,
    offers: [createMockOffer({ workerId: 'w9', capabilities: ['git.read', 'k3s.apply'] })],
    nowMs: now,
  });
  assert.equal(r9.selected, null);
  assert.equal(r9.rejected[0].reason, 'MISSING_REQUIRED_CAPABILITIES');

  // Same workerId
  const r10 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: requiredCaps,
    remainingCost,
    offers: [createMockOffer({ workerId: 'worker_primary_failed' })],
    nowMs: now,
  });
  assert.equal(r10.selected, null);
  assert.equal(r10.rejected[0].reason, 'SAME_WORKER');

  // Same failure domain
  const r11 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: requiredCaps,
    remainingCost,
    offers: [createMockOffer({ workerId: 'w11', failureDomain: 'domain_failed_us_east' })],
    nowMs: now,
  });
  assert.equal(r11.selected, null);
  assert.equal(r11.rejected[0].reason, 'SAME_FAILURE_DOMAIN');

  // Missing verified metrics
  const r12 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: requiredCaps,
    remainingCost,
    offers: [createMockOffer({ workerId: 'w12', verifiedSuccessRate: null })],
    nowMs: now,
  });
  assert.equal(r12.selected, null);
  assert.equal(r12.rejected[0].reason, 'MISSING_VERIFIED_METRICS');
});

test('8. Deterministic capacity ranking: provider diversity, success rate, latency, cost, and lexicographic tie-breaking', () => {
  const now = 1730974550000;
  const failedAttempt = {
    workerId: 'worker_failed',
    failureDomain: 'zone_a',
    provider: 'provider_alpha',
  };

  const offerSameProvider = createMockOffer({
    workerId: 'worker_same_prov',
    failureDomain: 'zone_b',
    providers: ['provider_alpha'], // same provider as failed attempt
    verifiedSuccessRate: 0.999,
    p95LatencyMs: 50,
    costBudgetRemaining: 100,
  });

  const offerDiffProvider = createMockOffer({
    workerId: 'worker_diff_prov',
    failureDomain: 'zone_c',
    providers: ['provider_beta'], // different provider (preferred!)
    verifiedSuccessRate: 0.95,
    p95LatencyMs: 150,
    costBudgetRemaining: 100,
  });

  // Test 1: Different provider wins over higher success rate
  const result1 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: ['git.read'],
    remainingCost: 50,
    offers: [offerSameProvider, offerDiffProvider],
    nowMs: now,
  });
  assert.equal(result1.selected?.workerId, 'worker_diff_prov');

  // Test 2: Higher verified success rate wins among distinct providers
  const offerHighSuccess = createMockOffer({
    workerId: 'worker_high_success',
    failureDomain: 'zone_b',
    providers: ['provider_gamma'],
    verifiedSuccessRate: 0.985,
    p95LatencyMs: 100,
    costBudgetRemaining: 100,
  });
  const offerLowerSuccess = createMockOffer({
    workerId: 'worker_low_success',
    failureDomain: 'zone_d',
    providers: ['provider_gamma'],
    verifiedSuccessRate: 0.92,
    p95LatencyMs: 50,
    costBudgetRemaining: 100,
  });
  const result2 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: ['git.read'],
    remainingCost: 50,
    offers: [offerLowerSuccess, offerHighSuccess],
    nowMs: now,
  });
  assert.equal(result2.selected?.workerId, 'worker_high_success');

  // Test 3: Lower p95 latency wins when success rates match
  const offerFaster = createMockOffer({
    workerId: 'worker_faster',
    failureDomain: 'zone_b',
    providers: ['provider_delta'],
    verifiedSuccessRate: 0.98,
    p95LatencyMs: 80,
    costBudgetRemaining: 100,
  });
  const offerSlower = createMockOffer({
    workerId: 'worker_slower',
    failureDomain: 'zone_e',
    providers: ['provider_delta'],
    verifiedSuccessRate: 0.98,
    p95LatencyMs: 160,
    costBudgetRemaining: 100,
  });
  const result3 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: ['git.read'],
    remainingCost: 50,
    offers: [offerSlower, offerFaster],
    nowMs: now,
  });
  assert.equal(result3.selected?.workerId, 'worker_faster');

  // Test 4: Lower cost wins when latency and success rates match
  const offerCheaper = createMockOffer({
    workerId: 'worker_cheaper',
    failureDomain: 'zone_f',
    providers: ['provider_epsilon'],
    verifiedSuccessRate: 0.98,
    p95LatencyMs: 80,
    costBudgetRemaining: 60,
  });
  const offerCostlier = createMockOffer({
    workerId: 'worker_costlier',
    failureDomain: 'zone_g',
    providers: ['provider_epsilon'],
    verifiedSuccessRate: 0.98,
    p95LatencyMs: 80,
    costBudgetRemaining: 120,
  });
  const result4 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: ['git.read'],
    remainingCost: 50,
    offers: [offerCostlier, offerCheaper],
    nowMs: now,
  });
  assert.equal(result4.selected?.workerId, 'worker_cheaper');

  // Test 5: Lexicographic worker ID breaks identical ties
  const offerAlpha = createMockOffer({
    workerId: 'worker_aaa',
    failureDomain: 'zone_h',
    providers: ['provider_zeta'],
    verifiedSuccessRate: 0.98,
    p95LatencyMs: 80,
    costBudgetRemaining: 60,
  });
  const offerBeta = createMockOffer({
    workerId: 'worker_bbb',
    failureDomain: 'zone_i',
    providers: ['provider_zeta'],
    verifiedSuccessRate: 0.98,
    p95LatencyMs: 80,
    costBudgetRemaining: 60,
  });
  const result5 = selectTakeoverCandidate({
    failedAttempt,
    requiredCapabilities: ['git.read'],
    remainingCost: 50,
    offers: [offerBeta, offerAlpha],
    nowMs: now,
  });
  assert.equal(result5.selected?.workerId, 'worker_aaa');
});

test('9. State machine transitions validate allowed and reject illegal transitions', () => {
  // Valid transitions
  assert.equal(isValidTransition('QUEUED', 'CLAIMED'), true);
  assert.equal(isValidTransition('CLAIMED', 'EXECUTING'), true);
  assert.equal(isValidTransition('EXECUTING', 'CHECKPOINTING'), true);
  assert.equal(isValidTransition('EXECUTING', 'HANDOVER_PENDING'), true);
  assert.equal(isValidTransition('EXECUTING', 'VERIFYING'), true);
  assert.equal(isValidTransition('CHECKPOINTING', 'EXECUTING'), true);
  assert.equal(isValidTransition('HANDOVER_PENDING', 'TAKEN_OVER'), true);
  assert.equal(isValidTransition('TAKEN_OVER', 'EXECUTING'), true);
  assert.equal(isValidTransition('VERIFYING', 'OPERATING'), true);
  assert.equal(isValidTransition('REPAIRING', 'EXECUTING'), true);

  // Invalid transitions
  assert.equal(isValidTransition('QUEUED', 'EXECUTING'), false);
  assert.equal(isValidTransition('OPERATING', 'EXECUTING'), false);
  assert.equal(isValidTransition('BLOCKED', 'CLAIMED'), false);
  assert.equal(isValidTransition('HANDOVER_PENDING', 'EXECUTING'), false);
  assert.equal(isValidTransition('CLAIMED', 'OPERATING'), false);
});

test('10. Effect key computation is deterministic and strictly formatted', () => {
  const missionId = 'mission_100';
  const stepId = 'step_42';
  const action = 'k3s.apply_manifest';
  const argsDigest = 'sha256:d991bce091a1';

  const key1 = computeEffectKey(missionId, stepId, action, argsDigest);
  const key2 = computeEffectKey(missionId, stepId, action, argsDigest);
  assert.equal(key1, key2);
  assert.equal(key1.length, 64);

  // Tampered arguments change the key
  const keyTampered = computeEffectKey(missionId, stepId, action, 'sha256:tampered');
  assert.notEqual(key1, keyTampered);
});
