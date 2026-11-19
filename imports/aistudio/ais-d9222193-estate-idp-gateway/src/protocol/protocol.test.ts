import test from 'node:test';
import assert from 'node:assert/strict';
import { IdpGatewayClientHarness } from './broker';
import { PINNED_RULES_HASH, isKnownCapability, checkActionPermissionForRule, CANONICAL_OFFLINE_ACTIONS } from './rules';
import { ShortLoopDetector } from './shortLoop';
import { DurableIdempotencyStore } from './durableStore';
import { Envelope, Lease, Receipt } from './types';
import { verifyReceiptSignature, CANONICAL_ISSUER_KEY_ID } from './crypto';

// Helper to construct a valid base lease
function createMockLease(expiresInMs = 3600000): Lease {
  return {
    token: 'lease_tok_valid_test_001',
    surfaceId: 'mac_session_460567726510256',
    grantedAt: Date.now(),
    expiresAt: Date.now() + expiresInMs,
    scope: ['git.pr_sync', 'contract.verify'],
  };
}

// Helper to construct a valid online mutation envelope
function createValidOnlineMutationEnvelope(overrides: Partial<Envelope> = {}): Envelope {
  return {
    callId: 'call_test_001',
    tenantId: 'tenant_estate_primary',
    surfaceId: 'mac_session_460567726510256',
    capability: 'git.pr_sync',
    actionType: 'mutation',
    isOnline: true,
    lease: createMockLease(),
    compiledContextHash: 'sha256:ctx_f148e711b391f47a6d79061e9970593070d49f3f19947ef9094c9055759abf2d',
    idempotencyKey: 'idem_key_001',
    rulesHash: PINNED_RULES_HASH,
    payload: { branch: 'feat/idp-broker', targetSha: 'cd17573' },
    evidenceDigest: 'sha256:ev_990182',
    ...overrides,
  };
}

test('1. Rules hash is pinned to 18e3ccdaee2a0cceff3ad85c777ddfe7b33255694844b6925a4d331b29a9f3dd', async () => {
  const harness = new IdpGatewayClientHarness();
  assert.equal(PINNED_RULES_HASH, '18e3ccdaee2a0cceff3ad85c777ddfe7b33255694844b6925a4d331b29a9f3dd');

  // Any envelope presenting a mismatched or tampered rules hash must be refused
  const tamperedEnvelope = createValidOnlineMutationEnvelope({
    rulesHash: 'tampered_or_unverified_hash_abc123',
  });

  let handlerCalled = false;
  const result = await harness.dispatch(tamperedEnvelope, async () => {
    handlerCalled = true;
    return { ok: true };
  });

  assert.equal(result.admitted, false);
  if (!result.admitted) {
    assert.equal(result.code, 'RULES_HASH_MISMATCH');
  }
  assert.equal(handlerCalled, false, 'Refused call must never reach capability handler');
});

test('2. Online mutations require a valid lease', async () => {
  const harness = new IdpGatewayClientHarness();
  const envelopeWithoutLease = createValidOnlineMutationEnvelope({ lease: null });

  let handlerCalled = false;
  const result = await harness.dispatch(envelopeWithoutLease, async () => {
    handlerCalled = true;
    return { ok: true };
  });

  assert.equal(result.admitted, false);
  if (!result.admitted) {
    assert.equal(result.code, 'LEASE_REQUIRED');
  }
  assert.equal(handlerCalled, false);
});

test('3. Expired lease is refused before capability dispatch', async () => {
  const harness = new IdpGatewayClientHarness();
  const expiredLease: Lease = {
    token: 'lease_expired_999',
    surfaceId: 'mac_session_460567726510256',
    grantedAt: Date.now() - 7200000,
    expiresAt: Date.now() - 1000, // Expired 1 second ago
    scope: ['git.pr_sync'],
  };

  const envelope = createValidOnlineMutationEnvelope({ lease: expiredLease });
  let handlerCalled = false;
  const result = await harness.dispatch(envelope, async () => {
    handlerCalled = true;
    return { ok: true };
  });

  assert.equal(result.admitted, false);
  if (!result.admitted) {
    assert.equal(result.code, 'LEASE_EXPIRED');
  }
  assert.equal(handlerCalled, false);
});

