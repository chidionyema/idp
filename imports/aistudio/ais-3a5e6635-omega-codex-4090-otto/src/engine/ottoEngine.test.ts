import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createInitialEstateState,
  evaluateEstateSweep,
  evaluateArgonPrePushGate,
  validateGenesisCommitTrailers,
  pruneEstateWorktreesAndCaches,
  resolveDefectControl,
  unblockAllArgonGates,
  runByzantineSieve,
  drainBacklogMission,
  createFounderMissionContract,
  forgeAutoTool,
  compareActuationEngines,
  triggerRealTimeSweep,
  executeArgonSyncGuarantee,
  toggleArgonSyncAutoPropagate,
} from './ottoEngine';

test('initial estate sweep matches measured Mac telemetry (DRIFT, 4.02 GiB free, REFUSED)', () => {
  const state = createInitialEstateState();
  const sweep = evaluateEstateSweep(state);
  assert.equal(sweep.verdict, 'DRIFT');
  assert.equal(sweep.diskAdmit, 'REFUSED');
  assert.equal(state.diskFreeGiB, 4.02);
  // 73 (idp) + 103 (argon) + 3566 (argon-sync) + 0 (wt-otto) = 3742
  assert.equal(sweep.totalDirtyFiles, 3742);
  // 25 + 7 + 2 + 1 = 35
  assert.equal(sweep.totalWorktrees, 35);
});

test('Genesis commit trailers reject invalid change class "tooling" and accept "feature"', () => {
  const rejected = validateGenesisCommitTrailers({
    instructionId: 'GEN-2026-1106-OTTO-SWEEP',
    changeClass: 'tooling',
    verification: 'pytest-3-passed',
    artifacts: 'bin/otto-background-sweep.py',
  });
  assert.equal(rejected.valid, false);
  assert.ok(rejected.errors.some((e) => e.includes('tooling')));

  const accepted = validateGenesisCommitTrailers({
    instructionId: 'GEN-2026-1106-OTTO-SWEEP',
    changeClass: 'feature',
    verification: 'pytest-3-passed',
    artifacts: 'bin/otto-background-sweep.py',
  });
  assert.equal(accepted.valid, true);
});

test('Argon pre-push gate blocks on untracked genesis-defect-controls.json and CONTROL_PROPOSED defects, then passes when unblocked', () => {
  const initial = createInitialEstateState();
  const gateBefore = evaluateArgonPrePushGate(initial.argonGate);
  assert.equal(gateBefore.verdict, 'BLOCKED');
  assert.equal(gateBefore.blockingDefects.length, 3);

  // Resolve single defect
  const partial = resolveDefectControl(initial, 'DEF-20261104-GATE-BYPASS-002', 'CONTROL_VERIFIED');
  assert.equal(evaluateArgonPrePushGate(partial.argonGate).blockingDefects.length, 2);

  // Unblock all Argon gates & prune stale worktrees
  const unblocked = unblockAllArgonGates(initial, 'TRACKED_COMMITTED');
  const gateAfter = evaluateArgonPrePushGate(unblocked.argonGate);
  assert.equal(gateAfter.verdict, 'PASS');
  assert.equal(gateAfter.blockingDefects.length, 0);
  assert.equal(unblocked.diskAdmit, 'GRANTED');
  assert.ok(unblocked.diskFreeGiB > 18.0);
});

test('pruning stale worktrees and build caches reclaims 14.62 GiB without wiping dirty file counts', () => {
  const initial = createInitialEstateState();
  const pruned = pruneEstateWorktreesAndCaches(initial);
  assert.equal(pruned.diskFreeGiB, 18.64);
  assert.equal(pruned.diskAdmit, 'GRANTED');
  // Non-destructive law: dirty file counts in unowned trees are preserved
  const idp = pruned.repos.find((r) => r.id === 'idp')!;
  const argonSync = pruned.repos.find((r) => r.id === 'argon-sync')!;
  assert.equal(idp.dirtyCount, 73);
  assert.equal(argonSync.dirtyCount, 3566);
  assert.equal(idp.staleWorktrees, 0);
});

