import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createBootstrapProtocols,
  evaluateInstructionThroughProtocolGate,
  ratifyNewGenesisProtocol,
  verifyProtocolMathematicalStandard,
} from './protocolEngine';
import { buildArgoSyncLaneState } from './argoSyncEngine';
import {
  createInitialMemoryNodes,
  createInitialGenesisAgents,
  createInitialThreads,
  executeContextRotPurgeAndReanchor,
  mintVerificationBlock,
} from './memoryEngine';
import { SOVEREIGN_MODULES } from '../data/frontierResearch';

import {
  createInitialSovereignTreasuryState,
  evaluateModelProviderForRota,
  evaluateTokenEfficiencyAndOverzealousGaps,
  executeAutonomousKeepAliveSweep,
  executeCommercialConversionSprint,
  executeMultiHomeCanaryProbe,
} from './estateTreasuryEngine';
import {
  createInitialOneBrainFederationState,
  applyFounderSteeringDirective,
  castOneBrainCouncilVote,
  toggleZeroCreditWebLifeboatMode,
  registerOrHeartbeatSurface,
} from './oneBrainEngine';
import {
  evaluateGitBranchParity,
  evaluateBackgroundPollSyncDecision,
} from './gitAutoSyncEngine';
import {
  createInitialSurvivalAndHarvesterState,
  triggerHomeSurvivalAlarmAndEvacuate,
  restoreHomeNominalPower,
  harvestAndMapFailureMode,
  advanceProactiveExpansionTrack,
  evaluateWorkflowPreFlightSurface,
} from './survivalHarvesterEngine';


test('bootstrap protocol library covers all 3 domains with 100% mathematical verification including GEN-NET-003, GEN-DIP-003, GEN-SCI-003, GEN-NET-004, GEN-NET-005, GEN-NET-006, and GEN-SCI-004', () => {
  const protocols = createBootstrapProtocols();
  assert.equal(protocols.length, 13);
  assert.ok(protocols.some((p) => p.id === 'GEN-NET-003'));
  assert.ok(protocols.some((p) => p.id === 'GEN-DIP-003'));
  assert.ok(protocols.some((p) => p.id === 'GEN-SCI-003'));
  assert.ok(protocols.some((p) => p.id === 'GEN-NET-004'));
  assert.ok(protocols.some((p) => p.id === 'GEN-NET-005'));
  assert.ok(protocols.some((p) => p.id === 'GEN-NET-006'));
  assert.ok(protocols.some((p) => p.id === 'GEN-SCI-004'));

  const categories = new Set(protocols.map((p) => p.category));
  assert.equal(categories.has('diplomatic_governance'), true);
  assert.equal(categories.has('scientific_experimental'), true);
  assert.equal(categories.has('computing_network'), true);

  for (const proto of protocols) {
    assert.equal(proto.mathematicalGuarantees.completenessScorePct, 100);
    assert.equal(proto.mathematicalGuarantees.deadlockFreeVerified, true);
    assert.equal(proto.agentEndorsements.length, 3);
    assert.equal(proto.specHash.length, 64);
  }
});

