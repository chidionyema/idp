/**
 * Unit Tests for P0 Autonomous Science & Optimisation Lane
 * Runs via: npx tsx --test src/science/science.test.ts
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { assignVariant, evaluateExperiment } from './experimentEngine';
import {
  PRE_REGISTRATION_EXP_001,
  PRODUCTION_OBSERVATIONS,
  PRODUCTION_EVALUATION,
  PROMOTED_OPTIMISATION_RECORD
} from './productionExperiment';
import { runAllAdversarialScienceTests } from './adversarialTests';

test('pre-registration contains immutable hash and full operational contract', () => {
  assert.ok(PRE_REGISTRATION_EXP_001.registrationHash.startsWith('sha256:'));
  assert.equal(PRE_REGISTRATION_EXP_001.experimentId, 'EXP-2026-GENESIS-001');
  assert.equal(PRE_REGISTRATION_EXP_001.primaryMetric.name, 'cost_per_verified_yield');
  assert.equal(PRE_REGISTRATION_EXP_001.primaryMetric.minimumMeaningfulEffect, 0.35);
  assert.equal(PRE_REGISTRATION_EXP_001.guardrails.maxAllowedFailureRate, 0.05);
});

test('consistent hashing variant assignment is deterministic across repeated calls', () => {
  const unitA = 'pr-branch-checkout-101';
  const unitB = 'pr-branch-payment-202';

  const assignmentA1 = assignVariant(unitA, 25);
  const assignmentA2 = assignVariant(unitA, 25);
  assert.equal(assignmentA1, assignmentA2, 'Assignment must be stable for same unit');

  const assignmentB1 = assignVariant(unitB, 25);
  const assignmentB2 = assignVariant(unitB, 25);
  assert.equal(assignmentB1, assignmentB2);
});

test('production experiment evaluation calculates total cost per verified yield and promotes candidate', () => {
  const evaluation = PRODUCTION_EVALUATION;

  assert.equal(evaluation.sampleSizes.control, 60);
  assert.equal(evaluation.sampleSizes.candidate, 60);
  assert.ok(evaluation.metrics.control.costPerVerifiedYield > 0.5);
  assert.ok(evaluation.metrics.candidate.costPerVerifiedYield < 0.2);

  // Candidate cost per yield is significantly lower
  assert.ok(evaluation.comparison.deltaCostPerYieldPercent < -50);
  assert.equal(evaluation.comparison.exceedsMde, true);
  assert.equal(evaluation.comparison.failureDisplacementDetected, false);
  assert.equal(evaluation.decision, 'PROMOTE');
  assert.equal(evaluation.authorizedForPromotion, true);
  assert.equal(evaluation.postActivationMonitoringDays, 14);
});

test('failed executions remain in total cost and effectiveness denominator', () => {
  const control = PRODUCTION_EVALUATION.metrics.control;
  assert.ok(control.failedCount > 0, 'Control must have failures recorded');
  // Total cost includes failed execution costs
  const totalCost = PRODUCTION_OBSERVATIONS.filter((o) => o.variant === 'CONTROL').reduce(
    (sum, o) => sum + o.cost.totalCostUsd,
    0
  );
  assert.equal(control.totalCostUsd, Math.round(totalCost * 1000) / 1000);
  // Cost per yield divides total cost by verified yields (not total executions)
  assert.ok(
    Math.abs(control.costPerVerifiedYield - control.totalCostUsd / control.verifiedYieldCount) < 0.005,
    'costPerVerifiedYield must equal totalCost / verifiedYieldCount within rounding tolerance'
  );
});

test('all 10 mandatory adversarial science acceptance tests pass', () => {
  const advResults = runAllAdversarialScienceTests();
  assert.equal(advResults.length, 10);
  for (const res of advResults) {
    assert.equal(res.passed, true, `Adversarial test ${res.id} (${res.name}) must pass`);
  }
});

test('promoted optimisation record contains complete durable intelligence', () => {
  assert.equal(PROMOTED_OPTIMISATION_RECORD.decision, 'PROMOTE');
  assert.ok(PROMOTED_OPTIMISATION_RECORD.verifiedSavingsUsdPerYield > 0.4);
  assert.equal(PROMOTED_OPTIMISATION_RECORD.promotedConfigKey, 'flow.resolution.strategy');
  assert.equal(PROMOTED_OPTIMISATION_RECORD.monitoringWindowStatus, 'ACTIVE');
  assert.ok(PROMOTED_OPTIMISATION_RECORD.independentEvidenceReceipt.length > 10);
});