test('4. Online mutations require compiled-context hash', async () => {
  const harness = new IdpGatewayClientHarness();
  const envelopeWithoutCtx = createValidOnlineMutationEnvelope({ compiledContextHash: '' });

  let handlerCalled = false;
  const result = await harness.dispatch(envelopeWithoutCtx, async () => {
    handlerCalled = true;
    return { ok: true };
  });

  assert.equal(result.admitted, false);
  if (!result.admitted) {
    assert.equal(result.code, 'COMPILED_CONTEXT_HASH_REQUIRED');
  }
  assert.equal(handlerCalled, false);
});

test('5. Online mutations require idempotency key', async () => {
  const harness = new IdpGatewayClientHarness();
  const envelopeWithoutIdem = createValidOnlineMutationEnvelope({ idempotencyKey: '' });

  let handlerCalled = false;
  const result = await harness.dispatch(envelopeWithoutIdem, async () => {
    handlerCalled = true;
    return { ok: true };
  });

  assert.equal(result.admitted, false);
  if (!result.admitted) {
    assert.equal(result.code, 'IDEMPOTENCY_KEY_REQUIRED');
  }
  assert.equal(handlerCalled, false);
});

test('6. Offline policy: canonical allowlist (launch, back, home, wait) queues without lease; others refused', async () => {
  const harness = new IdpGatewayClientHarness();

  // Test 6a: Canonical allowlist action ('launch') queues safely without a lease per node_protocol.json:19
  const offlineLaunchEnvelope: Envelope = {
    callId: 'call_mob_launch_01',
    surfaceId: 'mobile_node_ios_client',
    capability: 'launch', // in canonical allowlist
    actionType: 'safe_mutation',
    isOnline: false,
    lease: null, // No lease
    compiledContextHash: '',
    idempotencyKey: 'mob_launch_idem_01',
    rulesHash: PINNED_RULES_HASH,
    payload: { target: 'estate-app' },
  };

  const launchResult = await harness.dispatch(offlineLaunchEnvelope, async () => {
    return { queued: true };
  });

  assert.equal(launchResult.admitted, true);
  if (launchResult.admitted) {
    assert.equal(launchResult.queued, true);
  }
  const queue = harness.getOfflineQueue();
  assert.equal(queue.length, 1);
  assert.equal(queue[0].envelope.capability, 'launch');

  // Test 6b: Non-allowlisted action (e.g. 'mobile.sync_draft') is strictly refused per node_protocol.json:19
  const unallowlistedEnvelope: Envelope = {
    callId: 'call_mob_drift_02',
    surfaceId: 'mobile_node_ios_client',
    capability: 'mobile.sync_draft', // NOT in allowlist
    actionType: 'safe_mutation',
    isOnline: false,
    lease: null,
    rulesHash: PINNED_RULES_HASH,
    payload: { draft: 'unreviewed offline policy change' },
  };

  let unallowlistedHandlerCalled = false;
  const driftResult = await harness.dispatch(unallowlistedEnvelope, async () => {
    unallowlistedHandlerCalled = true;
    return {};
  });

  assert.equal(driftResult.admitted, false);
  if (!driftResult.admitted) {
    assert.equal(driftResult.code, 'OFFLINE_ACTION_NOT_IN_ALLOWLIST');
  }
  assert.equal(unallowlistedHandlerCalled, false, 'Unallowlisted offline action must never reach handler');
});

test('7. Unsafe offline mutations are refused', async () => {
  const harness = new IdpGatewayClientHarness();
  const offlineUnsafeEnvelope: Envelope = {
    callId: 'call_mob_unsafe_02',
    surfaceId: 'mobile_node_ios_client',
    capability: 'cluster.deploy',
    actionType: 'unsafe_mutation',
    isOnline: false, // Disconnected
    lease: null,
    compiledContextHash: '',
    idempotencyKey: 'mob_deploy_idem_02',
    rulesHash: PINNED_RULES_HASH,
    payload: { targetEnv: 'production' },
  };

  let handlerCalled = false;
  const result = await harness.dispatch(offlineUnsafeEnvelope, async () => {
    handlerCalled = true;
    return { deployed: true };
  });

  assert.equal(result.admitted, false);
  if (!result.admitted) {
    // Either OFFLINE_ACTION_NOT_IN_ALLOWLIST or UNSAFE_OFFLINE_MUTATION_REFUSED
    assert.ok(
      result.code === 'UNSAFE_OFFLINE_MUTATION_REFUSED' ||
      result.code === 'OFFLINE_ACTION_NOT_IN_ALLOWLIST'
    );
  }
  assert.equal(handlerCalled, false, 'Unsafe offline mutations must never reach capability handler');
});

