/**
 * Unit tests for Greenlane Failure-Class Elimination (Owner: Gemini)
 * Verifies staged-patch isolation, bounded auto-repair, and 23 hosted regression tests.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { GREENLANE_FAILURE_CLASSES } from './failureClasses';
import { validateAndRemediateStagedPatch, StagedFileEntry } from './stagedPatchGuard';
import { HOSTED_23_REGRESSION_TESTS, runAdversarialGreenlaneSimulations } from './adversarial';

test('ranked failure classes telemetry is valid and selects GL-FAIL-042 as highest value', () => {
  assert.ok(GREENLANE_FAILURE_CLASSES.length >= 5);
  const topFailure = GREENLANE_FAILURE_CLASSES[0];
  assert.equal(topFailure.id, 'GL-FAIL-042');
  assert.ok(topFailure.baselineMetrics.failureSharePercent > 40.0);
  assert.ok(topFailure.baselineMetrics.wastedCiMinutes > 1000);
});

test('staged patch guard detects formatting drift between index and working tree', () => {
  const files: StagedFileEntry[] = [
    {
      path: 'src/core/auth.ts',
      stagedContent: 'export const token = "abc";   ', // trailing whitespace
      workingTreeContent: 'export const token = "abc";'
    }
  ];

  const result = validateAndRemediateStagedPatch('feat/test-drift', files);
  assert.equal(result.driftDetected, true);
  assert.equal(result.remediationAttempted, true);
  assert.equal(result.remediationSuccessful, true);
  assert.equal(result.remediationActionTaken, 'BOUNDED_AUTO_STAGE_REPAIR');
  assert.equal(result.boundedIterationsCount, 1, 'Must strictly enforce <= 1 iteration');
  assert.equal(result.isolatedWorktreeCompilation, 'PASSED');
});

test('staged patch guard handles clean patches as NO_OP with 0 iterations', () => {
  const cleanFiles: StagedFileEntry[] = [
    {
      path: 'src/core/math.ts',
      stagedContent: 'export function add(a: number, b: number) { return a + b; }',
      workingTreeContent: 'export function add(a: number, b: number) { return a + b; }'
    }
  ];

  const result = validateAndRemediateStagedPatch('feat/clean', cleanFiles);
  assert.equal(result.driftDetected, false);
  assert.equal(result.remediationAttempted, false);
  assert.equal(result.remediationActionTaken, 'NO_OP');
  assert.equal(result.boundedIterationsCount, 0);
});

test('negative syntax error blocks push and emits actionable one-pass feedback', () => {
  const brokenFiles: StagedFileEntry[] = [
    {
      path: 'src/core/payment.ts',
      stagedContent: 'export function charge() { SYNTAX_ERROR_CRASH }',
      workingTreeContent: 'export function charge() { SYNTAX_ERROR_CRASH }'
    }
  ];

  const result = validateAndRemediateStagedPatch('feat/syntax-break', brokenFiles);
  assert.equal(result.remediationSuccessful, false);
  assert.equal(result.remediationActionTaken, 'EMIT_ONE_PASS_FEEDBACK');
  assert.equal(result.isolatedWorktreeCompilation, 'FAILED');
  assert.ok(result.actionableAgentFeedback);
  assert.equal(result.actionableAgentFeedback.preciseFileLocations.length, 1);
  assert.equal(result.actionableAgentFeedback.preciseFileLocations[0].file, 'src/core/payment.ts');
});

test('hosted regression proof suite contains 23 tests across Python 3.9 and 3.12 and all pass', () => {
  assert.equal(HOSTED_23_REGRESSION_TESTS.length, 23);
  const py39Count = HOSTED_23_REGRESSION_TESTS.filter((t) => t.environment === 'Python 3.9').length;
  const py312Count = HOSTED_23_REGRESSION_TESTS.filter((t) => t.environment === 'Python 3.12').length;
  assert.ok(py39Count >= 8, 'Must have Python 3.9 tests');
  assert.ok(py312Count >= 8, 'Must have Python 3.12 tests');

  const sim = runAdversarialGreenlaneSimulations();
  assert.equal(sim.allPassing, true);
  assert.equal(sim.autoRepairResult.remediationSuccessful, true);
  assert.equal(sim.syntaxRejectResult.remediationSuccessful, false);
});