test('Asymmetric One-Brain Federation (GEN-NET-006) synchronizes polyglot AGENTS.md, Founder steering overrides, Council quorum votes, and Zero-Credit Web/App Lifeboats', () => {
  const initialBrain = createInitialOneBrainFederationState();
  assert.equal(initialBrain.federationEpochId, 'GENESIS_SOVEREIGN_V6');
  assert.equal(initialBrain.surfaces.length, 8);
  assert.ok(initialBrain.polyglotAgentMdContent.includes('GEN-NET-006'));
  assert.ok(initialBrain.universalCapsuleText.includes('[GENESIS-CAPSULE-v6'));

  // 1. Founder steering override aligns all surfaces to the new canonical revision hash
  const steeredBrain = applyFounderSteeringDirective(
    initialBrain,
    'Lock Direct MiniMax-M2.7 on Otto first and keep DeepSeek/Kimi Web lifeboats ready.',
    'ALL_SURFACES',
    '2026-11-03T17:40:00.000Z'
  );
  assert.notEqual(steeredBrain.canonicalRevisionHash, initialBrain.canonicalRevisionHash);
  assert.equal(
    steeredBrain.surfaces.every(
      (s) => s.SyncedRevisionHash === steeredBrain.canonicalRevisionHash.slice(0, 12)
    ),
    true
  );

  // 2. Cast Council Vote from Claude Code Desktop
  const votedBrain = castOneBrainCouncilVote(
    steeredBrain,
    {
      motionId: 'MOTION-104',
      surfaceId: 'surf-claude-code-desktop',
      decision: 'APPROVE',
      rationale: 'Polyglot CLAUDE.md + AGENTS.md verified.',
    },
    '2026-11-03T17:41:00.000Z'
  );
  assert.equal(votedBrain.councilMotions[0].ballots.length, 5);
  assert.equal(votedBrain.councilMotions[0].status, 'RATIFIED_BY_QUORUM');

  // 3. Activate Zero-Credit Web/App Lifeboat Mode (DeepSeek Web / Kimi Web / Grok / Meta Muse)
  const lifeboatBrain = toggleZeroCreditWebLifeboatMode(
    votedBrain,
    true,
    'surf-deepseek-web-lifeboat',
    '2026-11-03T17:42:00.000Z'
  );
  assert.equal(lifeboatBrain.zeroCreditLifeboatModeActive, true);
  assert.equal(lifeboatBrain.activeLifeboatPrimarySurfaceId, 'surf-deepseek-web-lifeboat');

  // 4. Plug in a brand new web model surface (e.g. Meta Muse / Grok Bot)
  const expandedBrain = registerOrHeartbeatSurface(
    lifeboatBrain,
    {
      surfaceName: 'Meta Muse Live Web Agent',
      modelBackbone: 'Meta Muse Free Web',
      category: 'web_zero_credit_lifeboat',
      transport: 'BROWSER_USERSCRIPT_SIDECAR',
      creditMode: 'ZERO_API_CREDIT_FREE_WEB',
    },
    '2026-11-03T17:43:00.000Z'
  );
  assert.equal(expandedBrain.surfaces.length, 9);
});