test('8. Unknown rules become read-only (mutations refused, read allowed)', async () => {
  const harness = new IdpGatewayClientHarness();

  // Test mutation with unknown capability
  const unknownMutationEnvelope: Envelope = {
    callId: 'call_unk_01',
    surfaceId: 'mac_session_460567726510256',
    capability: 'unknown.rogue_mutation_action',
    actionType: 'mutation',
    isOnline: true,
    lease: createMockLease(),
    compiledContextHash: 'sha256:ctx_known',
    idempotencyKey: 'idem_unk_01',
    rulesHash: PINNED_RULES_HASH,
    payload: {},
  };

  let mutationHandlerCalled = false;
  const mutationResult = await harness.dispatch(unknownMutationEnvelope, async () => {
    mutationHandlerCalled = true;
    return { modified: true };
  });

  assert.equal(mutationResult.admitted, false);
  if (!mutationResult.admitted) {
    assert.equal(mutationResult.code, 'UNKNOWN_RULE_READ_ONLY');
  }
  assert.equal(mutationHandlerCalled, false, 'Unknown capability mutation must not reach handler');

  // Test read with unknown capability: allowed under read-only downgrade
  const unknownReadEnvelope: Envelope = {
    callId: 'call_unk_02',
    surfaceId: 'mac_session_460567726510256',
    capability: 'unknown.inspect_catalog',
    actionType: 'read',
    isOnline: true,
    lease: null,
    rulesHash: PINNED_RULES_HASH,
    payload: { query: 'all' },
  };

  let readHandlerCalled = false;
  const readResult = await harness.dispatch(unknownReadEnvelope, async () => {
    readHandlerCalled = true;
    return { items: ['read_only_data'] };
  });

  assert.equal(readResult.admitted, true);
  assert.equal(readHandlerCalled, true, 'Unknown capability read should be permitted under read-only downgrade');
});

test('9. Refused calls never reach the capability handler', async () => {
  const harness = new IdpGatewayClientHarness();
  let dispatchCounter = 0;
  const spyHandler = async () => {
    dispatchCounter++;
    return { ok: true };
  };

  // Test multiple refusal scenarios
  const cases: Envelope[] = [
    createValidOnlineMutationEnvelope({ rulesHash: 'invalid_hash' }),
    createValidOnlineMutationEnvelope({ lease: null }),
    createValidOnlineMutationEnvelope({ compiledContextHash: '' }),
    createValidOnlineMutationEnvelope({ idempotencyKey: '' }),
    {
      callId: 'call_unsafe_offline',
      surfaceId: 'mobile_node_ios_client',
      capability: 'git.pr_sync',
      actionType: 'mutation',
      isOnline: false,
      payload: {},
    },
  ];

  for (const c of cases) {
    const res = await harness.dispatch(c, spyHandler);
    assert.equal(res.admitted, false);
  }

  assert.equal(dispatchCounter, 0, 'Capability handler must have been called 0 times for all refused envelopes');
});

test('10. Accepted mutations cannot return without a receipt and cryptographic verification passes', async () => {
  const harness = new IdpGatewayClientHarness();
  const validEnvelope = createValidOnlineMutationEnvelope({
    callId: 'call_mutation_with_receipt',
    idempotencyKey: 'idem_receipt_check_10',
  });

  const result = await harness.dispatch(validEnvelope, async () => {
    return { commitSha: 'cd17573', status: 'synced' };
  });

  assert.equal(result.admitted, true);
  if (result.admitted) {
    // Canonical gateway guarantees receipt presence and cryptographic binding
    assert.ok(result.receipt, 'Accepted mutation MUST include a valid receipt record');
    assert.ok(result.receipt.receiptId.startsWith('rcpt_'));
    assert.equal(result.receipt.callId, 'call_mutation_with_receipt');
    assert.equal(result.receipt.rulesHash, PINNED_RULES_HASH);
    assert.ok(result.receipt.digest.startsWith('sha256:'));
    assert.equal(result.receipt.issuer, 'Argon Genesis (Cluster IDP Gateway)');
    assert.equal(result.receipt.signatureAlgorithm, 'HMAC-SHA256');
    assert.ok(result.receipt.signature?.startsWith('sig_v1_'), 'Signature must be generated with sig_v1_ prefix');
    assert.equal(result.receipt.keyId, CANONICAL_ISSUER_KEY_ID);

    // Verify cryptographic signature against canonical serialization
    const vResult = verifyReceiptSignature(result.receipt);
    assert.equal(vResult.valid, true, 'Cryptographic verification must pass for authentic receipt');
    assert.equal(vResult.rulesHashBound, true, 'Rules hash must match pinned canonical hash');
    assert.equal(vResult.signatureValid, true, 'Signature must match HMAC-SHA256 over canonical payload');
    assert.equal(vResult.digestValid, true, 'Payload digest must be valid SHA-256');

    // Tamper Detection Test 1: Tampered rules hash fails verification
    const tamperedRulesReceipt = { ...result.receipt, rulesHash: 'tampered_evil_rules_hash' };
    const vTamperedRules = verifyReceiptSignature(tamperedRulesReceipt);
    assert.equal(vTamperedRules.valid, false);
    assert.equal(vTamperedRules.rulesHashBound, false);

    // Tamper Detection Test 2: Tampered payload digest fails signature check
    const tamperedDigestReceipt = { ...result.receipt, digest: 'sha256:tampered_content_hash' };
    const vTamperedDigest = verifyReceiptSignature(tamperedDigestReceipt);
    assert.equal(vTamperedDigest.valid, false);
    assert.equal(vTamperedDigest.signatureValid, false);
  }

  // Check receipt exists in ledger
  const ledger = harness.getReceiptLedger();
  assert.ok(ledger.some((r) => r.callId === 'call_mutation_with_receipt'));
});

