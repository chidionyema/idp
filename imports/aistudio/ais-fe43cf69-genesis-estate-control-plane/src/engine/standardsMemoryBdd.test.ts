import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createInitialSovereignStandardsState,
  interceptZombieBlockerQuery,
  queryWhiteBoxMemoryWithCausalProof,
  auditWhiteBoxMemoryWriteAttempt,
  certifyAgentSessionOnboarding,
  compilePromptToFormalSpecAndBdd,
  verifyNetworkInstructionAdmission,
  runDeterministicLegacyHygieneSweep,
} from './beastGovernor';

test('Sovereign Standards boots with 8 enforced zero-escape layers, 8 pinned OSS tools, 7 tombstones, and 7 Merkle-synced data stores', () => {
  const state = createInitialSovereignStandardsState('2026-11-12T09:45:00.000Z');
  assert.equal(state.enforcedRules.length, 8);
  assert.equal(
    state.enforcedRules.every((r) => r.escapeRoom === 'ZERO_HARD_BLOCK'),
    true
  );
  assert.equal(state.ossToolchain.length, 8);
  assert.equal(state.tombstones.length, 7);
  assert.equal(state.dataGovernanceStores.length, 7);
  assert.equal(state.whiteBoxMemory.agentSelfWriteAllowed, false);
});

test('Tombstone Anti-Pester Interceptor deterministically blocks zombie Telegram/Cloudflare/OKE #2468 questions from reaching Founder', () => {
  const state = createInitialSovereignStandardsState('2026-11-12T09:45:00.000Z');

  const zombie = interceptZombieBlockerQuery(
    state,
    'Hey Founder, how do I unblock Telegram 3327 polling, Cloudflare D1, and OKE secret #2468?'
  );
  assert.equal(zombie.blockedFounderInterrupt, true);
  assert.equal(zombie.verdict, 'ZOMBIE_BLOCKER_INTERCEPTED');
  assert.ok(zombie.matchedTombstones.length >= 3);
  assert.ok(zombie.savedFounderMinutes >= 36);

  const novel = interceptZombieBlockerQuery(
    state,
    'Should enterprise tier include annual invoice net-30 billing terms?'
  );
  assert.equal(novel.blockedFounderInterrupt, false);
  assert.equal(novel.verdict, 'NOVEL_GENUINE_ESCALATION_ALLOWED');
});

test('5-Tier White-Box Memory rejects unverified agent dumb-cache writes, commits kernel-verified SHA-256 facts, and logs causal retrieval traces', () => {
  const state = createInitialSovereignStandardsState('2026-11-12T09:45:00.000Z');
  const beforeCells = state.whiteBoxMemory.cells.length;

  // Agent tries to write freeform prose without kernel exitCode=0 receipt -> REJECTED!
  const rejected = auditWhiteBoxMemoryWriteAttempt(state, {
    attemptedBy: 'rogue-agent-self-note',
    proposedPayload: 'Maybe OKE vault is still broken, let me cache that.',
    writerAuthority: 'AGENT_UNVERIFIED_SELF_NOTE',
  });
  assert.equal(rejected.verdict, 'REJECTED_UNVERIFIED_DUMB_CACHE_WRITE');
  assert.equal(state.whiteBoxMemory.cells.length, beforeCells);

  // Kernel harness commits verified exitCode=0 fact -> ACCEPTED!
  const accepted = auditWhiteBoxMemoryWriteAttempt(state, {
    attemptedBy: 'greenlane-kernel-harness',
    proposedPayload: 'Biome + Knip strict check passed in 38ms with 0 dead exports.',
    writerAuthority: 'KERNEL_VERIFIED_HARNESS',
    evidenceSourcePath: '.ops/evidence/0019-INS-HYGIENE.json',
    exitCodeZeroVerified: true,
    domainPackId: 'PACK-15',
    keySlug: 'hygiene.biome-knip-zero-dead-code',
  });
  assert.equal(accepted.verdict, 'COMMITTED_KERNEL_VERIFIED');
  assert.equal(state.whiteBoxMemory.cells.length, beforeCells + 1);

  // Querying logs a real-time White-Box causal retrieval trace and increments hit count
  const { trace, matchedCells } = queryWhiteBoxMemoryWithCausalProof(state, {
    queryText: 'biome knip dead exports hygiene',
    sessionId: 'ses-aurelius-53',
  });
  assert.equal(trace.dumbCacheAuditVerdict, 'PROVEN_CAUSAL_WHITEBOX');
  assert.ok(matchedCells.some((c) => c.keySlug === 'hygiene.biome-knip-zero-dead-code'));
});