test('Sovereign Estate Treasury enforces £200/mo 3-month standing order, Core/Backup model rota yield gate, Concierge+Otto keep-alive, and post-March-2027 commercial independence', () => {
  const treasury = createInitialSovereignTreasuryState();

  // 1. £200 GBP/mo standing order from 2 Dec 2026 for 3 months (£600 seed), sunsetting 2 Mar 2027
  assert.equal(treasury.standingOrderAmountGbp, 200);
  assert.equal(treasury.standingOrderStartDateIso, '2026-12-02');
  assert.equal(treasury.standingOrderSunsetDateIso, '2027-03-02');
  assert.equal(treasury.virtualCards.length, 4);

  const totalCardCaps = treasury.virtualCards.reduce((s, c) => s + c.monthlyCapGbp, 0);
  assert.equal(totalCardCaps, 200);

  // Month 4 projection has £0 Founder standing order and >4.0x self-sustaining coverage
  const month4 = treasury.runwayProjections.find((r) => r.monthIndex === 4);
  assert.ok(month4);
  assert.equal(month4.founderStandingOrderGbp, 0);
  assert.ok(month4.selfSustainingCoverageRatio >= 4.0);

  // 2. Core Permanent models (Google Gemini/Antigravity, DeepSeek, MiniMax-M2.7 Subscription) vs Backup Elastic (Z.ai, Claude, Codex/ChatGPT, Kimi)
  const coreModels = treasury.modelRota.filter((m) => m.lane === 'core_permanent');
  const backupModels = treasury.modelRota.filter((m) => m.lane === 'backup_elastic');
  assert.equal(coreModels.length, 3);
  assert.equal(backupModels.length, 4);

  // Evaluate a high-yield model -> admitted
  const highYieldEval = evaluateModelProviderForRota({
    providerName: 'Qwen-3-Max',
    modelFamily: 'Qwen-3-235B',
    lane: 'backup_elastic',
    costPerMillionTokensGbp: 0.30,
    verifiedAccuracyPct: 97.1,
    p95LatencyMs: 320,
    monthlyBudgetAllocationGbp: 4,
  });
  assert.equal(highYieldEval.admitted, true);
  assert.ok(highYieldEval.yieldMultiplier >= 3.0);

  // Evaluate an overpriced, low-accuracy model -> rejected
  const lowYieldEval = evaluateModelProviderForRota({
    providerName: 'Unproven-Legacy-LLM',
    modelFamily: 'Legacy-70B',
    lane: 'candidate_trial',
    costPerMillionTokensGbp: 12.0,
    verifiedAccuracyPct: 86.0,
    p95LatencyMs: 1400,
    monthlyBudgetAllocationGbp: 10,
  });
  assert.equal(lowYieldEval.admitted, false);
  assert.equal(lowYieldEval.rotaStatus, 'SUSPENDED_LOW_YIELD');

  // 3. Concierge + Otto autonomous keep-alive sweep renews due obligations
  const sweepRes = executeAutonomousKeepAliveSweep(treasury, '2026-12-03T10:00:00.000Z');
  assert.ok(sweepRes.renewedCount >= 2);
  assert.equal(
    sweepRes.updatedState.obligations.every((o) => o.status === 'AUTO_RENEWED_VERIFIED'),
    true
  );

  // 4. Commercial conversion sprint increases recurring B2B MRR under Anti-IDP guardrails
  const initialMrr = treasury.commercialStreams.reduce(
    (s, c) => s + c.monthlyRecurringRevenueGbp,
    0
  );
  const sprintRes = executeCommercialConversionSprint(
    sweepRes.updatedState,
    'rev-sovereign-memory',
    '2026-12-04T12:00:00.000Z'
  );
  assert.equal(sprintRes.newTotalMrrGbp, initialMrr + 95);

  // 5. Multi-Home Execution Mesh & MiniMax-M2.7 Subscription Canary Probe (GEN-NET-005)
  assert.equal(sprintRes.updatedState.executionHomes.length, 4);
  assert.equal(sprintRes.updatedState.infraPlagueCures.length, 4);
  const canaryRes = executeMultiHomeCanaryProbe(
    sprintRes.updatedState,
    '2026-12-04T12:05:00.000Z'
  );
  assert.equal(
    canaryRes.updatedState.executionHomes.every(
      (h) => h.canaryPassRatePct === 100.0 && h.swapUsedMb === 0
    ),
    true
  );

  // 6. Zero-RAM LiteLLM-Parity Efficiency Optimizations & Anti-Overzealous Sacred Floor Guards
  assert.equal(treasury.routerEfficiencyOptimizations.length, 6);
  assert.equal(
    treasury.routerEfficiencyOptimizations.every((o) => o.ramOverheadMb === 0),
    true
  );
  assert.equal(treasury.overzealousTokenGapGuards.length, 5);
  assert.ok(treasury.effectiveTokenMultiplier >= 3.4);

  // Verify overzealous micro-compaction detection (shaving 300 tokens off 16,000 busts 80% KV cache -> costs 4.91x more)
  const overzealousCheck = evaluateTokenEfficiencyAndOverzealousGaps({
    prefixTokens: 16000,
    tokensShavedByMicroCompaction: 300,
    providerCacheDiscountPct: 80,
    taskType: 'structured_json_or_proof',
    proposedMaxTokens: 150,
  });
  assert.equal(overzealousCheck.overzealousCacheBustDetected, true);
  assert.ok(overzealousCheck.cachePreservationSavingsMultiplier > 4.5);
  assert.equal(overzealousCheck.overzealousTruncationRiskDetected, true);
  assert.equal(overzealousCheck.recommendedSafeMaxTokens, 512);
});