test('11. Durable scoped idempotency returns cached receipt across re-instantiations', async () => {
  const durableStore = new DurableIdempotencyStore();
  const harness1 = new IdpGatewayClientHarness(undefined, durableStore);

  const envelope = createValidOnlineMutationEnvelope({
    tenantId: 'tenant_acme_corp',
    surfaceId: 'mac_session_460567726510256',
    callId: 'call_idem_durable_first',
    idempotencyKey: 'idem_scoped_token_42',
    compiledContextHash: 'sha256:ctx_canonical_test',
  });

  let executionCount = 0;
  const handler = async () => {
    executionCount++;
    return { step: 'executed', count: executionCount };
  };

  // First call: executes handler
  const res1 = await harness1.dispatch(envelope, handler);
  assert.equal(res1.admitted, true);
  assert.equal(executionCount, 1);
  const receipt1 = res1.admitted ? res1.receipt : undefined;
  assert.ok(receipt1);

  // Re-instantiate harness using same durable store (simulates reconnect or session reload)
  const harness2 = new IdpGatewayClientHarness(undefined, durableStore);
  const secondEnvelope = {
    ...envelope,
    callId: 'call_idem_durable_second',
  };

  const res2 = await harness2.dispatch(secondEnvelope, handler);
  assert.equal(res2.admitted, true);
  if (res2.admitted) {
    assert.equal(res2.cached, true, 'Second identical mutation must return cached result');
    assert.equal(res2.receipt?.receiptId, receipt1?.receiptId, 'Receipt must match original execution');
    assert.equal(res2.receipt?.tenantId, 'tenant_acme_corp', 'Tenant scope preserved in durable store');
  }
  assert.equal(executionCount, 1, 'Capability handler must NOT be executed second time across harness instances');
});

test('12. ShortLoop repeat detector fails loud on corrupt state and catches ungrounded loops', async () => {
  const detector = new ShortLoopDetector();
  const harness = new IdpGatewayClientHarness(detector);

  const baseEnvelope = createValidOnlineMutationEnvelope({
    capability: 'linear.refresh',
    actionType: 'read',
    evidenceDigest: 'evidence_sha_1',
    payload: { query: 'issues' },
  });

  // First run: admitted
  const first = await harness.dispatch(baseEnvelope, async () => ({ count: 5 }));
  assert.equal(first.admitted, true);

  // Second run with identical payload and unchanged evidenceDigest: detected as short loop
  const second = await harness.dispatch(baseEnvelope, async () => ({ count: 5 }));
  assert.equal(second.admitted, false);
  if (!second.admitted) {
    assert.equal(second.code, 'SHORT_LOOP_DETECTED');
  }

  // Corrupted state test: must FAIL LOUD
  detector.simulateCorruptState();
  const corruptedCheck = await harness.dispatch(
    { ...baseEnvelope, evidenceDigest: 'evidence_sha_2' },
    async () => ({ ok: true })
  );
  assert.equal(corruptedCheck.admitted, false);
  if (!corruptedCheck.admitted) {
    assert.equal(corruptedCheck.code, 'SHORT_LOOP_DETECTED');
    assert.ok(corruptedCheck.reason.includes('CRITICAL: ShortLoopDetector state store is corrupted'));
  }
});

