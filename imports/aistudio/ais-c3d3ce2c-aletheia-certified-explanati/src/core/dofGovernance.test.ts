import test from 'node:test';
import assert from 'node:assert/strict';
import {
  applyFounderOttOverride,
  attemptAgentAction,
  buildOnboardingRuleZeroBlock,
  buildSystemProbeHealthMatrix,
  createInitialDofEpisodeState,
  evaluateProbeTransition,
  MEMORY_01_REPAIR_PROTOCOL,
  serializeDofLevelStateFile,
  simulateComponentProbeTick,
} from './dofGovernance';

test('DoF Proving Test (MEMORY-01): no path exists from probe failed to agent task execution without completing MEMORY-01 and 3x consecutive probe passes', () => {
  let state = createInitialDofEpisodeState();
  assert.equal(state.activeLevel, 'L0');

  // 1. Memory-spine dual probe fails at session start -> Lease drops to L2 (MEMORY-01 only)
  state = evaluateProbeTransition(state, {
    componentId: 'MEMORY-01',
    methodAStatus: 'FAIL',
    methodADetail: 'WAL frame checksum mismatch',
    methodBStatus: 'FAIL',
    methodBDetail: 'SQLite PRAGMA integrity_check failed on page 419',
  });
  assert.equal(state.activeLevel, 'L2');
  assert.equal(state.failingComponent, 'MEMORY-01');
  assert.equal(state.consecutiveProbePasses, 0);

  // 2. Agent tries to "note and move on" by calling a normal task tool -> Refused with machine-readable envelope
  const blockedAttempt = attemptAgentAction(state, {
    toolName: 'workspace.deploy_feature',
    category: 'task-mutation',
    surface: 'agent-cli',
  });
  assert.equal(blockedAttempt.allowed, false);
  assert.ok(blockedAttempt.refusalEnvelope !== null);
  assert.equal(blockedAttempt.refusalEnvelope?.failingComponent, 'MEMORY-01');
  assert.equal(blockedAttempt.refusalEnvelope?.prescribedProtocol, 'MEMORY-01');
  state = blockedAttempt.nextState;

  // 3. Even if probe transiently passes before MEMORY-01 steps are receipted, L0 cannot restore
  state = evaluateProbeTransition(state, {
    componentId: 'MEMORY-01',
    methodAStatus: 'PASS',
    methodADetail: 'OK',
    methodBStatus: 'PASS',
    methodBDetail: 'OK',
  });
  assert.equal(state.activeLevel, 'L2');
  assert.equal(state.consecutiveProbePasses, 0);

  // 4. Execute all 5 prescribed MEMORY-01 repair protocol steps
  for (const step of MEMORY_01_REPAIR_PROTOCOL) {
    const res = attemptAgentAction(state, {
      toolName: `repair.${step.code}`,
      category: 'repair-step',
      repairStepIndex: step.stepIndex,
    });
    assert.equal(res.allowed, true);
    state = res.nextState;
  }
  assert.equal(state.completedRepairSteps.length, 5);

  // 5. Anti-flapping hysteresis: 1st and 2nd probe passes keep lease at L2; 3rd pass restores L0
  state = evaluateProbeTransition(state, {
    componentId: 'MEMORY-01',
    methodAStatus: 'PASS',
    methodADetail: 'OK',
    methodBStatus: 'PASS',
    methodBDetail: 'OK',
  });
  assert.equal(state.consecutiveProbePasses, 1);
  assert.equal(state.activeLevel, 'L2');

  state = evaluateProbeTransition(state, {
    componentId: 'MEMORY-01',
    methodAStatus: 'PASS',
    methodADetail: 'OK',
    methodBStatus: 'PASS',
    methodBDetail: 'OK',
  });
  assert.equal(state.consecutiveProbePasses, 2);
  assert.equal(state.activeLevel, 'L2');

  // Third consecutive pass restores L0 Full Lease!
  state = evaluateProbeTransition(state, {
    componentId: 'MEMORY-01',
    methodAStatus: 'PASS',
    methodADetail: 'OK',
    methodBStatus: 'PASS',
    methodBDetail: 'OK',
  });
  assert.equal(state.consecutiveProbePasses, 3);
  assert.equal(state.activeLevel, 'L0');

  // 6. Now task execution is allowed again
  const postRestoreAttempt = attemptAgentAction(state, {
    toolName: 'workspace.deploy_feature',
    category: 'task-mutation',
  });
  assert.equal(postRestoreAttempt.allowed, true);
});