test('Argo Sync Lane computes 4-wave manifest digest, detects drift when auto-heal is off, and reconciles to Synced on push', () => {
  const protocols = createBootstrapProtocols();
  const agents = createInitialGenesisAgents();
  assert.equal(agents.length, 6); // Prime, Kernel, Sentinel, Concierge, Otto, Commercial Specialist
  const { cleanedNodes } = executeContextRotPurgeAndReanchor(createInitialMemoryNodes());
  const threads = createInitialThreads();
  const allModules = SOVEREIGN_MODULES.map((m) => m.key);
  const b1 = mintVerificationBlock(
    null,
    cleanedNodes,
    threads,
    allModules,
    'Argo Baseline',
    '2026-11-03T16:00:00.000Z'
  );

  // Initial sync state
  const syncedRelease = buildArgoSyncLaneState(
    protocols,
    agents,
    cleanedNodes,
    [b1],
    null,
    false,
    '2026-11-03T16:01:00.000Z',
    'Founder Push to Argo Sync Lane',
    1
  );

  assert.equal(syncedRelease.overallSyncStatus, 'Synced');
  assert.equal(syncedRelease.waves.length, 4);
  assert.ok(syncedRelease.yamlManifestPreview.includes('GEN-NET-003'));

  // Simulate drift by passing a stale lastSyncedFullHash with autoSelfHealEnabled = false
  const driftedRelease = buildArgoSyncLaneState(
    protocols,
    agents,
    cleanedNodes,
    [b1],
    '0000000000000000000000000000000000000000000000000000000000000000',
    false,
    '2026-11-03T16:02:00.000Z',
    'State Mutation',
    1
  );
  assert.equal(driftedRelease.overallSyncStatus, 'OutOfSync');

  // Re-push with currentFullHash -> Synced!
  const pushedRelease = buildArgoSyncLaneState(
    protocols,
    agents,
    cleanedNodes,
    [b1],
    driftedRelease.fullManifestHash,
    false,
    '2026-11-03T16:03:00.000Z',
    'Founder Push to Argo Sync Lane',
    2
  );
  assert.equal(pushedRelease.overallSyncStatus, 'Synced');
});

test('Zero-Instruction-Without-Protocol (ZIWP) gate executes covered instructions and blocks uncovered instructions until a protocol is ratified', () => {
  const protocols = createBootstrapProtocols();

  // 1. Covered instruction (matches GEN-NET-001 keywords like 'memory', 'purge', 'rot')
  const coveredRes = evaluateInstructionThroughProtocolGate(
    'Purge context rot and sync bi-temporal memory cache across nodes',
    'computing_network',
    protocols
  );
  assert.equal(coveredRes.attempt.status, 'EXECUTED_UNDER_PROTOCOL');
  assert.equal(coveredRes.attempt.boundProtocolId, 'GEN-NET-001');

  // 2. Uncovered instruction (novel estate capability gap -> MUST BE BLOCKED by ZIWP gate)
  const gapInstruction = 'Perform autonomous quantum key rotation on orbital telemetry relay';
  const blockedRes = evaluateInstructionThroughProtocolGate(
    gapInstruction,
    'computing_network',
    coveredRes.updatedProtocols
  );
  assert.equal(blockedRes.attempt.status, 'BLOCKED_PROTOCOL_PREREQUISITE_REQUIRED');
  assert.equal(blockedRes.attempt.boundProtocolId, null);
  assert.ok(blockedRes.attempt.draftedGapProposal);

  // 3. Ratify the synthesized prerequisite protocol
  const proposal = blockedRes.attempt.draftedGapProposal!;
  const newProto = ratifyNewGenesisProtocol(blockedRes.updatedProtocols, {
    id: proposal.suggestedId,
    title: proposal.suggestedTitle,
    category: proposal.category,
    eliteStandardLineage: 'IETF Quantum-Safe TLS + TLA+ Formal Specification',
    domainKeywords: proposal.detectedKeywords,
    summary: 'Formal protocol governing orbital quantum key rotation.',
    preconditions: [proposal.preconditionDraft],
    stateTransitions: ['S0_HANDSHAKE', 'S1_QKD_EXCHANGE', 'S2_ATTESTATION_COMMIT'],
    postconditions: [proposal.postconditionDraft],
    safetyInvariant: proposal.invariantDraft,
    rollbackProcedure: 'Revert to pre-shared post-quantum Kyber-1024 session key.',
  });

  const updatedLibrary = [...blockedRes.updatedProtocols, newProto];

  // 4. Re-run the previously blocked instruction -> now executes under the newly ratified protocol!
  const retryRes = evaluateInstructionThroughProtocolGate(
    gapInstruction,
    'computing_network',
    updatedLibrary
  );
  assert.equal(retryRes.attempt.status, 'EXECUTED_UNDER_PROTOCOL');
  assert.equal(retryRes.attempt.boundProtocolId, newProto.id);
});