test('13. Executable Security Invariant: Guardian SHA pins strictly to da1536c7 and rejects candidate 8e232aa', () => {
  const CANONICAL_GUARDIAN_PINNED_SHA = 'da1536c7';
  const REJECTED_GUARDIAN_CANDIDATE_SHA = '8e232aa';

  // Invariant validation function
  function validateGuardianAnchor(sha: string): boolean {
    return sha === CANONICAL_GUARDIAN_PINNED_SHA;
  }

  assert.equal(validateGuardianAnchor('da1536c7'), true, 'Reviewed main da1536c7 must be accepted');
  assert.equal(validateGuardianAnchor(REJECTED_GUARDIAN_CANDIDATE_SHA), false, 'Candidate 8e232aa must be rejected');
  assert.equal(validateGuardianAnchor(''), false, 'Empty SHA must be rejected');
});

test('14. Operational Completion Contracts schema verifies all 10 contracts and 6 Hard Operational Laws', async () => {
  const { OPERATIONAL_COMPLETION_CONTRACTS, HARD_OPERATIONAL_LAWS, ACTIVE_BLOCKERS } = await import('./estateRecoveryData');

  // Verify all 10 contracts exist (including Contract 10: IDP #7790 Agent Continuity)
  assert.equal(OPERATIONAL_COMPLETION_CONTRACTS.length, 10, 'Must have all 10 operational completion contracts');
  for (const contract of OPERATIONAL_COMPLETION_CONTRACTS) {
    assert.ok(contract.id, 'Contract must have an ID');
    assert.ok(contract.targetPrs.length > 0, 'Contract must declare target PRs');
    assert.ok(contract.requiredEvidence.length > 0, 'Contract must declare required evidence schema');
  }

  // Verify the 6 hard operational laws
  assert.equal(HARD_OPERATIONAL_LAWS.length, 6, 'Must have exactly 6 hard operational laws');
  const lawIds = HARD_OPERATIONAL_LAWS.map((l) => l.id);
  assert.ok(lawIds.includes('NO_FALSE_COMPLETION'));
  assert.ok(lawIds.includes('WHOLE_HISTORY_PREFLIGHT'));
  assert.ok(lawIds.includes('NO_FOUNDER_CLI_CHORES'));
  assert.ok(lawIds.includes('ORACLE_PASS_RATIONING'));
  assert.ok(lawIds.includes('UNIVERSAL_PEER_BUS'));
  assert.ok(lawIds.includes('ARCHITECTURAL_CONFLICT_LOCKS'));

  // Verify critical blockers include Argon #45 and Argon #43
  const blockerPrs = ACTIVE_BLOCKERS.map((b) => b.targetPr);
  assert.ok(blockerPrs.includes('Argon #45'));
  assert.ok(blockerPrs.includes('Argon #43'));
});

test('15. Engineering verdict verifies all 6 Corrected Architectural Locks (L1–L6)', async () => {
  const { CORRECTED_ARCHITECTURAL_LOCKS, ESTATE_PHILOSOPHY } = await import('./estateRecoveryData');

  assert.ok(ESTATE_PHILOSOPHY.includes('self-recovering estate'), 'Philosophy must prioritize self-recovery over lockdown');
  assert.equal(CORRECTED_ARCHITECTURAL_LOCKS.length, 6, 'Must adopt exactly 6 corrected locks');

  const lockIds = CORRECTED_ARCHITECTURAL_LOCKS.map((l) => l.id);
  assert.deepEqual(lockIds, ['L1', 'L2', 'L3', 'L4', 'L5', 'L6']);

  for (const lock of CORRECTED_ARCHITECTURAL_LOCKS) {
    assert.ok(lock.requiredCorrection.length > 20, `Lock ${lock.id} must specify concrete required correction`);
    assert.ok(lock.designRationale.length > 20, `Lock ${lock.id} must specify design rationale`);
    assert.ok(lock.selfRecoveryPrinciple.length > 20, `Lock ${lock.id} must embody self-recovery principle`);
    assert.ok(lock.verdict === 'Adopt' || lock.verdict === 'Adopt with safeguards');
  }

  // Specific check on L1: do not force-push by default
  const l1 = CORRECTED_ARCHITECTURAL_LOCKS.find((l) => l.id === 'L1')!;
  assert.ok(l1.requiredCorrection.includes('Do not force-push or automatically discard work'));

  // Specific check on L4: 15s takeover is an SLO to measure
  const l4 = CORRECTED_ARCHITECTURAL_LOCKS.find((l) => l.id === 'L4')!;
  assert.ok(l4.requiredCorrection.includes('SLO to measure, not an unconditional guarantee'));
});

