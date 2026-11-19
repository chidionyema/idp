import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SWARM_SPORE_MAX_BYTES,
  createSeedSwarmSynapseState,
  hydrateSwarmLayer,
  commitSwarmDualYield,
  rollbackSwarmSagaLifo,
  triggerAutoTakeoverFailure,
  initiateFounderReassignment,
  attemptMissionWorkerWrite,
  acknowledgeWorkerHandoff,
  completeOfflineContinuityYield,
} from './swarmSynapse';

test('Swarm Synapse S1 disk floor halts execution below 1500 MB', () => {
  const state = createSeedSwarmSynapseState(1_762_930_000);
  const res = hydrateSwarmLayer(state, {
    agentId: 'codex-01',
    layer: 'idp/bin/new-layer',
    diskFreeMbOverride: 1420,
    nowSec: 1_762_930_010,
  });
  assert.equal(res.status, 'HALT_DISK_FLOOR');
  assert.equal(res.allowedToProceed, false);
});

test('Pass-0 Antibody hit resolves known failure signature in 0 LLM diagnostic passes', () => {
  const state = createSeedSwarmSynapseState(1_762_930_000);
  const res = hydrateSwarmLayer(state, {
    agentId: 'gemini-session-02',
    layer: 'idp/sqlite/step_runs',
    failureSig: 'SQLITE_STEP_RUNS_NOT_NULL_DRIFT',
    nowSec: 1_762_930_015,
  });
  assert.equal(res.status, 'PASS_0_ANTIBODY_HIT');
  if (res.status === 'PASS_0_ANTIBODY_HIT') {
    assert.equal(res.agentDiagPasses, 0);
    assert.equal(res.antibodyId, 'AB-S2DDL401');
    assert.ok(res.remediationCmd.includes('estate-swarm-synapse.py'));
  }
});

test('Stigmergic lease exclusivity blocks concurrent peer stampedes and completed layers', () => {
  const state = createSeedSwarmSynapseState(1_762_930_000);

  // Already completed layer -> ALREADY_LANDED_BY_PEER
  const completedCheck = hydrateSwarmLayer(state, {
    agentId: 'opencode-03',
    layer: 'idp/bin/estate-cache-trim',
    nowSec: 1_762_930_005,
  });
  assert.equal(completedCheck.status, 'ALREADY_LANDED_BY_PEER');
  assert.equal(completedCheck.allowedToProceed, false);

  // Active peer lease -> LOCKED_BY_ACTIVE_PEER
  const activeCheck = hydrateSwarmLayer(state, {
    agentId: 'minimax-04',
    layer: 'idp/platform/estate/memory/door.py',
    nowSec: 1_762_930_005,
  });
  assert.equal(activeCheck.status, 'LOCKED_BY_ACTIVE_PEER');
  assert.equal(activeCheck.allowedToProceed, false);
});

test('Dual-Yield Law enforces substantive --fact, fences stale tokens, and packs <= 4KB GENESIS_SPORE.dna', () => {
  const state = createSeedSwarmSynapseState(1_762_930_000);
  const lease = hydrateSwarmLayer(state, {
    agentId: 'aistudio-sniper-01',
    layer: 'idp/platform/estate/estate-proof',
    nowSec: 1_762_930_010,
  });
  assert.equal(lease.status, 'LEASE_GRANTED');
  if (lease.status !== 'LEASE_GRANTED') return;

  // 1. Missing/short fact is refused by Dual-Yield Law
  const badFact = commitSwarmDualYield(state, {
    agentId: 'aistudio-sniper-01',
    layer: 'idp/platform/estate/estate-proof',
    fencingToken: lease.fencingToken,
    commitSha: 'b31e032d8c6744109a8f12c34b778e910234abcd',
    learnedFact: 'fixed bug',
  });
  assert.equal(badFact.ok, false);
  if (!badFact.ok) {
    assert.equal(badFact.errorCode, 'REFUSED_BY_DUAL_YIELD_LAW');
  }

  // 2. Stale fencing token is rejected
  const stale = commitSwarmDualYield(state, {
    agentId: 'zombie-worker-00',
    layer: 'idp/platform/estate/estate-proof',
    fencingToken: lease.fencingToken - 1,
    commitSha: 'b31e032d8c6744109a8f12c34b778e910234abcd',
    learnedFact: 'Moved estate-proof into versioned idp/platform/estate/ directory.',
  });
  assert.equal(stale.ok, false);
  if (!stale.ok) {
    assert.equal(stale.errorCode, 'FENCED_OUT_STALE_SESSION');
  }

  // 3. Valid Dual-Yield commits fact + new antibody + repacks <= 4096B spore
  const good = commitSwarmDualYield(state, {
    agentId: 'aistudio-sniper-01',
    layer: 'idp/platform/estate/estate-proof',
    fencingToken: lease.fencingToken,
    commitSha: 'b31e032d8c6744109a8f12c34b778e910234abcd',
    learnedFact:
      'Versioned estate-proof inside idp/platform/estate/ so host verification survives laptop disk failure.',
    antibodySig: 'HOST_ONLY_PROOF_TOOLING_DRIFT',
    antibodyCmd: 'python3 idp/platform/estate/estate-swarm-synapse.py hydrate --agent host --layer proof',
  });
  assert.equal(good.ok, true);
  if (good.ok) {
    assert.ok(good.antibodyRegistered?.startsWith('AB-'));
    assert.ok(good.sporeBytes > 120 && good.sporeBytes <= SWARM_SPORE_MAX_BYTES);
    assert.equal(state.sporeDna.decodedPayload.fencing_token, lease.fencingToken);
  }
});