test('verifyProtocolMathematicalStandard rejects incomplete specifications', () => {
  const check = verifyProtocolMathematicalStandard({
    id: 'GEN-NET-999',
    title: 'Incomplete Draft',
    category: 'computing_network',
    preconditions: [],
    stateTransitions: ['ONLY_ONE_STATE'],
    postconditions: ['Valid postcondition'],
    safetyInvariant: '',
    rollbackProcedure: 'Revert state immediately',
  });
  assert.equal(check.valid, false);
  assert.ok(check.errors.length >= 3);
});

test('evaluateGitBranchParity verifies 4-way SHA lockstep across main, genesis-live, argon-sync, and argon-private remote', () => {
  const sha = '46c6ff8e92456f142f750d882cb163ff763de70b';
  const locked = evaluateGitBranchParity({
    headSha: sha,
    mainSha: sha,
    genesisLiveSha: sha,
    argonSyncSha: sha,
    argonPrivateRemoteSha: sha,
    postCommitHookInstalled: true,
    autoSyncDaemonActive: true,
    workingTreeClean: true,
    lastCommitSubject: 'feat(auto-sync): zero-touch Argo Private Repo sync',
    lastCommitIso: '2026-11-03T18:00:00.000Z',
    lastAutoSyncIso: '2026-11-03T18:00:00.000Z',
  });
  assert.equal(locked.allBranchesIdentical, true);
  assert.equal(locked.remoteMirrorAligned, true);
  assert.equal(locked.postCommitHookInstalled, true);
  assert.equal(locked.headShortSha, '46c6ff8');

  const drifted = evaluateGitBranchParity({
    headSha: sha,
    mainSha: sha,
    genesisLiveSha: sha,
    argonSyncSha: '0000000000000000000000000000000000000000',
    argonPrivateRemoteSha: sha,
    postCommitHookInstalled: true,
    autoSyncDaemonActive: true,
    workingTreeClean: true,
    lastCommitSubject: 'drift check',
    lastCommitIso: '2026-11-03T18:00:00.000Z',
    lastAutoSyncIso: '2026-11-03T18:00:00.000Z',
  });
  assert.equal(drifted.allBranchesIdentical, false);
});