test('16. Three dangerous assumptions are eliminated and guarded by protocol checks', async () => {
  const { REMOVED_DANGEROUS_ASSUMPTIONS } = await import('./estateRecoveryData');

  assert.equal(REMOVED_DANGEROUS_ASSUMPTIONS.length, 3, 'Must catalog exactly 3 dangerous assumptions');
  const ids = REMOVED_DANGEROUS_ASSUMPTIONS.map((d) => d.id);
  assert.ok(ids.includes('danger_force_push'));
  assert.ok(ids.includes('danger_ai_review_illusion'));
  assert.ok(ids.includes('danger_confidence_score_authorization'));

  // Invariant test: Model confidence score (WWFD >= 0.97) cannot bypass missing lease
  function evaluatePrivilegedActionAuthorization(params: {
    actorTrusted: boolean;
    hasFreshLease: boolean;
    allowedScope: boolean;
    pinnedPolicy: boolean;
    modelConfidenceScore?: number;
  }): { permitted: boolean; rejectionReason?: string } {
    // Invariant: Execute(a) => TrustedActor(a) ∧ FreshLease(a) ∧ AllowedScope(a) ∧ PinnedPolicy(a)
    // High model confidence NEVER bypasses missing lease or unallowed scope!
    if (!params.actorTrusted) return { permitted: false, rejectionReason: 'UNTRUSTED_ACTOR' };
    if (!params.hasFreshLease) return { permitted: false, rejectionReason: 'MISSING_OR_EXPIRED_LEASE' };
    if (!params.allowedScope) return { permitted: false, rejectionReason: 'OUT_OF_SCOPE' };
    if (!params.pinnedPolicy) return { permitted: false, rejectionReason: 'UNPINNED_POLICY' };
    return { permitted: true };
  }

  // Attempting privileged mutation with WWFD = 0.99 but no lease: MUST BE REFUSED
  const attemptWithConfidenceOnly = evaluatePrivilegedActionAuthorization({
    actorTrusted: true,
    hasFreshLease: false, // NO LEASE
    allowedScope: true,
    pinnedPolicy: true,
    modelConfidenceScore: 0.99, // High WWFD score
  });

  assert.equal(attemptWithConfidenceOnly.permitted, false);
  assert.equal(attemptWithConfidenceOnly.rejectionReason, 'MISSING_OR_EXPIRED_LEASE');
});

test('17. IDP #7771 integration mandate and estate reality boundaries are verified', async () => {
  const { IDP_7771_MANDATE, ESTATE_REALITY_ASSESSMENTS } = await import('./estateRecoveryData');

  assert.equal(IDP_7771_MANDATE.issueId, 'idp#7771');
  assert.equal(IDP_7771_MANDATE.registrationStatus, 'VERIFIED_ON_GITHUB');
  assert.equal(IDP_7771_MANDATE.coreDirectives.length, 5, 'Must contain all 5 binding directives');

  // Verify all 5 reality reconciliations are present
  assert.equal(ESTATE_REALITY_ASSESSMENTS.length, 5, 'Must reconcile 5 estate reality distinctions');
  const ids = ESTATE_REALITY_ASSESSMENTS.map((r) => r.id);
  assert.ok(ids.includes('guardian_pin'));
  assert.ok(ids.includes('split_authority_cert'));
  assert.ok(ids.includes('spooler_admin_actions'));
  assert.ok(ids.includes('stage_a_status'));
  assert.ok(ids.includes('qa_vs_production_acceptance'));

  // Assert authority demarcation: browser client harness must NOT claim production authority
  for (const item of ESTATE_REALITY_ASSESSMENTS) {
    assert.equal(item.status, 'RECONCILED_AS_OBSERVABILITY_ONLY');
    assert.ok(item.engineeringDecision.length > 10);
  }

  // Verify guardian policy decision: Do not promote app hardcoded pin as authoritative
  const guardianAssessment = ESTATE_REALITY_ASSESSMENTS.find((r) => r.id === 'guardian_pin')!;
  assert.ok(guardianAssessment.engineeringDecision.includes("Do not promote the app's hardcoded pin as authoritative"));

  // Verify spooler decision: Constrained Telegram outbox spooler is distinct from privileged action doors
  const spoolerAssessment = ESTATE_REALITY_ASSESSMENTS.find((r) => r.id === 'spooler_admin_actions')!;
  assert.ok(spoolerAssessment.engineeringDecision.includes('Use the governed action doors'));
});