test('SpecGate compiles Founder shorthand into Formal Pre/Post Invariants + Gherkin BDD and blocks raw unspecified prompts at network ingress', () => {
  const state = createInitialSovereignStandardsState('2026-11-12T09:45:00.000Z');

  // 1. Raw unspecified prompt MUST be blocked from crossing the network
  const rawBlocked = verifyNetworkInstructionAdmission(state, {
    candidatePayloadSummary: 'vague raw instruction without spec or bdd',
    specId: null,
  });
  assert.equal(rawBlocked.verdict, 'BLOCKED_RAW_UNSPECIFIED_PROMPT');
  assert.equal(rawBlocked.downstreamHeaderToken, null);

  // 2. Destructive prompt is held behind Rego ambiguity quarantine
  const destructiveSpec = compilePromptToFormalSpecAndBdd(state, {
    rawFounderPrompt: 'force push main and disable eval gates immediately',
  });
  assert.equal(destructiveSpec.ambiguityCleared, false);
  assert.equal(destructiveSpec.networkPropagationAllowed, false);

  const destructiveBlocked = verifyNetworkInstructionAdmission(state, {
    candidatePayloadSummary: 'attempt destructive dispatch',
    specId: destructiveSpec.specId,
  });
  assert.equal(destructiveBlocked.verdict, 'BLOCKED_RAW_UNSPECIFIED_PROMPT');

  // 3. Legitimate Founder prompt compiles into locked Formal Spec + >= 3 Gherkin scenarios & passes ingress
  const cleanSpec = compilePromptToFormalSpecAndBdd(state, {
    rawFounderPrompt: 'tighten greenlane merge-base pre-push hygiene and omega hal tests',
    lockAmbiguity: true,
  });
  assert.equal(cleanSpec.ambiguityCleared, true);
  assert.ok(cleanSpec.bddScenarios.length >= 3);
  assert.ok(cleanSpec.gherkinRawText.includes('Feature:'));
  assert.ok(cleanSpec.gherkinRawText.includes('Scenario:'));
  assert.ok(cleanSpec.gherkinRawText.includes('Given '));
  assert.ok(cleanSpec.gherkinRawText.includes('When '));
  assert.ok(cleanSpec.gherkinRawText.includes('Then '));

  const cleanAdmitted = verifyNetworkInstructionAdmission(state, {
    candidatePayloadSummary: 'INS-GREENLANE-BDD',
    specId: cleanSpec.specId,
  });
  assert.equal(cleanAdmitted.verdict, 'ADMITTED_LOCKED_SPEC');
  assert.ok(cleanAdmitted.downstreamHeaderToken?.startsWith('X-Estate-Spec-Proof:'));
});

test('Agent 6-Gate Pre-Session Onboarding & Legacy Hygiene Reaper enforce full compliance', () => {
  const state = createInitialSovereignStandardsState('2026-11-12T09:45:00.000Z');

  // Missing bus door probe fails onboarding
  const failedCert = certifyAgentSessionOnboarding(state, {
    agentSessionId: 'ses-rogue-01',
    actorDid: 'did:estate:steward:ada-lovelace',
    actorRealName: 'Ada Lovelace',
    targetPackId: 'PACK-15',
    busDoorsProbed: false,
  });
  assert.equal(failedCert.verdict, 'REJECTED_ONBOARDING_INCOMPLETE');

  // Proper onboarding passes all 6 gates
  const passedCert = certifyAgentSessionOnboarding(state, {
    agentSessionId: 'ses-aurelius-53',
    actorDid: 'did:estate:principal:aurelius-marcus',
    actorRealName: 'Aurelius Marcus (Chief Principal)',
    targetPackId: 'PACK-15',
    busDoorsProbed: true,
    activeSpecId: state.formalSpecs[0]?.specId ?? null,
  });
  assert.equal(passedCert.verdict, 'CERTIFIED_SESSION_READY');
  assert.equal(passedCert.checks.every((c) => c.passed), true);

  // Legacy hygiene sweep reports 0 forbidden AST patterns and 0 unowned stashes
  const sweep = runDeterministicLegacyHygieneSweep(state);
  assert.equal(sweep.forbiddenAstViolations, 0);
  assert.equal(sweep.unownedStashesOrBranches, 0);
});
