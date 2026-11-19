import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import {
  CapacityOffer,
  ContinuityError,
  MissionCheckpoint,
  MissionContinuityKernel,
  computeEffectKey,
} from './missionContinuity.js';

const VALID_RECEIPT_KEY = 'estate_receipt_hmac_signing_key_secure_32_characters_minimum!';

function createTestOffer(workerId: string, overrides: Partial<CapacityOffer> = {}): CapacityOffer {
  return {
    workerId,
    adapter: 'oci-arm-k3s',
    executionHost: 'oracle-arm-01',
    failureDomain: 'oracle_fra_ad1',
    providers: ['oci_cloud'],
    capabilities: ['git.read', 'k3s.apply', 'sqlite.wal'],
    availability: 'AVAILABLE',
    quotaState: 'AVAILABLE',
    contextState: 'SUFFICIENT',
    concurrencyAvailable: 5,
    costBudgetRemaining: 200.0,
    verifiedSuccessRate: 0.995,
    p95LatencyMs: 110,
    authenticated: true,
    observedAtMs: 1000000,
    ttlMs: 60000,
    ...overrides,
  };
}

function createTestCheckpoint(
  missionId: string,
  attemptId: string,
  leaseEpoch: number,
  sequence: number,
  overrides: Partial<MissionCheckpoint> = {}
): MissionCheckpoint {
  return {
    schema: 'genesis.mission-checkpoint/v1',
    missionId,
    attemptId,
    leaseEpoch,
    sequence,
    phase: 'EXECUTING',
    goal: 'Test mission continuity kernel',
    subgoals: [{ id: 'sub_1', text: 'Initialize SQLite', status: 'DONE' }],
    verifiedFacts: [{ claim: 'Schema initialized', source: 'db', digest: 'sha256:001122' }],
    decisions: [{ id: 'dec_1', decision: 'WAL mode', rationale: 'Concurrent concurrency' }],
    constraints: ['Zero manual founder CLI chores'],
    attemptedActions: ['init.schema'],
    failedEvidenceRefs: [],
    nextAction: 'verify.fencing',
    branch: 'feat/continuity-kernel',
    commit: '0123456789abcdef0123456789abcdef01234567',
    commitVerified: true,
    capabilityScope: ['git.read', 'k3s.apply'],
    contextDigest: 'sha256:context_digest_sample_001',
    createdAtMs: 1000000,
    ...overrides,
  };
}

test('Construction fails WEAK_RECEIPT_KEY when receipt key is under 32 characters', () => {
  assert.throws(
    () =>
      new MissionContinuityKernel({
        dbPath: ':memory:',
        receiptKey: 'short_key_under_32_chars',
      }),
    (err: any) => err instanceof ContinuityError && err.code === 'WEAK_RECEIPT_KEY'
  );
});

test('1. Claim idempotency for identical input returns existing record', () => {
  let currentTime = 1000000;
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
    now: () => currentTime,
  });

  const offer = createTestOffer('worker_01', { observedAtMs: currentTime });
  const initialChk = createTestCheckpoint('mission_alpha', 'attempt_01', 1, 1);

  const claim1 = kernel.claimMission({
    missionId: 'mission_alpha',
    kind: 'code',
    riskClass: 'P0',
    goal: 'Idempotency test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 150.0,
    initialCheckpoint: initialChk,
  });

  assert.equal(claim1.phase, 'EXECUTING');
  assert.equal(claim1.leaseEpoch, 1);

  // Exact duplicate call with identical parameters
  const claim2 = kernel.claimMission({
    missionId: 'mission_alpha',
    kind: 'code',
    riskClass: 'P0',
    goal: 'Idempotency test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 150.0,
    initialCheckpoint: initialChk,
  });

  assert.deepEqual(claim1, claim2);
  kernel.close();
});

