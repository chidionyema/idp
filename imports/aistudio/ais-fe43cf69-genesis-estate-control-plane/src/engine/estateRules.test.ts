import test from 'node:test';
import assert from 'node:assert/strict';
import {
  evaluateClaimGate,
  evaluateStagnationWatchdog,
  transitionFlowRecord,
  validateGenesisInboundPayload,
  reconcilePullRequestBacklog,
  LEGION_FORMATIONS,
  FLOW_STAGNATION_TIMEOUT_MS,
  type FlowInstructionRecord,
} from './estateRules';

test('LEGION_FORMATIONS defines all 8 canonical cloud formations', () => {
  assert.equal(LEGION_FORMATIONS.length, 8);
  const ids = LEGION_FORMATIONS.map((f) => f.id);
  assert.deepEqual(ids, [
    'sniper',
    'phalanx',
    'pipeline',
    'swarm',
    'centurion',
    'adversarial',
    'tournament',
    'sieve',
  ]);
});

test('evaluateClaimGate rejects silent E3/U -> E1 authority promotion and fake SHAs', () => {
  const res = evaluateClaimGate({
    claimedAuthority: 'E1',
    claimText: 'Bridge is 100% working and verified in production.',
    observedSha: 'b5531c...',
    missingCapabilities: ['GENESIS_GOOGLE_REFRESH_TOKEN'],
    integrationTestsPassed: false,
  });

  assert.equal(res.verdict, 'CLAIM_REJECTED');
  assert.equal(res.effectiveAuthority, 'U');
  const codes = res.violations.map((v) => v.code);
  assert.ok(codes.includes('SILENT_AUTHORITY_PROMOTION'));
  assert.ok(codes.includes('FAKE_SHA_OR_FABRICATED_COMMIT'));
  assert.ok(codes.includes('THEATRE_WITHOUT_FALSIFIER'));
});

test('evaluateClaimGate blocks direct git push to main and kubectl apply hand-mutations', () => {
  const res = evaluateClaimGate({
    claimedAuthority: 'E3',
    claimText: 'Deploying hotfix straight to cluster.',
    proposedCommands: ['git push origin main', 'kubectl apply -f external-secret.yaml'],
  });

  assert.equal(res.verdict, 'CLAIM_REJECTED');
  assert.ok(res.violations.some((v) => v.code === 'BANNED_GIT_MUTATION'));
});

test('evaluateClaimGate passes genuine E1 evidence with 40-char SHA, passing falsifier, and 7-Gate evaluation', () => {
  const res = evaluateClaimGate({
    claimedAuthority: 'E1',
    claimText: 'Observed main commit on chidionyema/idp and verified pre-push branch delta test.',
    proposedCommands: ['estate-execute lane-submit --repo idp --branch lane/ins-00091'],
    observedSha: '65251ecd428a8c7b7c683653dcf3ec382623bf5e',
    integrationTestsPassed: true,
    falsifierVerdict: 'PASS',
    sevenGates: {
      contextualScoping: 'Stateless CI pre-push hook evaluating branch commit range.',
      dimensionalThresholds: 'Zero false-red failures when main advances concurrently within <120s.',
      baselineDelta: 'Eliminates branch-vs-moving-main race observed prior to PR #7984.',
      architecturalTradeoffs: 'Requires merge-base calculation (+18ms git rev-list cost).',
      systemicReflexivity: 'Greenlane still verifies full fast-forward tree before main promotion.',
      deterministicVerification: 'Exact git merge-base diff tested against synthetic divergent refs.',
      provenanceAndTrust: 'E1 GitHub commit SHA observed directly on chidionyema/idp.',
    },
  });

  assert.equal(res.verdict, 'PASS');
  assert.equal(res.effectiveAuthority, 'E1');
  assert.equal(res.epistemicScore, 100);
  assert.equal(res.violations.length, 0);
});

test('validateGenesisInboundPayload enforces public:true firewall on public repos and idempotency', () => {
  const processed = new Set<string>(['INS-EXISTING-01']);

  // Negative case 1: Public repo chidionyema/idp without public: true
  const leakAttempt = validateGenesisInboundPayload(
    {
      v: 1,
      repo: 'chidionyema/idp',
      instruction_id: 'INS-00099',
      title: 'Sync internal bridge config',
      body: 'Deploy confidential outbox relay parameters.',
    },
    processed
  );
  assert.equal(leakAttempt.accepted, false);
  if (!leakAttempt.accepted) {
    assert.equal(leakAttempt.errorCode, 'PUBLIC_REPO_REQUIRES_EXPLICIT_PUBLIC_TRUE');
  }

  // Negative case 2: Private repo chidionyema/argon with public: true
  const privateMismatch = validateGenesisInboundPayload(
    {
      v: 1,
      repo: 'argon',
      instruction_id: 'INS-00100',
      title: 'Private Argon guardian audit',
      body: 'Inspect GENESIS_GUARDIAN_SHA baseline lineage.',
      public: true,
    },
    processed
  );
  assert.equal(privateMismatch.accepted, false);
  if (!privateMismatch.accepted) {
    assert.equal(privateMismatch.errorCode, 'PRIVATE_REPO_FORBIDS_PUBLIC_FLAG');
  }

  // Idempotent duplicate check
  const duplicate = validateGenesisInboundPayload(
    {
      v: 1,
      repo: 'argon',
      instruction_id: 'INS-EXISTING-01',
      title: 'Duplicate retry',
      body: 'Retrying network submission of existing instruction.',
    },
    processed
  );
  assert.equal(duplicate.accepted, true);
  if (duplicate.accepted) {
    assert.equal(duplicate.status, 'DUPLICATE_IDEMPOTENT_NOOP');
  }

  // Valid public dispatch
  const validPublic = validateGenesisInboundPayload(
    {
      v: 1,
      repo: 'chidionyema/idp',
      instruction_id: 'INS-7981-VERIFY',
      title: 'Verify inbound bridge workflow schema',
      body: 'Run deterministic negative tests on bin/genesis-inbound-bridge.py.',
      public: true,
    },
    processed
  );
  assert.equal(validPublic.accepted, true);
  if (validPublic.accepted) {
    assert.equal(validPublic.status, 'ACCEPTED_NEW');
    assert.equal(validPublic.laneBranch, 'lane/ins-7981-verify');
  }
});