test('Byzantine Sieve requires 2/3 deterministic hash consensus across Claude, Codex, and Pi', () => {
  const initial = createInitialEstateState();
  const dropMission = initial.missions.find((m) => m.id === 'DROP-2026-1082')!;
  const sieve = runByzantineSieve(dropMission.subordinateVotes);
  assert.equal(sieve.consensusReached, true);
  assert.equal(sieve.agreementRatio, '3/3');
  assert.equal(sieve.winningHash, 'sha256:c3d3ce2c91a4');
});

test('draining backlog mission seals DROP-2026-1082 and creating founder contract validates inputs', () => {
  const unblocked = unblockAllArgonGates(createInitialEstateState());
  const drained = drainBacklogMission(unblocked, 'DROP-2026-1082');
  assert.equal(drained.drop1082Synced, true);
  const dropMission = drained.missions.find((m) => m.id === 'DROP-2026-1082')!;
  assert.equal(dropMission.status, 'SEALED_TO_ORIGIN');

  assert.throws(() =>
    createFounderMissionContract(drained, {
      title: '',
      targetRepo: 'argon',
      bddSpec: '',
      pillar: 'SWARM_MAESTRO',
      priority: 'P1_HIGH',
    })
  );

  const withContract = createFounderMissionContract(drained, {
    title: 'Zero-Copy Rust IPC Ring Buffer for Argon Sync',
    targetRepo: 'argon-sync',
    bddSpec: 'GIVEN 3566 session blobs WHEN ring buffer flushes THEN latency < 4ms',
    pillar: 'AUTO_TOOL_FORGING',
    priority: 'P1_HIGH',
  });
  assert.equal(withContract.missions.length, drained.missions.length + 1);

  const withTool = forgeAutoTool(withContract, {
    name: 'otto-worktree-gc',
    language: 'Rust 2024',
    bottleneckSolved: 'Prunes detached worktree objects in <15ms',
    targetRepo: 'idp',
  });
  assert.equal(withTool.forgedTools.length, withContract.forgedTools.length + 1);
  assert.ok(compareActuationEngines().length >= 5);
});

test('triggerRealTimeSweep updates sweepTimestamp and tracks last drift detection time accurately', () => {
  const initial = createInitialEstateState();
  assert.equal(initial.sweepFrequencySec, 300);
  assert.equal(initial.lastDriftTimestamp, '2026-11-06T01:29:58Z');

  // Triggering a sweep with DRIFT updates lastDriftTimestamp
  const sweep1 = triggerRealTimeSweep(initial, {
    forcedVerdict: 'DRIFT',
    customTimestamp: '2026-11-06T01:34:58Z',
  });
  assert.equal(sweep1.sweepTimestamp, '2026-11-06T01:34:58Z');
  assert.equal(sweep1.lastDriftTimestamp, '2026-11-06T01:34:58Z');
  assert.equal(sweep1.sweepVerdict, 'DRIFT');

  // Triggering a clean sweep updates sweepTimestamp while preserving lastDriftTimestamp
  const sweep2 = triggerRealTimeSweep(sweep1, {
    forcedVerdict: 'CLEAN',
    customTimestamp: '2026-11-06T01:39:58Z',
  });
  assert.equal(sweep2.sweepTimestamp, '2026-11-06T01:39:58Z');
  assert.equal(sweep2.lastDriftTimestamp, '2026-11-06T01:34:58Z');
  assert.equal(sweep2.sweepVerdict, 'CLEAN');
});

test('executeArgonSyncGuarantee pushes unpushed commits and updates tracking state without prompting', () => {
  const initial = createInitialEstateState();
  const argonSyncBefore = initial.repos.find((r) => r.id === 'argon-sync')!;
  assert.equal(argonSyncBefore.unpushedCommits, 9);
  assert.equal(initial.argonSyncAutoPropagate, true);

  const { nextState, pushedCommits, receiptHash } = executeArgonSyncGuarantee(initial, {
    customTimestamp: '2026-11-06T01:45:00Z',
  });

  assert.equal(pushedCommits, 9);
  assert.ok(receiptHash.startsWith('sha256:argon-sync-guarantee'));
  assert.equal(nextState.lastArgonSyncPush, '2026-11-06T01:45:00Z');

  const argonSyncAfter = nextState.repos.find((r) => r.id === 'argon-sync')!;
  assert.equal(argonSyncAfter.unpushedCommits, 0);

  // Toggle auto-propagate setting test
  const toggled = toggleArgonSyncAutoPropagate(nextState);
  assert.equal(toggled.argonSyncAutoPropagate, false);
});