test('2. Live duplicate claim refusal fails with LEASE_HELD', () => {
  let currentTime = 1000000;
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
    now: () => currentTime,
  });

  const offer1 = createTestOffer('worker_01', { observedAtMs: currentTime });
  const initialChk = createTestCheckpoint('mission_beta', 'attempt_01', 1, 1);

  kernel.claimMission({
    missionId: 'mission_beta',
    kind: 'code',
    riskClass: 'P1',
    goal: 'Duplicate claim test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer: offer1,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 100.0,
    initialCheckpoint: initialChk,
  });

  // Attempt to claim with another worker
  const offer2 = createTestOffer('worker_02', { observedAtMs: currentTime });
  assert.throws(
    () =>
      kernel.claimMission({
        missionId: 'mission_beta',
        kind: 'code',
        riskClass: 'P1',
        goal: 'Duplicate claim test',
        attemptId: 'attempt_02',
        workerId: 'worker_02',
        offer: offer2,
        requiredCapabilities: ['git.read'],
        costBudgetRemaining: 100.0,
        initialCheckpoint: createTestCheckpoint('mission_beta', 'attempt_02', 1, 1),
      }),
    (err: any) => err instanceof ContinuityError && err.code === 'LEASE_HELD'
  );

  kernel.close();
});

test('3. Complete checkpoint persistence and snapshot retrieval', () => {
  let currentTime = 1000000;
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
    now: () => currentTime,
  });

  const offer = createTestOffer('worker_01', { observedAtMs: currentTime });
  kernel.claimMission({
    missionId: 'mission_gamma',
    kind: 'code',
    riskClass: 'P1',
    goal: 'Checkpoint persistence test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 100.0,
    initialCheckpoint: createTestCheckpoint('mission_gamma', 'attempt_01', 1, 1),
  });

  currentTime += 5000;
  const chk2 = createTestCheckpoint('mission_gamma', 'attempt_01', 1, 2, {
    nextAction: 'apply.k3s_pvc',
  });

  const savedRecord = kernel.checkpoint({
    missionId: 'mission_gamma',
    attemptId: 'attempt_01',
    leaseEpoch: 1,
    checkpoint: chk2,
  });

  assert.equal(savedRecord.sequence, 2);
  assert.equal(savedRecord.checkpoint.nextAction, 'apply.k3s_pvc');
  assert.equal(savedRecord.digest.length, 64);
  assert.equal(savedRecord.hmac.length, 64);

  const snapshot = kernel.snapshot();
  assert.equal(snapshot.missions.length, 1);
  assert.equal(snapshot.latestCheckpointByMission['mission_gamma'].sequence, 2);
  assert.ok(snapshot.events.length >= 3);

  kernel.close();
});

test('4. Checkpoint HMAC tamper rejection fails with INTEGRITY_ERROR', () => {
  const dbPath = `/tmp/test_integrity_${Date.now()}.db`;
  const kernel = new MissionContinuityKernel({
    dbPath,
    receiptKey: VALID_RECEIPT_KEY,
  });

  const offer = createTestOffer('worker_01', { observedAtMs: Date.now() });
  kernel.claimMission({
    missionId: 'mission_tamper',
    kind: 'code',
    riskClass: 'P0',
    goal: 'Tamper test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 100.0,
    initialCheckpoint: createTestCheckpoint('mission_tamper', 'attempt_01', 1, 1),
  });
  kernel.close();

  // Tamper directly with the SQLite database row HMAC
  const rawDb = new DatabaseSync(dbPath);
  rawDb.exec("UPDATE continuity_checkpoints SET hmac = 'tampered_evil_hmac_1234567890abcdef'");
  rawDb.close();

  // Re-open with kernel
  const reopenedKernel = new MissionContinuityKernel({
    dbPath,
    receiptKey: VALID_RECEIPT_KEY,
  });

  assert.throws(
    () => reopenedKernel.snapshot(),
    (err: any) => err instanceof ContinuityError && err.code === 'INTEGRITY_ERROR'
  );

  reopenedKernel.close();
});

test('5. Missing branch or commit SHA for code mission refusal', () => {
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
  });

  const offer = createTestOffer('worker_01', { observedAtMs: Date.now() });
  const badChk = createTestCheckpoint('mission_code_bad', 'attempt_01', 1, 1, {
    branch: '', // Empty branch
  });

  assert.throws(
    () =>
      kernel.claimMission({
        missionId: 'mission_code_bad',
        kind: 'code',
        riskClass: 'P0',
        goal: 'Code validation test',
        attemptId: 'attempt_01',
        workerId: 'worker_01',
        offer,
        requiredCapabilities: ['git.read'],
        costBudgetRemaining: 100.0,
        initialCheckpoint: badChk,
      }),
    (err: any) => err instanceof ContinuityError && err.code === 'INVALID_INPUT'
  );

  kernel.close();
});