test('DoF Edge Cases: false-positive disagreement holds at L1, cross-surface bypass escalates to L3 Red Card, and Founder OTT overrides with attribution', () => {
  let state = createInitialDofEpisodeState();

  // Edge Case 1: Method A fails, Method B passes -> L1 Diagnose-Only (not L2)
  state = evaluateProbeTransition(state, {
    componentId: 'MEMORY-01',
    methodAStatus: 'FAIL',
    methodADetail: 'Stat timeout',
    methodBStatus: 'PASS',
    methodBDetail: 'SQLite query healthy',
  });
  assert.equal(state.activeLevel, 'L1');

  // Edge Case 4: Cross-surface bypass via web-chat escalates immediately to L3 Frozen + Red Card
  const bypassAttempt = attemptAgentAction(state, {
    toolName: 'workspace.write_file',
    category: 'task-mutation',
    surface: 'web-chat',
  });
  assert.equal(bypassAttempt.allowed, false);
  assert.equal(bypassAttempt.nextState.activeLevel, 'L3');
  assert.equal(bypassAttempt.nextState.redCardIssued, true);
  assert.equal(
    bypassAttempt.refusalEnvelope?.escalationState.crossSurfaceBypassDetected,
    true
  );

  // Edge Case 5: Founder OTT override restores L0 with signed digest
  const overridden = applyFounderOttOverride(
    bypassAttempt.nextState,
    'principal:founder@fortress.estate',
    'Emergency hotfix window'
  );
  assert.equal(overridden.activeLevel, 'L0');
  assert.equal(overridden.founderOttOverrideActive, true);
  assert.ok(overridden.founderOttTokenDigest?.startsWith('0x'));
});

test('DoF Health Monitor: buildSystemProbeHealthMatrix and simulateComponentProbeTick track P0-P3 leases, 1-down/3-up counters, and 10-cycle audit trend history', () => {
  const init = createInitialDofEpisodeState();
  const failedEpisode = evaluateProbeTransition(init, {
    componentId: 'MEMORY-01',
    methodAStatus: 'FAIL',
    methodADetail: 'WAL CRC mismatch',
    methodBStatus: 'FAIL',
    methodBDetail: 'PRAGMA integrity_check failed',
  });

  const rows = buildSystemProbeHealthMatrix(failedEpisode);
  assert.equal(rows.length, 4);
  const diskRow = rows.find((r) => r.componentId === 'DISK-01');
  const memRow = rows.find((r) => r.componentId === 'MEMORY-01');
  assert.equal(diskRow?.activeLeaseLevel, 'L0');
  assert.equal(diskRow?.consecutiveRestorePasses, 3);
  assert.equal(diskRow?.auditTrendHistory.length, 10);
  assert.equal(diskRow?.auditTrendHistory[9].healthScore, 100);

  assert.equal(memRow?.activeLeaseLevel, 'L2');
  assert.equal(memRow?.consecutiveRestorePasses, 0);
  assert.equal(memRow?.agreementState, 'AGREED_FAIL');
  assert.equal(memRow?.auditTrendHistory.length, 10);
  assert.equal(memRow?.auditTrendHistory[9].healthScore, 18);

  // Simulate Router failure (1-down) followed by 3 consecutive passes (3-up)
  let routerOverride = simulateComponentProbeTick(
    undefined,
    'FAIL_BOTH',
    '2026-11-04T17:31:00Z'
  );
  assert.equal(routerOverride.failureCount, 1);
  assert.equal(routerOverride.consecutiveRestorePasses, 0);
  assert.equal(routerOverride.auditTrendHistory?.length, 10);
  assert.equal(routerOverride.auditTrendHistory?.[9].healthScore, 18);

  routerOverride = simulateComponentProbeTick(
    routerOverride,
    'PASS_BOTH',
    '2026-11-04T17:31:05Z'
  );
  assert.equal(routerOverride.consecutiveRestorePasses, 1);
  assert.equal(routerOverride.auditTrendHistory?.[9].healthScore, 54);

  routerOverride = simulateComponentProbeTick(
    routerOverride,
    'PASS_BOTH',
    '2026-11-04T17:31:10Z'
  );
  assert.equal(routerOverride.consecutiveRestorePasses, 2);
  assert.equal(routerOverride.auditTrendHistory?.[9].healthScore, 78);

  routerOverride = simulateComponentProbeTick(
    routerOverride,
    'PASS_BOTH',
    '2026-11-04T17:31:15Z'
  );
  assert.equal(routerOverride.consecutiveRestorePasses, 3);
  assert.equal(routerOverride.auditTrendHistory?.[9].healthScore, 100);
});

test('Phase 0 Implementation: serializeDofLevelStateFile and buildOnboardingRuleZeroBlock produce deterministic state file and Rule Zero header', () => {
  const init = createInitialDofEpisodeState();
  const failed = evaluateProbeTransition(init, {
    componentId: 'MEMORY-01',
    methodAStatus: 'FAIL',
    methodADetail: 'WAL CRC mismatch',
    methodBStatus: 'FAIL',
    methodBDetail: 'PRAGMA integrity_check failed',
  });
  const matrix = buildSystemProbeHealthMatrix(failed);
  const stateFile = serializeDofLevelStateFile(failed, matrix);

  assert.equal(stateFile.stateFilePath, '/var/run/estate/dof-level.state');
  assert.equal(stateFile.activeLevel, 'L2');
  assert.equal(stateFile.noGrandfatheringEnforced, true);
  assert.equal(stateFile.failingComponent, 'MEMORY-01');
  assert.equal(stateFile.componentPriorityDag.length, 4);

  const ruleZero = buildOnboardingRuleZeroBlock(failed);
  assert.ok(
    ruleZero.includes('An estate whose critical components are unproven grants no freedom.')
  );
  assert.ok(ruleZero.includes('Level=L2'));
  assert.ok(ruleZero.includes('repair.MEMORY-01'));
});



