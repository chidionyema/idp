/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * GEMINI — P0 Universal Agent Collaboration Recovery
 * Unit & Integration Tests (node:test)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import { createUniversalEnvelope, validateUniversalEnvelope } from './envelope';
import { NatsJetStreamTransport, AuthenticatedHttpsAdapter, GitPeerBoardEngine } from './transports';
import { TemporalContinuityEngine } from './temporalContinuity';
import { PatchExecutionPipeline } from './patchPipeline';
import { GreenlaneEvidenceBridge } from './greenlaneEvidenceBridge';
import { MultiAgentAcceptanceSuite } from './acceptanceSuite';
import { ESTATE_CAPABILITY_AUDIT, getAuditSummary } from './discovery';

describe('P0 Universal Agent Collaboration Recovery', () => {

  test('Phase 1: Rapid discovery audit reconciles all 10 estate capabilities', () => {
    assert.strictEqual(ESTATE_CAPABILITY_AUDIT.length, 10);
    const summary = getAuditSummary();
    assert.ok(summary.counts.LIVE >= 3);
    assert.ok(summary.counts.PARTIAL >= 4);
    assert.strictEqual(summary.counts.ABSENT, 1); // Argon PR #40 closed unmerged
    assert.ok(summary.operationalHealthScore > 50);
  });

  test('Phase 2: Universal agent envelope validates required semantics and rejects malformed fields', () => {
    const validEnv = createUniversalEnvelope({
      missionId: 'MSN-TEST-01',
      instructionId: 'INST-TEST-01',
      sender: {
        agent_id: 'gemini-executive-lead',
        provider: 'gemini',
        authenticated: true,
        role: 'Executive'
      },
      recipient: {
        agent_id: 'kimi-analyst-reader',
        provider: 'kimi',
        role: 'Analyst'
      },
      messageType: 'instruction',
      payload: { hello: 'world' }
    });

    const res = validateUniversalEnvelope(validEnv);
    assert.strictEqual(res.valid, true);
    assert.strictEqual(res.errors.length, 0);

    // Test rejection of unauthenticated sender
    const unauthEnv = {
      ...validEnv,
      sender: { ...validEnv.sender, authenticated: false }
    };
    const unauthRes = validateUniversalEnvelope(unauthEnv);
    assert.strictEqual(unauthRes.valid, false);
    assert.ok(unauthRes.errors.some(e => e.includes('Unauthenticated sender rejected')));
  });

  test('Phase 3: NATS JetStream handles ACKs, bounded redelivery and DLQ', () => {
    const nats = new NatsJetStreamTransport();
    const env = createUniversalEnvelope({
      missionId: 'MSN-NATS-TEST',
      instructionId: 'INST-NATS-01',
      sender: { agent_id: 'gemini-executive-lead', provider: 'gemini', authenticated: true, role: 'Lead' },
      recipient: { agent_id: 'worker-01', provider: 'system_executor', role: 'Worker' },
      messageType: 'instruction',
      payload: { task: 'compute' }
    });

    const pub = nats.publish(env);
    assert.strictEqual(pub.success, true);

    // Initial delivery
    const delivered1 = nats.deliver('consumer-01', 'worker-01');
    assert.strictEqual(delivered1.length, 1);

    // NAK until redelivery threshold (max 3) reached
    nats.negativeAcknowledge(env.message_id, 'Temporary worker glitch');
    nats.negativeAcknowledge(env.message_id, 'Temporary worker glitch 2');
    const finalNak = nats.negativeAcknowledge(env.message_id, 'Temporary worker glitch 3');
    assert.strictEqual(finalNak.routedToDlq, true);

    const dlq = nats.getDeadLetterQueue();
    assert.strictEqual(dlq.length, 1);
    assert.strictEqual(dlq[0].message_id, env.message_id);
  });

  test('Phase 3: Authenticated HTTPS adapter allows sandboxed agents to submit patches without git credentials', () => {
    const adapter = new AuthenticatedHttpsAdapter();
    const validToken = 'bearer_zai_sandboxed_token_99182';

    const patchEnv = createUniversalEnvelope({
      missionId: 'MSN-HTTPS-PATCH',
      instructionId: 'INST-ZAI-PATCH',
      sender: { agent_id: 'zai-sandboxed-agent-01', provider: 'zai', authenticated: true, role: 'Contributor' },
      recipient: { agent_id: 'gemini-executive-lead', provider: 'gemini', role: 'Executor' },
      messageType: 'patch_submission',
      payload: {
        patch_id: 'PATCH-ZAI-01',
        repo: 'chidionyema/idp',
        base_sha: 'e4f901c3',
        target_branch: 'master',
        commit_message: 'fix: patch via https',
        unified_diff: '--- a/file.ts\n+++ b/file.ts\n@@ -1 +1 @@\n+ test\n',
        files_changed: ['file.ts'],
        lines_added: 1,
        lines_deleted: 0,
        verification_commands: ['npm test']
      },
      leaseRef: {
        lease_id: 'L-ZAI-01',
        fenced_token: 1,
        owner: 'zai-sandboxed-agent-01',
        acquired_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
        heartbeat_interval_seconds: 60
      }
    });

    const submitRes = adapter.submitEnvelope(validToken, patchEnv);
    assert.strictEqual(submitRes.success, true);
    assert.ok(submitRes.receiptHash);

    // Verify receipt lookup by idempotency key
    const receipt = adapter.getReceipt(validToken, patchEnv.idempotency_key);
    assert.strictEqual(receipt.status, 'ACCEPTED_DURABLE');

    // Test rejection with invalid token
    const unauthRes = adapter.submitEnvelope('invalid_token', patchEnv);
    assert.strictEqual(unauthRes.success, false);
    assert.ok(unauthRes.error?.includes('UNAUTHORIZED'));
  });

  test('Phase 4: Temporal continuity triggers 600s stall recovery with monotonic fence tokens', () => {
    const temporal = new TemporalContinuityEngine();
    
    // Seeded mission MSN-COLLAB-2026-002 has elapsed 640s (>= 600s stall timeout)
    const recovered = temporal.evaluateAndRecoverStalledMissions('gemini-executive-lead');
    assert.ok(recovered.length >= 1);

    const recoveredMission = recovered.find(m => m.mission_id === 'MSN-COLLAB-2026-002');
    assert.ok(recoveredMission);
    assert.strictEqual(recoveredMission.status, 'STALLED_RECOVERED');
    assert.strictEqual(recoveredMission.current_executor, 'gemini-executive-lead');
    assert.strictEqual(recoveredMission.fenced_token, 2); // Monotonically incremented from 1 to 2

    // Verify stale lease validation: old token 1 must be rejected
    const staleValidation = temporal.validateFencedLease('MSN-COLLAB-2026-002', 1);
    assert.strictEqual(staleValidation.valid, false);
    assert.ok(staleValidation.error?.includes('STALE_FENCED_TOKEN'));

    // New token 2 must be valid
    const validValidation = temporal.validateFencedLease('MSN-COLLAB-2026-002', 2);
    assert.strictEqual(validValidation.valid, true);
  });

  test('Phase 5: Greenlane evidence bridge publishes sanitized projections and latest pointer', () => {
    const bridge = new GreenlaneEvidenceBridge();
    const latest = bridge.getLatestEvidence();
    assert.ok(latest);
    assert.strictEqual(latest.sanitized, true);
    assert.strictEqual(latest.payload.overall_status, 'DEGRADED');
    assert.ok(latest.payload.diagnostics.length > 0);
    assert.strictEqual(latest.payload.failure_class, 'GL-FAIL-042: Staged-Patch Working Tree Drift');
  });

  test('Phase 6: Multi-Agent Acceptance Suite passes all 8 mandatory scenarios', () => {
    const suite = new MultiAgentAcceptanceSuite();
    const results = suite.runAllScenarios();

    assert.strictEqual(results.length, 8);
    for (const res of results) {
      assert.strictEqual(res.status, 'PASS', `Scenario ${res.scenario_id} (${res.title}) failed: ${res.operational_evidence}`);
      assert.ok(res.verification_receipt_hash.length > 0);
      assert.ok(res.operational_evidence.length > 0);
    }
  });

});