test('FLOW 600s stagnation watchdog fences stale worker epoch and recovers autonomously', () => {
  const t0 = 1_760_000_000_000;
  const record: FlowInstructionRecord = {
    instructionId: 'INS-00050',
    idempotencyKey: 'idem-50',
    title: 'Execute Phalanx staging verification',
    body: 'Run cloud worker integration suite per SHA.',
    repo: 'chidionyema/idp',
    formation: 'phalanx',
    helmShots: 4,
    phase: 'EXECUTING_FORMATION',
    leaseEpoch: 1,
    assignedWorkerId: 'worker-alpha-e1',
    executionId: 'exec-01',
    laneBranch: 'lane/ins-00050',
    sourceSha: null,
    receiptHash: null,
    authorityClass: 'E1',
    createdAtMs: t0,
    lastHeartbeatMs: t0,
    recoveryCount: 0,
  };

  // At 599s -> not stagnant
  const beforeTimeout = evaluateStagnationWatchdog(record, t0 + FLOW_STAGNATION_TIMEOUT_MS - 1000);
  assert.equal(beforeTimeout.stagnant, false);
  assert.equal(beforeTimeout.updatedRecord.leaseEpoch, 1);

  // At 605s -> stagnant, bumps epoch to 2, transitions to RECOVERING_AUTONOMOUS
  const afterTimeout = evaluateStagnationWatchdog(record, t0 + 605_000);
  assert.equal(afterTimeout.stagnant, true);
  assert.equal(afterTimeout.updatedRecord.phase, 'RECOVERING_AUTONOMOUS');
  assert.equal(afterTimeout.updatedRecord.leaseEpoch, 2);
  assert.equal(afterTimeout.updatedRecord.recoveryCount, 1);

  // Stale worker from epoch 1 tries to write -> fenced out (fail-closed)
  const staleWrite = transitionFlowRecord(
    afterTimeout.updatedRecord,
    'EXECUTING_FORMATION',
    1, // stale epoch
    t0 + 606_000
  );
  assert.equal(staleWrite.ok, false);
  if (!staleWrite.ok) {
    assert.equal(staleWrite.errorCode, 'FENCE_EPOCH_STALE');
  }

  // New recovery worker at epoch 2 transitions cleanly
  const validWrite = transitionFlowRecord(
    afterTimeout.updatedRecord,
    'EXECUTING_FORMATION',
    2,
    t0 + 606_000
  );
  assert.equal(validWrite.ok, true);
});

test('reconcilePullRequestBacklog detects live SHA drift and orders Greenlane candidates first', () => {
  const reconciled = reconcilePullRequestBacklog([
    {
      repo: 'chidionyema/argon',
      number: 91,
      title: 'authenticated Google Gemini inbound bridge',
      handoverSha: '85d50c4d288653336eff2b09e2f5e07b38bf6a38',
      liveSha: null,
      handoverMainSha: 'bc61148828d04d84c4862cdef0be33f56060f7b0',
      liveMainSha: null,
      checksState: 'UNVERIFIED_PRIVATE',
      blockingIncident: 'Contract CI & provenance FAIL at 85d50c4',
      priorityTier: 1,
    },
    {
      repo: 'chidionyema/idp',
      number: 7981,
      title: 'feat(genesis): authenticated Gemini Gmail/Drive inbound transport (IDP)',
      handoverSha: 'a75bf6e8a20ad614fe27f5ddc8ba7b5d891f4612',
      liveSha: '15b0320000000000000000000000000000000000',
      handoverMainSha: 'd05d6fef60454f059cf9db943bfc66b0d3079e00',
      liveMainSha: '65251ecd428a8c7b7c683653dcf3ec382623bf5e',
      checksState: 'PASSING',
      priorityTier: 1,
    },
    {
      repo: 'chidionyema/idp',
      number: 7985,
      title: 'fix(web): canonical on every page and model roster',
      handoverSha: null,
      liveSha: 'c151131000000000000000000000000000000000',
      handoverMainSha: '65251ecd428a8c7b7c683653dcf3ec382623bf5e',
      liveMainSha: '65251ecd428a8c7b7c683653dcf3ec382623bf5e',
      checksState: 'PASSING',
      priorityTier: 2,
    },
  ]);

  assert.equal(reconciled[0].number, 7985);
  assert.equal(reconciled[0].disposition, 'READY_FOR_GREENLANE');
  assert.equal(reconciled[0].driftState, 'NEW_SINCE_HANDOVER');

  assert.equal(reconciled[1].number, 7981);
  assert.equal(reconciled[1].driftState, 'HEAD_MOVED_LIVE');
  assert.equal(reconciled[1].mainMoved, true);
  assert.equal(reconciled[1].disposition, 'REBASE_ONTO_LIVE_MAIN');

  assert.equal(reconciled[2].number, 91);
  assert.equal(reconciled[2].disposition, 'AWAITING_PRIVATE_CONNECTOR');
});
