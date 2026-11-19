import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createInitialIoCanonicalState,
  evaluateOmniscientMegaOracleAndCausalAdjudicator,
  evaluateSynapseEstateWideSyncAndZeroTouchOperationalization,
  evaluateAndTrainRealtimeActivity,
  startEstateSession,
  triageWorkGraphCluster,
  triageAllUnownedWorkGraphClusters,
} from './ioCanonicalEngine';

test('15-Pack Registry includes canonical PACK-15 io-engine with deterministic SHA-256 hashes and 8 owned domains', () => {
  const state = createInitialIoCanonicalState('2026-11-12T08:00:00.000Z');
  assert.equal(state.packs.length, 15);
  assert.equal(state.domains.length, 8);

  const pack15 = state.packs.find((p) => p.packId === 'PACK-15');
  assert.ok(pack15);
  assert.equal(pack15.slug, 'io-engine');
  assert.equal(pack15.canonicalPath, 'packages/io-engine/index.ts');
  assert.equal(pack15.sha256Hash.length, 64);

  // Every domain has a persistent real-name steward and accountable human principal
  for (const dom of state.domains) {
    assert.ok(dom.stewardRealName.length > 5);
    assert.match(dom.accountableHuman, /Chidi Onyema/);
  }
});

test('ORACLE-00 (evaluateOmniscientMegaOracleAndCausalAdjudicator) deduplicates 78 branch clones and blocks duplicate IO rebuilds', () => {
  const state = createInitialIoCanonicalState('2026-11-12T08:00:00.000Z');

  // 1. Canonical usage inside PACK-15 passes Ring-0 invariants
  const passVerdict = evaluateOmniscientMegaOracleAndCausalAdjudicator(state, {
    sessionId: 'ses-aurelius-io-01',
    actorDid: 'did:estate:principal:aurelius-marcus',
    targetLayer: 'packages/io-engine/index.ts',
    sporeBytesObserved: 1461,
  });
  assert.equal(passVerdict.verdict, 'ADJUDICATED_CANONICAL_PROCEED');
  assert.equal(passVerdict.ring0InvariantsPassed, true);
  assert.equal(passVerdict.deduplicatedBranchClones, 78);

  // 2. Attempting to rebuild a standalone mega-oracle outside PACK-15 is deterministically halted
  const duplicateVerdict = evaluateOmniscientMegaOracleAndCausalAdjudicator(state, {
    sessionId: 'ses-aurelius-io-01',
    actorDid: 'did:estate:principal:aurelius-marcus',
    targetLayer: 'src/scratch/new-mega-oracle-prototype.ts',
    proposedSymbolOrFile: 'mega-oracle',
    sporeBytesObserved: 1461,
  });
  assert.equal(duplicateVerdict.verdict, 'HALT_DUPLICATE_REBUILD_PREVENTED');
  assert.equal(duplicateVerdict.ring0InvariantsPassed, false);
  assert.equal(duplicateVerdict.canonicalPackMatch?.packId, 'PACK-15');
});