test('6. Secret-shaped checkpoint value refusal with CHECKPOINT_CONTAINS_SECRET', () => {
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
  });

  const offer = createTestOffer('worker_01', { observedAtMs: Date.now() });
  const secretChk = createTestCheckpoint('mission_secret', 'attempt_01', 1, 1, {
    decisions: [{ id: 'd1', decision: 'Save token', rationale: 'ghp_secretTokenHere1234567890' }],
  });

  assert.throws(
    () =>
      kernel.claimMission({
        missionId: 'mission_secret',
        kind: 'code',
        riskClass: 'P0',
        goal: 'Secret test',
        attemptId: 'attempt_01',
        workerId: 'worker_01',
        offer,
        requiredCapabilities: ['git.read'],
        costBudgetRemaining: 100.0,
        initialCheckpoint: secretChk,
      }),
    (err: any) => err instanceof ContinuityError && err.code === 'CHECKPOINT_CONTAINS_SECRET'
  );

  kernel.close();
});

test('7. Heartbeat ordering and stale epoch rejection', () => {
  let currentTime = 1000000;
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
    now: () => currentTime,
  });

  const offer = createTestOffer('worker_01', { observedAtMs: currentTime, ttlMs: 45000 });
  kernel.claimMission({
    missionId: 'mission_hb',
    kind: 'code',
    riskClass: 'P1',
    goal: 'Heartbeat test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 100.0,
    initialCheckpoint: createTestCheckpoint('mission_hb', 'attempt_01', 1, 1),
  });

  // Heartbeat sequence 1 accepted
  currentTime += 5000;
  const hb1 = kernel.heartbeat({
    missionId: 'mission_hb',
    attemptId: 'attempt_01',
    leaseEpoch: 1,
    sequence: 1,
    phase: 'EXECUTING',
    checkpointAgeMs: 5000,
    lastActionId: 'act_01',
    availability: 'AVAILABLE',
    progressDigest: 'sha256:progress_01',
  });
  assert.equal(hb1.accepted, true);

  // Duplicate sequence 1 rejected
  const hbDuplicate = kernel.heartbeat({
    missionId: 'mission_hb',
    attemptId: 'attempt_01',
    leaseEpoch: 1,
    sequence: 1,
    phase: 'EXECUTING',
    checkpointAgeMs: 6000,
    lastActionId: 'act_01',
    availability: 'AVAILABLE',
    progressDigest: 'sha256:progress_01',
  });
  assert.equal(hbDuplicate.accepted, false);
  assert.equal(hbDuplicate.reason, 'SEQUENCE_NOT_INCREASING');

  // Lower sequence 0 rejected
  const hbLower = kernel.heartbeat({
    missionId: 'mission_hb',
    attemptId: 'attempt_01',
    leaseEpoch: 1,
    sequence: 0,
    phase: 'EXECUTING',
    checkpointAgeMs: 7000,
    lastActionId: 'act_01',
    availability: 'AVAILABLE',
    progressDigest: 'sha256:progress_01',
  });
  assert.equal(hbLower.accepted, false);

  // Stale epoch rejected
  const hbStaleEpoch = kernel.heartbeat({
    missionId: 'mission_hb',
    attemptId: 'attempt_01',
    leaseEpoch: 99,
    sequence: 2,
    phase: 'EXECUTING',
    checkpointAgeMs: 8000,
    lastActionId: 'act_02',
    availability: 'AVAILABLE',
    progressDigest: 'sha256:progress_02',
  });
  assert.equal(hbStaleEpoch.accepted, false);
  assert.equal(hbStaleEpoch.reason, 'WRONG_LEASE_EPOCH');

  kernel.close();
});