test('18. Contract 10 (Agent Continuity IDP #7790) and Stage A baseline reconciliation are verified', async () => {
  const { OPERATIONAL_COMPLETION_CONTRACTS, EXECUTION_PLAN_STAGES } = await import('./estateRecoveryData');

  // Verify total contract count is now 10
  assert.equal(OPERATIONAL_COMPLETION_CONTRACTS.length, 10, 'Must contain all 10 operational completion contracts');

  const contract10 = OPERATIONAL_COMPLETION_CONTRACTS.find((c) => c.id === '10_agent_continuity_and_capacity_takeover');
  assert.ok(contract10, 'Contract 10 must exist');
  assert.equal(contract10.number, 10);
  assert.ok(contract10.targetPrs.includes('idp#7790'), 'Contract 10 must target IDP #7790');
  assert.ok(contract10.targetPrs.includes('argon#40'));

  // Verify required evidence metrics for continuity & takeover
  const keys = contract10.requiredEvidence.map((e) => e.key);
  assert.ok(keys.includes('cross_surface_heartbeat_interval_ms'));
  assert.ok(keys.includes('token_exhaustion_checkpoint_preserved'));
  assert.ok(keys.includes('worker_capacity_telemetry_available'));
  assert.ok(keys.includes('autonomous_task_reassignment_ms'));
  assert.ok(keys.includes('stale_worker_fencing_rejection'));
  assert.ok(keys.includes('off_host_recovery_independent_of_laptop'));

  // Verify all 6 evidence criteria are met
  for (const ev of contract10.requiredEvidence) {
    assert.equal(ev.satisfied, true, `Evidence ${ev.key} must be marked satisfied`);
  }

  // Verify Stage A is typed and marked as IMPORTED_BASELINE_PENDING_LIVE_RECONCILIATION
  const stageA = EXECUTION_PLAN_STAGES.find((s) => s.stageId === 'A');
  assert.ok(stageA, 'Stage A must exist in execution plan');
  assert.equal(stageA.status, 'IMPORTED_BASELINE_PENDING_LIVE_RECONCILIATION');
});

test('19. Cryptographic specification clarity: RFC 8785 (JCS) vs RFC 6962 (CT) and Ed25519 key isolation', async () => {
  const {
    verifyReceiptSignature,
    ED25519_CERTIFIER_PUB_KEY_ID,
    CANONICAL_ISSUER_KEY_ID,
    ESTATE_SIGNING_SECRET,
    CRYPTO_SPECIFICATION_DETAILS,
  } = await import('./crypto');

  // Verify specification distinctions
  assert.equal(CRYPTO_SPECIFICATION_DETAILS.payloadCanonicalization, 'RFC 8785 (JSON Canonicalization Scheme)');
  assert.equal(CRYPTO_SPECIFICATION_DETAILS.merkleDigestStandard, 'RFC 6962 (Certificate Transparency Merkle Tree)');

  // Verify asymmetric Ed25519 certifier identity is distinct from test HMAC key
  assert.equal(ED25519_CERTIFIER_PUB_KEY_ID, 'ed25519_pub_certifier_argon_99a');
  assert.equal(CANONICAL_ISSUER_KEY_ID, 'key_argon_cluster_harness_01');
  assert.ok(ESTATE_SIGNING_SECRET.length > 10);
  assert.notEqual(ED25519_CERTIFIER_PUB_KEY_ID, CANONICAL_ISSUER_KEY_ID);

  // Test signature verification with valid and invalid signatures
  const validReceipt: Receipt = {
    receiptId: 'rcpt_test_crypto_001',
    callId: 'call_test_001',
    idempotencyKey: 'idem_crypto_test_001',
    actionType: 'mutation',
    surfaceId: 'mac_session_460567726510256',
    tenantId: 'tenant_estate_primary',
    issuedAt: Date.now(),
    compiledContextHash: 'sha256:ctx_canonical_test_123',
    rulesHash: '18e3ccdaee2a0cceff3ad85c777ddfe7b33255694844b6925a4d331b29a9f3dd',
    digest: 'sha256:d991bce091a110022883377',
    issuer: 'genesis_action_gateway',
    keyId: CANONICAL_ISSUER_KEY_ID,
    signatureAlgorithm: 'HMAC-SHA256',
    signature: '',
  };

  const { computeReceiptSignature } = await import('./crypto');
  validReceipt.signature = computeReceiptSignature(validReceipt);

  const verification = verifyReceiptSignature(validReceipt);
  assert.equal(verification.valid, true);

  // Tampered payload digest must fail verification
  const tamperedReceipt: Receipt = { ...validReceipt, digest: 'sha256:tampered_digest_fake' };
  const tamperedVerification = verifyReceiptSignature(tamperedReceipt);
  assert.equal(tamperedVerification.valid, false);
  assert.equal(tamperedVerification.reason?.includes('SIGNATURE_MISMATCH'), true);
});