test('SYNAPSE-00 (evaluateSynapseEstateWideSyncAndZeroTouchOperationalization) flags 5.5KB host spore overflow and transitions to ZERO_TOUCH_SYNC_READY once triaged', () => {
  const state = createInitialIoCanonicalState('2026-11-12T08:00:00.000Z');

  // Initially 3 unowned clusters (32 stashes + 3 dist bundles + 19 previews = 54 artifacts) + 5632B host spore
  const preTriage = evaluateSynapseEstateWideSyncAndZeroTouchOperationalization(state, {
    sessionId: 'ses-aurelius-io-01',
    actorDid: 'did:estate:principal:aurelius-marcus',
    localHostSporeBytes: 5632,
    canonicalSporeBytes: 1461,
    argonBackupSha: 'b31e032',
    idpBackupSha: 'd4b1349ce',
    cloudPreviewAppletId: 'fe43cf69-d529-4d49-ad17-e2d3a79ce7eb',
  });
  assert.equal(preTriage.syncVerdict, 'SPORE_CAP_OR_UNOWNED_DRIFT_DETECTED');
  assert.equal(preTriage.hostSporeOverflowDetected, true);
  assert.equal(preTriage.unownedClusterCount, 3);
  assert.equal(preTriage.unownedArtifactTotal, 54);

  // Triage all unowned clusters with forced write-back
  const batch = triageAllUnownedWorkGraphClusters(state, 'ses-aurelius-io-01');
  assert.equal(batch.triagedCount, 3);
  assert.equal(batch.remainingUnownedClusters, 0);
  assert.equal(batch.remainingUnownedArtifacts, 0);

  const postTriage = evaluateSynapseEstateWideSyncAndZeroTouchOperationalization(state, {
    sessionId: 'ses-aurelius-io-01',
    actorDid: 'did:estate:principal:aurelius-marcus',
    localHostSporeBytes: 1461,
    canonicalSporeBytes: 1461,
    argonBackupSha: 'b31e032',
    idpBackupSha: 'd4b1349ce',
    cloudPreviewAppletId: 'fe43cf69-d529-4d49-ad17-e2d3a79ce7eb',
  });
  assert.equal(postTriage.syncVerdict, 'ZERO_TOUCH_SYNC_READY');
  assert.equal(postTriage.unownedArtifactTotal, 0);
});

test('AGENTS.md Line-1 estate-session & Forced Real-Time Eval + Training rejects anonymous/sessionless commits and crystallizes DPO + Antibody tuples', () => {
  const state = createInitialIoCanonicalState('2026-11-12T08:00:00.000Z');
  const initialTuples = state.trainingTuples.length;

  // 1. Anonymous / sessionless commit without write-back is blocked and converted into a DPO_REJECTION_PAIR
  const blocked = evaluateAndTrainRealtimeActivity(state, {
    sessionId: null,
    actorDid: 'anonymous-ephemeral-agent',
    domainId: 'DOM-IO-ENGINE',
    packId: 'PACK-15',
    actionType: 'UNOWNED_COMMIT_ATTEMPT',
    summary: 'Attempted to park uncommitted work in stash without estate-session or real-name owner',
    evidenceVerified: false,
    writeBackArtifactRef: null,
  });

  assert.equal(blocked.allowed, false);
  assert.equal(blocked.evalReceipt.verdict, 'BLOCKED_MANDATORY_CORRECTION');
  assert.equal(blocked.evalReceipt.gates.identityRealNameVerified, false);
  assert.equal(blocked.evalReceipt.gates.sessionLine1Bound, false);
  assert.equal(blocked.evalReceipt.gates.forcedWriteBackSealed, false);
  assert.equal(blocked.trainingTuple.datasetKind, 'DPO_REJECTION_PAIR');
  assert.equal(blocked.trainingTuple.rewardScalar, -1.0);
  assert.ok(blocked.trainingTuple.synthesizedAntibodyId?.startsWith('AB-RT-'));
  assert.equal(state.trainingTuples.length, initialTuples + 1);

  // 2. Starting a real-name estate-session and triaging a cluster succeeds with 100/100 score + SFT_GOLD_TRAJECTORY
  const started = startEstateSession(state, {
    actorDid: 'did:estate:steward:cassian-vance',
    domainId: 'DOM-EVAL-TRAINING',
    packId: 'PACK-14',
  });
  assert.equal(started.ok, true);
  assert.ok(started.session?.sessionId);
  assert.equal(started.evalReceipt?.overallScore, 100);
  assert.equal(started.trainingTuple?.datasetKind, 'SFT_GOLD_TRAJECTORY');

  const triaged = triageWorkGraphCluster(state, {
    nodeId: 'WG-STASHES-32',
    sessionId: started.session!.sessionId,
    ownerDid: 'did:estate:steward:helena-solis',
    boundPackId: 'PACK-09',
    disposition: 'SUPERSEDED_CLOSED',
  });
  assert.equal(triaged.ok, true);
  assert.equal(triaged.evalReceipt.overallScore, 100);
  assert.equal(triaged.node?.ownerRealName, 'Helena Solis (Greenlane & Git Steward)');
});