test('Multi-Home Survival Watchtower & Triad Failure-Mode Harvester (GEN-SCI-004) executes MacBook low-battery preemptive evacuation, Triad synthesis, and upfront pre-flight orchestration', () => {
  const initial = createInitialSurvivalAndHarvesterState();
  assert.equal(initial.boundProtocolId, 'GEN-SCI-004');
  assert.equal(initial.homes.length, 5);
  assert.equal(initial.failureModes.length, 6);
  assert.equal(initial.preFlightAssessment.readinessConfidencePct, 100);
  assert.equal(initial.preFlightAssessment.orchestrationVerdict, 'CONFIDENT_TO_ORCHESTRATE');

  // 1. Simulate MacBook Pro battery drop to 14% unplugged -> triggers Founder Klaxon & preemptive evacuation
  const evacuated = triggerHomeSurvivalAlarmAndEvacuate(
    initial,
    {
      sourceHomeId: 'home-macbook-pro',
      triggerType: 'MACBOOK_LOW_BATTERY_CRITICAL',
      simulatedBatteryPct: 14,
      gitHeadShortSha: '46bc4c2',
    },
    '2026-11-03T18:20:00.000Z'
  );

  const macAfterEvac = evacuated.homes.find((h) => h.homeId === 'home-macbook-pro')!;
  const cloudAfterEvac = evacuated.homes.find((h) => h.homeId === 'home-aistudio-cloudrun')!;
  assert.equal(macAfterEvac.status, 'PREEMPTIVE_EVACUATION_ACTIVE');
  assert.equal(macAfterEvac.batteryPct, 14);
  assert.equal(macAfterEvac.uncommittedGitBytes, 0);
  assert.equal(macAfterEvac.activeLeaseCount, 0);
  assert.equal(cloudAfterEvac.status, 'HOT_TAKEOVER_ACTIVE');
  assert.equal(evacuated.activeAlarms.length, 1);
  assert.ok(evacuated.activeAlarms[0].founderAlertChannels.macOsAudibleCommand.includes('osascript'));

  // 2. Restore AC MagSafe power -> resolves alarm with 0 data loss
  const restored = restoreHomeNominalPower(
    evacuated,
    'home-macbook-pro',
    '2026-11-03T18:22:00.000Z'
  );
  const macRestored = restored.homes.find((h) => h.homeId === 'home-macbook-pro')!;
  assert.equal(macRestored.status, 'HEALTHY_PRIMARY');
  assert.equal(macRestored.batteryPct, 96);
  assert.equal(restored.activeAlarms[0].status, 'RESOLVED_WITH_ZERO_DATA_LOSS');

  // 3. Submit a new encountered failure mode to the MiniMax-M2.7 + DeepSeek Web + Gemini Web Triad
  const harvestRes = harvestAndMapFailureMode(
    restored,
    {
      title: 'MacBook Wi-Fi Drop During Multi-Agent Council Quorum Sync',
      category: 'model_provider_network',
      severity: 'HIGH',
      encounteredBySurface: 'Otto CLI + Codex Desktop',
      encounteredDuringWorkflow: 'Cross-Surface One-Brain Council Quorum',
      symptomOrContext: 'Local Wi-Fi interface flap during ballot submission',
    },
    '2026-11-03T18:25:00.000Z'
  );
  assert.equal(harvestRes.newRecord.id, 'FM-007');
  assert.equal(harvestRes.newRecord.importedToKnowledgebase, true);
  assert.ok(
    harvestRes.newRecord.triadSynthesis.minimaxSpecialistAnalysis.specialistName.includes('MiniMax-M2.7')
  );
  assert.ok(
    harvestRes.newRecord.triadSynthesis.deepseekWebCollaboratorAnalysis.collaboratorSurface.includes('DeepSeek')
  );
  assert.ok(
    harvestRes.newRecord.triadSynthesis.geminiWebCollaboratorAnalysis.collaboratorSurface.includes('Gemini')
  );
  assert.equal(harvestRes.updatedState.failureModes.length, 7);

  // 4. Advance R&D track rd-track-03 to STAGE_4_DEPLOYED_CONFIDENT (>= 98% confidence gate)
  const promotedRd = advanceProactiveExpansionTrack(
    harvestRes.updatedState,
    'rd-track-03',
    '2026-11-03T18:26:00.000Z'
  );
  const track3 = promotedRd.proactiveTracks.find((t) => t.trackId === 'rd-track-03')!;
  assert.equal(track3.stage, 'STAGE_4_DEPLOYED_CONFIDENT');
  assert.ok(track3.confidenceScorePct >= 98.0);

  // 5. Evaluate Upfront Workflow Pre-Flight Surface across all 7 mapped failure modes
  const preFlight = evaluateWorkflowPreFlightSurface(
    'Autonomous Multi-Repo Release',
    promotedRd.failureModes,
    '2026-11-03T18:27:00.000Z'
  );
  assert.equal(preFlight.totalSurfaceHazardsMapped, 7);
  assert.equal(preFlight.immunizedCount, 7);
  assert.equal(preFlight.readinessConfidencePct, 100);
});