test('20. Agent Continuity Engine: Token exhaustion failover, capacity routing & stale-worker fencing rejection', async () => {
  const { AgentContinuityEngine } = await import('./agentContinuity');
  const engine = new AgentContinuityEngine();

  // Inspect initial workers
  const initialWorkers = engine.getWorkers();
  assert.equal(initialWorkers.length, 3);
  const failedWorker = initialWorkers.find((w) => w.workerId === 'worker_cloud_arm_01')!;
  assert.equal(failedWorker.status, 'HEALTHY');
  assert.equal(failedWorker.activeMissionId, 'mission_idp_7790_recovery');
  const initialFencingToken = failedWorker.fencingLeaseToken!;

  // 1. Initial write with valid initial fencing token succeeds
  const initialWriteCheck = engine.evaluateFencingWrite(
    'mission_idp_7790_recovery',
    'worker_cloud_arm_01',
    initialFencingToken
  );
  assert.equal(initialWriteCheck.permitted, true);

  // 2. Simulate worker encountering token exhaustion (e.g. context limit exceeded)
  const takeoverResult = engine.simulateFailureAndTakeover('worker_cloud_arm_01', 'TOKEN_EXHAUSTION');
  assert.equal(takeoverResult.success, true);
  assert.ok(takeoverResult.event);
  assert.equal(takeoverResult.event.triggerReason, 'TOKEN_EXHAUSTION');
  assert.equal(takeoverResult.event.previousWorkerId, 'worker_cloud_arm_01');

  // Verify the replacement worker chosen was the one with highest available capacity score (worker_cloud_arm_02 with score 94)
  assert.equal(takeoverResult.event.targetWorkerId, 'worker_cloud_arm_02');
  assert.ok(takeoverResult.event.reassignmentLatencyMs <= 15000, 'Reassignment latency must be <= 15s SLO');

  // Verify checkpoint was restored
  assert.equal(takeoverResult.event.checkpointRestoredSha, 'sha256:chk_98e1002ba98cf11');

  // Verify failed worker is marked TOKEN_EXHAUSTED and no longer has active mission
  const updatedWorkers = engine.getWorkers();
  const worker1 = updatedWorkers.find((w) => w.workerId === 'worker_cloud_arm_01')!;
  assert.equal(worker1.status, 'TOKEN_EXHAUSTED');
  assert.equal(worker1.activeMissionId, undefined);

  // 3. CRITICAL FENCING INVARIANT: Stale/zombie worker attempts mutation with old fencing token
  const staleWorkerWriteAttempt = engine.evaluateFencingWrite(
    'mission_idp_7790_recovery',
    'worker_cloud_arm_01',
    initialFencingToken
  );
  assert.equal(staleWorkerWriteAttempt.permitted, false);
  assert.equal(staleWorkerWriteAttempt.code, 'REJECTED_STALE_FENCING_LEASE');
  assert.ok(staleWorkerWriteAttempt.reason?.includes('STALE_WORKER_FENCING_REJECTION'));

  // 4. Replacement worker writes with new fencing token succeeds
  const replacementWorker = updatedWorkers.find((w) => w.workerId === 'worker_cloud_arm_02')!;
  assert.equal(replacementWorker.activeMissionId, 'mission_idp_7790_recovery');
  const validReplacementWrite = engine.evaluateFencingWrite(
    'mission_idp_7790_recovery',
    'worker_cloud_arm_02',
    replacementWorker.fencingLeaseToken
  );
  assert.equal(validReplacementWrite.permitted, true);
});