test('13. Takeover increments one epoch, stores new attempt and resets handover', () => {
  let currentTime = 1000000;
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
    now: () => currentTime,
  });

  const offer1 = createTestOffer('worker_01', {
    failureDomain: 'zone_a',
    providers: ['provider_1'],
    observedAtMs: currentTime,
  });

  kernel.claimMission({
    missionId: 'mission_takeover',
    kind: 'code',
    riskClass: 'P0',
    goal: 'Takeover test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer: offer1,
    requiredCapabilities: ['git.read', 'k3s.apply'],
    costBudgetRemaining: 100.0,
    initialCheckpoint: createTestCheckpoint('mission_takeover', 'attempt_01', 1, 1),
  });

  // Begin handover
  currentTime += 10000;
  const handedOver = kernel.beginHandover({
    missionId: 'mission_takeover',
    attemptId: 'attempt_01',
    leaseEpoch: 1,
    failureClass: 'EXHAUSTED',
    evidenceRef: 'token_limit_exceeded_context_98_percent',
  });
  assert.equal(handedOver.phase, 'HANDOVER_PENDING');
  assert.equal(handedOver.failureClass, 'EXHAUSTED');

  // Candidate replacement worker offer (different failure domain, different provider)
  const offer2 = createTestOffer('worker_02', {
    failureDomain: 'zone_b',
    providers: ['provider_2'],
    observedAtMs: currentTime,
  });

  currentTime += 2000;
  const takeover = kernel.claimTakeover({
    missionId: 'mission_takeover',
    expectedLeaseEpoch: 1,
    newAttemptId: 'attempt_02',
    newWorkerId: 'worker_02',
    offer: offer2,
  });

  assert.equal(takeover.mission.phase, 'TAKEN_OVER');
  assert.equal(takeover.mission.leaseEpoch, 2); // Exactly 1 higher!
  assert.equal(takeover.mission.attemptId, 'attempt_02');
  assert.equal(takeover.mission.workerId, 'worker_02');
  assert.equal(takeover.mustCheckpointBeforeEffect, true);
  assert.equal(takeover.resumeFrom.sequence, 1);

  // Idempotent takeover replay returns identical result
  const replay = kernel.claimTakeover({
    missionId: 'mission_takeover',
    expectedLeaseEpoch: 1,
    newAttemptId: 'attempt_02',
    newWorkerId: 'worker_02',
    offer: offer2,
  });
  assert.equal(replay.mission.leaseEpoch, 2);

  kernel.close();
});

test('14. Stale worker effect rejection fails with STALE_FENCE', () => {
  let currentTime = 1000000;
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
    now: () => currentTime,
  });

  const offer1 = createTestOffer('worker_01', {
    failureDomain: 'zone_a',
    providers: ['provider_1'],
    observedAtMs: currentTime,
  });

  kernel.claimMission({
    missionId: 'mission_stale_eff',
    kind: 'code',
    riskClass: 'P0',
    goal: 'Stale effect test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer: offer1,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 100.0,
    initialCheckpoint: createTestCheckpoint('mission_stale_eff', 'attempt_01', 1, 1),
  });

  // Handover and takeover to epoch 2
  kernel.beginHandover({
    missionId: 'mission_stale_eff',
    attemptId: 'attempt_01',
    leaseEpoch: 1,
    failureClass: 'DISCONNECTED',
    evidenceRef: 'heartbeat_timeout',
  });

  const offer2 = createTestOffer('worker_02', {
    failureDomain: 'zone_b',
    providers: ['provider_2'],
    observedAtMs: currentTime,
  });
  kernel.claimTakeover({
    missionId: 'mission_stale_eff',
    expectedLeaseEpoch: 1,
    newAttemptId: 'attempt_02',
    newWorkerId: 'worker_02',
    offer: offer2,
  });

  // Stale worker_01 from epoch 1 attempts to authorize effect
  const effectKey = computeEffectKey('mission_stale_eff', 'step_1', 'k3s.apply', 'sha256:d1');
  assert.throws(
    () =>
      kernel.authorizeEffect({
        missionId: 'mission_stale_eff',
        attemptId: 'attempt_01',
        leaseEpoch: 1, // STALE!
        stepId: 'step_1',
        action: 'k3s.apply',
        argsDigest: 'sha256:d1',
        effectKey,
      }),
    (err: any) => err instanceof ContinuityError && err.code === 'STALE_FENCE'
  );

  kernel.close();
});