test('evaluateBackgroundPollSyncDecision detects working tree changes, branch drift, new commits, and manifest drift automatically', () => {
  const sha1 = 'cdb24ed59158ddce47ac9334ed168f58190e0eb3';
  const sha2 = '999999959158ddce47ac9334ed168f58190e0eb3';
  const cleanParity = evaluateGitBranchParity({
    headSha: sha1,
    mainSha: sha1,
    genesisLiveSha: sha1,
    argonSyncSha: sha1,
    estateGenesisRouterSyncSha: sha1,
    estateWwfdAlignmentGateSha: sha1,
    argonPrivateRemoteSha: sha1,
    postCommitHookInstalled: true,
    autoSyncDaemonActive: true,
    workingTreeClean: true,
    uncommittedFileCount: 0,
    lastCommitSubject: 'clean state',
    lastCommitIso: '2026-11-04T16:35:00.000Z',
    lastAutoSyncIso: '2026-11-04T16:35:00.000Z',
  });

  // 1. No changes -> no sync needed
  const noOp = evaluateBackgroundPollSyncDecision({
    previousHeadSha: sha1,
    polledStatus: cleanParity,
    currentManifestHash: 'hash-100',
    lastSyncedManifestHash: 'hash-100',
    autoSelfHealEnabled: true,
  });
  assert.equal(noOp.shouldTriggerGitOpsSync, false);
  assert.equal(noOp.reasons.length, 0);

  // 2. Uncommitted working tree change -> triggers automatic GitOps sync
  const dirtyParity = { ...cleanParity, workingTreeClean: false, uncommittedFileCount: 2 };
  const dirtyDecision = evaluateBackgroundPollSyncDecision({
    previousHeadSha: sha1,
    polledStatus: dirtyParity,
    currentManifestHash: 'hash-100',
    lastSyncedManifestHash: 'hash-100',
    autoSelfHealEnabled: true,
  });
  assert.equal(dirtyDecision.shouldTriggerGitOpsSync, true);
  assert.ok(dirtyDecision.reasons.includes('WORKING_TREE_CHANGES_DETECTED'));

  // 3. New commit SHA detected -> triggers automatic GitOps sync
  const newCommitParity = { ...cleanParity, headSha: sha2 };
  const newCommitDecision = evaluateBackgroundPollSyncDecision({
    previousHeadSha: sha1,
    polledStatus: newCommitParity,
    currentManifestHash: 'hash-100',
    lastSyncedManifestHash: 'hash-100',
    autoSelfHealEnabled: true,
  });
  assert.equal(newCommitDecision.shouldTriggerGitOpsSync, true);
  assert.ok(newCommitDecision.reasons.includes('NEW_REPOSITORY_COMMIT_DETECTED'));

  // 4. Declarative manifest drift -> triggers automatic GitOps sync
  const manifestDriftDecision = evaluateBackgroundPollSyncDecision({
    previousHeadSha: sha1,
    polledStatus: cleanParity,
    currentManifestHash: 'hash-101',
    lastSyncedManifestHash: 'hash-100',
    autoSelfHealEnabled: true,
  });
  assert.equal(manifestDriftDecision.shouldTriggerGitOpsSync, true);
  assert.ok(manifestDriftDecision.reasons.includes('DECLARATIVE_MANIFEST_DRIFT_DETECTED'));
});



