/**
 * Unit Tests for Kimi Capability-First Estate Engine
 * Runs via: npx --yes tsx --test src/core/resolution.test.ts
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { ESTATE_CAPABILITIES } from './registry';
import { evaluateOperationalReadiness, matchCapabilityForInstruction, CallerContext } from './matcher';
import { resolveInstructionDecision } from './decision';
import { executeFlowLifecycle } from './flow';
import { BASELINE_20_INSTRUCTIONS, computeBaselineMetrics } from './baselineData';
import { ADVERSARIAL_TEST_CASES, runAdversarialTest } from './adversarial';
import { generateEconomicReport } from './economics';

const defaultCaller: CallerContext = {
  callerIdentity: 'argon-genesis-runner@argon.internal',
  permissions: ['*'],
  environment: 'production'
};

test('authoritative capability registry is populated and valid', () => {
  assert.ok(ESTATE_CAPABILITIES.length >= 15, 'Registry must contain estate capabilities');
  for (const cap of ESTATE_CAPABILITIES) {
    assert.ok(cap.id, 'Capability must have an ID');
    assert.ok(cap.authoritativeSource, 'Capability must reference authoritative source');
    assert.ok(cap.inputs.length > 0, 'Capability must define typed inputs');
    assert.ok(cap.outputs.length > 0, 'Capability must define typed outputs');
    assert.ok(cap.readinessEvidence, 'Capability must have readiness evidence');
  }
});

test('operational readiness classifier strictly adheres to evidence', () => {
  const verifiedCap = ESTATE_CAPABILITIES.find((c) => c.id === 'idp.db.migration-runner')!;
  const readiness = evaluateOperationalReadiness(verifiedCap);
  assert.equal(readiness, 'operationally_verified', 'High uptime and fresh healthcheck must yield operationally_verified');

  const staleCap = ESTATE_CAPABILITIES.find((c) => c.id === 'idp.infra.legacy-dns-updater')!;
  const staleReadiness = evaluateOperationalReadiness(staleCap);
  assert.equal(staleReadiness, 'degraded', 'Stale healthcheck or decommissioned flag must yield degraded');
});

test('matcher discovers correct capability for DB migration instruction', () => {
  const instruction = 'Execute safe zero-downtime database migration with rollback checkpoint verification on orders-db';
  const candidates = matchCapabilityForInstruction(instruction, defaultCaller);

  assert.ok(candidates.length > 0, 'Must discover at least one candidate');
  assert.equal(candidates[0].capability.id, 'idp.db.migration-runner');
  assert.equal(candidates[0].isReadinessVerified, true);
});

test('decision engine chooses REUSE for verified DB migration capability', () => {
  const instruction = 'Execute safe zero-downtime database migration with rollback checkpoint verification on orders-db';
  const candidates = matchCapabilityForInstruction(instruction, defaultCaller);
  const decision = resolveInstructionDecision(instruction, candidates);

  assert.equal(decision.decision, 'REUSE');
  assert.equal(decision.primaryCapabilityId, 'idp.db.migration-runner');
  assert.ok(decision.confidenceScore >= 0.9);
  assert.equal(decision.avoidedWorkHoursEstimate, 14);
});

test('decision engine identifies multi-domain composition intent as COMPOSE', () => {
  const instruction = 'Scan container image and deploy mesh canary routing rule with verification';
  const candidates = matchCapabilityForInstruction(instruction, defaultCaller);
  const decision = resolveInstructionDecision(instruction, candidates);

  assert.equal(decision.decision, 'COMPOSE');
  assert.ok(decision.composedCapabilityIds?.includes('idp.security.artifact-attestor'));
  assert.ok(decision.avoidedWorkHoursEstimate >= 20);
});

test('decision engine identifies estate gaps as IMPLEMENT_NEW without inventing capabilities', () => {
  const instruction = 'Cross-cloud multi-region active-active Spanner-to-DynamoDB bidirectional sync';
  const candidates = matchCapabilityForInstruction(instruction, defaultCaller);
  const decision = resolveInstructionDecision(instruction, candidates);

  assert.equal(decision.decision, 'IMPLEMENT_NEW');
  assert.equal(decision.avoidedWorkHoursEstimate, 0);
});

test('RBAC security boundary is strictly enforced and never weakened for reuse', () => {
  const restrictedCaller: CallerContext = {
    callerIdentity: 'unprivileged-agent',
    permissions: ['k8s:pods:get'],
    environment: 'production'
  };

  const instruction = 'Rotate AWS IAM session credentials and sync with Kubernetes Secret store';
  const candidates = matchCapabilityForInstruction(instruction, restrictedCaller);
  const decision = resolveInstructionDecision(instruction, candidates);

  assert.equal(candidates[0].permissionCheck.satisfied, false, 'RBAC check must fail');
  assert.equal(decision.compatibilityChecks.permissionsSatisfied, false);
  assert.notEqual(decision.decision, 'REUSE', 'Unprivileged caller must not be permitted direct REUSE');
});

test('FLOW lifecycle executes successfully and records verified yield', () => {
  const instruction = 'Provision ephemeral preview environment with isolated PostgreSQL and Redis for PR branch';
  const result = executeFlowLifecycle(instruction, defaultCaller);

  assert.equal(result.decision, 'REUSE');
  assert.equal(result.executionSuccess, true);
  assert.equal(result.steps.length, 6, 'FLOW must traverse all 6 lifecycle phases');
  assert.equal(result.yield.avoidedEngineeringHours, 18);
  assert.equal(result.yield.avoidedCostUsd, 2700);
});

test('Phase B baseline dataset contains exactly 20 records and accurate metrics', () => {
  assert.equal(BASELINE_20_INSTRUCTIONS.length, 20);
  const metrics = computeBaselineMetrics();

  assert.equal(metrics.capabilitiesExisted, 18);
  assert.equal(metrics.duplicateImplementations, 11);
  assert.ok(metrics.totalHoursWastedInBaseline > 100);
  assert.ok(metrics.totalAvoidedHoursPostChange > 150);
});

test('all 7 adversarial test cases pass security and contract boundaries', () => {
  assert.equal(ADVERSARIAL_TEST_CASES.length, 7);
  for (const testCase of ADVERSARIAL_TEST_CASES) {
    const res = runAdversarialTest(testCase);
    assert.equal(res.passed, true, `Adversarial test ${testCase.id} must pass`);
  }
});

test('economic report produces non-zero defensible savings', () => {
  const report = generateEconomicReport();
  assert.ok(report.reuseYieldMetrics.totalCostSavingsUsd > 20000);
  assert.equal(report.reuseYieldMetrics.duplicationAvoidedCount, 11);
  assert.ok(report.nextLeverageGap.projectedMonthlySavingsUsd > 10000);
});