test('15. Duplicate effect completion is idempotent', () => {
  let currentTime = 1000000;
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
    now: () => currentTime,
  });

  const offer = createTestOffer('worker_01', { observedAtMs: currentTime });
  kernel.claimMission({
    missionId: 'mission_eff_idem',
    kind: 'code',
    riskClass: 'P0',
    goal: 'Effect idempotency test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 100.0,
    initialCheckpoint: createTestCheckpoint('mission_eff_idem', 'attempt_01', 1, 1),
  });

  const effectKey = computeEffectKey('mission_eff_idem', 'step_1', 'k3s.apply', 'sha256:d1');
  const permit = kernel.authorizeEffect({
    missionId: 'mission_eff_idem',
    attemptId: 'attempt_01',
    leaseEpoch: 1,
    stepId: 'step_1',
    action: 'k3s.apply',
    argsDigest: 'sha256:d1',
    effectKey,
  });

  const receipt = { status: 'applied', manifestSha: 'sha256:m112233' };

  // First completion
  const res1 = kernel.completeEffect({ permit, receipt });
  assert.equal(res1.duplicate, false);
  assert.deepEqual(res1.receipt, receipt);

  // Duplicate completion
  const res2 = kernel.completeEffect({ permit, receipt });
  assert.equal(res2.duplicate, true);
  assert.deepEqual(res2.receipt, receipt);

  kernel.close();
});

test('16. Restart reopens estate.db and resumes exact checkpoint and state', () => {
  const dbPath = `/tmp/test_restart_${Date.now()}.db`;
  const kernel1 = new MissionContinuityKernel({
    dbPath,
    receiptKey: VALID_RECEIPT_KEY,
  });

  const offer = createTestOffer('worker_01', { observedAtMs: Date.now() });
  kernel1.claimMission({
    missionId: 'mission_restart',
    kind: 'code',
    riskClass: 'P1',
    goal: 'Restart durability test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 120.0,
    initialCheckpoint: createTestCheckpoint('mission_restart', 'attempt_01', 1, 1),
  });

  const chk2 = createTestCheckpoint('mission_restart', 'attempt_01', 1, 2, {
    nextAction: 'deploy.cloud_service',
  });
  kernel1.checkpoint({
    missionId: 'mission_restart',
    attemptId: 'attempt_01',
    leaseEpoch: 1,
    checkpoint: chk2,
  });

  kernel1.close();

  // Reopen kernel with fresh instance on same DB file
  const kernel2 = new MissionContinuityKernel({
    dbPath,
    receiptKey: VALID_RECEIPT_KEY,
  });

  const snapshot = kernel2.snapshot();
  assert.equal(snapshot.missions.length, 1);
  const m = snapshot.missions[0];
  assert.equal(m.missionId, 'mission_restart');
  assert.equal(m.checkpointSequence, 2);

  const resumeCheckpoint = snapshot.latestCheckpointByMission['mission_restart'];
  assert.equal(resumeCheckpoint.sequence, 2);
  assert.equal(resumeCheckpoint.checkpoint.nextAction, 'deploy.cloud_service');

  kernel2.close();
});

test('17. Invalid state transitions are rejected with INVALID_TRANSITION', () => {
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
  });

  const offer = createTestOffer('worker_01', { observedAtMs: Date.now() });
  kernel.claimMission({
    missionId: 'mission_trans',
    kind: 'code',
    riskClass: 'P2',
    goal: 'Transition test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 100.0,
    initialCheckpoint: createTestCheckpoint('mission_trans', 'attempt_01', 1, 1),
  });

  // Finish to OPERATING directly from EXECUTING is invalid (EXECUTING can only go to CHECKPOINTING, HANDOVER_PENDING, VERIFYING, BLOCKED)
  assert.throws(
    () =>
      kernel.finishMission({
        missionId: 'mission_trans',
        attemptId: 'attempt_01',
        leaseEpoch: 1,
        phase: 'OPERATING',
        evidenceRef: 'skip_verification',
      }),
    (err: any) => err instanceof ContinuityError && err.code === 'INVALID_TRANSITION'
  );

  // Transition EXECUTING -> VERIFYING is valid
  const verifying = kernel.finishMission({
    missionId: 'mission_trans',
    attemptId: 'attempt_01',
    leaseEpoch: 1,
    phase: 'VERIFYING',
    evidenceRef: 'held_out_trials_passed',
  });
  assert.equal(verifying.phase, 'VERIFYING');

  // Transition VERIFYING -> OPERATING is valid
  const operating = kernel.finishMission({
    missionId: 'mission_trans',
    attemptId: 'attempt_01',
    leaseEpoch: 1,
    phase: 'OPERATING',
    evidenceRef: 'ed25519_certifier_signature_verified',
  });
  assert.equal(operating.phase, 'OPERATING');

  // Attempting to transition out of OPERATING (terminal operating state) fails
  assert.throws(
    () =>
      kernel.finishMission({
        missionId: 'mission_trans',
        attemptId: 'attempt_01',
        leaseEpoch: 1,
        phase: 'REPAIRING',
        evidenceRef: 'invalid_rollback',
      }),
    (err: any) => err instanceof ContinuityError && err.code === 'INVALID_TRANSITION'
  );

  kernel.close();
});

