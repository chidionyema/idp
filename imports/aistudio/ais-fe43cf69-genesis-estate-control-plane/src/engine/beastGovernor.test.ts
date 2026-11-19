import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createInitialBeastGovernorState,
  evaluateBeastRegoPolicy,
  updateBeastDynamicDials,
  triggerBeastDisruptiveIncident,
  resolveBeastIncident,
  runBeastDreamsCycle,
} from './beastGovernor';

test('Beast boots with 6/6 Fractal Layers proven consistent, 15/15 UI surfaces green, and zero unevaluated sessions', () => {
  const state = createInitialBeastGovernorState('2026-11-12T08:55:00.000Z');
  assert.equal(state.allLayersConsistent, true);
  assert.equal(state.fractalLayers.length, 6);
  assert.equal(state.uiSurfaceProbes.length, 15);
  assert.equal(state.organs.length, 8);
  assert.equal(
    state.uiSurfaceProbes.every((u) => u.contractStatus === 'PROVEN_GREEN'),
    true
  );
  assert.equal(
    state.monitoredSessions.every((s) => s.realtimeEvalAttached && s.status === 'EVAL_ENFORCED_LIVE'),
    true
  );
  assert.ok(state.regoConsolidationStats.convertiblePercentage > 80);
});

test('Rego policy deterministically blocks any session lacking real-time eval, and loosens only when Founder Dial explicitly permits', () => {
  const state = createInitialBeastGovernorState('2026-11-12T08:55:00.000Z');

  const blocked = evaluateBeastRegoPolicy(state.dials, {
    sessionId: 'ses-unscored-01',
    actorDid: 'did:estate:steward:ada-lovelace',
    realtimeEvalAttached: false,
    actionKind: 'SESSION_HEARTBEAT',
    collectedTests: 30,
    epistemicConfidencePct: 96,
    requiresVaultSecret: false,
    bitwardenLeaseValid: true,
    targetBranch: 'lane/test',
    sessionUsedTokens: 1200,
  });
  assert.equal(blocked.allow, false);
  assert.ok(blocked.denyReasons.some((r) => r.includes('ZERO_UNEVALUATED_SESSIONS')));

  // Founder loosens dial deliberately for sandbox experiment
  updateBeastDynamicDials(state, { requireRealtimeEvalOnEverySession: false });
  const loosened = evaluateBeastRegoPolicy(state.dials, {
    sessionId: 'ses-unscored-01',
    actorDid: 'did:estate:steward:ada-lovelace',
    realtimeEvalAttached: false,
    actionKind: 'SESSION_HEARTBEAT',
    collectedTests: 30,
    epistemicConfidencePct: 96,
    requiresVaultSecret: false,
    bitwardenLeaseValid: true,
    targetBranch: 'lane/test',
    sessionUsedTokens: 1200,
  });
  assert.equal(loosened.allow, true);
});

test('Token overflow routes to Free Lane and Wake-Up Cascade coordinates Browser, Mac Console, and Always-On Cloud', () => {
  const state = createInitialBeastGovernorState('2026-11-12T08:55:00.000Z');

  // UI surface incident wakes WebAgent Browser Symbiont
  const uiInc = triggerBeastDisruptiveIncident(state, 'UI_SURFACE_DRIFT');
  assert.equal(uiInc.diagnosisPack.selectedWakeupSurface, 'WEB_BROWSER_SYMBIONT');
  assert.equal(state.allLayersConsistent, false);

  const resolvedUi = resolveBeastIncident(state, 'AUTO_COORDINATE_FIX');
  assert.equal(resolvedUi.resolvedIncidentId, uiInc.incidentId);
  assert.equal(state.allLayersConsistent, true);

  // Mac offline incident wakes Always-On Cloud Legion
  const cloudInc = triggerBeastDisruptiveIncident(state, 'LOCAL_MAC_OFFLINE_FAILOVER');
  assert.equal(cloudInc.diagnosisPack.selectedWakeupSurface, 'CLOUD_ALWAYS_ON_LEGION');

  // Token spike triggers Free-Lane routing
  const overflow = evaluateBeastRegoPolicy(state.dials, {
    sessionId: 'ses-aurelius-io-01',
    actorDid: 'did:estate:principal:aurelius-marcus',
    realtimeEvalAttached: true,
    actionKind: 'MUTATION_DISPATCH',
    collectedTests: 30,
    epistemicConfidencePct: 96,
    requiresVaultSecret: false,
    bitwardenLeaseValid: true,
    targetBranch: 'lane/overflow',
    sessionUsedTokens: state.dials.maxSessionTokenBudget + 5000,
  });
  assert.equal(overflow.routedToFreeLane, true);
});

test('Dreams counterfactual cycle synthesizes new Pass-0 antibody on zero-cost Free Lane', () => {
  const state = createInitialBeastGovernorState('2026-11-12T08:55:00.000Z');
  const beforeCount = state.dreamCycles.length;
  const dream = runBeastDreamsCycle(
    state,
    'Bitwarden lease expiry during multi-repo Greenlane rebase'
  );
  assert.equal(state.dreamCycles.length, beforeCount + 1);
  assert.ok(dream.synthesizedAntibodyId.startsWith('AB-DREAM-'));
  assert.equal(state.allLayersConsistent, true);
});