test('LIFO Compensating Saga rollback restores prior task state and increments authoritative fencing token', () => {
  const state = createSeedSwarmSynapseState(1_762_930_000);
  const beforeToken = state.authoritativeToken;

  const lease = hydrateSwarmLayer(state, {
    agentId: 'codex-temp-09',
    layer: 'argon/lane/temp-experiment',
    nowSec: 1_762_930_020,
  });
  assert.equal(lease.status, 'LEASE_GRANTED');
  assert.equal(
    state.myceliumTaskQueue.some((t) => t.taskId === 'argon/lane/temp-experiment'),
    true
  );

  const rolled = rollbackSwarmSagaLifo(state, 1);
  assert.equal(rolled.rolledBackEntries.length, 1);
  assert.equal(
    state.myceliumTaskQueue.some((t) => t.taskId === 'argon/lane/temp-experiment'),
    false
  );
  assert.equal(rolled.newAuthoritativeToken, beforeToken + 2);
});

test('Mac-Offline End-to-End Founder Reassignment Proof enforces Genesis/Otto parity, stale-worker fencing, and post-ACK owner switch', () => {
  const state = createSeedSwarmSynapseState(1_762_930_000);

  // Initial parity with Mac offline
  assert.equal(state.offlineContinuity.macHostStatus, 'OFFLINE_ISOLATED');
  assert.equal(state.offlineContinuity.genesisSurface.displayedOwner, 'codex-worker-alpha');
  assert.equal(state.offlineContinuity.ottoSurface.displayedOwner, 'codex-worker-alpha');
  assert.equal(state.offlineContinuity.parityVerified, true);

  // Step 1: Automatic takeover fails -> Both show "Needs reassignment"
  const afterFail = triggerAutoTakeoverFailure(state);
  assert.equal(afterFail.state, 'NEEDS_REASSIGNMENT');
  assert.equal(afterFail.genesisSurface.displayedStatusLabel, 'Needs reassignment');
  assert.equal(afterFail.ottoSurface.displayedStatusLabel, 'Needs reassignment');
  assert.equal(afterFail.parityVerified, true);

  // Step 2: Founder selects gemini-4-centurion-01 -> Fence bumps, but NEITHER surface shows new owner yet!
  const oldToken = afterFail.fencingToken;
  const afterInit = initiateFounderReassignment(state, 'gemini-4-centurion-01');
  assert.equal(afterInit.state, 'REASSIGN_PENDING_ACK');
  assert.equal(afterInit.fencingToken, oldToken + 1);
  assert.equal(afterInit.genesisSurface.displayedOwner, 'codex-worker-alpha');
  assert.equal(afterInit.ottoSurface.displayedOwner, 'codex-worker-alpha');
  assert.equal(afterInit.pendingNewOwner, 'gemini-4-centurion-01');

  // Step 3: Old worker attempts to write with old token -> Deterministically rejected (HTTP 409)
  const staleAttempt = attemptMissionWorkerWrite(state, {
    workerId: 'codex-worker-alpha',
    workerFencingToken: oldToken,
    attemptedProgress: 'Late zombie write from superseded session',
  });
  assert.equal(staleAttempt.accepted, false);
  if (!staleAttempt.accepted) {
    assert.equal(staleAttempt.rejection.httpStatus, 409);
    assert.equal(staleAttempt.rejection.errorCode, 'FENCED_OLD_WORKER_REJECTED');
  }

  // Step 4: New worker acknowledges handoff -> BOTH Genesis and Otto atomically switch to gemini-4-centurion-01!
  const afterAck = acknowledgeWorkerHandoff(state, {
    workerId: 'gemini-4-centurion-01',
    fencingToken: afterInit.fencingToken,
  });
  assert.equal(afterAck.state, 'ACKED_ACTIVE_NEW_OWNER');
  assert.equal(afterAck.genesisSurface.displayedOwner, 'gemini-4-centurion-01');
  assert.equal(afterAck.ottoSurface.displayedOwner, 'gemini-4-centurion-01');
  assert.equal(afterAck.parityVerified, true);

  // Step 5: Complete verified yield
  const afterYield = completeOfflineContinuityYield(state);
  assert.equal(afterYield.state, 'VERIFIED_YIELD');
  assert.equal(afterYield.genesisSurface.checkpointSha, afterYield.ottoSurface.checkpointSha);
  assert.equal(afterYield.parityVerified, true);
});