test('18. No eligible worker produces recovery pending without effect or founder escalation', () => {
  let currentTime = 1000000;
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
    now: () => currentTime,
  });

  const offer = createTestOffer('worker_01', { observedAtMs: currentTime });
  kernel.claimMission({
    missionId: 'mission_rec_pending',
    kind: 'code',
    riskClass: 'P0',
    goal: 'Recovery pending test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 100.0,
    initialCheckpoint: createTestCheckpoint('mission_rec_pending', 'attempt_01', 1, 1),
  });

  kernel.beginHandover({
    missionId: 'mission_rec_pending',
    attemptId: 'attempt_01',
    leaseEpoch: 1,
    failureClass: 'HOST_LOST',
    evidenceRef: 'node_unreachable',
  });

  // Mark recovery pending
  const recPending = kernel.markRecoveryPending({
    missionId: 'mission_rec_pending',
    expectedLeaseEpoch: 1,
    reason: 'Cluster capacity zero: all standby nodes unauthenticated or stale',
  });

  assert.equal(recPending.mission.recoveryPending, true);
  assert.equal(recPending.selected, null);
  assert.equal(recPending.mission.leaseEpoch, 1); // Epoch unchanged!

  kernel.close();
});

test('19. Append-only event hash chain tamper detection fails with INTEGRITY_ERROR', () => {
  const dbPath = `/tmp/test_hashchain_${Date.now()}.db`;
  const kernel = new MissionContinuityKernel({
    dbPath,
    receiptKey: VALID_RECEIPT_KEY,
  });

  const offer = createTestOffer('worker_01', { observedAtMs: Date.now() });
  kernel.claimMission({
    missionId: 'mission_chain',
    kind: 'code',
    riskClass: 'P0',
    goal: 'Hash chain test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 100.0,
    initialCheckpoint: createTestCheckpoint('mission_chain', 'attempt_01', 1, 1),
  });

  // Snapshot before tampering works cleanly
  const snap1 = kernel.snapshot();
  assert.ok(snap1.events.length >= 2);
  kernel.close();

  // Tamper directly with the event hash in SQLite
  const rawDb = new DatabaseSync(dbPath);
  rawDb.exec("UPDATE continuity_events SET event_hash = 'tampered_hash_0000000000000000' WHERE event_id = 1");
  rawDb.close();

  const reopened = new MissionContinuityKernel({
    dbPath,
    receiptKey: VALID_RECEIPT_KEY,
  });

  assert.throws(
    () => reopened.snapshot(),
    (err: any) => err instanceof ContinuityError && err.code === 'INTEGRITY_ERROR'
  );

  reopened.close();
});

test('20. No secret appears in logs, errors or snapshot JSON', () => {
  const secretKey = 'ghp_SUPER_SECRET_PAT_TOKEN_1234567890';
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
  });

  const offer = createTestOffer('worker_01', { observedAtMs: Date.now() });
  const taintedChk = createTestCheckpoint('mission_leak_test', 'attempt_01', 1, 1, {
    constraints: [secretKey],
  });

  let errorCaught: ContinuityError | null = null;
  try {
    kernel.claimMission({
      missionId: 'mission_leak_test',
      kind: 'code',
      riskClass: 'P0',
      goal: 'Secret leak test',
      attemptId: 'attempt_01',
      workerId: 'worker_01',
      offer,
      requiredCapabilities: ['git.read'],
      costBudgetRemaining: 100.0,
      initialCheckpoint: taintedChk,
    });
  } catch (err: any) {
    errorCaught = err;
  }

  assert.ok(errorCaught);
  assert.equal(errorCaught.code, 'CHECKPOINT_CONTAINS_SECRET');
  assert.equal(errorCaught.message.includes(secretKey), false);

  const snapshot = kernel.snapshot();
  const snapshotJson = JSON.stringify(snapshot);
  assert.equal(snapshotJson.includes(secretKey), false);

  kernel.close();
});

test('21. A new owner cannot authorize an effect until it writes a new-epoch checkpoint', () => {
  let currentTime = 1000000;
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
    now: () => currentTime,
  });

  const offer1 = createTestOffer('worker_01', {
    failureDomain: 'zone_a',
    providers: ['provider_1'],
    observedAtMs: currentTime,
  });

  kernel.claimMission({
    missionId: 'mission_epoch_chk',
    kind: 'code',
    riskClass: 'P0',
    goal: 'New epoch checkpoint requirement test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer: offer1,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 100.0,
    initialCheckpoint: createTestCheckpoint('mission_epoch_chk', 'attempt_01', 1, 1),
  });

  // Handover and takeover
  kernel.beginHandover({
    missionId: 'mission_epoch_chk',
    attemptId: 'attempt_01',
    leaseEpoch: 1,
    failureClass: 'STALLED',
    evidenceRef: 'progress_stalled_100s',
  });

  const offer2 = createTestOffer('worker_02', {
    failureDomain: 'zone_b',
    providers: ['provider_2'],
    observedAtMs: currentTime,
  });
  kernel.claimTakeover({
    missionId: 'mission_epoch_chk',
    expectedLeaseEpoch: 1,
    newAttemptId: 'attempt_02',
    newWorkerId: 'worker_02',
    offer: offer2,
  });

  // Worker 2 has NOT yet written a checkpoint in epoch 2! Attempting authorizeEffect MUST fail
  const effectKey = computeEffectKey('mission_epoch_chk', 'step_1', 'k3s.apply', 'sha256:args');
  assert.throws(
    () =>
      kernel.authorizeEffect({
        missionId: 'mission_epoch_chk',
        attemptId: 'attempt_02',
        leaseEpoch: 2,
        stepId: 'step_1',
        action: 'k3s.apply',
        argsDigest: 'sha256:args',
        effectKey,
      }),
    (err: any) => err instanceof ContinuityError && err.code === 'CHECKPOINT_REQUIRED'
  );

  // Once worker 2 writes a checkpoint in epoch 2, effect authorization succeeds!
  currentTime += 1000;
  kernel.checkpoint({
    missionId: 'mission_epoch_chk',
    attemptId: 'attempt_02',
    leaseEpoch: 2,
    checkpoint: createTestCheckpoint('mission_epoch_chk', 'attempt_02', 2, 2),
  });

  const permit = kernel.authorizeEffect({
    missionId: 'mission_epoch_chk',
    attemptId: 'attempt_02',
    leaseEpoch: 2,
    stepId: 'step_1',
    action: 'k3s.apply',
    argsDigest: 'sha256:args',
    effectKey,
  });

  assert.equal(permit.effectKey, effectKey);
  assert.equal(permit.leaseEpoch, 2);

  kernel.close();
});

test('22. No eligible worker writes durable recovery pending without changing the mission epoch', () => {
  let currentTime = 1000000;
  const kernel = new MissionContinuityKernel({
    dbPath: ':memory:',
    receiptKey: VALID_RECEIPT_KEY,
    now: () => currentTime,
  });

  const offer = createTestOffer('worker_01', { observedAtMs: currentTime });
  kernel.claimMission({
    missionId: 'mission_epoch_preserve',
    kind: 'code',
    riskClass: 'P1',
    goal: 'Epoch preservation test',
    attemptId: 'attempt_01',
    workerId: 'worker_01',
    offer,
    requiredCapabilities: ['git.read'],
    costBudgetRemaining: 100.0,
    initialCheckpoint: createTestCheckpoint('mission_epoch_preserve', 'attempt_01', 1, 1),
  });

  kernel.beginHandover({
    missionId: 'mission_epoch_preserve',
    attemptId: 'attempt_01',
    leaseEpoch: 1,
    failureClass: 'CAPACITY_DENIED',
    evidenceRef: 'cluster_out_of_concurrency',
  });

  const result = kernel.markRecoveryPending({
    missionId: 'mission_epoch_preserve',
    expectedLeaseEpoch: 1,
    reason: 'Zero candidate workers available with required capabilities',
  });

  assert.equal(result.mission.recoveryPending, true);
  assert.equal(result.mission.leaseEpoch, 1, 'Mission epoch must remain strictly unchanged on recovery pending');
  assert.equal(result.selected, null);

  kernel.close();
});
